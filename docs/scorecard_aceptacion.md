# Scorecard de aceptación del asistente imitador

> **Advertencia:** el margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo, precios de sistema) usado para comparar estrategias entre sí. La selección usa el **margen relativo al segmento** (cancela el artefacto). Ningún valor aquí es dinero real ni una recomendación de inversión.

Grid: **138** ventanas (estudio 90 d · impacto 7 d · paso 30 d) entre **2015-01-01** y el límite de datos · **984** (segmento × estrategia × ventana, modo topN) y **414** (segmento × ventana, modo arquetipo) evaluadas en el scan grueso.

Gates (N1/N2): bootstrap p ≤ 0.05 · N efectivo ≥ 3 · holdout ≥ 50.0 % · replicación ≥ 0.5 · DSR ≥ 0.95 · % días > segmento ≥ 60.0 · EV histórico ≥ 0.0 · sin kill-switch · capacidad ≤ 5.0 %.

## VEREDICTO: COMBINACIÓN OPERABLE ENCONTRADA

**45** combinación(es) pasan N0+N1+N2 (y N3 cuando se confirma con walk-forward) en una ventana reproducible:

- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-01-01→2015-03-31 · impacto 2015-04-01→2015-04-07 — p=0.0010 · réplica 0.98 · DSR 0.99 · N efectivo 5 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-05-31→2015-08-28 · impacto 2015-08-29→2015-09-04 — p=0.0010 · réplica 0.96 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2015-05-31→2015-08-28 · impacto 2015-08-29→2015-09-04 — p=0.0010 · réplica 0.96 · DSR 1.00 · N efectivo 9 · % días > segmento 85.70.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-07-30→2015-10-27 · impacto 2015-10-28→2015-11-03 — p=0.0010 · réplica 0.74 · DSR 1.00 · N efectivo 3 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2016-04-25→2016-07-23 · impacto 2016-07-24→2016-07-30 — p=0.0010 · réplica 1.00 · DSR 1.00 · N efectivo 4 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2016-09-22→2016-12-20 · impacto 2016-12-21→2016-12-27 — p=0.0010 · réplica 1.11 · DSR 1.00 · N efectivo 3 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-09-28→2015-12-26 · impacto 2015-12-27→2016-01-02 — p=0.0010 · réplica 1.06 · DSR 0.95 · N efectivo 5 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-08-29→2015-11-26 · impacto 2015-11-27→2015-12-03 — p=0.0010 · réplica 0.94 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2016-08-23→2016-11-20 · impacto 2016-11-21→2016-11-27 — p=0.0010 · réplica 1.05 · DSR 1.00 · N efectivo 4 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2017-01-20→2017-04-19 · impacto 2017-04-20→2017-04-26 — p=0.0010 · réplica 1.05 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2016-10-22→2017-01-19 · impacto 2017-01-20→2017-01-26 — p=0.0010 · réplica 0.99 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2016-12-21→2017-03-20 · impacto 2017-03-21→2017-03-27 — p=0.0010 · réplica 1.01 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2016-05-25→2016-08-22 · impacto 2016-08-23→2016-08-29 — p=0.0010 · réplica 0.83 · DSR 0.99 · N efectivo 6 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2017-03-21→2017-06-18 · impacto 2017-06-19→2017-06-25 — p=0.0010 · réplica 1.01 · DSR 1.00 · N efectivo 10 · % días > segmento 100.00.
- **MEDIANO · Comercializador regulado** (topN) — estudio 2017-04-20→2017-07-18 · impacto 2017-07-19→2017-07-25 — p=0.0010 · réplica 0.99 · DSR 0.98 · N efectivo 10 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-06-30→2015-09-27 · impacto 2015-09-28→2015-10-04 — p=0.0020 · réplica 0.73 · DSR 1.00 · N efectivo 4 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-12-27→2016-03-25 · impacto 2016-03-26→2016-04-01 — p=0.0020 · réplica 0.81 · DSR 1.00 · N efectivo 6 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-11-27→2016-02-24 · impacto 2016-02-25→2016-03-02 — p=0.0020 · réplica 1.01 · DSR 1.00 · N efectivo 6 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-03-02→2015-05-30 · impacto 2015-05-31→2015-06-06 — p=0.0040 · réplica 0.99 · DSR 1.00 · N efectivo 5 · % días > segmento 100.00.
- **PEQUEÑO · Comercializador regulado** (topN) — estudio 2015-05-01→2015-07-29 · impacto 2015-07-30→2015-08-05 — p=0.0070 · réplica 0.97 · DSR 1.00 · N efectivo 5 · % días > segmento 85.70.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-03-21→2017-06-18 · impacto 2017-06-19→2017-06-25 — p=0.0010 · réplica 1.05 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-04-20→2017-07-18 · impacto 2017-07-19→2017-07-25 — p=0.0010 · réplica 0.98 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2021-05-29→2021-08-26 · impacto 2021-08-27→2021-09-02 — p=0.0010 · réplica 1.00 · DSR 0.99 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2021-03-30→2021-06-27 · impacto 2021-06-28→2021-07-04 — p=0.0010 · réplica 1.03 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2018-08-13→2018-11-10 · impacto 2018-11-11→2018-11-17 — p=0.0010 · réplica 1.09 · DSR 0.99 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-09-17→2017-12-15 · impacto 2017-12-16→2017-12-22 — p=0.0010 · réplica 1.22 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2021-02-28→2021-05-28 · impacto 2021-05-29→2021-06-04 — p=0.0010 · réplica 1.53 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2018-07-14→2018-10-11 · impacto 2018-10-12→2018-10-18 — p=0.0010 · réplica 0.99 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2022-02-23→2022-05-23 · impacto 2022-05-24→2022-05-30 — p=0.0010 · réplica 1.72 · DSR 0.99 · % días > segmento 100.00.
- **MEDIANO · Comercializador mixto** (arquetipo) — estudio 2018-03-16→2018-06-13 · impacto 2018-06-14→2018-06-20 — p=0.0010 · réplica 1.10 · DSR 0.97 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2021-08-27→2021-11-24 · impacto 2021-11-25→2021-12-01 — p=0.0010 · réplica 1.02 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2022-03-25→2022-06-22 · impacto 2022-06-23→2022-06-29 — p=0.0010 · réplica 1.03 · DSR 0.99 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-01-20→2017-04-19 · impacto 2017-04-20→2017-04-26 — p=0.0010 · réplica 1.16 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2025-03-09→2025-06-06 · impacto 2025-06-07→2025-06-13 — p=0.0010 · réplica 1.16 · DSR 0.98 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2025-02-07→2025-05-07 · impacto 2025-05-08→2025-05-14 — p=0.0010 · réplica 2.97 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2016-06-24→2016-09-21 · impacto 2016-09-22→2016-09-28 — p=0.0010 · réplica 1.35 · DSR 0.97 · % días > segmento 85.70.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2021-06-28→2021-09-25 · impacto 2021-09-26→2021-10-02 — p=0.0010 · réplica 0.88 · DSR 1.00 · % días > segmento 100.00.
- **MEDIANO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2016-06-24→2016-09-21 · impacto 2016-09-22→2016-09-28 — p=0.0010 · réplica 1.33 · DSR 0.97 · % días > segmento 85.70.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2016-12-21→2017-03-20 · impacto 2017-03-21→2017-03-27 — p=0.0010 · réplica 1.09 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-06-19→2017-09-16 · impacto 2017-09-17→2017-09-23 — p=0.0010 · réplica 0.76 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-08-18→2017-11-15 · impacto 2017-11-16→2017-11-22 — p=0.0010 · réplica 1.09 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2017-10-17→2018-01-14 · impacto 2018-01-15→2018-01-21 — p=0.0010 · réplica 1.10 · DSR 0.97 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2016-10-22→2017-01-19 · impacto 2017-01-20→2017-01-26 — p=0.0010 · réplica 1.10 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2020-09-01→2020-11-29 · impacto 2020-11-30→2020-12-06 — p=0.0010 · réplica 1.47 · DSR 1.00 · % días > segmento 100.00.
- **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** (arquetipo) — estudio 2018-01-15→2018-04-14 · impacto 2018-04-15→2018-04-21 — p=0.0010 · réplica 1.14 · DSR 1.00 · % días > segmento 100.00.

## Confirmaciones (flujo completo: bootstrap fino + holdout + DSR)

| Ventana estudio | Segmento | Estrategia | N | N ef. | p-valor | Réplica | DSR | Holdout % | % > seg. | EV hist. | Kill | Operable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-01-01 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0010 | 0.98 | 0.99 | 90.00 | 100.00 | 82.07 | no | sí |
| 2015-05-31 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0010 | 0.96 | 1.00 | 70.00 | 100.00 | 77.62 | no | sí |
| 2015-05-31 | MEDIANO | Comercializador regulado | 10 | 9 | 0.0010 | 0.96 | 1.00 | — | 85.70 | 76.08 | no | sí |
| 2015-07-30 | PEQUEÑO | Comercializador regulado | 10 | 3 | 0.0010 | 0.74 | 1.00 | 80.00 | 100.00 | 58.70 | no | sí |
| 2016-04-25 | MEDIANO | Comercializador regulado | 10 | 4 | 0.0010 | 1.00 | 1.00 | — | 100.00 | 72.36 | no | sí |
| 2016-09-22 | MEDIANO | Comercializador regulado | 10 | 3 | 0.0010 | 1.11 | 1.00 | — | 100.00 | 71.07 | no | sí |
| 2015-09-28 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0010 | 1.06 | 0.95 | 80.00 | 100.00 | 65.37 | no | sí |
| 2015-08-29 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0010 | 0.94 | 1.00 | 90.00 | 100.00 | 58.98 | no | sí |
| 2016-08-23 | MEDIANO | Comercializador regulado | 10 | 4 | 0.0010 | 1.05 | 1.00 | — | 100.00 | 68.11 | no | sí |
| 2017-01-20 | MEDIANO | Comercializador regulado | 10 | 5 | 0.0010 | 1.05 | 1.00 | — | 100.00 | 67.18 | no | sí |
| 2016-10-22 | MEDIANO | Comercializador regulado | 10 | 5 | 0.0010 | 0.99 | 1.00 | — | 100.00 | 67.92 | no | sí |
| 2016-12-21 | MEDIANO | Comercializador regulado | 10 | 5 | 0.0010 | 1.01 | 1.00 | — | 100.00 | 65.78 | no | sí |
| 2016-05-25 | PEQUEÑO | Comercializador regulado | 10 | 6 | 0.0010 | 0.83 | 0.99 | 80.00 | 100.00 | 60.82 | no | sí |
| 2017-03-21 | MEDIANO | Comercializador regulado | 10 | 10 | 0.0010 | 1.01 | 1.00 | — | 100.00 | 68.35 | no | sí |
| 2017-04-20 | MEDIANO | Comercializador regulado | 10 | 10 | 0.0010 | 0.99 | 0.98 | — | 100.00 | 65.82 | no | sí |
| 2015-06-30 | PEQUEÑO | Comercializador regulado | 10 | 4 | 0.0020 | 0.73 | 1.00 | 80.00 | 100.00 | 60.27 | no | sí |
| 2015-12-27 | PEQUEÑO | Comercializador regulado | 10 | 6 | 0.0020 | 0.81 | 1.00 | 90.00 | 100.00 | 40.59 | no | sí |
| 2015-11-27 | PEQUEÑO | Comercializador regulado | 10 | 6 | 0.0020 | 1.01 | 1.00 | 80.00 | 100.00 | 61.87 | no | sí |
| 2015-03-02 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0040 | 0.99 | 1.00 | 80.00 | 100.00 | 81.94 | no | sí |
| 2015-05-01 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0070 | 0.97 | 1.00 | 60.00 | 85.70 | 80.09 | no | sí |
| 2015-01-31 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0010 | 1.00 | 0.90 | 10.00 | 100.00 | 82.84 | no | no |
| 2015-05-01 | MEDIANO | Comercializador regulado | 10 | 8 | 0.0010 | 1.00 | 0.70 | — | 71.40 | 78.90 | no | no |
| 2017-02-19 | GRANDE | Comercializador regulado | 3 | 1 | 0.0010 | 1.13 | 0.93 | — | 85.70 | 77.02 | no | no |
| 2015-04-01 | PEQUEÑO | Comercializador regulado | 10 | 2 | 0.0010 | 0.97 | 0.93 | 50.00 | 100.00 | 80.74 | no | no |
| 2015-01-31 | MEDIANO | Comercializador regulado | 10 | 2 | 0.0010 | 1.01 | 0.88 | — | 100.00 | 80.45 | no | no |
| 2015-05-01 | GRANDE | Comercializador regulado | 3 | 1 | 0.0010 | 1.01 | 1.00 | — | 28.60 | 78.55 | no | no |
| 2017-03-21 | GRANDE | Comercializador regulado | 3 | 3 | 0.0010 | 1.03 | 1.00 | — | 100.00 | 75.91 | no | no |
| 2015-01-31 | GRANDE | Comercializador regulado | 3 | 1 | 0.0010 | 1.01 | 0.99 | — | 0.00 | 78.89 | no | no |
| 2015-01-01 | MEDIANO | Comercializador regulado | 10 | 2 | 0.0010 | 0.99 | 0.98 | — | 100.00 | 78.71 | no | no |
| 2015-04-01 | MEDIANO | Comercializador regulado | 10 | 5 | 0.0010 | 0.97 | 0.88 | — | 100.00 | 78.15 | no | no |
| 2019-03-11 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 5 | 4 | 0.0020 | 0.92 | 0.00 | 60.00 | 0.00 | -1 238.44 | sí | no |
| 2019-04-10 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 5 | 4 | 0.0050 | 0.98 | 0.00 | 40.00 | 0.00 | -1 472.38 | sí | no |
| 2017-01-20 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 6 | 3 | 0.9201 | 1.17 | 1.00 | 50.00 | 100.00 | 81.81 | no | no |

**Lectura:** *Operable* = pasa N1 completo (bootstrap + N efectivo + holdout + replicación + DSR) y N2 (económico/riesgo) en esa ventana.

## Modo arquetipo (Ruta A): el arquetipo ganador por régimen

En vez de clonar el top-N de agentes de una estrategia fija (indistinguibles entre sí), la política mezcla **arquetipos por bin de spread**: en cada régimen despliega el perfil de la estrategia que mejor superó a su segmento en el estudio. La validez se re-pointa al nivel de arquetipo (bootstrap sobre arquetipos + persistencia del ganador).

### Confirmaciones (arquetipo)

| Ventana estudio | Segmento | Arquetipo ganador | N arq. | p-valor | Réplica | DSR | Holdout % | % > seg. | EV hist. | Kill | Operable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017-03-21 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.05 | 1.00 | 100.00 | 100.00 | 105.81 | no | sí |
| 2017-04-20 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 0.98 | 1.00 | 100.00 | 100.00 | 104.50 | no | sí |
| 2021-05-29 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.00 | 0.99 | 100.00 | 100.00 | 59.71 | no | sí |
| 2021-03-30 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.03 | 1.00 | 100.00 | 100.00 | 65.42 | no | sí |
| 2018-08-13 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.09 | 0.99 | 100.00 | 100.00 | 108.13 | no | sí |
| 2017-09-17 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.22 | 1.00 | 100.00 | 100.00 | 108.53 | no | sí |
| 2021-02-28 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.53 | 1.00 | 100.00 | 100.00 | 65.16 | no | sí |
| 2018-07-14 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 0.99 | 1.00 | — | 100.00 | 74.76 | no | sí |
| 2022-02-23 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.72 | 0.99 | 100.00 | 100.00 | 61.74 | no | sí |
| 2018-03-16 | MEDIANO | Comercializador mixto | 3 | 0.0010 | 1.10 | 0.97 | — | 100.00 | 105.12 | no | sí |
| 2021-08-27 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.02 | 1.00 | 100.00 | 100.00 | 46.84 | no | sí |
| 2022-03-25 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.03 | 0.99 | 100.00 | 100.00 | 55.91 | no | sí |
| 2017-01-20 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.16 | 1.00 | 100.00 | 100.00 | 101.13 | no | sí |
| 2025-03-09 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.16 | 0.98 | 100.00 | 100.00 | 39.69 | no | sí |
| 2025-02-07 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 2.97 | 1.00 | 100.00 | 100.00 | 80.12 | no | sí |
| 2016-06-24 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.35 | 0.97 | 100.00 | 85.70 | 98.50 | no | sí |
| 2021-06-28 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 0.88 | 1.00 | 100.00 | 100.00 | 46.98 | no | sí |
| 2016-06-24 | MEDIANO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.33 | 0.97 | — | 85.70 | 97.58 | no | sí |
| 2016-12-21 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.09 | 1.00 | 100.00 | 100.00 | 93.93 | no | sí |
| 2017-06-19 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 0.76 | 1.00 | 100.00 | 100.00 | 74.50 | no | sí |
| 2017-08-18 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.09 | 1.00 | 100.00 | 100.00 | 91.77 | no | sí |
| 2017-10-17 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.10 | 0.97 | 100.00 | 100.00 | 90.82 | no | sí |
| 2016-10-22 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.10 | 1.00 | 100.00 | 100.00 | 91.64 | no | sí |
| 2020-09-01 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.47 | 1.00 | 100.00 | 100.00 | 87.87 | no | sí |
| 2018-01-15 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.14 | 1.00 | — | 100.00 | 89.42 | no | sí |
| 2017-02-19 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 0.0010 | 1.26 | 0.91 | 100.00 | 100.00 | 125.59 | no | no |
| 2021-04-29 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 1.00 | 0.92 | 100.00 | 100.00 | 64.86 | no | no |
| 2022-04-24 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 0.97 | 0.92 | 100.00 | 100.00 | 11.46 | no | no |
| 2025-12-04 | PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 4 | 0.0010 | 2.08 | 0.84 | 100.00 | 100.00 | 77.25 | no | no |
| 2017-09-17 | MEDIANO | Trader no regulado | 2 | 0.0010 | 1.14 | 1.00 | — | 100.00 | 87.94 | no | no |
| 2015-01-31 | MEDIANO | Trader no regulado | 2 | 0.0010 | 1.00 | 1.00 | — | 100.00 | 84.79 | no | no |
| 2015-01-01 | MEDIANO | Trader no regulado | 2 | 0.0010 | 0.98 | 1.00 | — | 100.00 | 83.95 | no | no |
| 2017-04-20 | MEDIANO | Trader no regulado | 2 | 0.0020 | 0.98 | 1.00 | — | 100.00 | 87.39 | no | no |

### Diagnóstico del modo arquetipo

| Gate | Resultado |
|---|---|
| Combinaciones evaluadas (arquetipo) | 414 |
| Candidatas arquetipo (N1 cheap + N2) | 83 |
| V1' · bootstrap arquetipo p ≤ 0.05 (pasan / %) | 212 / 51.2 % |
| V2' · nº arquetipos ≥ 3 (pasan / %) | 213 / 51.4 % |
| V4 · replicación ≥ 0.5 (pasan / %) | 366 / 88.4 % |
| V5 · DSR ≥ 0.95 (pasan / %) | 311 / 75.1 % |
| E1 · % días > segmento ≥ 60 (pasan / %) | 294 / 71.0 % |
| E3 · EV histórico ≥ 0 (pasan / %) | 267 / 64.5 % |


## Diagnóstico de la falta de señal (tasas de paso por gate)

| Gate | Resultado |
|---|---|
| Combinaciones evaluadas (scan grueso) | 984 |
| p-valor mínimo (bootstrap skill-vs-luck) | 0.005 |
| p-valor mediana | 0.005 |
| V1 · bootstrap p ≤ 0.05 (pasan / %) | 777 / 79.0 % |
| V2 · N efectivo ≥ 3 (pasan / %) | 633 / 64.3 % |
| V4 · replicación ≥ 0.5 (pasan / %) | 879 / 89.3 % |
| V5 · DSR ≥ 0.95 (pasan / %) | 444 / 45.1 % |
| E1 · % días > segmento ≥ 60 (pasan / %) | 471 / 47.9 % |
| E2 · sin kill-switch (pasan / %) | 769 / 78.2 % |
| E3 · EV histórico ≥ 0 (pasan / %) | 452 / 45.9 % |
| E4 · capacidad ≤ límite (pasan / %) | 845 / 85.9 % |
| Combinaciones que pasan N1 cheap + N2 (candidatas) | 102 |

**Lectura:** el gate dominante es **V1 (bootstrap skill-vs-luck)**. El mejor maestro de cada (segmento × estrategia × ventana) **nunca supera el percentil 95 de la nula** en los 11 años analizados: la dispersión de 'habilidad' dentro de una estrategia es nula con el premio C16–C18 relativo (los agentes de una misma estrategia son conductualmente homogéneos → el 'top' es suerte entre iguales). Aun las combinaciones con N efectivo ≥ 3 caen en V1 (p ≈ 1.0).

## Mejores 20 del scan grueso (por p-valor, candidatas primero)

| Ventana estudio | Segmento | Estrategia | N | N ef. | p-valor | Réplica | DSR | % > seg. | Relativo | Candidata |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023-08-17 | PEQUEÑO | Comercializador regulado | 10 | 9 | 0.0050 | 0.40 | 0.00 | 100.00 | 210.31 | no |
| 2023-09-16 | PEQUEÑO | Comercializador regulado | 10 | 8 | 0.0050 | 1.11 | 0.00 | 100.00 | 200.26 | no |
| 2016-01-26 | PEQUEÑO | Comercializador regulado | 10 | 3 | 0.0050 | 1.05 | 0.91 | 100.00 | 166.10 | no |
| 2023-07-18 | PEQUEÑO | Comercializador regulado | 10 | 6 | 0.0050 | 0.93 | 0.00 | 100.00 | 166.03 | no |
| 2023-10-16 | PEQUEÑO | Comercializador regulado | 10 | 7 | 0.0050 | 1.15 | 0.00 | 100.00 | 163.58 | no |
| 2015-12-27 | PEQUEÑO | Comercializador regulado | 10 | 6 | 0.0050 | 0.99 | 1.00 | 100.00 | 134.93 | sí |
| 2024-09-10 | PEQUEÑO | Integrado/regional regulado | 10 | 9 | 0.0050 | 1.05 | 0.00 | 100.00 | 130.67 | no |
| 2023-09-16 | MEDIANO | Trader con sobrecobertura de contratos | 2 | 2 | 0.0050 | 2.90 | 0.00 | 100.00 | 127.90 | no |
| 2024-10-10 | PEQUEÑO | Integrado/regional regulado | 10 | 9 | 0.0050 | 0.43 | 0.00 | 100.00 | 127.25 | no |
| 2023-08-17 | PEQUEÑO | Trader no regulado | 10 | 10 | 0.0050 | 0.24 | 0.00 | 100.00 | 127.19 | no |
| 2024-08-11 | PEQUEÑO | Integrado/regional regulado | 10 | 9 | 0.0050 | 1.00 | 0.00 | 100.00 | 115.76 | no |
| 2023-08-17 | MEDIANO | Trader con sobrecobertura de contratos | 4 | 4 | 0.0050 | 5.89 | 0.00 | 42.90 | 109.64 | no |
| 2023-11-15 | PEQUEÑO | Comercializador regulado | 10 | 8 | 0.0050 | 1.01 | 0.00 | 100.00 | 104.67 | no |
| 2024-01-14 | PEQUEÑO | Comercializador regulado | 10 | 10 | 0.0050 | 1.73 | 0.00 | 100.00 | 101.81 | no |
| 2023-06-18 | PEQUEÑO | Comercializador regulado | 10 | 5 | 0.0050 | 1.76 | 0.00 | 100.00 | 100.58 | no |
| 2023-12-15 | PEQUEÑO | Comercializador regulado | 10 | 10 | 0.0050 | 1.11 | 0.00 | 100.00 | 98.45 | no |
| 2023-07-18 | PEQUEÑO | Trader con sobrecobertura de contratos | 7 | 6 | 0.0050 | 0.91 | 0.00 | 100.00 | 93.57 | no |
| 2024-02-13 | PEQUEÑO | Comercializador regulado | 10 | 7 | 0.0050 | 0.52 | 0.00 | 28.60 | 93.52 | no |
| 2024-11-09 | PEQUEÑO | Integrado/regional regulado | 10 | 9 | 0.0050 | 0.85 | 0.00 | 100.00 | 92.00 | no |
| 2026-04-03 | PEQUEÑO | Comercializador regulado | 10 | 10 | 0.0050 | 1.50 | 0.00 | 100.00 | 91.83 | no |

**Distancia a la barrera:** el p-valor del bootstrap skill-vs-luck es el gate más difícil; un valor ≈ 1 indica que el mejor maestro es indistinguible del azar dentro de su (segmento, estrategia).

## Contexto de escasez del histórico (para leer los resultados)

Días con escasez real (bolsa > precio de escasez): **10.64 %** del histórico (4230 días). Años Niño (2015-16, 2023-24) tuvieron 21-30 %; 2017-22 y 2025 ~0 %.

---
_Generado por `python -m sfeia.main --aceptacion`. No editar a mano._