# AGENTS.md — SFEIA

Asistente imitador del agente XXXC sobre el Mercado de Energía Mayorista (MEM) colombiano: Python + SQL sobre PostgreSQL (elecdb/XM), **un solo paquete MVC (`sfeia/`)**, sin framework web. Behaviora Cloning del top-N de un (segmento, estrategia).

## Estructura (un solo paquete)
- **`sfeia/` = TODO el proyecto** (MODEL `app/models` · CONTROLLERS `app/controllers` · SERVICES `app/services` · VIEWS `app/views`). El estudio híbrido diario es el **motor** interno; el **asistente** es la aplicación (`sfeia.main`).
- **`docs/` (raíz)** = plan e informe del asistente (salida generada). **`data/` (raíz)** = CSV del asistente (salida generada).
- Se eliminó la duplicación anterior (`asistente/` aparte) y todo el **código legacy** de los estudios reemplazados (fase_cartera/clustering/cobertura/contexto/financiera/mix/muestra/picovalle/sintesis, pipeline, informe_md, informe_clusters_md, kpi_cobertura, tipificacion, SQL f0–f5) y sus salidas `.md`/`.csv` en `sfeia/` ya **no existen** ni se generan.

## Comandos
- Ejecutar el asistente imitador (único punto de entrada): `./.venv/bin/python -m sfeia.main [--segmento PEQUEÑO] [--estrategia "..."] [--top 5] [--estudio-ini ...] [--estudio-fin ...] [--impacto-ini ...] [--impacto-fin ...] [--demanda-dia-gwh ...]`
- Modo walk-forward (serie de ventanas rodantes, P2.3): `./.venv/bin/python -m sfeia.main --walk-forward` → `data/walk_forward.csv`.
- Modo barrido (S2): `./.venv/bin/python -m sfeia.main --barrido` evalúa TODAS las (segmento × estrategia), las filtra por validez y exporta `data/barrido_combinaciones.csv` + `docs/informe_barrido_combinaciones.md`.
- Tests unitarios (lógica pura, sin BD): `./.venv/bin/python -m pytest -q`
- Dependencias (psycopg2-binary, pyyaml, pytest, requests, scikit-learn, scipy, numpy) solo existen en `.venv`; el Python del sistema no las tiene.

## Asistente imitador (Behavioral Cloning del top-N) — `sfeia.main`
- **Filosofía:** imitar, no predecir. Clona el comportamiento de los **top-N** agentes de un (segmento, estrategia) en una **ventana de estudio** y lo replica en una **ventana de impacto**. Plan en `docs/plan_agente_xxxc_asistente.md`; investigación y diagnóstico en `docs/investigacion_imitacion_traders_profesionales.md`.
- **Flujo (`FaseAsistente`):** valida ventanas contra `repo.fecha_max_sistema()` (la BD llega a 2026-07-31; el proyecto corre sobre **2025**, que tiene el año completo; error claro si la ventana excede la BD) → corre F-1+FaseDiaria sobre la ventana de estudio (config con `ventana` sobreescrita) → `seleccionar_maestros` (top-N por mediana del margen + métricas de riesgo, guarda `min_dias_pct`) → pruebas de **validez** (bootstrap skill-vs-luck, holdout de selección si `dias_holdout>0`, DSR, replicación IS→OOS) → `construir_politica` (BC por bin de `bins_spread`, ponderada por `pesos_maestros` si `ponderar_politica`, con zona de confianza `rango_spread`) → simula a XXXC en el impacto con `diario.desempeno_diario` (demanda = mediana del segmento o `--demanda-dia-gwh`), usando **spread del día anterior** (`usar_spread_previo`, sin look-ahead) y nivel de embalses (`d1_contexto_hidrologia.sql`).
- **Validez (P0):** `bootstrap_skill_luck` (¿el top-N supera al azar?), `persistencia_seleccion` (holdout), `detectar_duplicados` con correlación de series (N efectivo), métricas de riesgo en `AgenteMaestro`, `dsr_aprox` y `replicacion_is_oos`. La selección usa **margen relativo al segmento** (`seleccion_por_relativo`, S1): cancela el artefacto Pv=350.
- **Política (P1):** `usar_spread_previo` (ex-ante), `ponderar_politica`/`pesos_eta` (agregación tipo EWA en `clonacion._perfil_ponderado`), `factor_exposicion_fuera_distribucion` (P1.3: fuera de `rango_spread` reduce exposición trasladando a contratos), `usar_regimen_hidrologico` (embalses).
- **Negocio (P2):** `capacidad_max_pct_segmento` (P2.1), `kill_switch_drawdown_cop_kwh` (P2.2), `--walk-forward` (P2.3), ground truth pendiente (P2.4, advertencia en el informe). S3: si la combinación pedida no valida, el informe propone `alternativa_recomendada` (mejor (segmento × estrategia) por margen relativo).
- **Ventanas por defecto y configuración:** un solo archivo `sfeia/config/config.yaml` (motor + simulador). Las fechas del simulador (`estudio_ini/fin`, `impacto_ini/fin`) viven en la sección `asistente:`; si están en `null`, se derivan del ancla del motor `ventana.foco_*` con `asistente.dias_estudio_por_defecto: 30` y `asistente.dias_impacto_por_defecto: 7`. El CLI (`--estudio-ini`, `--impacto-fin`, …) sobreescribe el config.
- **Módulos activos:** `sfeia/main.py` (CLI) · `sfeia/app/controllers/fase_asistente.py` · `sfeia/app/services/{contexto,maestros,clonacion,simulacion}.py` · `sfeia/app/views/{informe_asistente_md,informe_barrido_md,exportar_csv}.py` · `sfeia/tests/test_asistente.py`. Los `services` son lógica pura (no tocan BD); solo los controladores consultan el repo.
- **Salidas en la raíz:** `docs/informe_asistente_imitador.md` + `data/{maestros_topN, politica_clonacion, simulacion_impacto, resumen_impacto, distribucion_margenes, escenario_escasez, historial_escasez, validacion_seleccion}.csv` (y `data/walk_forward.csv` con `--walk-forward`, `data/barrido_combinaciones.csv` + `docs/informe_barrido_combinaciones.md` con `--barrido`). El informe incluye medidas de riesgo (distribución, drawdown, garantías), escenarios de estrés de escasez, frecuencia histórica de escasez (2015→hoy), robustez, **validez de la selección** (bootstrap/holdout/DSR/replicación) y **alternativa recomendada** si la combinación pedida no valida.

## Estudio híbrido diario (motor interno — no genera salidas propias)
- `FaseSegmentacion` (F-1) siempre segmenta TODOS los comercializadores con demanda en la ventana (65); no existe muestra.
- **Granularidad diaria:** `sfeia/sql/d1_diario.sql` agrega por (agente, día) demanda, contratos, bolsa, SICEP y precios de sistema en una pasada.
- **Clustering pooled:** K-Means sobre la matriz de ~65×212 agentes-día con las 6 features (`log_dema`, `pct_noreg`, `pct_cobertura`, `pct_exposicion`, `pct_sicep`, `tiene_sicep`), log1p en cobertura/exposición, clip cobertura 300. Silhouette plana (~0.4): **k se fija en 5** (`diario.k`); `k: null` lo devuelve a automático.
- **Desempeño y ranking:** margen estimado por kWh (lógica C16–C18, Pv=350) sobre agregados diarios; ranking por mediana del margen; balance del período.
- **Guardas (`diario:` en config):** `clip_margen_cop_kwh: 500` (winsoriza traders), `min_dias_pct: 20` (presencia marginal → atípicos), `clip_pct_sicep: 100`.
- **Granularidad por segmento:** el segmento es **variable de análisis** (no entra al k-means); `FaseDiaria` calcula ranking/balance por segmento (GRANDE/MEDIANO/PEQUEÑO).
- **Módulos del motor:** `sfeia/app/services/{diario,clustering,kpi_cartera,segmentacion}.py`, `sfeia/app/controllers/{fase_segmentacion,fase_diaria}.py`, `sfeia/tests/{test_segmentacion,test_diario}.py`.

## BD elecdb (PostgreSQL)
- Local: DSN default `postgresql://postgres:postgres@localhost:5432/postgres` en `sfeia/config/config.yaml` (override con `DB_DSN`). No se necesita `.env`.
- **Semántica de fechas por familia:** C01–C14 usan fin EXCLUSIVO (`fecha_hora < fin`); C15/C16–C18 INCLUSIVO (`< fin + 1 día`). `config.yaml` codifica el par (`fin_c_familia` vs `fin_c15`); reutilice esas claves. Ventana actual: Ene–Jul 2025 (`fin_c_familia: 2025-08-01`).
- `dim_agente.activity` usa tilde: `'COMERCIALIZACIÓN'`.
- C15 valora todo volumen con el precio promedio **de sistema** (no hay precio ni contraparte por agente): los valores COP son estimaciones.
- `fact_daily_sistema` tiene una fila por fecha (JOIN seguro por `ds.fecha = date(ha.fecha_hora)`). Límite de datos: **2026-07-31** (`RepoElecdb.fecha_max_sistema()`).
- **Funciones de BD rotas — no usarlas** (referencian columnas inexistentes): `fn_estudio_c06_ciiu`, `fn_estudio_c07_mercados`, `fn_estudio_c10_precio_contratos`, `fn_estudio_c14_upme_vs_real`, `fn_estudio_g10_combustibles`. Ante un error de columna inexistente, use consulta directa sobre `fact_*`/`dim_*`.

## Arquitectura (MVC)
- `sfeia/main.py` (CLI del asistente) → `FaseAsistente` → `FaseSegmentacion` + `FaseDiaria`; cada fase es un controlador en `sfeia/app/controllers/fase_*.py`.
- Toda consulta SQL vive en `sfeia/sql/` (un archivo por fase; varios statements separados por `;`). `sfeia/app/models/repositories.py` los ejecuta con un splitter que ignora `;` en comentarios/literales. Nunca SQL inline en controllers/views.
- `sfeia/app/services/` = lógica pura; `sfeia/app/views/` = renderizado Markdown/CSV. Views no consultan BD; models no renderizan.
- Configuración **única** en `sfeia/config/config.yaml`: el motor (`database`, `ventana`, `segmentacion`, `modelo_financiero`, `diario`) y el simulador (`asistente:`). `sfeia.main` la carga con `settings.load_config`. Cámbiala ahí, no en código.

## Modelo financiero (caveat crítico)
- C16–C18 se calculan en Python (`sfeia/app/services/kpi_cartera.py`); NO llamar `fn_agente_garantias_exigidas`/`fn_agente_margen_comercializacion` (re-escanean C15; ≈26 s por agente).
- El "margen" C18 usa Pv=350 COP/kWh fijo → es un **artefacto de modelado** (márgenes negativos artificiales en regulados), no el margen real del agente. Reportar con la advertencia.

## Docs
- `docs/plan_agente_xxxc_asistente.md` (raíz) = metodología del asistente imitador (activo).
- `docs/investigacion_imitacion_traders_profesionales.md` (raíz) = investigación y diagnóstico que guio P0–P2 + S1–S3.
- `docs/informe_asistente_imitador.md` (raíz) = salida generada por `python -m sfeia.main`; no editar a mano.
- `docs/informe_barrido_combinaciones.md` (raíz) = salida generada por `python -m sfeia.main --barrido`; no editar a mano.
- No existen planes/informes del estudio dentro de `sfeia/` (se eliminaron con el refactor).