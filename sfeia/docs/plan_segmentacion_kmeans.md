# Plan Metodológico: Segmentación no supervisada con K-Means — Arquetipos emergentes de los comercializadores del MEM

> Estudio complementario al benchmark por segmento (F-1, F0–F6): aplica **k-means (scikit-learn)** sobre la **población completa de comercializadores (65)** para segmentar y explicar los clústeres y **determinar arquetipos emergentes** sin etiquetas predefinidas, validándolos contra la segmentación por umbrales y la tipificación por reglas existentes.
> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **implementado — informe generado (`docs/informe_arquetipos_kmeans.md`, k=3, H1-2026)**
> Documentos relacionados: `docs/plan_estrategias_comercializacion.md` (estudio actual, **no se modifica**) · `docs/informe_estrategias_comercializacion.md` (salida actual, **no se modifica**) · `docs/analisis_regulatorio.md` (marco CREG H1–H5)

---

## 1. Objetivo, motivación y definiciones

### 1.1 Objetivo
Definir el **método** para ejecutar un segundo estudio que segmenta a los **65 comercializadores** del MEM (misma población y ventana del estudio actual) con **k-means de scikit-learn**, **explica los clústeres** (perfil por variable), **nombra los arquetipos** que emergen de los datos y **los valida en contrapunto** con el estudio actual (segmentación GRANDE/MEDIANO/PEQUEÑO por umbrales + tipificación por reglas).

El entregable es **independiente**: no altera `plan_estrategias_comercializacion.md` ni `informe_estrategias_comercializacion.md`, no toca `tipificacion.py` ni el pipeline F-1/F0–F6. Reutiliza y **extiende** la arquitectura MVC para producir un segundo informe (`docs/informe_arquetipos_kmeans.md`).

### 1.2 Motivación: ¿qué aporta el no supervisado?
El estudio actual fija **etiquetas a priori**:
- Segmentos por **umbrales manuales** de demanda (2000 / 100 GWh-sem, `config/config.yaml` + `services/segmentacion.py`).
- Arquetipos por **reglas escritas a mano** en `services/tipificacion.py` (p. ej. `pct_sicep >= 80 → "Integrado de red"`, caso especial `CSIC → "Distribuidor en intervención"`).

El no supervisado invierte la lógica: primero deja que un algoritmo agrupe a los agentes por **similitud multivariada** y luego el analista **interpreta y nombra** los grupos. Eso evita el sesgo de imponer categorías antes de mirar los datos (qué etiqueta merece cada agente, qué umbral separa un grupo de otro).

> ⚠️ **Matiz de honestidad metodológica (leer en la interpretación del informe):** *"no supervisado"* **no** significa *"sin sesgo del analista"*. Siguen siendo decisiones del analista: qué **features** entran, el **escalado**, la **imputación** de valores faltantes y el **número de clústeres k**. Lo que k-means elimina es el sesgo de **etiquetar/umbralizar a mano** los arquetipos. Todo el proceso se documenta para que sea reproducible (config + `random_state`).

### 1.3 Dimensiones de negocio que alimentan el clustering (reuso del estudio actual)
Las mismas 5 dimensiones del plan actual (sección 1.2 de `plan_estrategias_comercializacion.md`), pero **solo las variables medibles por agente y sin artefactos de modelado**:

| # | Dimensión | Variables usadas como features | Fuente (query existente) |
|---|-----------|--------------------------------|--------------------------|
| D1 | **Abastecimiento / cobertura** | `pct_cobertura` (contratos), `pct_exposicion` (bolsa) | `f2_cobertura.sql` (C04) |
| D2 | **Mercado objetivo** | `pct_noreg` (mix), `pct_sicep` (proxy convocatoria) | `f1_cartera.sql` (C01 + SICEP) |
| D3 | **Precio y margen** | *(no existe por agente)* → **no entra**; solo contexto en interpretación | — |
| D4 | **Riesgo / red** | `pct_perdidas` | `f4_mix.sql` (C08) |
| D5 | **Flexibilidad horaria** | intensidad neta PICO (18–22h) normalizada por demanda | `f3_pico_valle.sql` (C05) |
| — | **Tamaño** | `log1p(dema_gwh)` (cola larga: 7 403 → 0,1 GWh) | `f-1_segmentacion.sql` |

**Regla de diseño:** no entran al clustering las columnas COP del modelo financiero (garantía/provisión/margen C16–C18), porque son **volumen × precio promedio de sistema** (lineales en exposición × tamaño) y son **artefactos de modelado**: introducirían correlación estructural que sesgaría los clústeres hacia una sola dimensión latente. Se usan solo *a posteriori* para enriquecer la narración de cada arquetipo.

---

## 2. Fuente de datos y matriz de features

### 2.1 Población y ventana
- **Población:** los 65 comercializadores con `DemaCome > 0` en H1-2026 (los mismos de F-1).
- **Ventana:** foco H1-2026 (`foco_ini`–`foco_fin` + convención fin exclusivo/inclusivo de `config/config.yaml`; reutilizar las claves existentes, no inventar fechas).
- **Diferencia clave con el estudio actual:** hoy F1–F5 agregan por agente **solo para la muestra de 25** (filtro `_sample_codes` en los controladores). Las queries SQL de `sql/f1…f4` **ya devuelven todos los agentes** (no filtran por código); el filtro ocurre en Python. Para k-means sobre 65 basta con **agregar sin filtrar**.

### 2.2 Matriz de features (65 × ~7)
| Feature | Cálculo | Tratamiento de datos faltantes / outliers |
|---------|---------|-------------------------------------------|
| `log_dema` | `log1p(DemaCome semestral GWh)` | log por cola larga (ENDC 7 403 vs GSAC 0,1) |
| `pct_noreg` | 100 − % regulado (C01) | 0–100; sin faltantes |
| `pct_cobertura` | CompCont/Dema (C04) | puede exceder 100 (sobrecobertura: ISGC 124 %, FERC 399 %) → **clip o RobustScaler** |
| `pct_exposicion` | CompBolsa/Dema (C04) | 0–100 |
| `pct_sicep` | CompContReg SICEP / CompContReg (C01) | **NaN** en puros no regulados (no compran regulado) → imputar `0` con bandera `tiene_sicep` (binaria); documentar |
| `pct_perdidas` | (DemaCome−DemaReal)/DemaCome (C08) | ~~~ evaluada y **excluida** (silhouette inferior; ≈0 en traders) ~~~ |
| `intensidad_pico` | posición neta bolsa PICO / DemaCome (C05) | ~~~ evaluada y **excluida** (ruido extremo en agentes diminutos: −1100 % a +713 %) ~~~ |

**Decisiones validadas en implementación** (materializadas en `config/config.yaml`):
- **Features finales (6):** `log_dema`, `pct_noreg`, `pct_cobertura`, `pct_exposicion`, `pct_sicep`, `tiene_sicep`. `pct_perdidas` e `intensidad_pico` se descartaron por silhouette inferior y ruido extremo (ver tabla).
- **Transformaciones:** `pct_cobertura`/`pct_exposicion` entran a la matriz como **log1p** (cola pesada: cobertura hasta 9 511 % en PEEC) y `pct_cobertura` se **clip a 300 %**. Los perfiles se reportan en escala original.
- **Escalado:** `StandardScaler` (el mejor balance silhouette/interpretabilidad; `RobustScaler` aislaba solo los outliers). Se ajusta sobre los 65; reproducible.
- **Colinealidad:** no se incluye `log_garantia` (∝ exposición×tamaño); cobertura y exposición se conservan como dimensiones distintas.
- **Imputación de SICEP:** `pct_sicep` imputado a 0 cuando no hay compras reguladas + feature binaria `tiene_sicep` para distinguir "0% convocatoria" de "no aplica".

---

## 3. Marco conceptual del algoritmo

### 3.1 Por qué k-means y no otro
- **Interpretable** y estándar para tipificar (centroides → perfil promedio del arquetipo).
- Rápido y determinista con `n_init` alto y `random_state` fijo.
- Alcance: **n=65**, variables continuas → adecuado. Se documentan sus supuestos (esfericidad, varianza similar) como limitación (sección 6).

### 3.2 Protocolo de elección de k
1. Escanear `k ∈ [k_min, k_max]` = **2..10** (config).
2. Métrica primaria: **silhouette medio** (elijo el k con mayor valor; se reportan todos).
3. Métrica secundaria: **codo de inercia** (inspección).
4. `k` resultante **se guarda en el resultado**; sobre-escribible por config (`clustering.k` explícito) para análisis de sensibilidad.
5. Robustez: repetir con `random_state` distintos y reportar estabilidad de la asignación (opcional: bootstrapping simple).

### 3.3 Parámetros fijos de reproducibilidad
`KMeans(n_clusters=k, n_init=10, random_state=42, max_iter=300)`. Toda semilla en `config/config.yaml`.

---

## 4. Arquitectura de implementación: MVC · SOLID · reuso

### 4.1 Principio de diseño: **misma app, independencia garantizada**
El estudio k-means se implementa **dentro de la misma app** (mismo árbol `app/`, misma base de código, misma BD, mismas queries SQL), pero **no modifica en nada el comportamiento del estudio actual**:

- **Archivos existentes que se tocan solo de forma ADITIVA** (se agregan líneas/secciones; no se cambia lógica ni salida existente):
  - `config/config.yaml` → secciones nuevas `clustering:` e `informe_kmeans:`.
  - `app/models/entities.py` → dataclasses nuevas (additiva).
  - `main.py` → flag nuevo `--estudio kmeans` con **default = comportamiento actual**.
  - `requirements.txt` → dependencia nueva (`scikit-learn`).
- **Archivos existentes que NO se tocan nunca:** `app/controllers/fase_*.py`, `app/controllers/pipeline.py`, `app/services/segmentacion.py`, `app/services/tipificacion.py`, `app/services/kpi_*.py`, `app/views/informe_md.py`, `app/models/repositories.py`, `sql/*`, `tests/*` existentes.
- **Nada se refactoriza para reutilizar**: la fase nueva agrega los KPI por su cuenta (las queries `sql/f1…f4` ya devuelven a los 65 agentes sin filtrar; solo hay que acumular en Python). Cero riesgo de romper la salida actual.
- El flujo actual sigue siendo reproducible con `./.venv/bin/python main.py` (sin flags) y sus tests intactos. El estudio k-means se registra **por extensión** (OCP): nuevos módulos + segundo informe.

### 4.2 Estructura (extensiones aditivas sobre el árbol actual)
```
SFEIA/
├── config/
│   ├── config.yaml              # + secciones `clustering:` e `informe_kmeans:` (aditivo)
│   └── settings.py              # sin cambios
├── docs/
│   ├── plan_segmentacion_kmeans.md      # ESTE documento
│   └── informe_arquetipos_kmeans.md     # nueva salida (generada, no editar a mano)
├── app/
│   ├── models/
│   │   ├── entities.py          # + dataclasses AgenteClusterizado, PerfilCluster (aditivo)
│   │   └── repositories.py      # sin cambios (f1..f4 ya devuelven los 65)
│   ├── services/
│   │   ├── clustering.py        # NUEVO: lógica pura (features, k, kmeans, perfil, ARI)
│   │   ├── segmentacion.py      # sin cambios
│   │   └── tipificacion.py      # sin cambios (se importa SOLO para validar en el contrapunto)
│   ├── controllers/
│   │   ├── pipeline.py          # sin cambios (flujo actual intacto)
│   │   ├── fase_clustering.py   # NUEVO: agrega F1–F4 a los 65 → matriz → kmeans → perfiles
│   │   └── fase_*.py            # sin cambios (NO se refactorizan)
│   ├── views/
│   │   ├── informe_md.py        # sin cambios
│   │   └── informe_clusters_md.py  # NUEVO: renderiza docs/informe_arquetipos_kmeans.md
├── sql/                         # sin cambios (f-1, f0, f1…f4 reutilizados)
├── tests/
│   ├── test_clustering.py       # NUEVO: matriz toy (k, ARI, perfiles) sin BD
│   └── (test_* existentes)      # sin cambios
├── main.py                      # + flag `--estudio kmeans` (default: benchmark actual)
└── requirements.txt             # + scikit-learn (arrastra numpy/scipy)
```

### 4.3 Config (adiciones a `config/config.yaml`)
```yaml
clustering:
  # Features activas. pct_perdidas e intensidad_pico se evaluaron y excluyeron
  # (silhouette inferior / ruido extremo); cobertura y exposición entran log1p.
  features:
    - log_dema
    - pct_noreg
    - pct_cobertura
    - pct_exposicion
    - pct_sicep
    - tiene_sicep
  transformes:
    pct_cobertura: pct_cobertura   # log1p en la matriz
    pct_exposicion: pct_exposicion # log1p en la matriz
  clip_sobrecobertura: 300
  k_min: 2
  k_max: 10
  metodo_k: silhouette # o "codo"; si `k:` se define explícito, lo respeta
  k: null              # null = automático (silhouette); int = fijo
  random_state: 42
  n_init: 10
  scaler: standard     # standard | robust

informe_kmeans:
  salida: "docs/informe_arquetipos_kmeans.md"
  titulo: "Arquetipos Emergentes de Comercializadores del MEM — Segmentación no supervisada (K-Means, H1-2026)"
```

### 4.4 Servicio `clustering.py` (lógica pura, testeable sin BD)
Entrada: dict de agregados por agente (los 65) + segmento de referencia (de F-1). **No consulta BD** (la agregación de los repos la hace el controlador, sección 4.5).

| Función | Responsabilidad |
|---------|-----------------|
| `construir_matriz(agregados: dict) -> tuple[X: np.ndarray, etiquetas: list[str]]` | arma la matriz (65×p) en el orden de `clustering.features`; imputa SICEP; aplica transformaciones (log, clip) |
| `elegir_k(X, k_min, k_max, semilla) -> list[dict]` | silhouette medio e inercia por k |
| `aplicar_kmeans(X, k, semilla, n_init) -> (labels, centroides)` | fit sobre datos **escalados** |
| `perfilar_clusters(X_raw, labels, nombres_features) -> list[PerfilCluster]` | medias/medianas por feature **en escala original** por clúster + n y composición |
| `comparar_con_segmento(labels, segmentos) -> dict` | tabla cruzada clúster×segmento + **ARI** |
| `comparar_con_tipificacion(labels, arquetipos_25) -> dict` | contrapunto contra `tipificacion.tipificar` (importada de solo-lectura) en la muestra 25 |

### 4.5 Controlador `fase_clustering.py` (nueva fase, posterior a F-1)
Orden en el pipeline del estudio k-means: `FaseSegmentacion` (65, para segmento de referencia) → **`FaseClustering`**. Este controlador:
1. **Agrega por su cuenta** los repos `cartera/cobertura/pico_valle/mix` para **los 65** agentes (las queries `sql/f1…f4` no filtran por código; se acumula sin `_sample_codes`, exactamente con el mismo criterio que los controladores actuales pero sin depender de ellos).
2. Llama a `clustering.py` (matriz → k → kmeans → perfiles → contraste).
3. Guarda en `datos["clustering"]`. Lee `datos["f-1"]` (segmento de referencia y nombres de agentes) — solo lectura, sin alterarlo.

### 4.6 Vista `informe_clusters_md.py`
Renderiza Markdown desde `datos["clustering"]` (jamás consulta BD). Estructura en sección 5.

### 4.7 Entrada `main.py`
- `python main.py` → **comportamiento actual** (F-1, F0–F6 → informe actual). Sin cambios.
- `python main.py --estudio kmeans` → ejecuta F-1 + `FaseClustering` y genera `docs/informe_arquetipos_kmeans.md`.

### 4.8 Dependencias
`requirements.txt += scikit-learn` (trae numpy y scipy como wheels). Instalar en `.venv` (único entorno con psycopg2/pytest). **Sin pandas**: la matriz se arma con listas + numpy.

---

## 5. Informe de salida (`docs/informe_arquetipos_kmeans.md`)

| Sección | Contenido |
|---------|-----------|
| Resumen ejecutivo | n=65, k elegido + silhouette, arquetipos emergentes en una línea cada uno |
| 1. Metodología | features, escalado, imputación, protocolo de k (gráfico/ tabla silhouette e inercia 2..10) — transparencia del "sesgo restante" del analista |
| 2. Elección de k | tabla k × (silhouette, inercia); k seleccionado y justificación |
| 3. Perfiles por clúster | por clúster: n, medias/medianas por feature (escala original), agentes representativos, composición por segmento GRANDE/MEDIANO/PEQUEÑO |
| 4. Arquetipos emergentes | nombre interpretado de cada clúster (perfil → etiqueta narrativa) con agentes ejemplares; columnas COP (F5) como **contexto** opcional de la muestra 25 |
| 5. Contrapunto y validación | tabla cruzada clúster×segmento y clúster×arquetipo-reglas (25); **ARI**; casos de desacuerdo (p. ej. CSIC, FERC, ISGC) explicados |
| 6. Estrategias por arquetipo | lectura de negocio por clúster (no por segmento de tamaño) |
| 7. Limitaciones | supuestos de k-means, n pequeño, sensibilidad a features/escalado/k, imputaciones, y el matiz "sin sesgo" |

---

## 6. Riesgos y limitaciones
1. **k-means asume esfericidad y varianza similar** por clúster; con variables de cola larga y outliers (ENDC 7 403 GWh, sobrecobertura 399 %) los resultados dependen del escalado (standard vs robust) y de transformaciones (log/clip) — **documentar y probar sensibilidades**.
2. **n=65 es pequeño**: los clústeres son frágiles ante cambios de features o de un agente. Mitigar con análisis de sensibilidad (k alternativo, semillas distintas) en vez de afirmar un "k verdadero".
3. **El "sin sesgo" es parcial**: features, escalado, imputación y k siguen siendo decisiones del analista (sección 1.2). El k-means no elimina la necesidad de interpretar (nombrar arquetipos es un acto humano).
4. **SICEP es NaN** en puros no regulados (no compran regulado): imputar 0 es razonable pero arrastra semántica; usar bandera `tiene_sicep` para no confundir "0% convocatoria" con "no aplica".
5. **`pct_perdidas` poco informativa en traders** (≈0, sin red): puede diluir la separación entre integrados de red; evaluar quitarla o dejarla según silhouette.
6. **`pct_cobertura` > 100 %** (sobrecobertura por trading, p. ej. FERC 399 %) distorsiona la distancia euclidiana → clip o RobustScaler.
7. **No hay precio ni margen por agente** (D3 no entra al modelo): los arquetipos describen estructura (cómo compran/venden), no desempeño financiero real.
8. **Convenciones del estudio actual que se reutilizan tal cual:** fechas fin exclusivo/inclusivo por familia (claves `fin_c_familia` vs `fin_c15` de config) y `dim_agente.activity = 'COMERCIALIZACIÓN'` (con tilde).
9. **Reproducibilidad:** toda semilla y parámetro en `config/config.yaml`; `random_state` fijo; resultados describen **comportamiento pasado** (H1-2026), no predicción.

---

## 7. Hipótesis del nuevo estudio (guía de interpretación, se contrastan de forma descriptiva)
| Hipótesis | Derivada de | Contrastación |
|-----------|-------------|---------------|
| M0: Emergen **clústeres que no coinciden 1:1 con los segmentos por tamaño** (el tamaño no es la única dimensión que separa) | Benchmark actual R0 | ARI clúster vs segmento; clústeres con composición mixta de segmentos |
| M1: El **mix regulado/no regulado** es la variable que más separa (traders puros vs integrados de red) | H1 regulatorio + R1 | importancia/varianza por feature en los perfiles; clústeres alineados a `pct_noreg` |
| M2: Dentro del no regulado, k-means **separa por apetito de riesgo spot** (exposición/cobertura/posición pico) mejor que por tamaño | R1, R2 | perfiles de clústeres con `pct_noreg` alto pero exposición/intensidad_pico distintas |
| M3: La **sobrecobertura** (trading de contratos, FERC 399 %) forma un arquetipo propio distinto del "regional regulado" | Datos F2 | clúster con cobertura > 100 % e intensidad pico vendedora |
| M4: La tipificación por reglas actual **captura bien** a los extremos (integrados grandes, puros no regulado) pero **pierde matices** que k-means recupera | `tipificacion.py` | tabla cruzada arquetipo-reglas vs clúster (25) y casos de desacuerdo |

---

## 8. Entregables y checklist de ejecución
- **Entregable A:** este documento metodológico (`docs/plan_segmentacion_kmeans.md`) — **hecho**.
- **Entregable B (código, todo aditivo — los módulos existentes quedan intactos):**
  - [x] `requirements.txt` += `scikit-learn==1.9.0` (instalado en `.venv` con numpy/scipy).
  - [x] `app/models/entities.py`: dataclasses `AgenteClusterizado`, `PerfilCluster` (sin tocar las existentes).
  - [x] `app/services/clustering.py`: matriz/transformes/clip, `elegir_k`, `aplicar_kmeans`, `perfilar_clusters`, `nombrar_arquetipo`, `comparar_con_segmento`, `comparar_con_tipificacion`.
  - [x] `app/controllers/fase_clustering.py`: agrega F1–F4 a los 65 (no modifica `fase_*.py` ni `pipeline.py`).
  - [x] `config/config.yaml`: secciones `clustering:` e `informe_kmeans:` (sección 4.3).
  - [x] `app/views/informe_clusters_md.py`.
  - [x] `main.py`: flag `--estudio kmeans` (default actual intacto).
- **Entregable C (tests, sin BD):**
  - [x] `tests/test_clustering.py`: matriz, log/clip, elección de k, reproducibilidad, perfiles, ARI (idéntico=1, aleatorio≈0), nombres de arquetipos.
- **Entregable D (resultado):**
  - [x] `./.venv/bin/python main.py --estudio kmeans` → `docs/informe_arquetipos_kmeans.md` (k=3, ARI vs segmento 0.05, ARI vs reglas 0.21).
  - [x] `./.venv/bin/python main.py` (sin flag) → `informe_estrategias_comercializacion.md` **no cambia** (verificado, sha256 idéntico).
  - [x] `./.venv/bin/python -m pytest -q` → todo verde (20 tests, incluidos los previos).
