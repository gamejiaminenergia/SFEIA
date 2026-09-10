# Experimento de poder estadístico (Ruta C)

> El margen es un artefacto de modelado (Pv=350 COP/kWh fijo). La selección usa el margen relativo al segmento. Ningún valor es dinero real.

Pregunta: ¿la señal operable que encontró el harness es un artefacto de bajo poder estadístico o de selección del pool? Las variantes usan el mismo premio C16-C18 relativo:

- **C1** bootstrap con n_boot=2000 (más simulaciones).
- **C2** ventana larga (365 d): más días por agente, mediana más precisa.
- **C3** pool entre segmentos: la nula se construye sobre TODA la estrategia, no solo el segmento.

## Combinaciones de ejemplo

| Ventana | Nota | Segmento · Estrategia | N agentes | p (n_boot=2000) | p (pool entre segmentos) |
|---|---|---|---|---|---|
| 2015-01-01..2015-03-31 | Niño 2015 (escasez) | PEQUEÑO · Comercializador regulado | 12 | 0.0005 | 0.001 |
| 2016-04-25..2016-07-23 | Niño 2016 | PEQUEÑO · Trader expuesto a bolsa (sin cobertura) | 6 | 0.0135 | 0.017 |
| 2019-03-11..2019-06-08 | benigno 2019 | PEQUEÑO · Comercializador regulado | 19 | 0.0005 | 0.007 |

## Ventana larga (C2)

| Ventana | Nota | N agentes | p (n_boot=2000) |
|---|---|---|---|
| 2015-01-01..2015-12-31 | ventana larga (365 d) · Comercializador regulado PEQUEÑO | 8 | 0.001 |

**Lectura:** si el p-valor operable se mantiene ≤ 0.05 con más simulaciones, en ventana larga y con una nula más amplia (pool entre segmentos), la señal NO es un artefacto de poder ni de selección del pool.

---
_Generado por `python -m sfeia.main --poder`. No editar a mano._