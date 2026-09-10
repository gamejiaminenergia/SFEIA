# Asistente imitador del agente XXXC — Behavioral Cloning del top-N

> Clona el comportamiento del top-10 de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en la ventana de estudio y lo replica en la ventana de impacto. Metodología: `docs/plan_agente_xxxc_asistente.md`.

> **Advertencia (léela antes que nada):** esto es un **ejercicio descriptivo sobre comportamiento pasado** con un margen de **modelado** (Pv=350 COP/kWh fijo, precios promedio de sistema). Los márgenes aquí son artefactos matemáticos para comparar estrategias entre sí, **no dinero real ni una recomendación de inversión**. No sustituye análisis financiero, regulatorio ni legal.

## 1. Parámetros

**Contexto de decisión (P1):** spread del día anterior = sí (sin look-ahead) · factor de exposición fuera de distribución = 0.50 · régimen hidrológico = sí.

| Parámetro | Valor |
|---|---|
| Segmento | PEQUEÑO |
| Estrategia a imitar | Trader expuesto a bolsa (sin cobertura) |
| Top de maestros | 10 |
| Demanda diaria de XXXC (GWh) | 0.20 |
| Presencia mínima en la estrategia | 20 % de los días |
| Ventana de estudio (define maestros) | 2026-04-26 → 2026-07-22 |
| Sub-validación (holdout) | 2026-07-23 → 2026-07-24 |
| Ventana de impacto (evalúa imitación) | 2026-07-25 → 2026-07-31 |

## 2. Maestros — top 10 del segmento en la ventana de estudio

Ranking de agentes por mediana del margen diario dentro de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en 2026-04-26 → 2026-07-22 (estudio de 65 agentes, 88 días, k=5).

| Pos. | Código | Comercializador | Días en la estrategia | Mediana margen (COP/kWh) | Media margen | Mediana relativa (COP/kWh) | % días > segmento | % días pérdida | Drawdown máx. (COP/kWh acum.) | Mediana días malos (COP/kWh) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TRPC | TERMOPIEDRAS S.A. E.S.P. | 70 | -305.21 | -285.42 | -58.38 | 28.60 | 87.10 | 20 170.33 | -402.50 |
| 2 | HIMC | GESTION ENERGETICA S.A. E.S.P. | 88 | -331.93 | -299.17 | -88.47 | 28.40 | 89.80 | 26 493.59 | -387.07 |
| 3 | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 88 | -345.52 | -306.44 | -92.67 | 23.90 | 89.80 | 27 157.79 | -402.50 |
| 4 | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 88 | -345.52 | -306.44 | -92.67 | 23.90 | 89.80 | 27 157.79 | -402.50 |

> **Selección por margen relativo al segmento** (S1): el ranking usa la *mediana relativa* (margen del agente − mediana del segmento el mismo día), que cancela el artefacto Pv=350. La mediana absoluta se reporta como contexto.

**Robustez de la selección** (misma ventana de estudio, otras configuraciones de top y presencia):

| min. días en estrategia | top-8 | top-10 | top-12 |
|---|---|---|---|
| 10 % | ESOC, TRPC, HIMC, RPEC, VICC | ESOC, TRPC, HIMC, RPEC, VICC | ESOC, TRPC, HIMC, RPEC, VICC |
| 20 % | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC |
| 30 % | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC |

> ⚠️ **Maestros con comportamiento idéntico o correlacionado**: HIMC y RPEC y TRPC y VICC; HIMC y TRPC. Contarlos como 'independientes' infla el top-N (ver N efectivo en la sección de validez).

## 3. Validez de la selección (¿los maestros son hábiles o suertudos?)

Tres pruebas separan la selección del ruido: **bootstrap skill-vs-luck** (¿el mejor maestro supera al azar?), **holdout** (¿la selección hecha en sub-estudio se sostiene en la sub-validación?) y **DSR** (¿el resultado de la imitación resiste la corrección por múltiples pruebas?). La **replicación IS→OOS** mide cuánto del desempeño del estudio se conserva en el impacto.

| Prueba | Métrica | Valor | Pasa |
|---|---|---|---|
| Bootstrap skill-vs-luck | p-valor | 0.5824 | no |
|  | Mejor maestro real (COP/kWh) | -58.38 |  |
|  | Nulo p50 / p95 (COP/kWh) | -58.38 / -36.41 |  |
|  | Candidatos rankeados (trials) | 4 |  |
| Holdout (sub-estudio → sub-validación) | % de maestros que siguen en la mitad superior | — | <50 % (azar) |
|  | Mediana del percentil de los maestros | — |  |
| Replicación IS→OOS | mediana imitación estudio / impacto (COP/kWh) | -352.98 / -419.05 | 1.19 |
|  | Criterio de sistema sano | ≥ 50–70 % |  |
| DSR (corrige múltiples pruebas) | Sharpe diario -3.461 · skew -1.40 · kurt 3.98 | 0.000 | no |

N efectivo de maestros (tras deduplicar correlacionados): **1** de 4.

## 4. Política de clonación (contexto → perfil de abastecimiento)

Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los maestros cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.

| Contexto (spread bolsa−contrato) | Rango (COP/kWh) | Días de entrenamiento | Cobertura contratos | Exposición bolsa | No regulado | SICEP |
|---|---|---|---|---|---|---|
| muy_barata | -999 999–0 | 48 | 1% | 99% | 59% | 0% |
| barata | 0–200 | 82 | 1% | 99% | 59% | 0% |
| neutral | 200–400 | 92 | 1% | 99% | 59% | 0% |
| cara | 400–600 | 109 | 1% | 99% | 59% | 0% |
| escasez | 600–999 999 | 3 | 2% | 98% | 29% | 0% |

> **Agregación ponderada** (P1.2): el perfil por bin combina a los maestros con pesos (TRPC: 0.42, HIMC: 0.24, RPEC: 0.17, VICC: 0.17) en vez de elegir un top-N duro. Los pesos premian superar la mediana del segmento.

> **Zona de confianza** (P1.3): la política fue entrenada con spreads en [-140, 625] COP/kWh. Un día fuera de ese rango reduce su exposición a bolsa (trasladándola a contratos) en vez de clonar a ciegas.

> **Fallback** (mediana global del estudio, para contextos sin datos): cobertura 1 %, exposición 99 %, no regulado 59 %, SICEP 0 %.

## 5. Escenarios de estrés (sintéticos — la ventana no tuvo estos días)

La ventana de impacto puede no contener días de bolsa cara/escasez. Estos escenarios **sintéticos** responden: ¿qué pasa con la imitación si mañana la bolsa se dispara? Se construyen con el perfil que la política asignaría en ese contexto.

| Escenario | Descripción | Bolsa (COP/kWh) | Contratos (COP/kWh) | Spread | Bin | Margen (COP/kWh) | Garantía (COP) |
|---|---|---|---|---|---|---|---|
| escasez_umbral | Bolsa en el precio de escasez | 906.1 | 323.9 | 582.2 | cara | -633.19 | 45 647 448 |
| escasez_extrema | Bolsa 25 % sobre el precio de escasez | 1 132.7 | 323.9 | 808.8 | escasez | -852.47 | 56 767 924 |

## 6. Frecuencia histórica de escasez (todo el histórico de la BD)

Con 4230 días de histórico (2015 → límite de datos), la escasez real (bolsa > precio de escasez) ocurre el **10.64 %** de los días, y el contexto en que la política de clonación **no tiene datos** (spread > 600, bin 'escasez') es raro pero existe. Cuando ocurre, la sección 4 muestra pérdidas de **−520 a −715 COP/kWh/día**.

| Contexto (spread) | Días históricos | % del histórico |
|---|---|---|
| muy_barata | 2209 | 52.22 |
| barata | 1206 | 28.51 |
| neutral | 374 | 8.84 |
| cara | 194 | 4.59 |
| escasez | 247 | 5.84 |

| Métrica | Valor |
|---|---|
| Días con escasez real (bolsa > precio de escasez) | 450 de 4230 (10.64 %) |
| Spread p50 (COP/kWh) | -8.80 |
| Spread p95 (COP/kWh) | 639.50 |
| Spread p99 (COP/kWh) | 1 075.50 |
| Spread máximo (COP/kWh) | 2 182.70 |

**Por año:**

| Año | Días | Días de escasez | % del año |
|---|---|---|---|
| 2015 | 365 | 109 | 29.90 |
| 2016 | 366 | 103 | 28.10 |
| 2017 | 365 | 0 | 0.00 |
| 2018 | 365 | 0 | 0.00 |
| 2019 | 365 | 0 | 0.00 |
| 2020 | 366 | 39 | 10.70 |
| 2021 | 365 | 0 | 0.00 |
| 2022 | 365 | 0 | 0.00 |
| 2023 | 365 | 77 | 21.10 |
| 2024 | 366 | 103 | 28.10 |
| 2025 | 365 | 0 | 0.00 |
| 2026 | 212 | 19 | 9.00 |

## 7. Distribución de márgenes en el impacto (riesgo)

Medidas de la serie diaria de márgenes. **p5** es un día malo, **% días con pérdida** la frecuencia de pérdidas, **drawdown máximo** la peor caída pico→valle acumulada del período.

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Días | 7 | 5 | 7 |
| Mediana (COP/kWh) | -419.05 | -423.37 | 83.28 |
| Media (COP/kWh) | -438.59 | -443.78 | 88.02 |
| p5 (COP/kWh) | -703.76 | -500 | 46.98 |
| p95 (COP/kWh) | -307.61 | -388.68 | 127.05 |
| % días con pérdida | 100.00 | 100.00 | 0.00 |
| Peor día (COP/kWh) | -703.76 | -500 | 46.98 |
| Mejor día (COP/kWh) | -307.61 | -388.68 | 127.05 |
| Drawdown máximo (COP/kWh acum.) | 3 070.14 | 2 218.89 | 0.00 |

> **Lectura:** la imitación logra una mediana de **-419.1 COP/kWh/día** frente a **-423.4** de sus maestros reales y **83.3** del segmento, con **100.00 % de días en pérdida** y un drawdown de **3070.1 COP/kWh** acumulados en el período. El margen es un artefacto de modelado; solo sirve para comparar entre sí.

## 8. Simulación día a día (2026-07-25 → 2026-07-31)

XXXC replica cada día el perfil recomendado y se calcula su margen y garantía estimada con la misma lógica del estudio (C16–C18 sobre precios de sistema). Se compara contra la mediana real de los maestros y del segmento ese día. **En distribución** indica si el spread del día cae dentro del rango entrenado (si no, la exposición a bolsa se redujo — P1.3); **Embalses** es el nivel agregado del SIN (P1.4).

| Fecha | Contexto | Escasez | En distribución | Embalses (%) | Cobertura | Exposición | Margen imitación | Mediana maestros | Mediana segmento | Garantía (COP) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-25 | neutral | no | sí | 80.60 | 1% | 99% | -419.05 | -388.68 | 127.05 | 34 787 208 |
| 2026-07-26 | neutral | no | sí | 80.80 | 1% | 99% | -307.61 | — | 83.28 | 29 135 727 |
| 2026-07-27 | neutral | no | sí | 80.70 | 1% | 99% | -365.98 | — | 116.08 | 32 096 219 |
| 2026-07-28 | neutral | no | sí | 80.40 | 1% | 99% | -437.59 | -406.84 | 83.40 | 35 727 887 |
| 2026-07-29 | neutral | no | sí | 80.30 | 1% | 99% | -452.78 | -423.37 | 82.04 | 36 497 978 |
| 2026-07-30 | neutral | sí | sí | 80.20 | 1% | 99% | -703.76 | -500 | 46.98 | 49 226 241 |
| 2026-07-31 | escasez | sí | **no** | 80.00 | 51% | 49% | -383.37 | -500 | 77.34 | 32 977 969 |

## 9. Balance del impacto

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Mediana margen (COP/kWh) | -419.05 | -423.37 | 83.28 |
| Media margen (COP/kWh) | -438.59 | — | — |
| % días que la imitación gana | — | 20.00 | 0.00 |
| Replicación IS→OOS (ratio estudio→impacto) | 1.19 | — | — |
| DSR (corregido por múltiples pruebas) | 0.000 (no) | — | — |

Garantía estimada por día (COP): mediana **34 787 208**  máximo **49 226 241**. Demanda simulada: **202 942 kWh** (0.203 GWh).

## 10. Advertencias y limitaciones

1. El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para comparar estrategias, no como margen real del negocio.
2. Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin entrenamiento se resuelven con el bin más cercano y los días fuera del rango entrenado reducen su exposición a bolsa (zona de confianza).
3. La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.
4. Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.
5. No existe ground truth real (liquidaciones XM) para validar el margen: la validación externa queda pendiente (P2.4 del plan de investigación).
6. Solo se encontraron 4 agentes en el (segmento, estrategia) de la ventana de estudio; el top pedido era 10.
7. N efectivo de maestros: 1 de 4 (hay maestros con comportamiento correlacionado/duplicado que no suman información independiente).
8. La selección del top-10 NO supera el bootstrap skill-vs-luck (p=0.5824 > 0.05): el 'mejor maestro' es indistinguible del azar. No operar sin más evidencia.
9. DSR ≈ 0.00 (< 0.95) con 4 trials: el resultado de la imitación puede ser producto de la selección por azar.
10. KILL-SWITCH activado: el drawdown acumulado (3070 COP/kWh) supera el umbral (500 COP/kWh).
11. La combinación objetivo NO pasó la validez (bootstrap/holdout/replicación/N efectivo). Alternativa recomendada: **PEQUEÑO · Integrado/regional regulado** (relativo 152.3 COP/kWh).

## 11. Alternativa recomendada (la combinación pedida no validó)

El objetivo **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** no superó las pruebas de validez. La mejor alternativa del mismo estudio es **PEQUEÑO · Integrado/regional regulado** (maestros: ESOC, ASCC, CETC, CQTC, EGVC), con mediana relativa de **152.35 COP/kWh** por encima de su segmento.

| Métrica | Valor |
|---|---|
| Mediana margen imitación (COP/kWh) | -61.75 |
| Mediana maestros (COP/kWh) | 227.50 |
| Mediana segmento (COP/kWh) | 83.28 |
| % días que la imitación gana al segmento | 0.00 |
| Replicación IS→OOS | 1.06 |
| Garantía mediana (COP) | 16 667 410 |

Perfil alternativo (fallback): cobertura **100 %**, exposición bolsa **0 %**, no regulado **0 %**, SICEP **95 %**.

## 12. Decisiones de negocio para el agente XXXC

Resumen ejecutivo para **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en el período planteado (estudio 2026-04-26 → 2026-07-22; impacto 2026-07-25 → 2026-07-31):

- **Perfil a replicar:** compra **99 % de tu demanda en bolsa** y **1 % en contratos**, con mix **59 % no regulado** y **0 % SICEP** (perfil mediano de los maestros).
- **Capital para operar:** constituye garantías por al menos **49 226 241 COP/día** (mediana **34 787 208 COP**).
- **Pérdida en un día de escasez:** si la bolsa toca el precio de escasez pierdes **128 500 617 COP** en un día (173 001 660 COP si la supera 25 %), sobre tu demanda simulada de 0.203 GWh/día.
- **Expectativa de negocio:** con la frecuencia histórica de escasez (10.64 % de los días) tu beneficio esperado es **-441.83 COP/kWh/día**; en un año Niño (25 % de escasez) baja a **-472.59 COP/kWh/día**.
- **Kill-switch (activado):** el drawdown acumulado del período **3 070.14 COP/kWh** supera el umbral: **no operar** la estrategia imitada sin rediseño.
- **Capacidad:** la demanda simulada de XXXC (202,942 kWh/día) es el **1.6 %** de la demanda mediana del segmento (5 % = umbral): dentro del límite.
- **Regla de protección:** define un límite/cobertura cuando el spread bolsa−contrato se acerque a 600 COP/kWh (contexto 'escasez'): ahí la política no tiene datos de entrenamiento y el perfil imitado (sin cobertura) es el que más pierde.
- **Re-evaluación:** el top de maestros es pequeño y con comportamientos duplicados; no operes con datos de un solo período. Revisa esta decisión cada ventana (modo `--walk-forward`).

**Veredicto:** KILL-SWITCH: el drawdown acumulado del período simulado (3,070 COP/kWh) supera el umbral (500 COP/kWh). NO operar la estrategia imitada sin rediseñar el perfil o reducir la exposición.
