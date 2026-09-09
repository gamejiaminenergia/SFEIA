# Plan Metodológico: Estrategias Diarias de Comercialización en el MEM — Estudio híbrido

> Un único estudio que fusiona el benchmark por segmento (F-1, F0–F6) y el k-means de H1-2026, y los reemplaza:
> agrupa a los **65 comercializadores** en arquetipos por **k-means pooled sobre agentes-día** (no supervisado,
> sin umbrales ni reglas manuales) y rankea las estrategias por su **desempeño diario** (margen estimado por kWh,
> lógica C16–C18 del benchmark), con balance final del período.
> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **implementado — informe generado (`docs/informe_estrategias_diarias.md`, k=5, Ene–Jul 2026)**
> Documentos relacionados: `docs/plan_estrategias_comercializacion.md` y `docs/plan_segmentacion_kmeans.md` (estudios **reemplazados**; informes archivados en `docs/archivado/`).

---

## 1. Objetivo

Dado un período de fechas (por defecto **2026-01-01 → 2026-07-31**), determinar para **todos** los comercializadores
su **estrategia diaria** y, basado en esa agrupación de estrategias, ordenar **cada día** cuál funcionó mejor y
hacer un **balance** de cuál funcionó mejor en el período. El entregable es `docs/informe_estrategias_diarias.md`.

### 1.1 Qué toma de cada estudio anterior

| Fuente | Qué aporta |
|--------|-----------|
| **k-means (H1-2026)** | Agrupación no supervisada en arquetipos; elección de k; features (6) y transformaciones (log1p, clip); reproducibilidad (seed fija). |
| **Benchmark (F-1, F0–F6)** | Modelo financiero C16–C18 (margen estimado por kWh) como métrica de desempeño; segmentación por tamaño como contexto; advertencias de datos (COP = volumen × precio de sistema). |
| **Nuevo** | Granularidad **diaria** y ranking temporal de estrategias con balance del período. |

### 1.2 Definición de "estrategia" diaria
- **Población:** los 65 comercializadores con demanda en la ventana (F-1).
- **Matriz pooled de agentes-día:** una fila por (agente, día) con las **6 features diarias** del estudio k-means
  (`log_dema`, `pct_noreg`, `pct_cobertura`, `pct_exposicion`, `pct_sicep`, `tiene_sicep`).
- **K-Means sobre la matriz pooled** (~13 800 filas): los arquetipos emergen del comportamiento diario real;
  un agente puede cambiar de estrategia de un día a otro. Nombres de arquetipo: etiquetas post-hoc sobre los centroides.
- **k:** la silhouette es plana (~0.4) en la población diaria pooled (no discrimina); **k se fija en 5** por
  interpretabilidad (config `diario.k`). `k: null` lo devolvería a automático.

### 1.3 Definición de "funcionó mejor"
- **Desempeño diario por agente:** margen estimado por kWh (lógica C16–C18) sobre los agregados diarios de C15:
  compras/ventas valoradas con el precio promedio **de sistema** del día (`PrecPromCont`, `PPPrecBolsNaci`).
  Diferencia a los agentes por su mix diario contratos/bolsa y reg/no-reg. No existe precio ni margen real por agente.
- **Ranking diario:** por día, se ordenan las estrategias por la **mediana** del margen diario (empates por media).
- **Balance del período:** por estrategia — mediana/media del margen diario, días en 1.er puesto, % top-3, rango
  promedio y tendencia (2.ª mitad − 1.ª mitad).

### 1.4 Granularidad por segmento (GRANDE/MEDIANO/PEQUEÑO)
El ranking pooled mezcla segmentos de tamaños muy distintos (los GRANDE integrados podrían dominar). Para no
meter "todo en el mismo saco", el **segmento F-1 es variable de análisis** (no entra al k-means) y se calcula:

- **`ranking_por_segmento`**: ranking diario de estrategias **dentro de cada segmento** (solo agentes-día de ese
  segmento, mismos arquetipos pooled).
- **`balance_por_segmento`**: balance del período por segmento (con el guard `min_dias_pct` aplicado dentro de
  cada segmento).
- **`estrategia_x_segmento`**: matriz estrategia × segmento con la **mediana de medianas diarias** (coherente con
  el balance; celdas = mediana del margen diario y días presentes). Las estrategias atípicas del segmento se marcan
  y no se resaltan como la mejor.

Esto responde "¿qué estrategia les funciona a los MEDIANO y PEQUEÑO?" sin que los GRANDE contaminen el ranking.

---

## 2. Datos y granularidad (verificado)

- `fact_hourly_agente` cubre la ventana (212 días, ~1.2 M filas); `fact_daily_sistema` tiene **una fila por fecha**
  con precios diarios (`PrecPromCont`, `PPPrecBolsNaci`, `PrecEsca`) → JOIN seguro.
- `sql/d1_diario.sql` agrega por (fecha, agente) una sola pasada para todos los agentes (~1 s) e incluye compras/
  ventas de bolsa y contratos (necesarias para la exposición neta del modelo).
- Convención de fechas: familia C01–C14 fin **exclusivo** (`fin_c_familia: 2026-08-01`); C15/C16–C18 fin **inclusivo**
  (`fin_c15: 2026-07-31`). Población verificada: **65 agentes**, 50 381 GWh.

---

## 3. Guardas de robustez (config `diario:`)

1. **Winsorización del margen** (`clip_margen_cop_kwh: 500`): los traders con volumen transado muy superior a su
   demanda producen márgenes por kWh desproporcionados (artefacto del denominador `demanda`); se tech a ±500.
2. **Umbral mínimo de presencia** (`min_dias_pct: 20`): las estrategias presentes en menos del 20 % de los días se
   reportan como **casos atípicos** y se excluyen del ranking (no representan al período). Evita que un clúster
   espurio de 2–3 agentes-día "gane" la narrativa.
3. **Techo de SICEP** (`clip_pct_sicep: 100`): `CompContEnerSICEP` puede incluir compras no reguladas y superar el
   100 % en días puntuales; se techa para no generar features espurias.

---

## 4. Implementación (MVC)

| Archivo | Rol |
|---------|-----|
| `sql/d1_diario.sql` | Query diaria (agregación por agente/día + precios). |
| `app/models/repositories.py` | + `RepoElecdb.diario(ini, fin)` (aditivo). |
| `app/models/entities.py` | + `AgenteDia`, `PerfilEstrategia`, `BalanceEstrategia` (aditivo). |
| `app/services/diario.py` | Lógica pura: `construir_agente_dia`, `features_diarias`, `desempeno_diario`, `construir_matriz_diaria`, `elegir_k_diario`, `perfilar_estrategias`, `ranking_diario`, `balance_periodo`, `separar_atipicos`, `matriz_puestos`, `ranking_diario_por_segmento`, `balance_por_segmento`, `matriz_estrategia_x_segmento`. |
| `app/controllers/fase_diaria.py` | Orquesta: F-1 (reusa `FaseSegmentacion`) + agregación diaria + clustering + ranking. |
| `app/views/informe_diario_md.py` | Renderiza `docs/informe_estrategias_diarias.md`. |
| `tests/test_diario.py` | Pruebas sin BD (matriz, margen, k, ranking, balance, guardas). |
| `config/config.yaml` | Sección `diario:` (features, k, guardas) + `informe_diario:` + `ventana:` Ene–Jul 2026. |
| `main.py` | Sin flags: F-1 + `FaseDiaria` → informe único. |

**Consolidación:** los controladores/servicios/vistas de los estudios anteriores se conservan en el árbol pero ya
no se invocan desde `main.py`; sus informes se archivaron en `docs/archivado/`. **No existe muestra**: F-1 y el
estudio diario cubren **todos** los comercializadores con demanda en la ventana (los 65); se eliminaron las listas
`muestra:` y la selección de muestra de `config/config.yaml`.

---

## 5. Estructura del informe

1. Resumen ejecutivo — ranking final de estrategias.
2. Metodología — features diarias, clustering, desempeño, guardas.
3. Elección de k — tabla silhouette/inercia.
4. Arquetipos diarios — perfiles por clúster (n agentes-día, medias, composición por segmento, representativos).
5. Ranking diario — matriz de puestos (pooled y **por segmento**) + días destacados (bolsa cara, escasez).
6. **Ranking y balance por segmento** — mejor estrategia de GRANDE/MEDIANO/PEQUEÑO + matriz estrategia × segmento.
7. Balance del período — ranking final pooled + casos atípicos + narrativa.
8. Limitaciones.

---

## 6. Riesgos y limitaciones

1. No hay precio ni margen real por agente: todo COP es volumen × precio de sistema; margen = artefacto (Pv=350 fijo).
2. K-means descriptivo: asume esfericidad/varianza similar; features, escalado y k son decisiones del analista.
3. Agentes diminutos → features ruidosas y márgenes extremos (mitigado con log1p/clip/winsorización).
4. SICEP diario 0 imputado en puros no regulados (`tiene_sicep` los distingue).
5. Sin precios de contrato por agente ni contraparte: el margen solo capta el mix y el nivel de precio de sistema.
6. Describe comportamiento **pasado** (Ene–Jul 2026), no predicción.