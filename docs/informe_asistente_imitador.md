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
| Demanda diaria de XXXC (GWh) | 0.26 |
| Presencia mínima en la estrategia | 20 % de los días |
| Ventana de estudio (define maestros) | 2025-06-25 → 2025-07-22 |
| Sub-validación (holdout) | 2025-07-23 → 2025-07-24 |
| Ventana de impacto (evalúa imitación) | 2025-07-25 → 2025-07-31 |

## 2. Maestros — top 10 del segmento en la ventana de estudio

Ranking de agentes por mediana del margen diario dentro de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en 2025-06-25 → 2025-07-22 (estudio de 65 agentes, 28 días, k=5).

| Pos. | Código | Comercializador | Días en la estrategia | Mediana margen (COP/kWh) | Media margen | Mediana relativa (COP/kWh) | % días > segmento | % días pérdida | Drawdown máx. (COP/kWh acum.) | Mediana días malos (COP/kWh) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 28 | 93.68 | 88.88 | 146.49 | 100.00 | 0.00 | 0.00 | 0.00 |
| 2 | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 28 | 93.68 | 88.88 | 146.49 | 100.00 | 0.00 | 0.00 | 0.00 |
| 3 | HIMC | GESTION ENERGETICA S.A. E.S.P. | 28 | 88.16 | 83.38 | 139.46 | 100.00 | 0.00 | 0.00 | 0.00 |

> **Selección por margen relativo al segmento** (S1): el ranking usa la *mediana relativa* (margen del agente − mediana del segmento el mismo día), que cancela el artefacto Pv=350. La mediana absoluta se reporta como contexto.

**Robustez de la selección** (misma ventana de estudio, otras configuraciones de top y presencia):

| min. días en estrategia | top-8 | top-10 | top-12 |
|---|---|---|---|
| 10 % | RPEC, VICC, HIMC | RPEC, VICC, HIMC | RPEC, VICC, HIMC |
| 20 % | RPEC, VICC, HIMC | RPEC, VICC, HIMC | RPEC, VICC, HIMC |
| 30 % | RPEC, VICC, HIMC | RPEC, VICC, HIMC | RPEC, VICC, HIMC |

> ⚠️ **Maestros con comportamiento idéntico o correlacionado**: HIMC y RPEC y VICC. Contarlos como 'independientes' infla el top-N (ver N efectivo en la sección de validez).

## 3. Validez de la selección (¿los maestros son hábiles o suertudos?)

Tres pruebas separan la selección del ruido: **bootstrap skill-vs-luck** (¿el mejor maestro supera al azar?), **holdout** (¿la selección hecha en sub-estudio se sostiene en la sub-validación?) y **DSR** (¿el resultado de la imitación resiste la corrección por múltiples pruebas?). La **replicación IS→OOS** mide cuánto del desempeño del estudio se conserva en el impacto.

| Prueba | Métrica | Valor | Pasa |
|---|---|---|---|
| Bootstrap skill-vs-luck | p-valor | 0.9930 | no |
|  | Mejor maestro real (COP/kWh) | 139.46 |  |
|  | Nulo p50 / p95 (COP/kWh) | 148.85 / 161.35 |  |
|  | Candidatos rankeados (trials) | 3 |  |
| Holdout (sub-estudio → sub-validación) | % de maestros que siguen en la mitad superior | 66.70 | ≥50 % |
|  | Mediana del percentil de los maestros | 50.00 |  |
| Replicación IS→OOS | mediana imitación estudio / impacto (COP/kWh) | 88.70 / 85.44 | 0.96 |
|  | Criterio de sistema sano | ≥ 50–70 % |  |
| DSR (corrige múltiples pruebas) | Sharpe diario 2.297 · skew -1.01 · kurt 2.74 | 0.936 | no |

N efectivo de maestros (tras deduplicar correlacionados): **1** de 3.

## 4. Política de clonación (contexto → perfil de abastecimiento)

Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los maestros cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.

| Contexto (spread bolsa−contrato) | Rango (COP/kWh) | Días de entrenamiento | Cobertura contratos | Exposición bolsa | No regulado | SICEP |
|---|---|---|---|---|---|---|
| muy_barata | -999 999–0 | 84 | 1% | 99% | 42% | 0% |
| barata | 0–200 | — | — | — | — | — |
| neutral | 200–400 | — | — | — | — | — |
| cara | 400–600 | — | — | — | — | — |
| escasez | 600–999 999 | — | — | — | — | — |

> **Agregación ponderada** (P1.2): el perfil por bin combina a los maestros con pesos (RPEC: 0.42, VICC: 0.42, HIMC: 0.16) en vez de elegir un top-N duro. Los pesos premian superar la mediana del segmento.

> **Zona de confianza** (P1.3): la política fue entrenada con spreads en [-190, -108] COP/kWh. Un día fuera de ese rango reduce su exposición a bolsa (trasladándola a contratos) en vez de clonar a ciegas.

> **Fallback** (mediana global del estudio, para contextos sin datos): cobertura 1 %, exposición 99 %, no regulado 42 %, SICEP 0 %.

## 5. Escenarios de estrés (sintéticos — la ventana no tuvo estos días)

La ventana de impacto puede no contener días de bolsa cara/escasez. Estos escenarios **sintéticos** responden: ¿qué pasa con la imitación si mañana la bolsa se dispara? Se construyen con el perfil que la política asignaría en ese contexto.

| Escenario | Descripción | Bolsa (COP/kWh) | Contratos (COP/kWh) | Spread | Bin | Margen (COP/kWh) | Garantía (COP) |
|---|---|---|---|---|---|---|---|
| escasez_umbral | Bolsa en el precio de escasez | 699.2 | 295.8 | 403.4 | cara | -429.74 | 45 764 693 |
| escasez_extrema | Bolsa 25 % sobre el precio de escasez | 874.0 | 295.8 | 578.2 | cara | -603.39 | 57 171 846 |

## 6. Frecuencia histórica de escasez (todo el histórico de la BD)

Con 4230 días de histórico (2015 → límite de datos), la escasez real (bolsa > precio de escasez) ocurre el **10.64 %** de los días, y el contexto en que la política de clonación **no tiene datos** (spread > 600, bin 'escasez') es raro pero existe. Cuando ocurre, la sección 4 muestra pérdidas de **−520 a −715 COP/kWh/día**.

> ⚠️ **La ventana de impacto (2025) es un año sin días de escasez.** La distribución 'ideal' de la sección 6 refleja ese clima benigno; en un año con escasez (2015–16, 2023–24: 21–30 % de los días) la misma estrategia produce las pérdidas de la sección 4.

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
| Días | 7 | 7 | 7 |
| Mediana (COP/kWh) | 85.44 | 86.20 | -44.82 |
| Media (COP/kWh) | 71.81 | 77.65 | -52.77 |
| p5 (COP/kWh) | 13.01 | 48.74 | -98.02 |
| p95 (COP/kWh) | 102.51 | 103.38 | -34.03 |
| % días con pérdida | 0.00 | 0.00 | 100.00 |
| Peor día (COP/kWh) | 13.01 | 48.74 | -98.02 |
| Mejor día (COP/kWh) | 102.51 | 103.38 | -34.03 |
| Drawdown máximo (COP/kWh acum.) | 0.00 | 0.00 | 369.42 |

> **Lectura:** la imitación logra una mediana de **85.4 COP/kWh/día** frente a **86.2** de sus maestros reales y **-44.8** del segmento, con **0.00 % de días en pérdida** y un drawdown de **0.0 COP/kWh** acumulados en el período. El margen es un artefacto de modelado; solo sirve para comparar entre sí.

## 8. Simulación día a día (2025-07-25 → 2025-07-31)

XXXC replica cada día el perfil recomendado y se calcula su margen y garantía estimada con la misma lógica del estudio (C16–C18 sobre precios de sistema). Se compara contra la mediana real de los maestros y del segmento ese día. **En distribución** indica si el spread del día cae dentro del rango entrenado (si no, la exposición a bolsa se redujo — P1.3); **Embalses** es el nivel agregado del SIN (P1.4).

| Fecha | Contexto | Escasez | En distribución | Embalses (%) | Cobertura | Exposición | Margen imitación | Mediana maestros | Mediana segmento | Garantía (COP) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07-25 | muy_barata | no | sí | 80.90 | 1% | 99% | 87.74 | 88.51 | -34.03 | 8 702 731 |
| 2025-07-26 | muy_barata | no | sí | 81.20 | 1% | 99% | 93.41 | 94.22 | -72.06 | 8 146 925 |
| 2025-07-27 | muy_barata | no | sí | 81.50 | 1% | 99% | 102.51 | 103.38 | -98.02 | 7 254 953 |
| 2025-07-28 | muy_barata | no | sí | 81.90 | 1% | 99% | 72.31 | 72.98 | -35.95 | 10 214 759 |
| 2025-07-29 | muy_barata | no | sí | 82.20 | 1% | 99% | 85.44 | 86.20 | -47.04 | 8 927 392 |
| 2025-07-30 | muy_barata | no | sí | 82.20 | 1% | 99% | 48.24 | 48.74 | -44.82 | 12 574 852 |
| 2025-07-31 | muy_barata | no | **no** | 81.90 | 50% | 50% | 13.01 | 49.52 | -37.50 | 16 028 381 |

## 9. Balance del impacto

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Mediana margen (COP/kWh) | 85.44 | 86.20 | -44.82 |
| Media margen (COP/kWh) | 71.81 | — | — |
| % días que la imitación gana | — | 0.00 | 100.00 |
| Replicación IS→OOS (ratio estudio→impacto) | 0.96 | — | — |
| DSR (corregido por múltiples pruebas) | 0.936 (no) | — | — |

Garantía estimada por día (COP): mediana **8 927 392**  máximo **16 028 381**. Demanda simulada: **262 882 kWh** (0.263 GWh).

## 10. Advertencias y limitaciones

1. El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para comparar estrategias, no como margen real del negocio.
2. Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin entrenamiento se resuelven con el bin más cercano y los días fuera del rango entrenado reducen su exposición a bolsa (zona de confianza).
3. La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.
4. Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.
5. No existe ground truth real (liquidaciones XM) para validar el margen: la validación externa queda pendiente (P2.4 del plan de investigación).
6. Solo se encontraron 3 agentes en el (segmento, estrategia) de la ventana de estudio; el top pedido era 10.
7. N efectivo de maestros: 1 de 3 (hay maestros con comportamiento correlacionado/duplicado que no suman información independiente).
8. La selección del top-10 NO supera el bootstrap skill-vs-luck (p=0.993 > 0.05): el 'mejor maestro' es indistinguible del azar. No operar sin más evidencia.
9. DSR ≈ 0.94 (< 0.95) con 3 trials: el resultado de la imitación puede ser producto de la selección por azar.
10. La combinación objetivo NO pasó la validez (bootstrap/holdout/replicación/N efectivo). Alternativa recomendada: **PEQUEÑO · Integrado/regional regulado** (relativo 48.4 COP/kWh).

## 11. Alternativa recomendada (la combinación pedida no validó)

El objetivo **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** no superó las pruebas de validez. La mejor alternativa del mismo estudio es **PEQUEÑO · Integrado/regional regulado** (maestros: EBSC, CHCC, EDQC, EMPC, ENIC), con mediana relativa de **48.38 COP/kWh** por encima de su segmento.

| Métrica | Valor |
|---|---|
| Mediana margen imitación (COP/kWh) | -7.19 |
| Mediana maestros (COP/kWh) | -5.71 |
| Mediana segmento (COP/kWh) | -44.82 |
| % días que la imitación gana al segmento | 100.00 |
| Replicación IS→OOS | 1.19 |
| Garantía mediana (COP) | 17 961 101 |

Perfil alternativo (fallback): cobertura **85 %**, exposición bolsa **16 %**, no regulado **0 %**, SICEP **88 %**.

## 12. Decisiones de negocio para el agente XXXC

Resumen ejecutivo para **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en el período planteado (estudio 2025-06-25 → 2025-07-22; impacto 2025-07-25 → 2025-07-31):

- **Perfil a replicar:** compra **99 % de tu demanda en bolsa** y **1 % en contratos**, con mix **42 % no regulado** y **0 % SICEP** (perfil mediano de los maestros).
- **Capital para operar:** constituye garantías por al menos **16 028 381 COP/día** (mediana **8 927 392 COP**).
- **Pérdida en un día de escasez:** si la bolsa toca el precio de escasez pierdes **112 971 014 COP** en un día (158 620 515 COP si la supera 25 %), sobre tu demanda simulada de 0.263 GWh/día.
- **Expectativa de negocio:** con la frecuencia histórica de escasez (10.64 % de los días) tu beneficio esperado es **30.62 COP/kWh/día**; en un año Niño (25 % de escasez) baja a **-43.36 COP/kWh/día**.
- **Kill-switch:** drawdown acumulado del período **0.00 COP/kWh**; el umbral de protección está en 500 COP/kWh.
- **Capacidad:** la demanda simulada de XXXC (262,882 kWh/día) es el **0.7 %** de la demanda mediana del segmento (5 % = umbral): dentro del límite.
- **Regla de protección:** define un límite/cobertura cuando el spread bolsa−contrato se acerque a 600 COP/kWh (contexto 'escasez'): ahí la política no tiene datos de entrenamiento y el perfil imitado (sin cobertura) es el que más pierde.
- **Re-evaluación:** el top de maestros es pequeño y con comportamientos duplicados; no operes con datos de un solo período. Revisa esta decisión cada ventana (modo `--walk-forward`).

**Veredicto:** En un año Niño (escasez ~25 % de los días) la estrategia PIERDE en expectativa. Es viable solo en años benignos; exige cobertura o reducción de exposición si el clima se torna seco.
