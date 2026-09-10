# Plan — Scorecard de aceptación y búsqueda autónoma de una combinación operable

> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **ejecutado — veredicto NO-OPERABLE** (evidencia en `docs/scorecard_aceptacion.md`)
> Documentos relacionados: `docs/plan_agente_xxxc_asistente.md` (plan del asistente),
> `docs/investigacion_imitacion_traders_profesionales.md` (investigación y diagnóstico),
> `docs/informe_asistente_imitador.md` y `docs/informe_barrido_combinaciones.md` (salidas actuales).

---

## 1. Objetivo y decisiones acordadas

Mejorar el asistente imitador hasta que sea **aceptable según métricas objetivas**, trabajando de forma
autónoma (harness reproducible + iteraciones). Decisiones acordadas con el dueño del proyecto:

| Decisión | Elección |
|---|---|
| Definición de "aceptable" | **Operable estricto**: debe existir **≥1** (segmento × estrategia × ventana) que pase **N0+N1+N2+N3** en una corrida reproducible. Si ninguna pasa tras el presupuesto → veredicto **NO-OPERABLE** con evidencia. |
| Recompensa | **Fija: margen C16–C18 relativo al segmento** (selección por `seleccion_por_relativo`, S1). No se cambia la definición de premio. |
| Alcance de autonomía | **Todo, incl. SQL y datos** (nuevas queries, contexto adicional, ventanas históricas). No se toca la recompensa. |
| Presupuesto | **Por iteraciones**: máximo 30 iteraciones del harness. Cada iteración = 1 experimento reproducible medido contra el scorecard. Al agotarse → veredicto final. |

## 2. Diagnóstico (por qué hoy NO es operable)

Combinación objetivo actual (PEQUEÑO · Trader expuesto a bolsa, top-10, 2025):

| Gate | Valor hoy | Umbral propuesto | Estado |
|---|---|---|---|
| Bootstrap skill-vs-luck | p=0.993 | ≤ 0.05 | ✗ |
| N efectivo de maestros | 1 de 3 | ≥ 3 | ✗ |
| Holdout de selección | 66.7 % | ≥ 50 % | ✓ |
| Replicación IS→OOS | 0.96 | ≥ 0.5 | ✓ |
| DSR | 0.94 | ≥ 0.95 | ✗ |
| Barrido (todas las combos, 2025) | 0 válidas | ≥ 1 | ✗ |
| Walk-forward 2026 (6 ventanas) | kill-switch en las 6, DSR=0 | mayoría positivas | ✗ |

Causas de fondo:
1. **Recompensa-artefacto**: el margen C16–C18 usa Pv=350 fijo + impuestos/provisión/garantías
   (`kpi_cartera.py:17`). Relativizado al segmento cancela el nivel, pero los agentes de la misma
   estrategia quedan con series casi idénticas → correlación > 0.9 → **N_eff=1**. Con 1 maestro
   independiente el bootstrap no puede dar p<0.05 por construcción.
2. **N pequeño en la ventana actual**: la estrategia objetivo tiene 3 agentes en la ventana de 2025
   (y son duplicados entre sí). Imposible N_eff≥3 con esa ventana.
3. **Selección circular**: maestros elegidos in-sample por la misma métrica de evaluación.
4. **Régimen 2026**: el walk-forward muestra margen muy negativo y kill-switch en todas las ventanas.

### Hallazgo de viabilidad (cambia el diagnóstico)

`fact_hourly_agente` tiene datos por agente **2015→2026-07-31** (145→265 agentes/año, días completos),
no solo precios de sistema como afirmaba la investigación. Esto abre un espacio de búsqueda de **~11 años**
con regímenes Niño (2015-16, 2023-24) donde el spread ejercita los bins `cara`/`escasez` y donde la
dispersión real de skill entre cubiertos y descubiertos puede aparecer en el margen relativo.

## 3. Criterios de aceptación (scorecard por niveles)

**Regla global:** ACEPTABLE-OPERABLE si existe **≥1** (segmento × estrategia × ventana) que pase
**N0+N1+N2+N3** en una corrida reproducible **y** reproducible por defecto (`python -m sfeia.main` apunta a
esa combinación). El resto de combinaciones nunca se recomiendan. Si ninguna cumple tras el presupuesto →
**NO-OPERABLE** con `docs/scorecard_aceptacion.md` completo.

### N0 — Integridad (obligatorio, no negociable)

| Gate | Umbral | Verificación |
|---|---|---|
| N0.1 Tests | `./.venv/bin/python -m pytest -q` verde | comando |
| N0.2 Determinismo | Misma semilla (42) → scorecard idéntico byte a byte | re-ejecución |
| N0.3 Sin look-ahead | `information_set` auditable (spread previo, contrato del día, embalses) | test de auditoría |
| N0.4 Errores claros | Ventanas inválidas fallan con mensaje explícito | test existente |

### N1 — Validez de la selección (obligatorio para recomendar)

| Gate | Umbral |
|---|---|
| V1 Bootstrap skill-vs-luck | p ≤ 0.05 (una cola, n_boot=1000, sobre margen relativo) |
| V2 N efectivo de maestros | ≥ 3 |
| V3 Holdout de selección | persistencia ≥ 50 % |
| V4 Replicación IS→OOS | ratio ≥ 0.5 |
| V5 DSR | ≥ 0.95 |

### N2 — Económico / riesgo (obligatorio para recomendar)

| Gate | Umbral |
|---|---|
| E1 % días imitación gana al segmento (OOS) | ≥ 60 % |
| E2 Kill-switch | no activado en ventana de impacto benigna |
| E3 Expectativa | EV ≥ 0 bajo frecuencia histórica de escasez; EV bajo año Niño se reporta como riesgo (no gate) |
| E4 Capacidad | demanda de XXXC ≤ 5 % de la demanda del segmento |

### N3 — Robustez (obligatorio para recomendar)

| Gate | Umbral |
|---|---|
| R1 Walk-forward | ≥ 6 ventanas contiguas de la combinación validada: réplica ≥ 0.5 en ≥ 70 % de ventanas; margen relativo OOS positivo en ≥ 70 %; DSR de la curva OOS cosida ≥ 0.95 |
| R2 Múltiples pruebas | p-valor corregido por Bonferroni (p ≤ 0.05 / n_combos probadas) o trials reales en el DSR |

### N4 — Fidelidad del clon (monitoreo, no bloquea)

| Gate | Umbral |
|---|---|
| F1 MAE del perfil clonado vs. perfil realizado de los maestros (OOS) | ≤ 10 pp por feature |

## 4. Fases de ejecución (máx. 30 iteraciones)

### Fase 0 — Harness `--aceptacion` (iter 0)

- Nuevos módulos: `sfeia/app/controllers/fase_aceptacion.py`, `sfeia/app/services/scorecard.py`,
  vistas para `docs/scorecard_aceptacion.md` y `data/scorecard.csv`.
- Corre barrido + walk-forward sobre un **grid de ventanas 2015→2026** (estudio 90 días + impacto 7–14,
  rodando mensual, regímenes benigno y Niño), **cacheando el estudio por ventana** (como ya hace
  `ejecutar_barrido`) y reusándolo para todas las combinaciones.
- Registra por corrida: config snapshot, semilla, parámetros, resultados por (segmento × estrategia × ventana).
- Los arquetipos se **descubren por ventana** (el k-means etiqueta por ventana; el scan lista las
  estrategias reales de cada una).

### Fase 1 — Feasibility scan (iters 1-2, con corte temprano)

- Scan grueso (n_boot=200) sobre todo el grid: p, N_eff, holdout, réplica, DSR por combinación.
- **Corte temprano:** si ninguna (segmento, estrategia, ventana) alcanza p≤0.05 **y** N_eff≥3 →
  veredicto NO-OPERABLE de inmediato (ahorra el presupuesto) con el scorecard como evidencia.

### Fase 2 — Confirmar y pulir candidatas (iters 3-10)

- Confirmación fina (n_boot=1000, DSR con trials reales) de las candidatas que pasaron el scan.
- Palancas de selección (1 por iteración, comparando scorecard):
  - Ventana de estudio 30 → 90–180 días (más agentes-día, medianas estables, más candidatos por combo).
  - Ranking por riesgo (Sortino / downside / margen-a-drawdown) en `maestros.seleccionar_maestros`.
  - Dedup refinada (perfil + serie) y ajuste de `top` / `min_dias_pct`.

### Fase 3 — Política (iters 11-20)

- Bins de spread re-calibrados por percentiles del **histórico** (no fijos), para que los contextos
  `cara`/`escasez` entren con datos en la política.
- Régimen hidrológico como variable de **política** (no solo informativo).
- EWA online con decaimiento en `clonacion` / `maestros.pesos_maestros`.
- Zona de confianza y kill-switch calibrados por régimen.

### Fase 4 — Robustez y cierre (iters 21-30)

- Walk-forward ≥ 6 ventanas contiguas de la(s) candidata(s) con confirmación fina; si falla, rotar a la
  siguiente candidata.
- **Cierre ACEPTABLE:** config por defecto apunta a la combinación+ventana validada; `python -m sfeia.main`
  la produce por defecto; se actualizan AGENTS.md, README, informes; commits "Checkpoint:" por fase.
- **Cierre NO-OPERABLE:** `docs/scorecard_aceptacion.md` completo + informe de por qué C16–C18 relativo no
  deja señal en ningún régimen.

## 5. Palancas permitidas (sin tocar la recompensa)

- **SQL/datos**: ampliar `d1_diario` a ventanas históricas (ya paramétrica), contexto adicional (volatilidad
  del spread, nivel de embalses como input de política), query de "estrategias por ventana" para el scan.
- **Config**: `top`, `min_dias_pct`, `bins_spread` (percentiles históricos), `dias_holdout`, `n_boot`,
  `alpha` (con Bonferroni), `umbral_corr_duplicados`, `pesos_eta`, `factor_exposicion_fuera_distribucion`,
  `kill_switch_drawdown_cop_kwh`, ventanas.
- **Metodología (services)**: ranking por riesgo, dedup por perfil+serie, EWA con decaimiento, réplica por
  régimen, persistencia sobre ventanas móviles.
- **No permitido**: cambiar el premio C16–C18 relativo, aflojar umbrales de aceptación, sobre-afirmar.

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Costo del grid completo (k-means por ventana) | Cache del estudio por ventana; scan grueso (n_boot=200) primero; confirmación fina solo sobre candidatas |
| Etiquetas de arquetipo inestables entre ventanas | Los arquetipos se descubren por ventana; el scan las lista explícitamente |
| DSR ruidoso en ventanas cortas | Se evalúa sobre la curva OOS cosida (R1), no ventana a ventana |
| El premio puede no dejar señal en ningún régimen | El veredicto NO-OPERABLE es un resultado válido y honesto; **no** se aflojan umbrales para forzar un pase |
| Regresión en funcionalidad existente | Commit de retorno (`docs/plan_aceptacion_imitador.md` + estado actual); tests verdes por fase |

## 7. Criterio de parada

- **ACEPTABLE:** el scorecard muestra ≥ 1 combinación operable (N0+N1+N2+N3 verdes) y
  `python -m sfeia.main` la corre por defecto.
- **NO-OPERABLE:** agotadas las 30 iteraciones (o corte temprano de la Fase 1) sin ninguna combinación
  operable; se entrega el scorecard completo y el informe de evidencia.

## 8. Ejecución (2026-09-09) — veredicto final

**Fases ejecutadas:** 0 (harness `--aceptacion`) y 1 (feasibility scan). El **corte temprano** de la Fase 1 se
activó: el harness barrió el grid completo (138 ventanas, 984 combinaciones, 2015→2026-07-31) y **ninguna**
combinación alcanzó el gate V1 (bootstrap skill-vs-luck p ≤ 0.05; mínimo observado **0.4577**, mediana 1.0).
No hay candidatas que confirmar, por lo que las fases 2–4 (pulir política, walk-forward, config por defecto)
**no se ejecutaron** por diseño: no se relajan umbrales para forzar un pase.

**Evidencia (resumen del scorecard):**

| Gate | Combinaciones que pasan (de 984) | % |
|---|---|---|
| V1 · bootstrap p ≤ 0.05 | 0 | 0.0 |
| V2 · N efectivo ≥ 3 | 633 | 64.3 |
| V4 · replicación ≥ 0.5 | 879 | 89.3 |
| V5 · DSR ≥ 0.95 | 444 | 45.1 |
| E1 · % días > segmento ≥ 60 | 471 | 47.9 |
| E2 · sin kill-switch | 769 | 78.2 |
| E3 · EV histórico ≥ 0 | 452 | 45.9 |
| E4 · capacidad ≤ límite | 845 | 85.9 |
| N1 cheap + N2 (candidatas) | **0** | 0.0 |

**Veredicto: NO-OPERABLE.** Con el premio C16–C18 relativo al segmento (recompensa fija acordada) no existe
señal de skill cross-sectional imitable en ningún (segmento × estrategia × ventana) de los 11 años analizados:
los agentes de una misma estrategia son conductualmente homogéneos (misma acción → margen relativo casi
idéntico), el "top" es suerte entre iguales, y el bootstrap no lo puede separar. La corrección del determinismo
(N0.2) se resolvió en la capa SQL (`MAX` en vez de `AVG` para precios de sistema; `ROUND` de sumas en F-1).

**Lecciones para una futura aceptación:**
1. La única palanca que podría crear señal es **cambiar la recompensa** (p. ej. margen bruto sin el modelo
   contable, o ground truth XM) — decisión explícitamente excluida por el dueño en esta iteración.
2. El harness `--aceptacion` queda operativo: si cambian la recompensa o los datos, se re-corre un solo comando.