# Scorecard de aceptación del asistente imitador

> **Advertencia:** el margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo, precios de sistema) usado para comparar estrategias entre sí. La selección usa el **margen relativo al segmento** (cancela el artefacto). Ningún valor aquí es dinero real ni una recomendación de inversión.

Grid: **138** ventanas (estudio 90 d · impacto 7 d · paso 30 d) entre **2015-01-01** y el límite de datos · **984** (segmento × estrategia × ventana) evaluadas en el scan grueso.

Gates (N1/N2): bootstrap p ≤ 0.05 · N efectivo ≥ 3 · holdout ≥ 50.0 % · replicación ≥ 0.5 · DSR ≥ 0.95 · % días > segmento ≥ 60.0 · EV histórico ≥ 0.0 · sin kill-switch · capacidad ≤ 5.0 %.

## VEREDICTO: NO-OPERABLE (no se encontró combinación válida)

Tras el barrido completo del grid, **ninguna** (segmento × estrategia × ventana) supera la barrera de validez con el margen C16–C18 relativo al segmento. La siguiente tabla muestra las confirmaciones más cercanas a la barrera (la distancia es la evidencia de por qué no hay señal).

## Confirmaciones (flujo completo: bootstrap fino + holdout + DSR)

| Ventana estudio | Segmento | Estrategia | N | N ef. | p-valor | Réplica | DSR | Holdout % | % > seg. | EV hist. | Kill | Operable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019-02-09 | MEDIANO | Trader expuesto a bolsa (sin cobertura) | 1 | 1 | 0.5255 | 2.37 | 1.00 | — | 71.40 | 36.60 | no | no |
| 2025-10-05 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5265 | 1.52 | 1.00 | — | 100.00 | -41.38 | no | no |
| 2023-03-20 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5305 | 4.46 | 1.00 | — | 100.00 | -60.88 | no | no |
| 2021-03-30 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5365 | 1.05 | 1.00 | — | 0.00 | -72.72 | no | no |
| 2023-02-18 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5365 | 2.48 | 1.00 | — | 100.00 | -40.45 | no | no |
| 2023-04-19 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5425 | 0.78 | 1.00 | — | 100.00 | -29.96 | no | no |
| 2025-12-04 | MEDIANO | Trader no regulado | 1 | 1 | 0.5455 | -0.57 | 1.00 | — | 100.00 | -7.91 | no | no |
| 2021-04-29 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5554 | 1.06 | 1.00 | — | 0.00 | -72.28 | no | no |

**Lectura:** *Operable* = pasa N1 completo (bootstrap + N efectivo + holdout + replicación + DSR) y N2 (económico/riesgo) en esa ventana.

## Diagnóstico de la falta de señal (tasas de paso por gate)

| Gate | Resultado |
|---|---|
| Combinaciones evaluadas (scan grueso) | 984 |
| p-valor mínimo (bootstrap skill-vs-luck) | 0.4577 |
| p-valor mediana | 1.0 |
| V1 · bootstrap p ≤ 0.05 (pasan / %) | 0 / 0.0 % |
| V2 · N efectivo ≥ 3 (pasan / %) | 633 / 64.3 % |
| V4 · replicación ≥ 0.5 (pasan / %) | 879 / 89.3 % |
| V5 · DSR ≥ 0.95 (pasan / %) | 444 / 45.1 % |
| E1 · % días > segmento ≥ 60 (pasan / %) | 471 / 47.9 % |
| E2 · sin kill-switch (pasan / %) | 769 / 78.2 % |
| E3 · EV histórico ≥ 0 (pasan / %) | 452 / 45.9 % |
| E4 · capacidad ≤ límite (pasan / %) | 845 / 85.9 % |
| Combinaciones que pasan N1 cheap + N2 (candidatas) | 0 |

**Lectura:** el gate dominante es **V1 (bootstrap skill-vs-luck)**. El mejor maestro de cada (segmento × estrategia × ventana) **nunca supera el percentil 95 de la nula** en los 11 años analizados: la dispersión de 'habilidad' dentro de una estrategia es nula con el premio C16–C18 relativo (los agentes de una misma estrategia son conductualmente homogéneos → el 'top' es suerte entre iguales). Aun las combinaciones con N efectivo ≥ 3 caen en V1 (p ≈ 1.0).

## Mejores 20 del scan grueso (por p-valor, candidatas primero)

| Ventana estudio | Segmento | Estrategia | N | N ef. | p-valor | Réplica | DSR | % > seg. | Relativo | Candidata |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021-03-30 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.4577 | 1.05 | 1.00 | 0.00 | -87.17 | no |
| 2023-03-20 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.4726 | 4.33 | 1.00 | 100.00 | 3.89 | no |
| 2019-02-09 | MEDIANO | Trader expuesto a bolsa (sin cobertura) | 1 | 1 | 0.4726 | 2.42 | 1.00 | 71.40 | -16.53 | no |
| 2023-04-19 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.4925 | 0.75 | 1.00 | 100.00 | 19.69 | no |
| 2021-04-29 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.4925 | 1.06 | 1.00 | 0.00 | -82.85 | no |
| 2023-02-18 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5025 | 4.46 | 1.00 | 100.00 | 3.62 | no |
| 2025-10-05 | MEDIANO | Trader con sobrecobertura de contratos | 1 | 1 | 0.5075 | 1.52 | 1.00 | 100.00 | 9.00 | no |
| 2025-12-04 | MEDIANO | Trader no regulado | 1 | 1 | 0.5124 | -0.59 | 1.00 | 100.00 | 34.60 | no |
| 2021-07-28 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5174 | 1.27 | 1.00 | 0.00 | -71.09 | no |
| 2022-05-24 | MEDIANO | Integrado/regional regulado | 1 | 1 | 0.5174 | 1.05 | 1.00 | 0.00 | -153.91 | no |
| 2018-02-14 | MEDIANO | Comercializador mixto | 1 | 1 | 0.5224 | 1.10 | 1.00 | 100.00 | 19.85 | no |
| 2016-05-25 | MEDIANO | Trader expuesto a bolsa (sin cobertura) | 1 | 1 | 0.5224 | 0.24 | 1.00 | 0.00 | 12.56 | no |
| 2018-09-12 | MEDIANO | Comercializador mixto | 1 | 1 | 0.5274 | 0.55 | 1.00 | 28.60 | 37.50 | no |
| 2021-10-26 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5323 | 1.20 | 1.00 | 0.00 | -100.08 | no |
| 2022-02-23 | GRANDE | Trader no regulado | 1 | 1 | 0.5373 | 63.14 | 1.00 | 0.00 | -2.57 | no |
| 2021-06-28 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5373 | 1.27 | 1.00 | 0.00 | -68.43 | no |
| 2021-05-29 | MEDIANO | Comercializador mixto con convocatoria | 1 | 1 | 0.5373 | 1.07 | 1.00 | 0.00 | -77.20 | no |
| 2022-06-23 | MEDIANO | Integrado/regional regulado | 1 | 1 | 0.5373 | 1.11 | 1.00 | 0.00 | -154.69 | no |
| 2022-04-24 | MEDIANO | Integrado/regional regulado | 1 | 1 | 0.5373 | 1.05 | 1.00 | 0.00 | -156.92 | no |
| 2024-02-13 | MEDIANO | Comercializador mixto | 1 | 1 | 0.5423 | 0.86 | 1.00 | 0.00 | 73.70 | no |

**Distancia a la barrera:** el p-valor del bootstrap skill-vs-luck es el gate más difícil; un valor ≈ 1 indica que el mejor maestro es indistinguible del azar dentro de su (segmento, estrategia).

## Contexto de escasez del histórico (para leer los resultados)

Días con escasez real (bolsa > precio de escasez): **10.64 %** del histórico (4230 días). Años Niño (2015-16, 2023-24) tuvieron 21-30 %; 2017-22 y 2025 ~0 %.

---
_Generado por `python -m sfeia.main --aceptacion`. No editar a mano._