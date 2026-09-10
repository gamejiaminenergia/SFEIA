# SFEIA — Asistente imitador del agente XXXC (Behavioral Cloning del top-N)

En vez de **predecir** o crear una estrategia propia (imposible de competir con información privilegiada,
modelos meteorológicos y músculo financiero de los grandes), el asistente **imita** a los agentes a los que
mejor les fue en un **(segmento, estrategia)** dentro de una **ventana de estudio**, y replica su perfil de
abastecimiento en una **ventana de impacto**. Es Behavioral Cloning (BC) puro: tabla
`contexto de mercado → perfil de abastecimiento` aprendida de los **top-N** maestros.

Todo el proyecto es **un solo paquete MVC** (`sfeia/`): el estudio híbrido diario (segmentación F-1 +
estrategias por agente-día, k-means pooled, margen estimado C16–C18) es el **motor** interno; el asistente es la
aplicación. Ya **no se generan informes/CSV del estudio** (solo los del asistente, en `docs/` y `data/` de la raíz).

## Requisitos

- Python 3.12+ y PostgreSQL local con la base `elecdb` cargada (XM/SIN).
- Dependencias (psycopg2-binary, PyYAML, pytest, scikit-learn) en un entorno virtual:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Los comandos se ejecutan desde la raíz del repo, siempre con el Python del entorno: `./.venv/bin/python ...`.

## Uso

| Qué quieres | Comando |
|---|---|
| Asistente imitador (punto de entrada único) | `./.venv/bin/python -m sfeia.main [flags]` |
| Tests unitarios (sin BD) | `./.venv/bin/python -m pytest -q` |

### Ejecutar el asistente

```bash
./.venv/bin/python -m sfeia.main \
  --segmento PEQUEÑO \
  --estrategia "Trader expuesto a bolsa (sin cobertura)" \
  --top 5 \
  --estudio-ini 2025-07-01 --estudio-fin 2025-07-31 \
  --impacto-ini 2025-08-01 --impacto-fin 2025-08-08
```

- Sin fechas: **estudio** = ventana principal menos los últimos `asistente.dias_impacto_por_defecto` días;
  **impacto** = esos últimos días.
- `--demanda-dia-gwh`: demanda diaria de XXXC; si se omite, mediana diaria del segmento en el estudio.
- La BD llega a **2026-07-31**; el proyecto corre sobre **2025** (año completo), así que cualquier ventana de
  2025 funciona y las posteriores a 2026-07-31 **fallan con un error claro**.

### Salidas

| Salida | Contenido |
|---|---|
| `docs/informe_asistente_imitador.md` | Informe Markdown (maestros, política, simulación, balance). |
| `data/maestros_topN.csv` | Los top-N maestros del (segmento, estrategia) en el estudio. |
| `data/politica_clonacion.csv` | Tabla contexto (bin de spread) → perfil de abastecimiento. |
| `data/simulacion_impacto.csv` | Día a día: perfil recomendado, margen de la imitación vs maestros/segmento. |
| `data/resumen_impacto.csv` | Medidas del impacto (medianas, % días ganados). |

## Estructura

```
docs/    Plan e informe del asistente (salida generada)
data/    CSVs del asistente (salida generada)
sfeia/   Un solo paquete MVC
  main.py                  CLI del asistente (python -m sfeia.main)
  config/                  config.yaml (ventana, diario, modelo financiero, asistente) + settings.py
  sql/                     Queries parametrizadas (f-1_segmentacion, d1_diario, d1_max_fecha)
  app/
    controllers/           fase_segmentacion · fase_diaria · fase_asistente
    models/                entities (dataclasses) · repositories (RepoElecdb)
    services/              segmentacion · diario · clustering · kpi_cartera · contexto · maestros · clonacion · simulacion
    views/                 informe_asistente_md · exportar_csv
  tests/                   test_segmentacion · test_diario · test_asistente
```

## Configuración

La configuración está dividida en **dos archivos independientes** (cada uno se entiende solo):

- `sfeia/config/config.yaml` — **ESTUDIO** (motor): `database`, `ventana`, `segmentacion`, `modelo_financiero`, `diario`.
- `sfeia/config/asistente.yaml` — **SIMULADOR**: solo la sección `asistente` (segmento/estrategia/top, bins de spread, guardas, salidas).

El asistente (`python -m sfeia.main`) carga ambos y los fusiona en memoria; puede apuntar a otros con
`--config` (estudio) y `--asistente-config` (simulador). La conexión a la BD usa por defecto
`postgresql://postgres:postgres@localhost:5432/postgres` (configurable con `DB_DSN`).

## Metodología

- **Ventana de estudio** → F-1 (segmentación) + FaseDiaria (k-means pooled sobre agentes-día) → se rankean los
  agentes del (segmento, estrategia) por mediana del margen → **top-N maestros**.
- **Clonación (BC)** → por bin de `spread = bolsa − contrato` se aprende la **mediana del perfil** de
  abastecimiento (cobertura, exposición, reg/no-reg, SICEP) de los maestros; bins sin datos usan el más cercano.
- **Ventana de impacto** → se simula a XXXC con la demanda del segmento y el perfil recomendado cada día, y se
  compara su margen contra el real de maestros y segmento.
- El margen es un **artefacto de modelado** (Pv=350 fijo, precios de sistema): sirve para comparar, no como
  margen real. Detalle completo en `docs/plan_agente_xxxc_asistente.md`.

## Advertencias

- Los valores COP son **estimaciones** (volumen × precio promedio de sistema); no hay precio ni contraparte por
  agente en elecdb.
- BC **no generaliza fuera de la distribución** de spread del estudio; la ventana de impacto es retrospectiva
  (datos ya cargados), no predicción en vivo.
- Los maestros se eligen **dentro** de su segmento: el asistente no compite contra GRANDE (por diseño).