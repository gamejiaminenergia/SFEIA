# AGENTS.md — SFEIA

Análisis de estrategias de comercialización del MEM colombiano: Python + SQL sobre PostgreSQL (elecdb/XM), arquitectura MVC sin framework web. No es repo git.

## Estructura
- **`sfeia/` = paquete autocontenido del estudio actual** (lo que se reutilizará). Contiene `app/` (MVC), `config/`, `sql/`, `tests/`, `main.py`, y las salidas `docs/` y `data/`.
- La raíz del repo queda libre para el **simulador** (proyecto nuevo que importará funcionalidades vía `from sfeia.app.services import ...`). No mezclar código del simulador dentro de `sfeia/`.
- **`asistente/` (raíz) = simulador actual:** asistente imitador del agente XXXC (Behavioral Cloning del top-N), con su propio MVC (`asistente/app/`), CLI (`python -m asistente`), tests y salidas en la raíz (`docs/` y `data/`). Reutiliza de `sfeia` `RepoElecdb`, `FaseSegmentacion`, `FaseDiaria`, `diario` y el modelo financiero.

## Comandos
- Ejecutar el estudio híbrido diario (único) y regenerar el informe: `./.venv/bin/python -m sfeia.main`
- Tests unitarios (lógica pura, sin BD): `./.venv/bin/python -m pytest -q`
- Asistente imitador (raíz): `./.venv/bin/python -m asistente [--segmento PEQUEÑO] [--estrategia "..."] [--top 5] [--estudio-ini ...] [--estudio-fin ...] [--impacto-ini ...] [--impacto-fin ...]`
- Dependencias (psycopg2-binary, pyyaml, pytest, requests, scikit-learn) solo existen en `.venv`; el Python del sistema no las tiene.

## Estudio híbrido diario (único estudio — reemplaza al benchmark y al k-means de H1-2026)
- `sfeia/main.py` (sin flags) ejecuta `FaseSegmentacion` (F-1, población de 65) + `FaseDiaria` y genera `sfeia/docs/informe_estrategias_diarias.md`. Los informes de los estudios anteriores quedaron en `sfeia/docs/archivado/`; sus módulos (fase_*.py, pipeline.py, clustering, informe_md/informe_clusters_md) se conservan pero **no se invocan**.
- **Población completa, sin muestra:** `FaseSegmentacion` siempre segmenta TODOS los comercializadores con demanda en la ventana (65). Se eliminaron de config las listas `muestra:` y la clave `seleccion_muestra`; no existe concepto de muestra en el estudio.
- **Granularidad diaria:** `sfeia/sql/d1_diario.sql` agrega por (agente, día) demanda, contratos (compra/venta), bolsa (compra/venta), SICEP y precios de sistema (`PrecPromCont`, `PPPrecBolsNaci`, `PrecEsca`) en una pasada para los 65.
- **Clustering pooled:** K-Means sobre la matriz de ~65×212 agentes-día con las 6 features del estudio k-means (`log_dema`, `pct_noreg`, `pct_cobertura`, `pct_exposicion`, `pct_sicep`, `tiene_sicep`), transformaciones log1p en cobertura/exposición y clip cobertura 300. La silhouette es plana (~0.4) y no discrimina: **k se fija en 5** (`diario.k`); `k: null` lo devuelve a automático.
- **Desempeño y ranking:** margen estimado por kWh (lógica C16–C18, Pv=350) sobre agregados diarios; ranking diario por mediana del margen; balance del período (días 1.º, % top-3, rango promedio, tendencia).
- **Guardas de robustez (`diario:` en config):** `clip_margen_cop_kwh: 500` (winsoriza márgenes de traders con volumen >> demanda), `min_dias_pct: 20` (estrategias con presencia marginal → casos atípicos, fuera del ranking), `clip_pct_sicep: 100` (SICEP puede incluir no regulado).
- **Granularidad por segmento:** además del ranking pooled, `FaseDiaria` calcula ranking diario y balance del período **por segmento** (GRANDE/MEDIANO/PEQUEÑO) con los mismos arquetipos (segmento = variable de análisis, no entra al k-means). Resultados en `datos["diario"]["ranking_por_segmento"]`, `["balance_por_segmento"]` y `["estrategia_x_segmento"]` (mediana de medianas diarias, coherente con el balance).
- **Informe explícito para el lector:** sección 1 incluye la **tabla de criterios de segmentación** y la **tabla de los 65 comercializadores por segmento** (código, nombre, demanda GWh, % reg/no-reg); sección 3 abre con una **explicación en lenguaje de negocio de cada estrategia** (qué hace, cuándo le va mejor, riesgo principal). No editar a mano (`informe_diario_md.py`).
- **Módulos activos del estudio diario:** `sfeia/app/services/diario.py`, `sfeia/app/controllers/fase_diaria.py`, `sfeia/app/views/informe_diario_md.py`, `sfeia/app/views/exportar_csv.py`, `sfeia/tests/test_diario.py`. No tocar `fase_diaria.py`, `informe_diario_md.py` ni `exportar_csv.py` salvo para el estudio diario.
- **CSV exportados a `sfeia/data/`:** `main.py` además del informe genera `agentes_dia.csv`, `ranking_diario.csv`, `balance_periodo.csv`, `perfil_arquetipos.csv`, `matriz_puestos.csv`, `dias_mercado.csv` y los por-segmento `balance_por_segmento.csv`, `ranking_por_segmento.csv`, `estrategia_x_segmento.csv` (UTF-8 con BOM para Excel, cabeceras en español).

## Asistente imitador (simulador en la raíz)
- **Filosofía:** imitar, no predecir. En vez de crear estrategia propia (imposible de competir), clona el comportamiento de los **top-N** agentes de un (segmento, estrategia) en una **ventana de estudio** y lo replica en una **ventana de impacto**. Plan en `docs/plan_agente_xxxc_asistente.md`.
- **Flujo (`FaseAsistente`):** valida ventanas contra `repo.fecha_max_sistema()` (la BD llega a 2026-07-31; el proyecto corre sobre **2025**, que tiene el año completo; error claro si la ventana excede la BD) → corre F-1+FaseDiaria sobre la ventana de estudio (config con `ventana` sobreescrita) → `seleccionar_maestros` (top-N por mediana del margen, guarda `min_dias_pct`) → `construir_politica` (BC: mediana del perfil por bin de `bins_spread`, con fallback al bin más cercano) → simula a XXXC en el impacto con `diario.desempeno_diario` (demanda = mediana del segmento o `--demanda-dia-gwh`).
- **Módulos activos:** `asistente/main.py` (CLI), `asistente/app/controllers/fase_asistente.py`, `asistente/app/services/{contexto,maestros,clonacion,simulacion}.py`, `asistente/app/views/{informe_asistente_md,exportar_csv}.py`, `asistente/tests/test_asistente.py`. Los `services` son lógica pura (no tocan BD); solo el controlador consulta el repo.
- **Salidas en la raíz:** `docs/informe_asistente_imitador.md` + `data/{maestros_topN, politica_clonacion, simulacion_impacto, resumen_impacto}.csv`.
- **Config:** sección `asistente:` en `sfeia/config/config.yaml` (defaults, bins de spread, guardas). Añadido `RepoElecdb.fecha_max_sistema()` y `sql/d1_max_fecha.sql` (aditivos, no tocan el estudio).
- **Ventanas por defecto** (si no se pasan fechas): estudio = ventana principal menos los últimos `dias_impacto_por_defecto` días; impacto = esos últimos días.

## BD elecdb (PostgreSQL)
- Local: DSN default `postgresql://postgres:postgres@localhost:5432/postgres` en `sfeia/config/config.yaml` (override con `DB_DSN`). No se necesita `.env`.
- Esquema completo y funciones `fn_estudio_*` documentados en la skill `elecdb` (`~/.config/opencode/skills/mercado_energetico/SKILL.md`).
- **Funciones de BD rotas — no usarlas:** `fn_estudio_c06_ciiu`, `fn_estudio_c07_mercados`, `fn_estudio_c10_precio_contratos`, `fn_estudio_c14_upme_vs_real`, `fn_estudio_g10_combustibles` (referencian columnas inexistentes). `sfeia/sql/f4_mix.sql` y `sfeia/sql/f5_precio_contratos.sql` reemplazan C06/C10 con consultas directas. Inventario completo, causas y DDL de corrección en `sfeia/docs/funciones_rotas_bd.md`. Ante un error de columna inexistente, prefiera consulta directa sobre `fact_*`/`dim_*` en vez de la función.
- **Semántica de fechas por familia:** C01–C14 usan fin EXCLUSIVO (`fecha_hora < fin`); C15/C16–C18 INCLUSIVO (`< fin + 1 día`). `sfeia/config/config.yaml` ya codifica el par correcto (`fin_c_familia` vs `fin_c15`); reutilice esas claves, no invente fechas. Ventana actual: Ene–Jul 2025 (`fin_c_familia: 2025-08-01`).
- `dim_agente.activity` usa tilde: `'COMERCIALIZACIÓN'`.
- C15 valora todo volumen con el precio promedio **de sistema** (no hay precio ni contraparte por agente): los valores COP son estimaciones.
- `fact_daily_sistema` tiene una fila por fecha (JOIN seguro por `ds.fecha = date(ha.fecha_hora)`).

## Arquitectura (MVC)
- `sfeia/main.py` → `FaseSegmentacion` (F-1) + `FaseDiaria`; cada fase es un controlador en `sfeia/app/controllers/fase_*.py`.
- Toda consulta SQL vive en `sfeia/sql/` (un archivo por fase; varios statements por archivo separados por `;`). `sfeia/app/models/repositories.py` los ejecuta con un splitter que ignora `;` en comentarios/literales. Nunca SQL inline en controllers/views.
- `sfeia/app/services/` = lógica pura (diario, clustering, segmentación, KPIs, tipificación); `sfeia/app/views/informe_diario_md.py` renderiza Markdown. Views no consultan BD; models no renderizan.
- Umbrales de segmentación, ventana y parámetros del modelo financiero están en `sfeia/config/config.yaml` — cámbielos ahí, no en código.

## Modelo financiero (caveat crítico)
- C16–C18 se calculan en Python (`sfeia/app/services/kpi_cartera.py`) a partir de C15; NO llamar `fn_agente_garantias_exigidas`/`fn_agente_margen_comercializacion` (cada llamada re-escanea C15; `fn_agente_margen_comercializacion` ≈26 s por agente).
- El "margen" C18 usa Pv=350 COP/kWh fijo → es un **artefacto de modelado** (márgenes negativos artificiales en regulados), no el margen real del agente. Reportar con la advertencia.

## Docs
- `sfeia/docs/plan_estrategias_diarias.md` = metodología del estudio híbrido diario (activo).
- `sfeia/docs/plan_estrategias_comercializacion.md` y `sfeia/docs/plan_segmentacion_kmeans.md` = metodología de los estudios reemplazados (referencia).
- `sfeia/docs/informe_estrategias_diarias.md` = salida generada por `main.py`; no editar a mano.
- `sfeia/docs/archivado/` = informes antiguos de los estudios reemplazados.
- `docs/plan_agente_xxxc_asistente.md` (raíz) = plan del asistente imitador (activo).
- `docs/informe_asistente_imitador.md` (raíz) = salida generada por `python -m asistente`; no editar a mano.