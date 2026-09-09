# SFEIA — Estrategias de Comercialización en el MEM

Benchmark de estrategias de comercialización del Mercado de Energía Mayorista (MEM) colombiano: análisis por segmento (GRANDE / MEDIANO / PEQUEÑO) de los agentes comercializadores, cruzando el marco regulatorio CREG con datos reales de mercado (base elecdb / XM).

## Requisitos

- Python 3.12+ y PostgreSQL local con la base `elecdb` cargada (esquema y funciones `fn_estudio_*` documentados en la skill `elecdb`).
- Las dependencias se instalan en un entorno virtual:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Uso

```bash
./.venv/bin/python main.py                  # ejecuta F-1, F0–F6 y regenera el informe
./.venv/bin/python -m pytest -q             # tests unitarios (lógica pura, sin BD)
```

La conexión a la BD usa por defecto `postgresql://postgres:postgres@localhost:5432/postgres` (configurable con `DB_DSN`). Los umbrales de segmentación, la muestra de agentes, la ventana de análisis y los parámetros del modelo financiero se cambian en `config/config.yaml`.

El pipeline ejecuta las fases:
- **F-1** segmentación de los ~65 comercializadores por demanda semestral (GRANDE ≥ 2000 GWh-sem, MEDIANO 100–2000, PEQUEÑO < 100) y muestra estratificada.
- **F0–F6** contexto de mercado, cartera, cobertura/exposición, pico/valle, mix reg/no-reg, modelo financiero y síntesis de arquetipos con contraste de hipótesis R0–R5.

## Estructura

```
config/   Configuración (DSN, umbrales, ventana, modelo financiero)
sql/      Queries SQL parametrizadas, una por fase
app/      MVC: models (repositorio elecdb) · controllers (fases) · services (lógica pura) · views (informe)
tests/    Pruebas unitarias
docs/     Plan metodológico y análisis regulatorio (fuente) + informe generado (salida)
```

## Documentación

- `docs/plan_estrategias_comercializacion.md` — metodología, limitaciones de datos y hipótesis R0–R5.
- `docs/analisis_regulatorio.md` — marco normativo CREG (Q1–Q5).
- `docs/informe_estrategias_comercializacion.md` — salida generada por `main.py` (no editar a mano).

## Advertencias

- Los valores COP son **estimaciones** (volumen × precio promedio de sistema); no hay precio ni contraparte por agente en elecdb.
- El margen por kWh del modelo financiero (Pv=350 fijo) es un artefacto de modelado, no el margen real del agente.