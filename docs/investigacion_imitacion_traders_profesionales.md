# Investigación: cómo funcionan los programas profesionales de imitación de traders — y qué lecciones aplican a SFEIA

> Documento de investigación y diagnóstico que guio la remediación. Proyecto: SFEIA · Fecha: 2026-09-09 ·
> Estado: **implementado** — las fases P0 (validez), P1 (política) y P2 (negocio) están en `sfeia.main`, y las
> soluciones S1–S3 (selección por margen relativo, barrido de combinaciones, alternativa recomendada) cierran el
> círculo: cuando una combinación no valida, el asistente encuentra dónde hay señal.
> Documentos relacionados: `docs/plan_agente_xxxc_asistente.md` (plan del asistente), `docs/informe_asistente_imitador.md` (salida), `docs/informe_barrido_combinaciones.md` (barrido).

---

## Resumen ejecutivo

La intuición de que "algo estamos haciendo mal" es correcta. El asistente actual es un Behavioral Cloning (BC) de los
top-N de un (segmento, estrategia), y hereda **tres fallas metodológicas de fondo** que la práctica profesional y la
literatura académica documentan ampliamente:

1. **Seleccionamos a los maestros por el mismo resultado que luego decimos "imitar", sin validar que esa selección
   generalice.** Elegir al top-N por la mediana del margen en la ventana de estudio es exactamente el sesgo de
   supervivencia / *hindsight* que la literatura de selección de gestores documenta: los ganadores pasados no
   se mantienen, y con 8 días y 4 agentes la selección es ruido puro.
2. **Clonamos una "recompensa" que es un artefacto de modelado.** El margen C16–C18 usa Pv=350 COP/kWh fijo y
   precios de sistema. En la salida actual **todos** los maestros tienen margen negativo y el "mejor" es el menos malo.
   BC es fiel: si la recompensa es un artefacto, la imitación reproduce el artefacto, no una habilidad.
3. **BC con un único estado (`spread`) y sin tratar el *distribution shift*.** El maestro actúa en su distribución de
   estados; XXXC actuará en otra. El "fallback a la mediana global" es el parche que la literatura de imitation
   learning muestra que falla. Además, usar el spread **del mismo día** puede ser *look-ahead*.

A estas tres se suman fallas importantes: es "Follow-the-Leader" puro (regret lineal, subóptimo en teoría de online
learning), no hay walk-forward, no hay corrección por múltiples pruebas (Deflated Sharpe / PBO), no hay métricas
ajustadas por riesgo, y no hay mecánica de réplica (capacidad, correlación entre maestros, kill-switch).

El documento: (1) describe cómo funcionan los programas profesionales, (2) diagnostica SFEIA contra ese estándar con
referencias `archivo:línea`, (3) traduce cada brecha a una lección accionable, y (4) propone un roadmap de remediación
en tres fases (P0 validez, P1 política, P2 negocio) con métricas y criterios de aceptación.

---

## 1. Cómo funcionan los programas profesionales de imitación

### 1.1 Copy trading / mirror trading / social trading (retail e institucional)

Fuente normativa de referencia: **IOSCO CR/10/2024** y **FR/06/2025** *"Online Imitative Trading Practices: Copy
Trading, Mirror Trading, Social Trading"* — encuesta global a reguladores (AFM, ASIC, ISA, etc.).

- **Definición.** *Copy trading*: replicar automáticamente las órdenes de uno o más *lead traders*. *Mirror trading*:
  mismo concepto pero **automatizado por algoritmos**, sin que el seguidor elija la operación individual. *Social
  trading*: seguimiento con componente social/comunitario.
- **Ciclo de réplica de una orden** (desde la documentación de vendors profesionales de copiers): (1) detección del
  *fill* del maestro → (2) *risk checks* por cuenta (whitelist de símbolos, límites de posición, límite diario de
  pérdida, drawdown) → (3) *sizing* de la orden del seguidor → (4) construcción y transmisión → (5) *matching* en el
  broker del seguidor → (6) confirmación. La latencia total (ms) es solo la optimización; el riesgo está en los pasos 2–3.
- **Sizing profesional** (tres familias):
  - *Fijo*: mismo lote siempre (pierde la convicción del líder).
  - *Proporcional a capital*: `tamaño = (capital_follower / capital_master) × tamaño_master`, con **tope absoluto por
    cuenta** y tope por operación; si el cálculo da cero, **se omite la operación**, no se fuerza un mínimo.
  - *Basado en riesgo*: `contratos = (balance × %riesgo) / (stop_en_puntos × valor_por_punto)` — ignora el tamaño del
    maestro y lo recalcula por operación con el *risk budget* propio.
  - (Predicción de mercados: *Kelly-scaled* = fracción de Kelly del borde implícito, con cap.)
- **Riesgos que un sistema serio gestiona explícitamente**:
  - **Riesgo correlacionado**: "replicar es lo opuesto a diversificar". N cuentas copiando al mismo líder son **una**
    posición de tamaño N con N kill-switches que se disparan a la vez; un drawdown en el líder golpea a todos
    simultáneamente. Hay *circuit breaker* de drawdown del portafolio agregado y *cooling-off*.
  - **Slippage/latencia**: el seguidor entra después del maestro; el borde del líder se captura parcialmente. Se exige
    que el borde por operación supere (comisión + slippage esperado); si no, no se replica.
  - **Capacidad**: si el maestro toma un % grande del libro, el espejo no se ejecuta sin slippage inaceptable → cap por
    profundidad de mercado.
  - **Sesgo de supervivencia del leaderboard**: los rankings que muestran solo a los sobrevivientes y que ordenan por
    retorno total (no por riesgo) empujan el capital hacia los más arriesgados/lucky.
  - **Alineación de incentivos y riesgo del líder** (apalancamiento, margen, liquidación): el seguidor replica la
    dirección, no el resultado.

### 1.2 Selección de "líderes"/gestores en allocators institucionales: skill vs luck

- **La persistencia del desempeño es débil en el corto plazo.** S&P *Persistence Scorecard*: los gestores en la mitad
  superior en un período de 5 años **repiten menos de lo que el azar predice (50%)**; a 1 año casi todos los top-half
  caen. Conclusión: el *outperformance* pasado corto es mayormente **suerte**, no habilidad.
- **Goetzmann–Ibbotson y la literatura de sesgo de supervivencia**: si solo miras a los sobrevivientes, parece que los
  ganadores repiten aunque no lo hagan. En CTAs (Handy & Meksi 2025, sobre el índice SocGen CTA 2000–2020): el 61 % de
  los programas del índice ya no existen; seleccionar el top por trailing return-to-risk **no produce retornos
  superiores** hacia adelante.
- **Separación estadística skill vs luck (bootstrap)**: Fama–French (2010) y Kosowski et al. (2006) comparan la
  sección cruzada real de alphas contra 10 000 simulaciones bootstrap; sin eso, no se puede decir que un top sea hábil
  o suertudo. El resultado típico: **pocos fondos cubren sus costos**; los extremos pueden tener alpha, pero es
  difícil identificarlo ex ante ("investable persistence" baja, sobre todo en VC).
- **Qué predice mejor**: el desempeño **en condiciones adversas** (*DownsideReturns*) predice el futuro mejor que el
  retorno incondicional; el retorno "upside" refleja más suerte. La **eficiencia** (costos de implementación) es más
  persistente que el "alpha bruto". Es decir: **rankea por consistencia y riesgo, no por retorno total**.

### 1.3 Behavioral Cloning / Imitation Learning (ML)

- **Definición.** BC = aprender la política `estado → acción` del experto por supervisión sobre demostraciones. Es el
  método más simple de imitation learning. Sus limitaciones conocidas:
  - **Distribution/covariate shift** (el problema #1): el BC entrena sobre la distribución de estados inducida por el
    *experto*; cuando la política aprendida actúa, visita su propia distribución de estados y los errores se **componen**
    (el error se acumula). Mitigaciones: DAgger (recolectar nuevas demostraciones en los estados que visita la política),
    SQIL (regularizar BC penalizando el *soft Bellman error* para volver a estados conocidos), DrilDICE (BC robusto a
    shift con corrección de distribución estacionaria).
  - **Causal confusion** (de Haan et al., NeurIPS 2019): BC no conoce la estructura causal; **más información puede
    empeorar** el desempeño si el modelo aprende correlaciones espurias (p. ej., clonar el *contexto del mismo día*
    puede aprender "predije ayer" en vez de "actúo hoy").
  - **Copycat problem** (Wen et al., NeurIPS 2020): en estados parcialmente observados con acciones correlacionadas en
    el tiempo, el imitador "copia" la acción anterior en vez de la siguiente.
  - **El experto puede ser subóptimo** (Stanford CS237b): BC no razona sobre recompensas ni intenciones; si el "experto"
    es en realidad un agente mediocre o con suerte, clona mediocridad.
- **Implicación para SFEIA**: la ventana de estudio **8 días / 4 agentes** genera exactamente los tres problemas:
  covariate shift (fallback a la mediana global), causal confusion (spread del día), y "experto subóptimo" (el menos
  malo de un ranking de artefactos).

### 1.4 Validación de estrategias: el estándar de los quants

- **Walk-forward (gold standard, Pardo 1992/2008).** Dividir la historia en ventanas rodantes *in-sample/out-of-sample*,
  optimizar parámetros solo en IS, evaluar solo en OOS, **coser los segmentos OOS en una sola curva** y exigir que el
  borde sobreviva a **múltiples regímenes** (p. ej., 34 períodos OOS en el framework de microestructura citado en
  referencias). Ningún resultado reportado debe provenir de datos usados para ajustar.
- **Múltiples pruebas y sesgo de selección (López de Prado; Harvey–Liu).** Seleccionar el mejor de N trials es una
  forma de *multiple testing*: la probabilidad de falso positivo crece con N. Correctores: **Deflated Sharpe Ratio**
  (DSR), **Probability of Backtest Overfitting** (PBO/CSCV), y el *haircut* de Harvey–Liu. Regla práctica citada: con
  ~3 trials "cualquier" estrategia parece significativa; con 100 trials y Sharpe bruto 2.0 el DSR cae a ~0.5.
- **Decaimiento OOS medido.** En estudios sobre cientos de estrategias publicadas: el retorno baja ~26 % OOS y ~58 %
  tras publicación; el Sharpe degrada 33–44 %. Regla práctica: un sistema sano conserva **50–70 %** del desempeño IS
  en OOS; si cae a cero, era ruido.
- **Disciplina de *point-in-time* y *information set*.** Prohibido usar datos futuros o de la ventana evaluada para
  decidir (look-ahead). Incluye el uso de probabilidades de régimen **filtradas** (no suavizadas con datos futuros).
- **Lección directa**: SFEIA usa **un solo split** estudio/impacto contiguo y **no cuenta trials**; la tabla de
  "robustez" (`maestros.sensibilidad`) re-rankea sobre la misma ventana, no es una prueba de generalización.

### 1.5 Agregación online de expertos (por qué NO elegir al "mejor" en hindsight)

- **Follow-the-Leader** (elegir al que mejor le fue hasta ahora) tiene **regret lineal** en el peor caso: inestable,
  cambia de experto bruscamente y no da garantías.
- **Hedge / Exponential Weights / Weighted Majority** (Littlestone–Warmuth; Vovk): mantiene un peso por experto,
  `w ← w·exp(−η·pérdida)`, y **agrega** en vez de elegir. Garantiza regret `O(√(T log N))` (y `O(log N)` con pérdidas
  exponencialmente cóncavas). **Cover's Universal Portfolios** es la versión continua (regret óptimo).
- **Implicación**: imitar un top-N discreto elegido por desempeño pasado es FTL. La alternativa robusta es **distribuir
  peso sobre muchos agentes** (o perfiles) y actualizarlo con el desempeño *en línea*; así no se apuesta todo a un
  maestro lucky.

### 1.6 Detección de regímenes de mercado

- Los mercados financieros alternan regímenes (calma/turbulencia, riesgo-on/off, seco/húmedo). Herramientas:
  **Hidden Markov Models** (Hamilton 1989; estados latentes con probabilidades de transición), **clustering de ventanas**
  (k-means/Wasserstein sobre momentos de retornos), *change-point detection*. La estrategia se **condiciona al régimen**
  y rota entre políticas por régimen.
- **Riesgo metodológico clave**: usar probabilidades de régimen **suavizadas** (con datos futuros) en vez de
  **filtradas** es look-ahead (lo advierte incluso la doc de *tradingstrategy.ai*). Para SFEIA, "escasez" debería ser
  un régimen **detectable ex ante** (señales de hidrología, embalses, aportes), no el bin del spread realizado.

---

## 2. Diagnóstico de SFEIA contra el estado del arte

Lectura del código actual: `sfeia/app/controllers/fase_asistente.py`, services `{contexto,maestros,clonacion,simulacion,diario}.py`,
config `asistente.yaml`, informe `docs/informe_asistente_imitador.md`.

| # | Práctica profesional | Implementación actual en SFEIA | Brecha |
|---|---|---|---|
| 1 | Validar que la **selección** generaliza (OOS) | Maestros = top-N por mediana del margen **dentro** de la ventana de estudio (`maestros.py:58`, `fase_asistente.py:129`) y se evalúan en una ventana de impacto contigua pero **sin** prueba de que la selección prediga (no hay holdout de la selección ni bootstrap) | **Crítica** |
| 2 | Separar skill de luck (bootstrap) | No existe. La "robustez" (`maestros.sensibilidad`) re-rankea la misma ventana con otros (top, min_dias) — no es significancia (`maestros.py:62`) | **Crítica** |
| 3 | Recompensa válida antes de imitar | Margen = artefacto C16–C18 con Pv=350 fijo (`kpi_cartera.py:17`); **todos** los márgenes del informe son negativos (`informe…md:25-28,107`) | **Crítica** |
| 4 | Tratar el distribution shift / causalidad del BC | Política = mediana del perfil por bin de spread (`clonacion.py:36`); contexto único = spread del **mismo día** (`fase_asistente.py:185`); fallback = mediana global (`clonacion.py:114`) | **Crítica** |
| 5 | Walk-forward y cuenta de trials | Un solo split estudio/impacto contiguo (`asistente.yaml:15-18`); sin DSR/PBO/haircut | Alta |
| 6 | Métrica ajustada por riesgo y consistencia | Ranking solo por mediana del margen (`maestros.py:58`); no hay Sortino/% pérdida/drawdown en la selección (sí en el informe, pero no en la selección) | Alta |
| 7 | No apostar todo al "mejor" en hindsight (agregación) | Top-N discreto elegido por desempeño pasado = Follow-the-Leader; sin pesos continuos ni actualización en línea | Alta |
| 8 | Gestión de réplica: capacidad, correlación, kill-switch | Se detectan duplicados (`maestros.detectar_duplicados`) pero **aún se cuentan** como maestros independientes (`fase_asistente.py:240`); sin límite de capacidad ni circuit breaker | Media |
| 9 | Contexto ex-ante (información disponible a la hora de decidir) | El contexto de decisión usa spread del día **realizado** (`fase_asistente.py:185`); la señal de escasez es `bolsa > precio_escasez` del mismo día (`contexto.py:38`) | Media |
| 10 | Rebalanceo / decay / re-selección periódica | Estático por ejecución; solo se recomienda "re-evaluar" en texto (`informe…md:160`) | Media |
| 11 | Régimen condicional (embalses/aportes/hidrología) | "Escasez" se mide solo por spread/bin histórico (`contexto.py:57`); no entra a la política de clonación | Media |
| 12 | Validación contra ground truth real | No hay ground truth externo (por decisión acordada: se mantiene el artefacto y se marca como pendiente) | Pendiente |

---

## 3. Lecciones accionables (una por brecha)

1. **L1 — Separar selección de evaluación.** La ventana de estudio debe poder **subdividirse**: entrenar la política con
   un sub-período y validar la *selección de maestros* en otro (holdout), o hacer walk-forward rodante. Nunca reportar
   como evidencia el desempeño de una selección hecha sobre los mismos datos.
2. **L2 — Bootstrap skill-vs-luck.** Re-muestrear la sección cruzada de márgenes (con reemplazo) y comparar el top-N
   real contra el top-N esperado por azar; reportar p-valor/percentil y *exigir* un umbral antes de llamar "maestros"
   a alguien.
3. **L3 — Arreglar la recompensa antes de imitar.** Si el margen es artefacto, que lo sea **igual para todos** y que la
   métrica de selección sea **relativa** al segmento y **ajustada por riesgo**, no el nivel absoluto de un modelo
   contable. Dejar explícito qué se optimiza y por qué es proxy de utilidad.
4. **L4 — Enriquecer y adelantar el estado, y acotar el fallback.** Usar contexto **ex-ante** (spread esperado/rezagado,
   nivel de embalses, precio de escasez proyectado, volatilidad, régimen hidrológico) y, para el *shift*, limitar el
   fallback con una **zona de confianza** (si el día está fuera de distribución, no actuar "por defecto" sino reducir
   exposición / avisar).
5. **L5 — Walk-forward + conteo de trials.** Convertir la ejecución en una serie de ventanas rodantes (o al menos un
   holdout de selección) y reportar DSR/PBO y el ratio de replicación IS→OOS. Criterio: conservar ≥ 50–70 % del IS.
6. **L6 — Ranking por riesgo.** Seleccionar maestros con una métrica tipo *Sortino / ratio margen-a-drawdown / % días
   ganadores / downside*, y documentar la dispersión (el "maestro" es una distribución, no una mediana).
7. **L7 — Agregar en vez de elegir.** Ponderar perfiles de varios maestros (o usar EWA sobre agentes) y actualizar los
   pesos con el desempeño observado en el impacto; así un maestro lucky no domina la política.
8. **L8 — Gestión de réplica.** Deduplicar maestros idénticos/correlacionados **antes** de contar el N; modelar
   capacidad (su demanda vs. profundidad del mercado de bolsa/contratos) y añadir *kill-switch* por drawdown agregado.
9. **L9 — Contexto sin look-ahead.** La decisión de un día debe usar solo información disponible **antes** de decidir
   (precio de contrato conocido, bolsa proyectada o del cierre anterior); documentar el *information set* por variable.
10. **L10 — Rebalanceo.** Re-seleccionar/re-ponderar con frecuencia (semanal/mensual) y penalizar el *decay* (peso que
    decae si el maestro deja de confirmar la política).
11. **L11 — Régimen hidrológico.** Incorporar embalses/aportes/hidrología como variable de contexto y de política; la
    escasez debe ser un régimen **anticipable**, no un bin del spread realizado.
12. **L12 — Ground truth.** Mantener el artefacto como métrica interna, pero definir un plan para validar contra datos
    de liquidación XM cuando existan.

---

## 4. Roadmap de remediación (fases)

> Orden propuesto: **P0 (validez) primero**, porque sin validez, ninguna mejora de la política es interpretable.
> Cada fase termina con pruebas y una ejecución de referencia del asistente.

### P0 — Validez (cambios de bajo riesgo, alto impacto)

| Tarea | Archivos | Entregable |
|---|---|---|
| P0.1 Holdout de selección: la ventana de estudio se divide en *sub-estudio* (elegir maestros) y *sub-validación* (comprobar que la selección generaliza) antes del impacto | `fase_asistente.py`, `asistente.yaml`, `maestros.py`, `entities.py` | Métrica: % de maestros del sub-estudio que siguen arriba en sub-validación |
| P0.2 Bootstrap skill-vs-luck de la sección cruzada de márgenes | `maestros.py` (nuevo service o función pura) | p-valor/percentil del top-N vs. azar; umbral configurable |
| P0.3 Deduplicar maestros correlacionados (correlación de series diarias > umbral ⇒ un solo maestro) | `maestros.py`, `fase_asistente.py` | N efectivo reportado; los duplicados no inflan el top |
| P0.4 Métricas de riesgo en la selección (Sortino / margen-a-drawdown / % días pérdida / downside) además de la mediana | `maestros.py`, `entities.py`, `informe_asistente_md.py` | Ranking maestro con tabla de riesgo |
| P0.5 Reportar DSR/PBO aproximado (contar trials: agentes × estrategias × configs probadas) y ratio de replicación IS→OOS | `simulacion.py`, `informe_asistente_md.py` | Columnas nuevas en el informe |

**Criterio de aceptación P0:** la selección de maestros pasa el bootstrap (p<0.05) o se reporta explícitamente como
no significativa; los maestros duplicados no cuentan; el informe muestra riesgo y replicación IS→OOS.

### P1 — Política (el núcleo del BC)

| Tarea | Archivos | Entregable |
|---|---|---|
| P1.1 Contexto ex-ante: definir `information_set` (contrato conocido; bolsa rezagada/proyectada; embalses; precio de escasez proyectado; volatilidad) y eliminar el look-ahead del spread del día | `contexto.py`, `fase_asistente.py`, `sql/d1_diario.sql` (o nueva query de contexto) | Doc de variables y disponibilidad temporal |
| P1.2 Agregación ponderada en vez de top-N discreto: pesos por desempeño ajustado a riesgo + decaimiento temporal, actualizables | `clonacion.py`, `maestros.py`, `entities.py` | Política = distribución de perfiles ponderada (no solo mediana del top-N) |
| P1.3 Zona de confianza del estado: si el día cae fuera de la distribución de entrenamiento, reducir exposición / abstenerse en vez del fallback ciego | `clonacion.py`, `simulacion.py` | Bandas de validez por bin; comportamiento de "no operar" documentado |
| P1.4 Régimen hidrológico como variable de política (embalses/aportes por agente de demanda, o proxy disponible en elecdb) | `contexto.py`, `asistente.yaml` | Bin/flag de régimen que alimenta la política |

**Criterio de aceptación P1:** la política no usa información futura (revisión manual de `information_set`); el fallback
solo actúa dentro de zonas con datos; los pesos de los maestros se actualizan con el desempeño del impacto.

### P2 — Negocio (ejecutabilidad y decisión)

| Tarea | Archivos | Entregable |
|---|---|---|
| P2.1 Capacidad: tope de volumen de la imitación vs. profundidad del mercado (dema del segmento como proxy) y garantías acordes | `simulacion.py`, `informe_asistente_md.py` | Límite de capacidad en el resumen |
| P2.2 Kill-switch por drawdown agregado del período simulado | `simulacion.py`, `entities.py` | Regla: si drawdown > umbral ⇒ "no operar / reducir" en el veredicto |
| P2.3 Re-selección periódica explícita (ventana de estudio rodante) y reporte de decay | `fase_asistente.py`, CLI | Modo "walk-forward" como variante del CLI |
| P2.4 Validación contra ground truth real (pendiente de disponibilidad de liquidaciones XM) | — | Plan de validación documentado |

**Criterio de aceptación P2:** la recomendación de negocio incluye capacidad, kill-switch y re-selección; el CLI
permite correr la serie de ventanas rodantes de un clic.

---

## 5. Métricas y criterios de aceptación (transversales)

- **Replicación IS→OOS**: la política conserva ≥ 50–70 % del desempeño del estudio en el impacto (si el margen es
  artefacto, aplicar la métrica *relativa* al segmento, no absoluta).
- **Significancia de la selección**: el top-N real supera el percentil 95 del bootstrap de la sección cruzada; si no,
  el informe lo dice en rojo y la decisión de negocio se degrada a "no operar".
- **Sin look-ahead**: el `information_set` de cada decisión es documentado y auditable en el informe.
- **N efectivo de maestros**: reportado (post-deduplicación) y usado en advertencias.
- **Frecuencia de errores claros**: las nuevas validaciones fallan con mensaje explícito (estilo actual `_validar_fechas`).
- **Tests**: `pytest` verde en cada fase (`sfeia/tests/test_asistente.py` y nuevos casos para bootstrap/dedup/riesgo).

---

## 6. Riesgos y limitaciones (de la remediación)

1. El margen C16–C18 seguirá siendo artefacto mientras no haya ground truth (acordado). Las métricas de riesgo mitigan
   pero no eliminan el problema: **ninguna ingeniería estadística convierte un premio roto en uno válido**.
2. Los datos de elecdb terminan en **2026-07-31**; las series largas (2015→hoy) solo cubren precios de sistema, no
   comportamientos por agente → el bootstrap y el walk-forward están limitados en longitud para estrategias diarias.
3. No hay precio ni contraparte por agente en contratos: la "acción" clonada (perfil de abastecimiento) no incluye
   decisiones de precio de contrato; la réplica es parcial por construcción.
4. El contexto hidrológico (embalses/aportes) puede no estar disponible en la granularidad que el motor necesita;
   P1.4 depende de una exploración de datos (tarea a incluir).
5. La agregación ponderada (P1.2) reduce el riesgo de un maestro lucky pero **aumenta el turnover** de la política y la
   complejidad interpretativa (trade-off frente a la filosofía "determinista e interpretable" del plan actual).

---

## 7. Referencias

**Copy/mirror/social trading y riesgo de réplica**
- IOSCO, *Online Imitative Trading Practices* — CR/10/2024 (reporte de consulta) y FR/06/2025 (reporte final): https://www.iosco.org/library/pubdocs/pdf/IOSCOPD776.pdf y https://www.iosco.org/library/pubdocs/pdf/IOSCOPD793.pdf
- Thor/Phoenix Technologies, *The Copy Trading Latency Budget* y *Multi-Account Copy Trading: Fill Sync, Slippage and Correlated Risk*: https://thortradecopier.com/blog/copy-trading-latency-budget-end-to-end y https://thortradecopier.com/blog/multi-account-copy-trading-sync-slippage-risk
- Thor, *Copy Trading Sizing Methods* (fijo/proporcional/riesgo): https://thortradecopier.com/blog/copy-trading-position-sizing-methods
- BitMEX blog, *How Does Copy Trading Work* y *Copy Trading Derivatives Risk* (sizing proporcional, margen, liquidación): https://www.bitmex.com/blog/how-does-copy-trading-work y https://www.bitmex.com/blog/copy-trading-derivatives-risk
- Nurp, *The Hidden Risks of Copy Trading* (leaderboards, sesgo de supervivencia, apalancamiento): https://nurp.com/wisdom/the-hidden-risks-of-copy-trading-what-they-dont-tell-you
- CoinMarketMan, *Don't Mirror Whales 1:1* (sizing por cohortes, drawdown limits, kill switches): https://coinmarketman.com/blog/copy-trading-risk-management-position-sizing-by-wallet-cohort--en

**Selección de gestores: skill vs luck y sesgo de supervivencia**
- Handy & Meksi (2025), *Blinded By Bias: Hindsight and Survivorship Biases in Managed Futures* (J. Wealth Management), resumido en Alpha Architect: https://alphaarchitect.com/survivorship-biases
- Goetzmann & Ibbotson, *Survivorship Bias in Performance Studies* (Oxford Academic): https://academic.oup.com/book/52483/chapter/421376585
- S&P Global, *U.S. Persistence Scorecard* (resumen en Index Fund Advisors): https://www.ifa.com/articles/persistence-active-fund-management-performance
- Fama & French (2010), *Luck versus Skill in the Cross-Section of Mutual Fund Returns* (J. Finance): https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2010.01598.x
- Kosowski, Timmermann, Wermers & White (2006), *Can Mutual Fund "Stars" Really Pick Stocks?* (bootstrap de alphas).
- Korteweg & Sorensen (2014), *Skill and Luck in Private Equity Performance* (persistencia vs. "investable persistence", VC necesita ~25 fondos): https://www.gsb.stanford.edu/faculty-research/working-papers/skill-luck-private-equity-performance
- *Only Winners in Tough Times Repeat* (desempeño downside como predictor, Fed): https://www.federalreserve.gov/econresdata/feds/2016/files/2016030pap.pdf

**Behavioral Cloning / Imitation Learning**
- Stanford CS237b, *Imitation Learning* (BC, distribution mismatch, DAgger): https://web.stanford.edu/class/cs237b/pdfs/lecture/lecture_10111213.pdf
- de Haan, Jayaraman & Levine, *Causal Confusion in Imitation Learning* (NeurIPS 2019): https://arxiv.org/abs/1905.11979
- Wen et al., *Fighting Copycat Agents in Behavioral Cloning from Observation Histories* (NeurIPS 2020): https://papers.nips.cc/paper/2020/hash/1b113258af3968aaf3969ca67e744ff8-Abstract.html
- Reddy, Dragan & Levine, *SQIL: Imitation Learning via Regularized Behavioral Cloning* (arXiv:1905.11108): https://arxiv.org/abs/1905.11108
- Seo et al., *Mitigating Covariate Shift in Behavioral Cloning via DrilDICE* (NeurIPS 2024): https://proceedings.neurips.cc/paper_files/paper/2024/hash/c556da88a2665e6266453d8c9b8a552d-Abstract-Conference.html
- Lin, *Behavioral Cloning and Imitation Learning* (Springer, 2025; DAgger/BCDR): https://link.springer.com/chapter/10.1007/978-3-031-53720-2_7

**Validación de estrategias y backtest overfitting**
- Bailey & López de Prado, *The Deflated Sharpe Ratio* (J. Portfolio Management): http://davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* (CSCV/PBO).
- Harvey & Liu, *Backtesting* (haircut de Sharpe por múltiples pruebas; SSRN 2345489): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489
- Walk-forward con doble OOS (arXiv 2602.10785) y con microestructura + 34 OOS (arXiv 2512.12924): https://arxiv.org/pdf/2602.10785 y https://arxiv.org/pdf/2512.12924v1
- PickMyTrade, *Walk-Forward Optimization: Why 90% of Backtests Fail* (decaimiento OOS ~26 %/58 %; Sharpe −33/44 %): https://blog.pickmytrade.trade/walk-forward-optimization-backtesting
- GitHub `OutOfSampleLab/oos-lab` (PSR, DSR, PBO/CSCV, walk-forward): https://github.com/OutOfSampleLab/oos-lab

**Agregación online de expertos**
- Littlestone & Warmuth (1994), *Weighted Majority*; Vovk (1990), *Aggregating Strategy*.
- Cesa-Bianchi & Lugosi (2006), *Prediction, Learning, and Games* (EWA, regret).
- Hazan, *Online Learning Algorithms* (FTL/FTRL; FTL inestable): https://par.nsf.gov/servlets/purl/10208409
- Cover (1991), *Universal Portfolios*.
- Oxford CLT, *Online Learning with Expert Advice* (Hedge vs. Follow-the-Leader): https://www.cs.ox.ac.uk/people/varun.kanade/teaching/CLT-MT2021/lectures/lecture11.pdf

**Detección de regímenes**
- Hamilton (1989), *A New Approach to the Economic Analysis of Nonstationary Time Series* (Markov switching).
- *A Hybrid Learning Approach to Detecting Regime Switches in Financial Markets* (PCA + k-means + clasificación): https://arxiv.org/pdf/2108.05801
- *Structural Clustering of Volatility Regimes for Dynamic Trading Strategies*: https://arxiv.org/pdf/2004.09963
- Werge, *Predicting Risk-adjusted Returns using an Asset Independent Regime-switching Model* (HMM sticky): https://arxiv.org/pdf/2107.05535v1
- Advertencia sobre look-ahead en probabilidades suavizadas de HMM: https://tradingstrategy.ai/docs/learn/market-regimes.html

---

## 8. Veredicto y siguiente paso

El asistente actual **no está mal implementado, está mal planteado metodológicamente**: clona fielmente un ranking de
ruido medido con un premio-artefacto, sin validación de selección ni walk-forward. La remediación empieza por **P0
(validez)**, no por más features ni mejor ML. Este documento es la base; la implementación se decide tras su revisión.