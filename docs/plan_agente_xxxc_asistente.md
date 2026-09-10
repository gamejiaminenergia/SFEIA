# Plan — Asistente imitador del agente XXXC: Behavioral Cloning del top-N

> Objetivo: en vez de **predecir** o inventar una estrategia propia (imposible de competir con información
> privilegiada, modelos meteorológicos y músculo financiero de los grandes), el asistente **imita** a los agentes
> que mejor les fue en un (segmento, estrategia) dados, dentro de una ventana de estudio, y replica su
> comportamiento en una ventana de impacto. Es **Behavioral Cloning** (BC) puro y simple: tabla
> `contexto de mercado → perfil de abastecimiento` aprendida de los **top-N** maestros.
> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **implementado — `python -m sfeia.main`**
> Documentos relacionados: el estudio híbrido diario (segmentación F-1 + estrategias por agente-día) está
> **embebido** en el mismo paquete (`sfeia.app.controllers.fase_diaria`): ya no genera informes propios.

---

## 1. Motivación y decisiones de diseño (acordadas)

| Decisión | Elección |
|---|---|
| Filosofía | **Imitar, no predecir.** La experiencia muestra que los integrados/regionales regulados (casi siempre GRANDE, con contratos, años de mercado y monopolio) dominan cualquier ranking pooled. Para que un agente nuevo **MEDIANO/PEQUEÑO** tenga sentido, no se compite contra ellos: se **clona al que mejor les va dentro de su propio segmento y estrategia**. |
| Método | **Behavioral Cloning (BC)** por tabla: se binifica el **spread bolsa−contrato** del día (contexto) y, por bin, se aprende la **mediana del perfil de abastecimiento** (cobertura, exposición, reg/no-reg, SICEP) de los **top-N** maestros. Política determinista, interpretable, sin ML. |
| Quiénes son los maestros | Los **top-N** agentes del (segmento, estrategia) en la **ventana de estudio**, por **mediana del margen diario** (misma lógica C16–C18 del estudio), con guarda de presencia mínima. |
| Qué se clona | Los **agentes-día** de esos maestros **cuando jugaron la estrategia objetivo** (no sus días de otras estrategias). |
| Cómo se evalúa | En la **ventana de impacto** (posterior al estudio), se simula a XXXC con el perfil recomendado cada día y se compara su margen contra el **margen real** de los maestros y del segmento en ese mismo período. |
| Forma de entrega | CLI (`python -m sfeia.main`) + informe Markdown (`docs/informe_asistente_imitador.md`) + CSV en `data/`. |
| Entrada del asistente | `--segmento`, `--estrategia`, `--top`, fechas de **estudio** y de **impacto**, `--demanda-dia-gwh` (opcional). |

> **Por qué no IRL ni RL:** IRL (inferir recompensa) y RL (warm-start BC+RL) requieren un simulador de mercado
> causal y recompensas reales. BC puro es lo que el objetivo pide: copiar la acción del exitoso dado el estado.
> Si más adelante hay un simulador con estados estocásticos, el paso natural es **warm-start**: inicializar la
> política con esta tabla (BC) y refinarla con RL.

## 2. Partes del asistente

### 2.1 Ventana de estudio (identifica a los maestros)
- Se ejecuta **F-1 (segmentación)** + **FaseDiaria** (clustering k-means pooled, ranking, balance) sobre la
  **ventana de estudio** (por defecto la ventana principal menos los últimos N días). El segmento se recalcula
  dentro de la ventana de estudio (variable de análisis, no entra al k-means).
- Se filtran los agentes-día del **(segmento, estrategia)** objetivo y se rankean los agentes por **mediana del
  margen por kWh** (con `min_dias_pct` de presencia en la estrategia). Los **top-N** son los maestros.

### 2.2 Clonación (Behavioral Cloning)
- Estado del mercado por día: `spread = bolsa − contrato` binificado con `bins_spread` de config
  (muy barata / barata / neutral / cara / escasez).
- Para cada bin: se toman los agentes-día de los maestros (en la estrategia objetivo) y se calcula la **mediana**
  del perfil de abastecimiento → `pct_cobertura`, `pct_exposicion`, `pct_noreg`, `pct_sicep`, `tiene_sicep`.
- Política = tabla `{bin → perfil}` + **fallback** al bin más cercano con datos si un bin no tiene entrenamiento.

### 2.3 Ventana de impacto (evalúa la imitación)
- Se lee la BD para la ventana de impacto (posterior al estudio). Por día:
  1. Contexto del día → bin → perfil recomendado.
  2. Se construye el agente-día de XXXC con demanda = mediana diaria del segmento (o `--demanda-dia-gwh`) y el
     perfil recomendado; se calcula su margen con la **misma lógica** de `diario.desempeno_diario`.
  3. Se compara contra la **mediana real** de los maestros y del segmento ese día.
- Balance del impacto: mediana del margen de la imitación vs maestros vs segmento + % días en que gana.

### 2.4 Validaciones (fallar claro)
- `estudio_ini ≤ estudio_fin < impacto_ini ≤ impacto_fin`.
- Las dos ventanas deben tener datos en elecdb (la BD llega a **2026-07-31**, pero el proyecto corre sobre **2025** para pruebas). Si no, error explícito.
- El (segmento, estrategia) debe existir en la ventana de estudio y haber al menos 1 maestro; si no, error claro.

## 3. Ejemplo de invocación

```
# Ejemplo del plan: el estudio del top corre en julio y la imitación se evalúa en agosto (2025 tiene datos completos).
./.venv/bin/python -m sfeia.main \
  --segmento PEQUEÑO \
  --estrategia "Trader expuesto a bolsa (sin cobertura)" \
  --top 5 \
  --estudio-ini 2025-07-01 --estudio-fin 2025-07-31 \
  --impacto-ini 2025-08-01 --impacto-fin 2025-08-08
```

> Nota: el ejemplo original (estudio 01/07–31/07, impacto 01/08–08/08) funciona con **2025** porque ese año la BD
> tiene datos hasta diciembre. Con 2026 el mismo ejemplo **falla claro** (elecdb solo llega a **2026-07-31**); en
> cuanto la BD tenga agosto-2026, las mismas fechas funcionan sin tocar nada.

## 4. Arquitectura (MVC + SOLID — paquete único `sfeia/`)

Todo el proyecto es un solo paquete `sfeia/` (MODEL `app/models` · CONTROLLERS `app/controllers` ·
SERVICES `app/services` · VIEWS `app/views`). El estudio híbrido diario es el **motor** que alimenta al asistente;
ya no genera informes propios (se eliminaron sus `.md`/`.csv`).

| Archivo | Rol |
|---|---|
| `sfeia/main.py` | CLI (`python -m sfeia.main`): parsea argumentos, orquesta el controlador, imprime resumen. |
| `sfeia/app/controllers/fase_asistente.py` | Controlador del asistente: valida ventanas, corre F-1+FaseDiaria sobre la ventana de estudio, selecciona maestros, construye política, simula impacto. Habla con el repo. |
| `sfeia/app/controllers/fase_segmentacion.py` | Controlador F-1: segmenta la población (motor del estudio). |
| `sfeia/app/controllers/fase_diaria.py` | Controlador del estudio diario: clustering pooled, ranking, balance (motor del asistente). |
| `sfeia/app/models/entities.py` | MODEL: entidades del estudio (`AgenteSegmentado`, `AgenteDia`, `PerfilEstrategia`, `BalanceEstrategia`) + del asistente (`AgenteMaestro`, `PerfilAccion`, `PoliticaClonacion`, `SimulacionDia`, `ParametrosAsistente`). Dataclasses puras. |
| `sfeia/app/models/repositories.py` | MODEL: `RepoElecdb` (solo lectura): `segmentacion_poblacion`, `diario`, `fecha_max_sistema`. |
| `sfeia/app/services/segmentacion.py` | Lógica pura: asignar segmento GRANDE/MEDIANO/PEQUEÑO. |
| `sfeia/app/services/diario.py` | Lógica pura: agregados diarios, features, desempeño (margen), matriz, ranking, balance. |
| `sfeia/app/services/clustering.py` | Lógica pura: k-means pooled + arquetipos. |
| `sfeia/app/services/kpi_cartera.py` | Lógica pura: modelo financiero C16–C18 (margen por kWh). |
| `sfeia/app/services/contexto.py` | Lógica pura: binificar spread, flag de escasez, demanda de referencia del segmento. |
| `sfeia/app/services/maestros.py` | Lógica pura: selección del top-N por (segmento, estrategia) en la ventana de estudio. |
| `sfeia/app/services/clonacion.py` | Lógica pura: política BC (bin → mediana del perfil) + fallback al bin cercano. |
| `sfeia/app/services/simulacion.py` | Lógica pura: construir el agente-día de XXXC y simular su margen en el impacto + comparaciones. |
| `sfeia/app/views/informe_asistente_md.py` | VIEW: renderiza `docs/informe_asistente_imitador.md` (raíz). |
| `sfeia/app/views/exportar_csv.py` | VIEW: CSV en `data/` (raíz): maestros, política, simulación, comparación. |
| `sfeia/sql/` | Queries parametrizadas (solo las activas: `f-1_segmentacion`, `d1_diario`, `d1_max_fecha`). |
| `sfeia/tests/` | Pruebas sin BD (`test_segmentacion`, `test_diario`, `test_asistente`). |
| `sfeia/config/config.yaml` | Config única: ventana, segmentación, modelo financiero, `diario:` y `asistente:`. |

Principios SOLID:
- **S**ingle responsibility: cada service hace una sola cosa (contexto / maestros / clonación / simulación / diario / clustering).
- **O**pen/closed: añadir un nuevo contexto (p. ej. nivel de embalses) no toca maestros/simulación.
- **L**iskov: las entidades son dataclasses puras; los servicios operan sobre contratos de datos.
- **I**nterface segregation: los controladores dependen de `RepoElecdb` (solo lectura) y de los services puros.
- **D**ependency inversion: los services reciben datos + parámetros (no consultan BD); el controller inyecta.

## 5. Config propuesta (dos archivos independientes)

La configuración se divide en: `sfeia/config/config.yaml` (**ESTUDIO/motor**: database, ventana, segmentación,
modelo financiero, clustering) y `sfeia/config/asistente.yaml` (**SIMULADOR**, solo lo del asistente).
`settings.load_merged` los fusiona en memoria.

```yaml
# sfeia/config/asistente.yaml (SIMULADOR)
asistente:
  segmento_por_defecto: PEQUEÑO
  estrategia_por_defecto: "Trader expuesto a bolsa (sin cobertura)"
  top_por_defecto: 5
  min_dias_pct: 20          # presencia mínima del agente en la estrategia (ventana estudio)
  dema_dia_gwh: null        # null -> mediana diaria del segmento en la ventana de estudio
  dias_impacto_por_defecto: 7  # si no se dan fechas de impacto: últimas N días de la ventana
  bins_spread:              # spread = bolsa − contrato (COP/kWh)
    muy_barata: [-999999, 0]
    barata: [0, 200]
    neutral: [200, 400]
    cara: [400, 600]
    escasez: [600, 999999]
  salida: "docs/informe_asistente_imitador.md"
  data_dir: "data"
```

## 6. Verificación

- `./.venv/bin/python -m sfeia.main --segmento PEQUEÑO --top 5` → informe + CSV + resumen en consola.
- `./.venv/bin/python -m sfeia.main --impacto-ini 2026-08-01 --impacto-fin 2026-08-08` → **error claro** (la BD solo llega a 2026-07-31; con 2025 las mismas fechas sí corren).
- `./.venv/bin/python -m pytest -q` → verde (tests del estudio + del asistente).

## 7. Limitaciones a documentar (en el informe)

1. El margen es **artefacto de modelado** (Pv=350 fijo, precio de sistema): sirve para comparar, no como margen real.
2. BC **no generaliza fuera de la distribución** del spread observado en el estudio; un bin sin datos usa fallback.
3. La ventana de impacto depende de datos ya cargados en la BD (hoy hasta 2026-07-31; proyecto en 2025); es retrospectiva, no en vivo.
4. Los maestros se eligen **dentro** de su segmento: no se compara contra GRANDE (por diseño).
5. Clona el **perfil de abastecimiento** (cobertura/exposición/reg-no-reg/SICEP), no decisiones de precio de contrato
   ni de contraparte (no existen por agente en elecdb).