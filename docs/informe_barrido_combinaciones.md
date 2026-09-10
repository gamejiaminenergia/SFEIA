# Barrido de combinaciones (segmento × estrategia) — ¿dónde hay señal?

> **Advertencia (léela antes que nada):** este es un **ejercicio descriptivo sobre comportamiento pasado** con un margen de **modelado** (Pv=350 COP/kWh fijo, precios promedio de sistema). Los márgenes aquí son artefactos matemáticos para comparar estrategias entre sí, **no dinero real ni una recomendación de inversión**. La selección usa el **margen relativo al segmento** (cancela el artefacto); la mediana absoluta se reporta como contexto.

Ventana de estudio: **2025-06-25 → 2025-07-24** · Ventana de impacto: **2025-07-25 → 2025-07-31**.

Filtros de validez (S2): bootstrap p-valor ≤ 0.05 · replicación IS→OOS ≥ 0.5 · N efectivo de maestros ≥ 3.

## Resultado: ninguna combinación pasó la validez

Con este margen de modelado y estas ventanas, **ninguna** (segmento × estrategia) supera el filtro. Esto es información útil: el mercado no es imitable de forma estadísticamente robusta con los datos actuales. Las mejores candidatas (más abajo) son las menos malas, pero NO pasan la barrera.

## Ranking de combinaciones (válidas primero)

| Segmento | Estrategia | N maestros | N efectivo | Códigos | Relativo top (COP/kWh) | Margen abs. mediana (COP/kWh) | p-valor | Replicación IS→OOS | Válida | Kill-switch |
|---|---|---|---|---|---|---|---|---|---|---|
| PEQUEÑO | Trader expuesto a bolsa (sin cobertura) | 3 | 1 | RPEC, VICC, HIMC | 142.76 | 86.20 | 0.9801 | 0.97 | no | no |
| PEQUEÑO | Integrado/regional regulado | 10 | 9 | EBSC, CHCC, EDQC, EMPC, ENIC, EVSC, TENC, CASC, EDPC, EMSC | 33.61 | -21.93 | 1.0000 | 1.04 | no | no |
| PEQUEÑO | Trader no regulado | 10 | 10 | FREC, GAPC, EXIC, CMXC, CBNC, DRUC, BEIC, TRPC, LESC, GNYC | 18.54 | -52.42 | 1.0000 | 1.02 | no | no |
| MEDIANO | Trader no regulado | 1 | 1 | GECC | 12.46 | -1.12 | 0.5174 | 2.73 | no | no |
| MEDIANO | Integrado/regional regulado | 9 | 9 | ESSC, CNSC, CSIC, CMMC, EMIC, ENDC, EPMC, EPSC, GNCC | 0.00 | -11.88 | 1.0000 | 1.08 | no | no |
| MEDIANO | Trader con sobrecobertura de contratos | 2 | 2 | SOEC, ISGC | -53.23 | -62.00 | 1.0000 | 1.01 | no | no |
| PEQUEÑO | Trader con sobrecobertura de contratos | 10 | 6 | ASCC, ETTC, CHVC, CMXC, EMEC, BEIC, VESC, PEEC, SCEC, FERC | -211.33 | -238.03 | 1.0000 | 1.00 | no | sí |

**Lectura:** *Relativo top* es la mediana del margen relativo al segmento del top-N (positivo = los maestros superaron a su segmento). *Válida* combina p-valor, replicación y N efectivo. *Kill-switch* indica si el drawdown del período superó el umbral de protección.