# Asistente imitador del agente XXXC — Behavioral Cloning del top-N

> Clona el comportamiento del top-5 de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en la ventana de estudio y lo replica en la ventana de impacto. Metodología: `docs/plan_agente_xxxc_asistente.md`.

> **Advertencia (léela antes que nada):** esto es un **ejercicio descriptivo sobre comportamiento pasado** con un margen de **modelado** (Pv=350 COP/kWh fijo, precios promedio de sistema). Los márgenes aquí son artefactos matemáticos para comparar estrategias entre sí, **no dinero real ni una recomendación de inversión**. No sustituye análisis financiero, regulatorio ni legal.

## 1. Parámetros

| Parámetro | Valor |
|---|---|
| Segmento | PEQUEÑO |
| Estrategia a imitar | Trader expuesto a bolsa (sin cobertura) |
| Top de maestros | 5 |
| Demanda diaria de XXXC (GWh) | 0.27 |
| Presencia mínima en la estrategia | 20 % de los días |
| Ventana de estudio (define maestros) | 2026-06-01 → 2026-06-30 |
| Ventana de impacto (evalúa imitación) | 2026-07-01 → 2026-07-08 |

## 2. Maestros — top 5 del segmento en la ventana de estudio

Ranking de agentes por mediana del margen diario dentro de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en 2026-06-01 → 2026-06-30 (estudio de 65 agentes, 30 días, k=5).

| Pos. | Código | Comercializador | Días en la estrategia | Mediana margen (COP/kWh) | Media margen |
|---|---|---|---|---|---|
| 1 | TRPC | TERMOPIEDRAS S.A. E.S.P. | 23 | -246.95 | -285.47 |
| 2 | HIMC | GESTION ENERGETICA S.A. E.S.P. | 30 | -257.22 | -280.35 |
| 3 | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 30 | -268.34 | -291.34 |
| 4 | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 30 | -268.34 | -291.34 |

**Robustez de la selección** (misma ventana de estudio, otras configuraciones de top y presencia):

| min. días en estrategia | top-3 | top-5 | top-7 |
|---|---|---|---|
| 10 % | TRPC, HIMC, RPEC | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC |
| 20 % | TRPC, HIMC, RPEC | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC |
| 30 % | TRPC, HIMC, RPEC | TRPC, HIMC, RPEC, VICC | TRPC, HIMC, RPEC, VICC |

> ⚠️ **Maestros con comportamiento idéntico** (misma mediana y media de margen): RPEC y VICC. Cuántos como 'independientes' infla el top-N.

## 3. Política de clonación (contexto → perfil de abastecimiento)

Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los maestros cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.

| Contexto (spread bolsa−contrato) | Rango (COP/kWh) | Días de entrenamiento | Cobertura contratos | Exposición bolsa | No regulado | SICEP |
|---|---|---|---|---|---|---|
| muy_barata | -999 999–0 | — | — | — | — | — |
| barata | 0–200 | 51 | 0% | 100% | 0% | 0% |
| neutral | 200–400 | 50 | 0% | 100% | 0% | 0% |
| cara | 400–600 | 12 | 0% | 100% | 50% | 0% |
| escasez | 600–999 999 | — | — | — | — | — |

> **Fallback** (mediana global del estudio, para contextos sin datos): cobertura 0 %, exposición 100 %, no regulado 0 %, SICEP 0 %.

## 4. Escenarios de estrés (sintéticos — la ventana no tuvo estos días)

La ventana de impacto puede no contener días de bolsa cara/escasez. Estos escenarios **sintéticos** responden: ¿qué pasa con la imitación si mañana la bolsa se dispara? Se construyen con el perfil que la política asignaría en ese contexto.

| Escenario | Descripción | Bolsa (COP/kWh) | Contratos (COP/kWh) | Spread | Bin | Margen (COP/kWh) | Garantía (COP) |
|---|---|---|---|---|---|---|---|
| escasez_umbral | Bolsa en el precio de escasez | 906.1 | 323.9 | 582.2 | cara | -639.60 | 61 392 699 |
| escasez_extrema | Bolsa 25 % sobre el precio de escasez | 1 132.7 | 323.9 | 808.8 | escasez | -866.22 | 76 740 874 |

## 5. Frecuencia histórica de escasez (todo el histórico de la BD)

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

## 6. Distribución de márgenes en el impacto (riesgo)

Medidas de la serie diaria de márgenes. **p5** es un día malo, **% días con pérdida** la frecuencia de pérdidas, **drawdown máximo** la peor caída pico→valle acumulada del período.

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Días | 8 | 8 | 8 |
| Mediana (COP/kWh) | -511.79 | -500 | -218.96 |
| Media (COP/kWh) | -515.53 | -486.15 | -226.52 |
| p5 (COP/kWh) | -566.91 | -500 | -266.09 |
| p95 (COP/kWh) | -435.50 | -435.50 | -208.76 |
| % días con pérdida | 100.00 | 100.00 | 100.00 |
| Peor día (COP/kWh) | -566.91 | -500 | -266.09 |
| Mejor día (COP/kWh) | -435.50 | -435.50 | -208.76 |
| Drawdown máximo (COP/kWh acum.) | 4 124.28 | 3 889.20 | 1 812.19 |

> **Lectura:** la imitación logra una mediana de **-529.9 COP/kWh/día** frente a **-500.0** de sus maestros reales y **-221.0** del segmento, con **100.00 % de días en pérdida** y un drawdown de **4124.3 COP/kWh** acumulados en el período. El margen es un artefacto de modelado; solo sirve para comparar entre sí.

## 7. Simulación día a día (2026-07-01 → 2026-07-08)

XXXC replica cada día el perfil recomendado y se calcula su margen y garantía estimada con la misma lógica del estudio (C16–C18 sobre precios de sistema). Se compara contra la mediana real de los maestros y del segmento ese día.

| Fecha | Contexto | Escasez | Cobertura | Exposición | Margen imitación | Mediana maestros | Mediana segmento | Garantía (COP) |
|---|---|---|---|---|---|---|---|---|
| 2026-07-01 | cara | sí | 0% | 100% | -566.91 | -500 | -230.31 | 56 469 722 |
| 2026-07-02 | cara | sí | 0% | 100% | -560.21 | -500 | -217.61 | 56 016 122 |
| 2026-07-03 | cara | sí | 0% | 100% | -547.98 | -500 | -218.38 | 55 188 135 |
| 2026-07-04 | cara | no | 0% | 100% | -511.79 | -500 | -208.76 | 52 737 176 |
| 2026-07-05 | neutral | no | 0% | 100% | -435.50 | -435.50 | -266.09 | 47 569 894 |
| 2026-07-06 | cara | sí | 0% | 100% | -548.19 | -500 | -229.07 | 55 202 318 |
| 2026-07-07 | cara | no | 0% | 100% | -467.67 | -467.67 | -223.01 | 49 748 532 |
| 2026-07-08 | cara | no | 0% | 100% | -486.03 | -486.03 | -218.96 | 50 992 517 |

## 8. Balance del impacto

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Mediana margen (COP/kWh) | -529.88 | -500.00 | -220.99 |
| Media margen (COP/kWh) | -515.53 | — | — |
| % días que la imitación gana | — | 0.00 | 0.00 |

Garantía estimada por día (COP): mediana **53 962 656**  máximo **56 469 722**. Demanda simulada: **271 013 kWh** (0.271 GWh).

## 9. Advertencias y limitaciones

1. El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para comparar estrategias, no como margen real del negocio.
2. Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin entrenamiento se resuelven con el bin más cercano o el fallback.
3. La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.
4. Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.
5. Solo se encontraron 4 agentes en el (segmento, estrategia) de la ventana de estudio; el top pedido era 5.

## 10. Decisiones de negocio para el agente XXXC

Resumen ejecutivo para **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en el período planteado (estudio 2026-06-01 → 2026-06-30; impacto 2026-07-01 → 2026-07-08):

- **Perfil a replicar:** compra **100 % de tu demanda en bolsa** y **0 % en contratos**, con mix **0 % no regulado** y **0 % SICEP** (perfil mediano de los maestros).
- **Capital para operar:** constituye garantías por al menos **56 469 722 COP/día** (mediana **53 962 656 COP**).
- **Pérdida en un día de escasez:** si la bolsa toca el precio de escasez pierdes **173 340 228 COP** en un día (234 757 305 COP si la supera 25 %), sobre tu demanda simulada de 0.271 GWh/día.
- **Expectativa de negocio:** con la frecuencia histórica de escasez (10.64 % de los días) tu beneficio esperado es **-541.55 COP/kWh/día**; en un año Niño (25 % de escasez) baja a **-557.31 COP/kWh/día**.
- **Regla de protección:** define un límite/cobertura cuando el spread bolsa−contrato se acerque a 600 COP/kWh (contexto 'escasez'): ahí la política no tiene datos de entrenamiento y el perfil imitado (sin cobertura) es el que más pierde.
- **Re-evaluación:** el top de maestros es pequeño y con comportamientos duplicados; no operes con datos de un solo período. Revisa esta decisión cada ventana.

**Veredicto:** En un año Niño (escasez ~25 % de los días) la estrategia PIERDE en expectativa. Es viable solo en años benignos; exige cobertura o reducción de exposición si el clima se torna seco.
