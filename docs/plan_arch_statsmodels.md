# Plan — Validación estadística con `arch` + `statsmodels` (uso máximo, aislado)

> Proyecto: SFEIA · Fecha: 2026-09-10 · Estado: **aprobado en diseño, pendiente de implementación**
> (interrumpido por la tarea prioritaria del dashboard semanal)
> Origen: investigación de librerías para skill-vs-luck, DSR, comparaciones múltiples y régimen.

---

## 0. Resumen

La capa de **dominio** del proyecto (SQL MEM, margen C16–C18, segmentación, política) no la cubre
ninguna librería y se conserva. La capa de **validación estadística** sí se reimplementó a mano y es
donde `arch` (8.0.0) y `statsmodels` (0.15) aportan métodos maduros y probados:

- `arch.bootstrap`: bootstraps IID/estacionario/de bloques, IC de cualquier estadístico, y
  **comparaciones múltiples** (`SPA`/Reality Check, `StepM`, `MCS`).
- `arch.unitroot`, `arch.cointegration`, `arch.covariance.kernel`, `arch.arch_model` (GARCH).
- `statsmodels`: FDR (`multitest`), proporciones con IC, McNemar pareado, tests no paramétricos,
  poder y tamaño de muestra, quiebres estructurales, Markov-switching, meta-análisis, regresión
  cuantil, knockoffs, HAC (Newey–West).

Ni `arch` ni `statsmodels` traen el Deflated Sharpe Ratio empaquetado: el DSR se calcula **por
bootstrap** (distribución nula del máximo Sharpe), manteniendo la fórmula cerrada actual como contraste.

## 1. Principios de diseño

- **Aislamiento:** todo el contacto con `arch`/`statsmodels`/`pandas` vive en **un solo módulo nuevo**,
  `sfeia/app/services/validacion.py`. Entra y sale `list[float]`/`np.ndarray`/`dict`; ningún objeto
  pandas cruza la frontera.
- **Compatibilidad:** no se rompen las claves actuales (`p_valor`, `dsr`, `ratio_replicacion`, …);
  se **añaden** claves nuevas; las vistas las muestran.
- **Determinismo:** toda llamada lleva `semilla` explícita; se preserva el requisito N0.2 del scorecard
  (byte-a-byte idéntico).
- **Arquitectura MVC:** `validacion.py` es un service (lógica pura, sin BD); los controllers inyectan
  datos y consumen resultados.

## 2. Dependencias y configuración

- `requirements.txt`: añadir `arch==8.0.0`, `statsmodels==0.15.*` (arrastran `pandas`, solo usado
  dentro de `validacion.py`).
- `sfeia/config/config.yaml`, nueva sección:

```yaml
validacion:
  metodo_ic: bca            # bca | percentile | studentized
  n_boot: 2000              # bootstrap fino (confirmación)
  n_boot_scan: 200          # bootstrap grueso (barrido/aceptación)
  alpha: 0.05
  metodo_fdr: fdr_bh        # bonferroni | holm | fdr_bh | fdr_by | ...
  block_size: null          # null -> arch.bootstrap.optimal_block_length
  n_trials_registro: true   # registrar N honesto de combinaciones probadas
  spa_benchmark: segmento   # segmento | cero
  mcs_size: 0.10
  dsm: bootstrap            # bootstrap | formula | ambos
```

## 3. Módulo nuevo `sfeia/app/services/validacion.py`

Funciones puras (entrada listas/ndarray, salida dict):

**3.1 Bootstrap (`arch.bootstrap`)**
- `bootstrap_ic(serie, func, n_boot, metodo_ic, block_size, semilla)` — `StationaryBootstrap`/`IIDBootstrap`
  + `.conf_int(func, method=...)`.
- `bootstrap_max_mediana(series_por_unidad, n_boot, block_size, semilla)` — nula del máximo de N
  medianas por **bloques** (reemplaza el remuestreo IID de `bootstrap_skill_luck`): `p_valor`, IC.
- `bootstrap_ratio(serie_is, serie_oos, n_boot, semilla)` — IC bootstrap del ratio de replicación.
- `optimal_block_size(serie)` — `arch.bootstrap.optimal_block_length`.

**3.2 DSR por bootstrap**
- `dsr_bootstrap(margenes, n_trials, n_boot, block_size, semilla)`:
  1. Sharpe observado de la serie de la imitación.
  2. H0 sin skill: centrar la serie (media 0) y remuestrear por bloques `n_trials` veces tomando el
     **máximo Sharpe** de cada réplica → nula del max-Sharpe.
  3. `dsr_boot = P(max-Sharpe_nulo < Sharpe_obs)`; `p_valor = 1 - dsr_boot`.
  - Devuelve además `sharpe_diario, skew, kurt, n_trials, dsr, significativo` (compatibilidad).
- `dsr_formula(...)`: conservar `dsr_aprox` actual como contraste (modo `ambos`).

**3.3 Comparaciones múltiples**
- `spa(benchmark_losses, models_losses, ...)` — `arch.bootstrap.SPA` (pvalues lower/consistent/upper).
- `stepm(...)` — `arch.bootstrap.StepM` (`superior_models`).
- `mcs(losses_matrix, size)` — `arch.bootstrap.MCS` (included/excluded; plateau vs spike).
- `fdr(p_valores, alpha, metodo)` — `statsmodels.stats.multitest.multipletests`.

**3.4 Inferencia de proporciones y pareada**
- `proporcion_ic(k, n, metodo='wilson')`, `test_proporcion(k, n, p0=0.5)` — `statsmodels.stats.proportion`.
- `mcnemar(gana_a, gana_b)` — `statsmodels.stats.contingency_tables.mcnemar` (imitación vs maestros).
- `rank_compare(a, b)` — `statsmodels.stats.nonparametric.rank_compare_2indep` + `prob_larger_continuous`.
- `tost(a, b, margen)` — `statsmodels.stats.weightstats.ttost_ind` (equivalencia → duplicados).
- `diebold_mariano(loss_a, loss_b)` — `statsmodels.tsa.stattools.diebold_mariano_test`.

**3.5 Series temporales / régimen**
- `estacionariedad(serie)` — `arch.unitroot` (ADF, KPSS, ZivotAndrews).
- `quiebres(serie)` — `statsmodels.stats.diagnostic.breaks_cusumolsresid` / `breaks_hansen`.
- `regimen_markov(serie, k=2)` — `statsmodels.tsa.regime_switching.MarkovRegression`.
- `cointegracion(a, b)` — `arch.cointegration.EngleGranger` (bolsa vs contrato).

**3.6 Poder, meta-análisis, modelado**
- `poder_ttest`, `poder_proporciones`, `tamano_muestra(...)` — `statsmodels.stats.power`.
- `meta_efectos(efectos, errores)` — `statsmodels.stats.meta_analysis.combine_effects` (I²).
- `regresion_cuantil(y, X, q)` — `statsmodels.regression.quantile_regression.QuantReg`.
- `garch_vol(serie)` — `arch.arch_model`.
- `hac_se(y, X)` — `statsmodels.stats.sandwich_covariance.cov_hac`.
- `knockoffs(X, y)` — `statsmodels.stats.knockoff_regeffects`.

## 4. Integración archivo por archivo

| Archivo | Cambio |
|---|---|
| `services/validacion.py` | **Nuevo** (todo §3) |
| `services/maestros.py` | `bootstrap_skill_luck` → `validacion.bootstrap_max_mediana`; `persistencia_seleccion` → IC Wilson + binom; `detectar_duplicados` → opción TOST; `sensibilidad` → MCS |
| `services/simulacion.py` | `dsr_aprox` se conserva; nuevo `dsr_bootstrap` (delegado) y `replicacion_is_oos` con IC; `distribucion` enriquecida con GARCH/robustos |
| `services/scorecard.py` | `evaluar_gates` → p-valor FDR y gates nuevos (`V1_fdr`, `V1_spa`, `V6_mcs`); `fidelidad_mae` → DM test |
| `controllers/fase_asistente.py` | `ejecutar`: DSR bootstrap + estacionariedad + StepM/SPA del objetivo + IC de proporciones. `ejecutar_scan_ventana(_arquetipo)`: acumular series de pérdida diaria por combinación para SPA/MCS y aplicar FDR. `ejecutar_barrido`: SPA/StepM + FDR |
| `controllers/fase_aceptacion.py` | `_scan_modo`: FDR y SPA/StepM por ventana; nuevo `valida_fdr`. `_confirmar`: DSR bootstrap + McNemar + IC |
| `controllers/estudio_poder.py` | reemplazar `_bootstrap_cross_segmento` por `arch`; añadir `statsmodels.stats.power` (tamaño de muestra / MDE) |
| `services/contexto.py` | helpers de régimen (quiebres, Markov) sobre spread/embalses |
| `views/*.py` | nuevas columnas/secciones: FDR, IC, p-SPA, MCS, DM, régimen |
| `config/config.yaml` | sección `validacion:` |
| `requirements.txt` | `arch`, `statsmodels` |
| `tests/test_validacion.py` | **Nuevo** |
| `AGENTS.md` | documentar el módulo y las dependencias |

## 5. Fases de ejecución

**Fase A — Comparaciones múltiples (mayor valor)**
1. Crear `validacion.py` con `spa/stepm/mcs/fdr`.
2. `fase_aceptacion._scan_modo`: matriz T×k de pérdidas por ventana + FDR + SPA/StepM.
3. `fase_asistente.ejecutar_barrido`: SPA/StepM + FDR.
4. `scorecard.evaluar_gates`: gate FDR.
5. Tests: datos sintéticos sin skill no deben ser rechazados.

**Fase B — Reemplazar inferencia casera**
6. `bootstrap_skill_luck` → arch con bloques + `optimal_block_length`.
7. `persistencia_seleccion` → IC Wilson + binom.
8. `pct_dias_gana_segmento` / `replicacion` → IC bootstrap.
9. `mcnemar` imitación vs maestros; `rank_compare` para maestros.
10. `sensibilidad` → MCS.

**Fase C — DSR por bootstrap y régimen**
11. `dsr_bootstrap` y switch de callers; `dsr_aprox` como contraste.
12. `estacionariedad` + `quiebres` + `regimen_markov`; formalizar "operabilidad por régimen".
13. `meta_efectos` sobre las 138 ventanas.

**Fase D — Modelado al máximo**
14. `estudio_poder` con `statsmodels.stats.power`.
15. `regresion_cuantil`, `garch_vol`, `hac_se`, `cointegracion`.
16. `knockoffs` para features de contexto.

## 6. Verificación

- `./.venv/bin/python -m pytest -q` (nuevos tests de `validacion`: SPA sobre ruido ≈ 1; DSR bootstrap de
  serie sin skill ≈ 0.5; FDR sobre p-valores uniformes no rechaza).
- Reproducir el scorecard antes/después y confirmar que el veredicto se endurece de forma trazable.
- Test de determinismo: dos corridas con la misma semilla → salida idéntica (N0.2).
- Smoke test de integración del barrido y aceptación con la BD local.

## 7. Riesgos y decisiones abiertas

1. **Alineación temporal para SPA/MCS:** cada combinación tiene ventanas válidas distintas. Propuesta:
   matriz T×k sobre la **intersección de días**; si queda corta, restringir a combinaciones con cobertura
   completa. Pendiente de confirmación.
2. **Costo:** DSR bootstrap + SPA sobre 138×984 con `n_boot=2000` es pesado → `n_boot_scan` bajo en
   barrido, fino solo en confirmación.
3. **`n_trials` honesto:** el DSR depende de cuántas combinaciones se probaron; se registrará en el
   scorecard (idea tomada de `sharpe-gate`).
4. **Determinismo:** fijar semilla en cada llamada a arch/statsmodels.
5. **Peso de pandas:** aunque aislado, es dependencia dura de ambas librerías.
