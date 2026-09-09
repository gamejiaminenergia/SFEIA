# SFEIA — Estrategias de Comercialización en el MEM

Análisis de estrategias de comercialización del Mercado de Energía Mayorista (MEM) colombiano: para **todos** los comercializadores, se determina su **estrategia diaria** (k-means pooled sobre agentes-día) y se **rankea el desempeño diario** de cada estrategia (margen estimado por kWh), con balance del período. Cruza el marco regulatorio CREG con datos reales de mercado (base elecdb / XM).

Todo el estudio actual vive en el paquete autocontenido **`sfeia/`** (MVC + config + sql + tests + salidas `docs/`/`data/`). La raíz del repo queda libre para el **simulador**, que reutilizará funcionalidades vía `from sfeia.app.services import ...`.

## Requisitos

- Python 3.12+ y PostgreSQL local con la base `elecdb` cargada (esquema y funciones `fn_estudio_*` documentados en la skill `elecdb`).
- Las dependencias se instalan en un entorno virtual:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Uso (nueva funcionalidad: estudio híbrido diario)

| Qué quieres | Comando | Resultado |
|---|---|---|
| Estudio híbrido diario (único) | `./.venv/bin/python -m sfeia.main` | `sfeia/docs/informe_estrategias_diarias.md` |
| Asistente imitador del agente XXXC (top-N) | `./.venv/bin/python -m asistente` | `docs/informe_asistente_imitador.md` |
| Tests unitarios (sin BD) | `./.venv/bin/python -m pytest -q` | — |

> **Un solo estudio, toda la población.** El informe diario reemplaza al benchmark por segmento (H1-2026) y al
> k-means de H1-2026 (archivados en `sfeia/docs/archivado/`). El estudio analiza **TODOS los comercializadores** con
> demanda en la ventana (65) — no hay muestra. `sfeia/main.py` no tiene flags de estudio/muestra.

### 1) Ejecutar el estudio (paso a paso)

```bash
# (1) Entorno virtual con dependencias (una sola vez)
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# (2) Regenerar el estudio y el informe Markdown
./.venv/bin/python -m sfeia.main
```

El comando conecta a elecdb, ejecuta `F-1` (segmentación de los 65) + `FaseDiaria` y deja el informe en
**`sfeia/docs/informe_estrategias_diarias.md`** y **9 archivos CSV en `sfeia/data/`** (análisis directo en Excel/Sheets).
En consola imprime un resumen con los segmentos y el **ranking final de
estrategias** (mediana de margen COP/kWh/día y días en 1.er puesto), p. ej.:

```
Ranking de estrategias del período (mediana margen COP/kWh/día):
  1. Trader expuesto a bolsa (sin cobertura) · -19.19 · 108 días 1.º
  2. Integrado/regional regulado · -46.65 · 76 días 1.º
  3. Comercializador regulado · -68.73 · 1 días 1.º
  ...
```

> **Granularidad por segmento:** además del ranking pooled, el estudio analiza cada segmento
> **GRANDE/MEDIANO/PEQUEÑO por separado** (no compiten entre sí), para ver qué estrategia les funciona a los
> MEDIANO y PEQUEÑO sin que los grandes dominen el ranking.

### 1.1 Los 9 CSV generados en `data/`

Todos abren directo en Excel (UTF-8 con BOM; cabeceras en español y unidades claras):

| Archivo | Filas | Qué contiene |
|---|---|---|
| `agentes_dia.csv` | ~13 500 | Una fila por (agente, día): fecha, agente, **segmento**, estrategia, features diarias y margen/costo estimado. El detalle más fino. |
| `ranking_diario.csv` | ~1 060 | Una fila por (día, estrategia): mediana/media del margen y **puesto** de la estrategia ese día. |
| `balance_periodo.csv` | 5 | **Ranking final del período** (pooled): mediana/media de margen, días 1.º, % top-3, rango promedio, tendencia, caso atípico. |
| `perfil_arquetipos.csv` | 5 | Perfil de cada estrategia: agentes-día/únicos, medias de features y composición por segmento. |
| `matriz_puestos.csv` | 5 | Cuántos días cada estrategia ocupó el 1.º, 2.º, 3.º… puesto (pooled). |
| `dias_mercado.csv` | 212 | Precios diarios de bolsa/contratos/escasez, spread, día de escasez y **qué estrategia ganó** ese día. |
| `balance_por_segmento.csv` | ~14 | **Ranking final POR segmento** (GRANDE/MEDIANO/PEQUEÑO): la misma métrica del balance pooled, pero cada segmento compite contra sí mismo. **Empieza por aquí.** |
| `ranking_por_segmento.csv` | ~2 300 | Una fila por (segmento, día, estrategia): puesto de la estrategia ese día **dentro de su segmento**. |
| `estrategia_x_segmento.csv` | ~14 | Matriz estrategia × segmento: mediana del margen diario de cada estrategia dentro de cada segmento. |

> Consejo de lectura: para la pregunta «¿qué estrategia les va mejor a los MEDIANO/PEQUEÑO?» usa
> `balance_por_segmento.csv` filtrando por segmento, y `dias_mercado.csv` para el porqué. El detalle agente-día
> está en `agentes_dia.csv` (filtra por segmento y fecha).

### 2) Cambiar el período de fechas

En `sfeia/config/config.yaml`, sección `ventana:`. El estudio usa `foco_ini`–`foco_fin` y la convención de fechas de
elecdb (familia C01–C14 con fin **exclusivo** `fin_c_familia`, C15 con fin **inclusivo** `fin_c15`). P. ej. para
analizar Q1-2025: `foco_ini: "2025-01-01"`, `foco_fin: "2025-03-31"`, `fin_c_familia: "2025-04-01"`, `fin_c15: "2025-03-31"`.

### 3) Ajustar el modelo (opcional)

Todo se parametriza en `sfeia/config/config.yaml`, no en código:

- **Número de estrategias (arquetipos):** `diario.k: 5`. La silhouette es plana (~0.4) en la población diaria, por
  eso `k` va fijo; `diario.k: null` lo devuelve a automático (máximo silhouette en `diario.k_min`–`diario.k_max`).
- **Métrica de desempeño:** `diario.desempeno: margen_kwh` (única implementada; margen estimado por kWh, lógica C16–C18).
- **Guardas de robustez del ranking:** `diario.clip_margen_cop_kwh: 500` (winsoriza márgenes de traders con volumen
  >> demanda), `diario.min_dias_pct: 20` (estrategias con presencia marginal → casos atípicos fuera del ranking),
  `diario.clip_pct_sicep: 100` (SICEP puede incluir no regulado).
- **Características del clustering:** `diario.features`, `diario.transformes`, `diario.clip_sobrecobertura`,
  `diario.random_state`, `diario.n_init`, `diario.scaler`, `diario.submuestra_k` (silhouette sobre submuestra).
- **Modelo financiero:** `modelo_financiero.pv_tarifa_cop_kwh: 350` (fijo, artefacto), cargos y garantías.
- **Salida:** `informe_diario.salida` y `informe_diario.titulo`.

### 4) Qué contiene el informe generado

1. **Resumen ejecutivo** — ranking final de estrategias del período.
2. **Metodología** — features diarias, **criterios de segmentación (GRANDE/MEDIANO/PEQUEÑO)** y **tabla de los 65 comercializadores por segmento**, clustering, métrica de desempeño y guardas.
3. **Elección de k** — tabla silhouette/inercia (sensibilidad).
4. **Arquetipos diarios** — **explicación en lenguaje de negocio de cada estrategia** (qué hace, cuándo le va mejor, riesgo) + perfil de cada una (n agentes-día, medias, composición por segmento, agentes representativos).
5. **Ranking diario** — días que cada estrategia ocupó cada puesto (+ desglose **por segmento**) + **días destacados** (bolsa cara y días de escasez).
6. **Ranking y balance por segmento** — qué estrategia le funcionó mejor a GRANDE, MEDIANO y PEQUEÑO **por separado** + matriz estrategia × segmento.
7. **Balance del período** — ranking final pooled con mediana/media de margen, días 1.º, % top-3, rango promedio, tendencia y casos atípicos.
8. **Limitaciones** — advertencias de datos y modelado.

### 5) Asistente imitador del agente XXXC (simulador en la raíz)

En vez de predecir o crear estrategia propia, el asistente **imita** (Behavioral Cloning) a los **top-N** agentes de un
(segmento, estrategia) en una ventana de **estudio** y replica su perfil de abastecimiento en una ventana de **impacto**.

```bash
./.venv/bin/python -m asistente \
  --segmento PEQUEÑO \
  --estrategia "Trader expuesto a bolsa (sin cobertura)" \
  --top 5 \
  --estudio-ini 2025-07-01 --estudio-fin 2025-07-31 \
  --impacto-ini 2025-08-01 --impacto-fin 2025-08-08
```

- Salida: `docs/informe_asistente_imitador.md` + `data/{maestros_topN, politica_clonacion, simulacion_impacto, resumen_impacto}.csv`.
- Sin fechas: estudio = ventana principal menos los últimos `asistente.dias_impacto_por_defecto` días; impacto = esos últimos días.
- La BD llega a **2026-07-31**; el proyecto corre sobre **2025** (año completo), así que cualquier ventana de 2025 funciona y las posteriores a 2026-07-31 **fallan con un error claro**. Metodología en `docs/plan_agente_xxxc_asistente.md`.

## Configuración (`sfeia/config/config.yaml`)

- `ventana:` foco del análisis (Ene–Jul 2025) + convención fin exclusivo/inclusivo (`fin_c_familia` vs `fin_c15`).
- `diario:` parámetros del clustering diario y guardas de robustez del ranking.
- `asistente:` defaults del asistente imitador (segmento/estrategia/top, bins de spread, guardas, salidas).
- `informe_diario:` ruta y título del informe único.
- `modelo_financiero:` parámetros C16–C18 (Pv=350 fijo, cargos, garantías).

La conexión a la BD usa por defecto `postgresql://postgres:postgres@localhost:5432/postgres` (configurable con `DB_DSN`).

## Estructura

```
sfeia/    Paquete autocontenido del estudio (app/ MVC, config/, sql/, tests/, main.py, salidas docs/ y data/)
  app/      MVC: models (repositorio elecdb) · controllers (FaseSegmentacion + FaseDiaria) · services (diario, clustering, kpis) · views (informe_diario_md)
  config/   Configuración (DSN, ventana, diario, modelo financiero)
  sql/      Queries SQL parametrizadas (f-1…f5, d1_diario)
  tests/    Pruebas unitarias
  data/     CSVs exportados por main.py (análisis en Excel/Sheets)
  docs/     Planes metodológicos + informe generado (salida) + archivado/ (informes de los estudios reemplazados)
asistente/  Simulador (raíz): asistente imitador del agente XXXC (app/ MVC propio, main.py CLI, tests/)
docs/       (raíz) Plan e informe del asistente imitador
data/       (raíz) CSVs exportados por `python -m asistente`
```

## Documentación

- `sfeia/docs/plan_estrategias_diarias.md` — metodología del estudio híbrido diario.
- `sfeia/docs/plan_estrategias_comercializacion.md`, `sfeia/docs/plan_segmentacion_kmeans.md` — metodología de los estudios reemplazados (referencia).
- `sfeia/docs/analisis_regulatorio.md` — marco normativo CREG (Q1–Q5).
- `sfeia/docs/informe_estrategias_diarias.md` — salida de `main.py` (no editar a mano).
- `sfeia/docs/archivado/` — informes antiguos (`informe_estrategias_comercializacion.md`, `informe_arquetipos_kmeans.md`).
- `docs/plan_agente_xxxc_asistente.md` (raíz) — metodología del asistente imitador.
- `docs/informe_asistente_imitador.md` (raíz) — salida de `python -m asistente` (no editar a mano).

## Advertencias

- Los valores COP son **estimaciones** (volumen × precio promedio de sistema); no hay precio ni contraparte por agente en elecdb.
- El margen por kWh (Pv=350 fijo) es un **artefacto de modelado**, no el margen real del agente; sirve para **comparar estrategias**.
- El k-means es un método descriptivo: los arquetipos dependen de features, escalado y k; describen comportamiento **pasado**, no predicción.