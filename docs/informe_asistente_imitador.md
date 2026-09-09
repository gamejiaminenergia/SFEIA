# Asistente imitador del agente XXXC — Behavioral Cloning del top-N

> Proyecto SFEIA (simulador) · Clona el comportamiento del top-5 de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** y lo replica en una ventana de impacto. Documentado en `docs/plan_agente_xxxc_asistente.md`.

## 1. Parámetros

| Parámetro | Valor |
|---|---|
| Segmento | PEQUEÑO |
| Estrategia a imitar | Trader expuesto a bolsa (sin cobertura) |
| Top de maestros | 5 |
| Demanda diaria de XXXC (GWh) | 0.07 |
| Presencia mínima en la estrategia | 20 % de los días |
| Ventana de estudio (define maestros) | 2025-01-01 → 2025-07-24 |
| Ventana de impacto (evalúa imitación) | 2025-07-25 → 2025-07-31 |

## 2. Maestros — top 5 del segmento en la ventana de estudio

Ranking de agentes por mediana del margen diario dentro de **PEQUEÑO · Trader expuesto a bolsa (sin cobertura)** en 2025-01-01 → 2025-07-24 (estudio de 65 agentes, 205 días, k=5). Los maestros son quienes se imitan: su perfil de abastecimiento por contexto se clona.

| Pos. | Código | Comercializador | Días en la estrategia | Mediana margen (COP/kWh) | Media margen |
|---|---|---|---|---|---|
| 1 | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 205 | 62.48 | -10.29 |
| 2 | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 205 | 62.48 | -10.29 |
| 3 | HIMC | GESTION ENERGETICA S.A. E.S.P. | 205 | 58.61 | -11.16 |
| 4 | EGVC | EMPRESA DE ENERGIA ELECTRICA DEL DEPARTAMENTO DEL GUAVIARE S.A. E.S.P. | 90 | -28.59 | -132.91 |

## 3. Política de clonación (contexto → perfil de abastecimiento)

Por bin de spread (bolsa − contrato) se aprende la **mediana** del perfil que usaron los maestros cuando jugaron la estrategia objetivo. Un día con ese contexto recibe ese perfil.

| Contexto (spread bolsa−contrato) | Rango (COP/kWh) | Días de entrenamiento | Cobertura contratos | Exposición bolsa | No regulado | SICEP |
|---|---|---|---|---|---|---|
| muy_barata | -999 999–0 | 529 | 0% | 100% | 0% | 0% |
| barata | 0–200 | 64 | 2% | 98% | 0% | 0% |
| neutral | 200–400 | 84 | 2% | 98% | 0% | 0% |
| cara | 400–600 | 28 | 2% | 98% | 0% | 0% |
| escasez | 600–999 999 | — | — | — | — | — |

> **Fallback** (mediana global del estudio, para contextos sin datos): cobertura 0 %, exposición 100 %, no regulado 0 %, SICEP 0 %.

## 4. Simulación en la ventana de impacto (2025-07-25 → 2025-07-31)

XXXC replica cada día el perfil recomendado y se calcula su margen con la misma lógica del estudio (C16–C18 sobre precios de sistema). Se compara contra la **mediana real** de los maestros y del segmento ese día en los datos cargados.

| Fecha | Contexto | Escasez | Cobertura | Exposición | Margen imitación | Mediana maestros | Mediana segmento |
|---|---|---|---|---|---|---|---|
| 2025-07-25 | muy_barata | no | 0% | 100% | 88.51 | 88.51 | -65.47 |
| 2025-07-26 | muy_barata | no | 0% | 100% | 94.22 | 94.22 | -91.68 |
| 2025-07-27 | muy_barata | no | 0% | 100% | 103.38 | 103.38 | -125.28 |
| 2025-07-28 | muy_barata | no | 0% | 100% | 72.98 | 72.98 | -69.97 |
| 2025-07-29 | muy_barata | no | 0% | 100% | 86.20 | 86.20 | -47.04 |
| 2025-07-30 | muy_barata | no | 0% | 100% | 48.74 | 48.74 | -58.30 |
| 2025-07-31 | muy_barata | no | 0% | 100% | 49.52 | 49.52 | -32.62 |

## 5. Balance del impacto

| Métrica | Imitación (XXXC) | Maestros (real) | Segmento (real) |
|---|---|---|---|
| Mediana margen (COP/kWh) | 86.20 | 86.20 | -65.47 |
| Media margen (COP/kWh) | 77.65 | — | — |
| % días que la imitación gana | — | 0.00 | 100.00 |

La imitación logra una mediana de **86.2 COP/kWh/día** frente a **86.2** de sus maestros reales (delta **+0.0**) y **-65.5** del segmento. Recuerda: el margen es un artefacto de modelado, válido para comparar entre sí.

Demanda diaria simulada: **67 758 kWh** (0.068 GWh).

## 6. Advertencias y limitaciones

1. El margen es un artefacto de modelado (Pv=350 COP/kWh fijo, precios de sistema): sirve para comparar estrategias, no como margen real del negocio.
2. Behavioral Cloning no generaliza fuera de la distribución de spread del estudio; los bins sin entrenamiento se resuelven con el bin más cercano o el fallback.
3. La ventana de impacto usa datos ya cargados en elecdb; es retrospectiva, no predicción en vivo.
4. Los maestros se eligen dentro de su segmento: el asistente no compite contra GRANDE por diseño.
5. Solo se encontraron 4 agentes en el (segmento, estrategia) de la ventana de estudio; el top pedido era 5.
