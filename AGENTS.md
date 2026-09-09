# AGENTS.md — SFEIA

Análisis de estrategias de comercialización del MEM colombiano: Python + SQL sobre PostgreSQL (elecdb/XM), arquitectura MVC sin framework web. No es repo git.

## Comandos
- Ejecutar el pipeline (F-1, F0–F6) y regenerar el informe: `./.venv/bin/python main.py`
- Tests unitarios (lógica pura, sin BD): `./.venv/bin/python -m pytest -q`
- Dependencias (psycopg2-binary, pyyaml, pytest, requests) solo existen en `.venv`; el Python del sistema no las tiene.

## BD elecdb (PostgreSQL)
- Local: DSN default `postgresql://postgres:postgres@localhost:5432/postgres` en `config/config.yaml` (override con `DB_DSN`). No se necesita `.env`.
- Esquema completo y funciones `fn_estudio_*` documentados en la skill `elecdb` (`~/.config/opencode/skills/mercado_energetico/SKILL.md`).
- **Funciones de BD rotas — no usarlas:** `fn_estudio_c06_ciiu`, `fn_estudio_c07_mercados`, `fn_estudio_c10_precio_contratos`, `fn_estudio_c14_upme_vs_real`, `fn_estudio_g10_combustibles` (referencian columnas inexistentes). `sql/f4_mix.sql` y `sql/f5_precio_contratos.sql` reemplazan C06/C10 con consultas directas. Inventario completo, causas y DDL de corrección en `docs/funciones_rotas_bd.md`. Ante un error de columna inexistente, prefiera consulta directa sobre `fact_*`/`dim_*` en vez de la función.
- **Semántica de fechas por familia:** C01–C14 usan fin EXCLUSIVO (`fecha_hora < fin`); C15/C16–C18 INCLUSIVO (`< fin + 1 día`). `config/config.yaml` ya codifica el par correcto (`fin_c_familia` vs `fin_c15`); reutilice esas claves, no invente fechas.
- `dim_agente.activity` usa tilde: `'COMERCIALIZACIÓN'`.
- C15 valora todo volumen con el precio promedio **de sistema** (no hay precio ni contraparte por agente): los valores COP son estimaciones.

## Arquitectura (MVC)
- `main.py` → `app/controllers/pipeline.py` orquesta las fases (F-1, F0–F6); cada fase es un controlador en `app/controllers/fase_*.py` (orden importa: F-1 antes de F0–F6).
- Toda consulta SQL vive en `sql/` (un archivo por fase; varios statements por archivo separados por `;`). `app/models/repositories.py` los ejecuta con un splitter que ignora `;` en comentarios/literales. Nunca SQL inline en controllers/views.
- `app/services/` = lógica pura (segmentación, KPIs, tipificación); `app/views/informe_md.py` renderiza Markdown. Views no consultan BD; models no renderizan.
- Umbrales de segmentación (2000/100 GWh-sem), muestra de 25 agentes, ventana y parámetros del modelo financiero están en `config/config.yaml` — cámbielos ahí, no en código.

## Modelo financiero (caveat crítico)
- C16–C18 se calculan en Python (`app/services/kpi_cartera.py`) a partir de C15; NO llamar `fn_agente_garantias_exigidas`/`fn_agente_margen_comercializacion` (cada llamada re-escanea C15; `fn_agente_margen_comercializacion` ≈26 s por agente).
- El "margen" C18 usa Pv=350 COP/kWh fijo → es un **artefacto de modelado** (márgenes negativos artificiales en regulados), no el margen real del agente. Reportar con la advertencia.

## Docs
- `docs/plan_estrategias_comercializacion.md` = metodología (segmentación, fases, hipótesis R0–R5, limitaciones de datos). Léalo antes de modificar lógica de análisis.
- `docs/informe_estrategias_comercializacion.md` = salida generada; no editar a mano (se regenera con `main.py`).