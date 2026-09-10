# SFEIA — Asistente imitador del agente XXXC (Behavioral Cloning del top-N)

En vez de **predecir** o crear una estrategia propia (imposible de competir con información privilegiada,
modelos meteorológicos y músculo financiero de los grandes), el asistente **imita** a los agentes a los que
mejor les fue en un **(segmento, estrategia)** dentro de una **ventana de estudio**, y replica su perfil de
abastecimiento en una **ventana de impacto**. Es Behavioral Cloning (BC): tabla
`contexto de mercado → perfil de abastecimiento` aprendida de los **top-N** maestros.

El proyecto implementa la lección aprendida de los programas profesionales de imitación (copy trading,
selección de gestores, imitation learning): **no se clona a ciegas**. Antes de recomendar, el asistente valida
que la selección no sea suerte (bootstrap, holdout, DSR, replicación), y si la combinación pedida no pasa la
barrera, **busca dónde sí hay señal** (barrido) y propone la alternativa. Documentación metodológica completa en
`docs/investigacion_imitacion_traders_profesionales.md`.

Todo el proyecto es **un solo paquete MVC** (`sfeia/`): el estudio híbrido diario (segmentación F-1 +
estrategias por agente-día, k-means pooled, margen estimado C16–C18) es el **motor** interno; el asistente es la
aplicación. Las salidas del asistente viven en `docs/` (Markdown) y `data/` (CSV) de la raíz.

## Requisitos

- Python 3.12+ y PostgreSQL local con la base `elecdb` cargada (XM/SIN).
- Dependencias (psycopg2-binary, PyYAML, pytest, scikit-learn, scipy) en un entorno virtual:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Los comandos se ejecutan desde la raíz del repo, siempre con el Python del entorno: `./.venv/bin/python ...`.

---

## Funcionalidades

### 1. Asistente imitador (modo normal)

Imita el comportamiento del top-N de un **(segmento, estrategia)** y evalúa la imitación en una ventana
posterior. Es el modo por defecto y produce el informe completo.

```bash
./.venv/bin/python -m sfeia.main \
  --segmento PEQUEÑO \
  --estrategia "Trader expuesto a bolsa (sin cobertura)" \
  --top 10
```

Qué hace (por dentro):
1. **Estudio** → F-1 (segmentación) + FaseDiaria (k-means pooled por agente-día).
2. **Selección de maestros** por **margen relativo al segmento** (margen del agente − mediana del segmento el
   mismo día), que cancela el artefacto del modelo (Pv=350 fijo), con métricas de riesgo (%, drawdown, colas).
3. **Validez**: bootstrap skill-vs-luck (¿el top supera al azar?), holdout (sub-estudio vs sub-validación),
   deduplicación de maestros correlacionados (N efectivo), DSR y replicación IS→OOS.
4. **Política BC** ponderada por bin de spread (agregación tipo EWA, no top-N duro), con **zona de confianza**
   (fuera del rango entrenado reduce exposición a bolsa trasladando a contratos) y contexto ex-ante
   (spread del día anterior, sin look-ahead) + nivel de embalses.
5. **Impacto** → simula a XXXC cada día, compara contra maestros y segmento, calcula garantías, drawdown,
   escenarios de escasez, capacidad y kill-switch.
6. Si la combinación **no pasa la validez**, el informe propone una **alternativa recomendada** (la mejor
   combinación válida del mismo estudio, con su simulación).

### 2. Barrido de combinaciones (`--barrido`)

¿**Dónde** hay señal? Evalúa **todas** las combinaciones (segmento × estrategia) presentes en el estudio, les
aplica el filtro de validez y reporta las que pasan, ordenadas por margen relativo. No te cases con una
combinación: encuentra la que de verdad es imitable.

```bash
./.venv/bin/python -m sfeia.main --barrido
```

Salidas: `data/barrido_combinaciones.csv` + `docs/informe_barrido_combinaciones.md`.

### 3. Walk-forward (`--walk-forward`)

Serie de **ventanas rodantes** (estudio → impacto) hacia atrás desde la última fecha con datos, cosiendo los
resultados OOS. Evalúa si la estrategia sobrevive a múltiples regímenes (estándar de los quants), no a un solo
período afortunado.

```bash
./.venv/bin/python -m sfeia.main --walk-forward
```

Salida: `data/walk_forward.csv` (un paso por fila: ventanas, mediana del margen, réplica, DSR, kill-switch).

### 4. Harness de aceptación (`--aceptacion`)

Barre el grid de ventanas **2015→hoy** (estudio 90 d + impacto 7 d, paso 30 d) y evalúa **todas** las
(segmento × estrategia × ventana) contra el scorecard N0–N4 definido en `docs/plan_aceptacion_imitador.md`
(integridad, validez de selección, riesgo, robustez y fidelidad del clon). Confirma candidatas con el flujo
completo (bootstrap fino + holdout + DSR). Es el "termómetro" reproducible del imitador.

```bash
./.venv/bin/python -m sfeia.main --aceptacion
```

Salidas: `docs/scorecard_aceptacion.md` + `data/scorecard.csv` + `data/scorecard_confirmadas.csv`.

> **Veredicto actual (2026-09-09): OPERABLE (por régimen).** Tras corregir un bug en el bootstrap skill-vs-luck
> (el estadístico real era el mínimo, no el máximo), el harness `--aceptacion` encontró combinaciones operables
> (p≤0.05, réplica≥0.5, DSR≥0.95, holdout≥50 %, E1≥60 %, EV>0): 20 en modo topN y 25 en modo arquetipo,
> dominadas por Comercializador regulado (PEQUEÑO/MEDIANO) en 2015–2021. Las ventanas 2023–2025 (escasez)
> siguen fallando: la operabilidad es por régimen. El experimento `--poder` confirma que la señal no es un
> artefacto de poder. Evidencia en `docs/scorecard_aceptacion.md` y `docs/experimento_poder_estadistico.md`.

### 5. Tests

```bash
./.venv/bin/python -m pytest -q
```

Lógica pura, sin BD (segmentación, diario, maestros, clonación, simulación, validez, scorecard).

---

## Referencia de flags del CLI

| Flag | Descripción |
|---|---|
| `--segmento` | `GRANDE` \| `MEDIANO` \| `PEQUEÑO` (default: `segmento_por_defecto`). |
| `--estrategia` | Arquetipo del estudio a imitar (default: `estrategia_por_defecto`). |
| `--top` | N de maestros (default: `top_por_defecto`). |
| `--estudio-ini` / `--estudio-fin` | Ventana de estudio (define maestros). |
| `--impacto-ini` / `--impacto-fin` | Ventana de impacto (evalúa la imitación). |
| `--demanda-dia-gwh` | Demanda diaria de XXXC; si se omite, mediana del segmento. |
| `--walk-forward` | Modo ventanas rodantes (P2.3). |
| `--barrido` | Modo evaluación de todas las combinaciones (S2). |
| `--aceptacion` | Harness de aceptación: grid 2015→hoy + scorecard N0–N4. |
| `--config` | Ruta alternativa al `config.yaml` único. |

**Ventanas por defecto** (si no se pasan fechas): estudio = últimos `dias_estudio_por_defecto` (30) días antes del
impacto; impacto = últimos `dias_impacto_por_defecto` (7) días del ancla `ventana.foco_*` (ver "Cómo se resuelven
las fechas" en Configuración). El CLI sobreescribe el config. La BD llega a **2026-07-31**; el proyecto corre sobre
**2025** (año completo), y las ventanas posteriores a 2026-07-31 **fallan con un error claro**.

---

## Salidas

| Salida | Contenido |
|---|---|
| `docs/informe_asistente_imitador.md` | Informe Markdown completo (parámetros, maestros, validez, política, escenarios, riesgo, simulación diaria, advertencias, alternativa y decisión de negocio). |
| `docs/informe_barrido_combinaciones.md` | Ranking de combinaciones con filtro de validez (`--barrido`). |
| `data/maestros_topN.csv` | Maestros con mediana absoluta y **relativa**, riesgo y % días > segmento. |
| `data/politica_clonacion.csv` | Tabla contexto (bin de spread) → perfil de abastecimiento. |
| `data/simulacion_impacto.csv` | Día a día: contexto, embalses, en/out de distribución, perfil, márgenes y garantías. |
| `data/resumen_impacto.csv` | Medidas del impacto (medianas, % días ganados, garantías). |
| `data/distribucion_margenes.csv` | Distribución de márgenes imitación/maestros/segmento (riesgo). |
| `data/escenario_escasez.csv` | Estrés sintético: bolsa en/precio sobre escasez. |
| `data/historial_escasez.csv` | Frecuencia histórica de contextos de spread y escasez (2015→hoy). |
| `data/validacion_seleccion.csv` | Pruebas de validez: bootstrap, holdout, replicación, DSR, N efectivo. |
| `data/walk_forward.csv` | Serie walk-forward (`--walk-forward`). |
| `data/barrido_combinaciones.csv` | Todas las combinaciones evaluadas (`--barrido`). |
| `docs/scorecard_aceptacion.md` + `data/scorecard{,_confirmadas}.csv` | Scorecard N0–N4 del harness (`--aceptacion`). |

---

## Estructura

```
docs/    Planes e informes del asistente (salida generada)
data/    CSVs del asistente (salida generada)
sfeia/   Un solo paquete MVC
  main.py                  CLI del asistente (python -m sfeia.main)
  config/                  config.yaml (única: motor + simulador) + settings.py
  sql/                     Queries parametrizadas (f-1_segmentacion, d1_diario, d1_max_fecha,
                           d1_historial_precios, d1_contexto_hidrologia)
  app/
    controllers/           fase_segmentacion · fase_diaria · fase_asistente (ejecutar, barrido, walk-forward) · fase_aceptacion
    models/                entities (dataclasses) · repositories (RepoElecdb)
    services/              segmentacion · diario · clustering · kpi_cartera · contexto · maestros · clonacion · simulacion · scorecard
    views/                 informe_asistente_md · informe_barrido_md · informe_scorecard_md · exportar_csv
  tests/                   test_segmentacion · test_diario · test_asistente · test_scorecard
```

Los `services` son **lógica pura** (no tocan BD); solo los controladores consultan el repo. Toda query vive en
`sql/`; las vistas solo serializan.

---

## Configuración

**Un solo archivo** `sfeia/config/config.yaml` (antes eran dos; se fusionaron porque el asistente reutiliza el
motor). Contiene el motor y el simulador, cada uno en su sección:

| Sección | Rol |
|---|---|
| `database`, `ventana`, `segmentacion`, `modelo_financiero`, `diario` | **MOTOR** (estudio híbrido diario). |
| `asistente` | **SIMULADOR** (imitador). Reutiliza las secciones del motor. |

Parámetros clave del simulador (`asistente:`):

| Clave | Función |
|---|---|
| `seleccion_por_relativo` | Selección por margen relativo al segmento (S1). |
| `dias_holdout`, `n_boot`, `alpha_significancia` | Validez: holdout, bootstrap, umbral de p. |
| `umbral_corr_duplicados` | Deduplicación de maestros (N efectivo). |
| `usar_spread_previo` | Contexto ex-ante (sin look-ahead). |
| `ponderar_politica`, `pesos_eta` | Agregación ponderada de perfiles (P1.2). |
| `factor_exposicion_fuera_distribucion` | Zona de confianza (P1.3). |
| `usar_regimen_hidrologico` | Nivel de embalses por día (P1.4). |
| `capacidad_max_pct_segmento` | Límite de capacidad (P2.1). |
| `kill_switch_drawdown_cop_kwh` | Kill-switch por drawdown (P2.2). |
| `walk_forward` / `barrido` | Parámetros de los modos (`--walk-forward`, `--barrido`). |
| `salida`, `salida_barrido`, `data_dir` | Rutas de salida. |

### Cómo se resuelven las fechas

Las fechas del simulador (`asistente.estudio_ini/fin`, `asistente.impacto_ini/fin`) viven en el mismo archivo que
el motor, en su sección. Si están en `null` (por defecto), se derivan del **ancla** del motor
(`ventana.foco_ini/foco_fin`):

- `estudio_fin` = `foco_fin` − `dias_impacto_por_defecto`
- `estudio_ini` = `estudio_fin` − (`dias_estudio_por_defecto` − 1)
- `impacto_fin` = `foco_fin`; `impacto_ini` = `estudio_fin` + 1

No son parámetros duplicados: el motor define la ventana de análisis y el simulador deriva (o sobreescribe con el
CLI `--estudio-ini`/`--impacto-fin`) sus ventanas de estudio e impacto a partir de esa única ancla.

La conexión usa por defecto `postgresql://postgres:postgres@localhost:5432/postgres` (configurable con `DB_DSN`).

---

## Metodología (resumen)

- **Estudio** → ranking de agentes del (segmento, estrategia) por **margen relativo** → top-N maestros (con
  riesgo y presencia mínima).
- **Validez** → bootstrap skill-vs-luck, holdout, N efectivo, DSR, replicación IS→OOS.
- **Clonación** → tabla `bin de spread → perfil` ponderada, con zona de confianza y contexto ex-ante.
- **Impacto** → simulación de XXXC vs maestros y segmento, riesgo, escenarios de escasez, decisión de negocio.
- **Si no valida** → alternativa recomendada (mejor combinación del estudio) o barrido para encontrar dónde sí hay señal.
- El margen es un **artefacto de modelado** (Pv=350 fijo, precios de sistema): sirve para comparar, no como
  margen real. Detalle en `docs/plan_agente_xxxc_asistente.md` y `docs/investigacion_imitacion_traders_profesionales.md`.

## Advertencias

- Los valores COP son **estimaciones** (volumen × precio promedio de sistema); no hay precio ni contraparte por
  agente en elecdb, y **no existe ground truth** (liquidaciones XM) — la validación externa está pendiente.
- BC **no generaliza fuera de la distribución** de spread del estudio; por eso la zona de confianza reduce
  exposición en días fuera de rango.
- La ventana de impacto es **retrospectiva** (datos ya cargados), no predicción en vivo.
- Los maestros se eligen **dentro** de su segmento: el asistente no compite contra GRANDE (por diseño).