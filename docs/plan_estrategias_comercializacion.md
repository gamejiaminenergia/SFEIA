# Plan Metodológico: Estrategias de Comercialización en el MEM

> Benchmark de mercado (regulado/no regulado, contratos vs bolsa) usando marco regulatorio CREG + datos reales XM (elecdb), con implementación en Python + SQL bajo arquitectura MVC y principios SOLID.
> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **revisado — marco regulatorio ejecutado + validación de datos elecdb (2026-09-09)**
> Documentos relacionados: `docs/analisis_regulatorio.md` (marco CREG, Q1–Q5 respondidas) · `docs/informe_estrategias_comercializacion.md` (pendiente, fase de datos)

---

## 1. Objetivo y definiciones

### 1.1 Objetivo
Definir el **método** para determinar y comparar las estrategias de comercialización de los agentes comercializadores del Mercado de Energía Mayorista (MEM) colombiano, cruzando el marco regulatorio (consultas a la CREG) con el comportamiento real de mercado (base elecdb XM). El análisis se realiza sobre la **población completa de comercializadores segmentada por tamaño (GRANDE / MEDIANO / PEQUEÑO)** — no solo los top — para tipificar arquetipos estratégicos **dentro y entre segmentos** y extraer patrones de desempeño que el foco en los grandes oculta.

### 1.2 Qué es "estrategia de comercialización" — 5 dimensiones
| # | Dimensión | Pregunta que responde |
|---|-----------|----------------------|
| D1 | **Abastecimiento / cobertura** | ¿Cómo compra la energía que vende? (contratos bilaterales vs bolsa) |
| D2 | **Mercado objetivo** | ¿A quién le vende? (regulado, no regulado por CIIU, mercados) |
| D3 | **Precio y margen** | ¿A qué precio compra/vende y qué margen neto obtiene por kWh? |
| D4 | **Riesgo y garantías** | ¿Qué exposición al spot y qué costo de garantías/cartera asume? |
| D5 | **Flexibilidad horaria** | ¿Cómo se comporta en bloques PICO vs fuera de pico? |

> **Nota de factibilidad (2026-09-09):** D3 y D5 solo son **parcialmente medibles** con elecdb. No existe precio de compra/venta **por agente** (ni contraparte de contratos): el spread contratos–bolsa solo existe a nivel de **sistema** (C10) y el margen neto por kWh (C18) es un modelo con parámetros fijos (ver secciones 3.2, 6 y 7). D5 solo captura la posición residual de bolsa (C05), no los contratos con perfil horario.

---

## 2. Marco regulatorio — ejecutado y verificado

> **Estado: ✅ completado.** Las 5 consultas (Q1–Q5) se respondieron con el asistente del gestor normativo CREG (2026-09-09). El análisis consolidado, con normas citadas e implicaciones por dimensión, está en **`docs/analisis_regulatorio.md`** (secciones 2–6). Este plan incorpora esos hallazgos; ya **no se requieren nuevas consultas** para la fase de datos (F0–F6), salvo verificación puntual de textos oficiales.

Fuente usada: skill `creg-ai-client` → API `localhost:3000/api/ask`.

### 2.1 Hallazgos regulatorios clave por dimensión
| # | Hallazgo (síntesis) | Normas núcleo citadas | Dimensión |
|---|---------------------|-----------------------|-----------|
| H1 | Mercado regulado = tarifa CREG (volumen, margen regulado CV); no regulado = precio libre (palanca de margen). Umbral no regulado: demanda > **0,1 MW** o **≥ 55 MWh/mes** en un sitio, 6 meses, con telemedida | Ley 142 y 143/1994 · Res. 131/1998 mod. 183/2009 · Res. 015/2018 y mod. (remuneración **distribución**) | D2 |
| H2 | Contratos bilaterales: **CPLC** (pague lo contratado) vs *pague lo demandado*; registro obligatorio ASIC; respaldo limitado por CROM1/CROM2; convocatoria pública (precio único, no indexado a bolsa) para regulado; tope de autocontratación con integrados **10 %** (2025) | Res. 024/1995 · 020/1996 · 079/2019 · 130/2019 · SICEP | D1, D4 |
| H3 | CU (fórmula Res. 119/2007): **G** (compra energía), **T** (STN), **D** (distribución), **CV** (margen comercialización, IPC), **PR** (pérdidas), **R** (restricciones, incluye cargo por confiabilidad), contribuciones CREG/SSPD | Res. 119/2007 | D3 |
| H4 | Opciones de compra: bolsa (spot, volátil), contratos (cobertura), cargo por confiabilidad/OEF (se activa sobre **precio de escasez** = techo del riesgo), AGPE (recepción obligatoria), TIE (cobertura financiera) | Res. 071/2006 (cargo por confiabilidad) | D1 |
| H5 | Garantías ante ASIC/XM por **exposición neta** (compras bolsa) cubriendo ~**3 meses** de liquidaciones; instrumentos líquidos/irrevocables; mora → ejecución, sanción SSPD y **retiro del mercado**; riesgo no cubierto se redistribuye entre agentes | Res. 024/1995 · 116/1998 · 070/1999 · 019/2006 · 144/2010 · 101 029/2022 | D4 |

### 2.2 Correcciones al marco (respecto al borrador previo)
- **Q1:** la Res. 015/2018 **no** define el mercado regulado/no regulado: es la metodología de **remuneración de la distribución**. El régimen reg/no-reg proviene de la Ley 143/1994 y Res. 131/1998 mod. 183/2009.
- **Q5:** las garantías **no** se rigen por la 015/2018 sino por Res. 024/1995 (Anexo C), 116/1998, 070/1999, 019/2006, 144/2010 y 101 029/2022.
- **Implicación para el plan:** usar la H1–H5 (sección 2.1) como **línea base normativa** para interpretar cada KPI de la fase de datos; ninguna fase F0–F6 depende de volver a consultar la CREG.

---

## 3. Fuente de datos de mercado — catálogo elecdb

Ventana de análisis: **enero 2024 – junio 2026** (ciclo hidrológico con Niño/Niña), foco H1-2026. Datos reales en elecdb: `fact_hourly_agente` cubre **2015-01-01 → 2026-07-31**, el rango está disponible.

> ⚠️ **Convención de fechas (verificada en el código fuente 2026-09-09):** la familia C01–C14 usa `fecha_hora >= ini AND fecha_hora < fin` (fin **EXCLUSIVO**); C15 y C16–C18 usan fin **INCLUSIVO** (`< fin + 1 día`). Para cubrir H1-2026: en C01–C14 llamar con `('2026-01-01','2026-07-01')`; en C15/C16–C18 con `('2026-01-01','2026-06-30')`. Si se pasa `'2026-06-30'` a C01–C14 se **excluye el 30-jun**.

### 3.1 Segmentación de la población por tamaño (GRANDE / MEDIANO / PEQUEÑO)

Verificación 2026-09-09 sobre `fact_hourly_agente` (2026-01-01 → 2026-07-01, `activity='COMERCIALIZACIÓN'`, `DemaCome > 0`): **65 agentes con demanda comercial** en H1-2026. La distribución es de cola larga (7 403 GWh en ENDC → 0,1 GWh en GSAC); un análisis limitado a los top-10 pierde la perspectiva del mercado minorista y de los traders especializados.

**Criterio de segmentación (variable y umbrales):**
- **Variable:** demanda comercial semestral `DemaCome` (GWh/semestre), suma de H1-2026 — métrica de tamaño de un comercializador.
- **GRANDE:** ≥ **2 000 GWh/sem** (≈ ≥330 GWh/mes, ≈460 MW promedio)
- **MEDIANO:** **100 – <2 000 GWh/sem** (≈17–330 GWh/mes)
- **PEQUEÑO:** **< 100 GWh/sem** (≈ <17 GWh/mes)

| Segmento | Criterio | Agentes | Demanda H1-2026 (GWh) | % del mercado | % regulado del segmento | % no regulado del segmento |
|----------|----------|--------:|----------------------:|--------------:|------------------------:|---------------------------:|
| **GRANDE** | ≥ 2 000 GWh/sem | 7 | 30 211,6 | 70,1 | 67 | 33 |
| **MEDIANO** | 100 – <2 000 GWh/sem | 28 | 12 196,5 | 28,3 | 76 | 24 |
| **PEQUEÑO** | < 100 GWh/sem | 30 | 688,6 | 1,6 | 37 | 63 |
| **Total** | | 65 | 43 096,7 | 100 | | |

> **Lectura estratégica:** los 7 grandes concentran el **70 %** de la demanda, pero los 30 pequeños (<2 %) tienen un mix **invertido** (63 % no regulado): el segmento pequeño es el de los **traders especializados en no regulado y de frontera**, con lógicas distintas a los integrados de red. Esa es la perspectiva que un análisis de "top" oculta.

#### 3.1.1 Muestra estratificada (selección por segmento y arquetipo)

El estudio corre sobre una **muestra estratificada** que garantiza cobertura de los tres segmentos. La asignación de segmento se calcula para **todos** los agentes (65) en la fase F-1 (sección 5) con lógica reutilizable en `app/services/segmentacion.py` (umbrales parametrizados para reproducibilidad).

| Segmento | Códigos seleccionados | N | Criterio dentro del segmento |
|----------|-----------------------|---|------------------------------|
| **GRANDE** | ENDC, EPMC, CSIC, CMMC, EPSC, GECC, ISGC | 7 | los 7 completos (columna vertebral del mercado) |
| **MEDIANO** | EMIC, ESSC, CNSC, GNCC, EMSC, NEUC, ETTC, CHVC, DRUC, BIAC | 10 | integrados regionales (EMIC, ESSC), regionales regulados (CNSC, GNCC, EMSC), traders mixtos (NEUC, ETTC, BIAC), no regulado puro (CHVC, DRUC) |
| **PEQUEÑO** | FERC, FREC, EXIC, TPLC, VESC, EBPC, EGVC, GAPC | 8 | traders no regulado especializados (FERC, FREC, EXIC, GAPC, VESC), mixto menor (TPLC), frontera regulada (EBPC, EGVC) |
| **Total** | | 25 | |

**Notas de modelo de datos (verificadas):**
- `dim_agente` tiene **una fila por (agente, actividad)**: los grupos integrados tienen códigos distintos por actividad (ENDC/ENDG/ENDD/ENDT, EPMC/EPMG/…, EPSC/EPSG/…). "Integrado" es una propiedad **corporativa que no existe como atributo** en el esquema; se reconstruye agrupando por nombre (frágil) o con una tabla de grupos a construir en `app/`.
- `dim_agente_recurso` solo enlaza el código de **GENERACIÓN** con sus plantas: sirve para métricas de generación, **no** para mapear el grupo completo.
- Se filtra `dim_agente.activity = 'COMERCIALIZACIÓN'` (con tilde) para las métricas comerciales.

### 3.2 Estudios analíticos a usar (elecdb) — granularidad verificada

> Verificación 2026-09-09 de `pg_proc`: las funciones existen con estas firmas y granularidades. Leer junto con la convención de fechas (sección 3).

| Código | Función (firma verificada) | Granularidad real | Uso en el plan |
|--------|----------------------------|-------------------|----------------|
| C01 | `fn_estudio_c01_demanda_comercial(ini, fin)` | **por agente/mes** (reg, no-reg, DemaReal) | F1, F4 (% reg/no-reg por agente) |
| C02 | `fn_estudio_c02_compras_ventas_bolsa(ini, fin)` | **por agente/mes** — incluye **generadores** (no filtra actividad) | F1 (compras bolsa, posición neta) — filtrar por lista |
| C03 | `fn_estudio_c03_contratos(ini, fin)` | **por agente/mes** — **sin contraparte** | F1 (compras/ventas contratos) |
| C04 | `fn_estudio_c04_exposicion_bolsa(ini, fin)` | **por agente/mes**: cobertura = CompCont/Dema; exposición = CompBolsa/Dema | F2 |
| C05 | `fn_estudio_c05_posicion_neta(ini, fin)` | **por agente**, bloques PICO (18–22h) / fuera de pico | F3 |
| C06 | `fn_estudio_c06_ciiu(ini, fin)` | **nivel SIN** (fact_hourly_ciiu no tiene `agente_code`) | F4 solo contexto nacional por sector CIIU |
| C07 | `fn_estudio_c07_mercados(ini, fin)` | **por mercado/zona**, no por agente | F4 contexto por mercado |
| C08 | `fn_estudio_c08_perdidas(ini, fin)` | **por agente/mes** (pérdidas % = (DemaCome−DemaReal)/DemaCome) | F4, R5 |
| C10 | `fn_estudio_c10_precio_contratos(ini, fin)` | **nivel SISTEMA** (PrecPromCont, reg/no-reg, bolsa, spread) | F5 contexto de mercado |
| C13 | `fn_estudio_c13_informe_mercado(ini, fin)` | mensual, nivel sistema | F0 |
| C15 | `fn_estudio_agente_enriquecido(ini, fin, agente?)` | **por agente/hora** + precios diarios de **sistema** | F1–F5 por agente |
| C16 | `fn_agente_garantias_exigidas(ag, ini, fin, factor=0.25, tasa=0.02)` | por agente (sobre C15) | F5 riesgo |
| C17 | `fn_agente_provision_cartera(ag, ini, fin, pv=350, incob=0.02)` | por agente (sobre C15) | F5 riesgo |
| C18 | `fn_agente_margen_comercializacion(ag, ini, fin)` | por agente (sobre C15) | **NO usar como margen real** (ver abajo) |

**Advertencias críticas verificadas en el código fuente:**
- **C15 valora la energía de TODOS los agentes con el mismo precio de sistema** (`CompContEner × PrecPromCont`, `CompBolsNaciEner × PPPrecBolsNaci`, diarios). Los valores COP por agente son **volumen × precio único de mercado**: no contienen señal de precio, spread ni margen por agente.
- **C18 usa parámetros fijos quemados** (Pv=350 COP/kWh, cargo regulado=76,1, cobertura 25 %, tasa 2 %, incobrables 2 %, impuesto 33 %). Para un comercializador regulado real (tarifa ~800 COP/kWh) su "margen" es un **artefacto de modelado**; a lo sumo sirve como proxy de riesgo estructural (vía C16), no como margen del negocio.
- **C15 mezcla escalas:** `pct_cob_cont`/`pct_expos_bolsa` están en % (0–100), pero `pct_dema_reg`/`pct_dema_noreg`/`pct_perdidas` están en fracción (0–1). Multiplicar por 100 antes de usar en la matriz.
- **C06/C07 no son por agente**: `fact_hourly_ciiu` (fecha_hora, ciiu_code, DemaComeNoReg) y `fact_hourly_mercadocomercializacion` (fecha_hora, mercado_code, DemaCome) carecen de `agente_code`.
- Existen columnas adicionales útiles en `fact_hourly_agente`: `CompContEnerSICEP`/`VentContEnerSICEP` (proxy de compras/ventas con registro SICEP, i.e. convocatoria), `CompBolsaTIEEner/Moneda`, `CompBolsaIntEner`, `ExcedenteAGPE`. En la muestra H1-2026 TIE y AGPE salieron **NULL** para los 10 sujetos → verificar cobertura antes de usarlos.

---

## 4. Arquitectura de implementación: Python + SQL · MVC · SOLID

La ejecución de F0–F6 (y toda la lógica del análisis) se construye en **Python 3** con **SQL** sobre PostgreSQL (elecdb) y el cliente CREG externo (`localhost:3000/api/ask`), aplicando **MVC** y **principios SOLID**.

### 4.1 Estructura del proyecto (MVC)
```
SFEIA/
├── config/                      # CONFIG: entorno, umbrales y parámetros (sin secretos)
│   ├── settings.py              # Carga DB_DSN/CREG_URL desde variables de entorno
│   ├── config.yaml              # Umbrales segmentación (F-1), parámetros modelos C16–C18
│   └── .env.example             # Plantilla de variables de entorno (credenciales fuera de git)
├── docs/                        # Plan y entregables .md (View de reportes)
├── app/
│   ├── models/                  # MODEL: datos y negocio
│   │   ├── entities.py          # Agente, Benchmark, Estudio, KPI, Segmento (dataclasses)
│   │   └── repositories.py      # Acceso a datos: elecdb (SQL desde sql/) y cliente CREG
│   ├── controllers/             # CONTROLLER: orquestación
│   │   ├── pipeline.py          # Ejecuta fases F-1, F0–F6 en orden
│   │   └── fase_*.py            # Un controlador por fase de la metodología
│   ├── views/                   # VIEW: renderizado de resultados
│   │   ├── informe_md.py        # Genera docs/*.md (tablas y matriz por segmento)
│   │   └── templates/           # Plantillas de informe/matriz
│   └── services/                # Lógica de negocio reutilizable (cálculos KPI)
│       ├── segmentacion.py      # Asignación GRANDE/MEDIANO/PEQUEÑO (F-1, umbrales config.yaml)
│       ├── kpi_cartera.py
│       ├── kpi_cobertura.py     # % cobertura/exposición
│       └── tipificacion.py      # Asignación de arquetipos por segmento
├── sql/                         # Queries SQL parametrizadas (una por estudio/fase)
│   ├── f-1_segmentacion.sql     # DemaCome H1-2026 por agente (insumo F-1)
│   ├── f0_contexto_mercado.sql  # C13
│   ├── f1_cartera.sql           # C01–C03 + SICEP
│   ├── f2_cobertura.sql         # C04
│   ├── f3_pico_valle.sql        # C05
│   ├── f4_mix.sql               # C01, C08
│   └── f5_financiero.sql        # C15, C16–C18
├── tests/                       # Pruebas unitarias e integración
└── main.py                      # Punto de entrada (invoca controllers)
```

**Flujo MVC:** `Controller` (pipeline por fases) → solicita datos a `Model` (repositorios SQL elecdb / CREG) → procesa en `services` → entrega datos limpios a `View` (genera los `.md`). La vista jamás consulta la BD ni la CREG; el modelo jamás renderiza.

### 4.2 SQL
- Consultas **siempre parametrizadas** y con filtro de fecha obligatorio (`fecha_hora >= %s AND fecha_hora < %s`) sobre tablas horarias (~11–17 M filas).
- Reutilizar las funciones analíticas existentes `fn_estudio_*` (C01–C18) y `fn_*` de la capa semántica en lugar de duplicar JOINs manuales.
- Queries aisladas en `sql/` (una por estudio/fase, ver árbol de la sección 4.1) para reuso por el modelo y los tests; **nunca** literales SQL dentro de controllers/views.

### 4.3 Principios SOLID aplicados
| Principio | Aplicación concreta |
|-----------|---------------------|
| **S** — Responsabilidad única | Una clase por función: `RepoElecdb` (solo SQL/BD), `RepoCreg` (solo API CREG), `CalculadoraCobertura`, `GeneradorInforme`. |
| **O** — Abierto/Cerrado | Nuevos estudios o KPIs se agregan como nuevas clases/repositorios **sin modificar** `pipeline.py` (registro por extensión). |
| **L** — Sustitución de Liskov | `RepoElecdb`/`RepoCreg` implementan una interfaz común `FuenteDatos`; cualquier fuente nueva es intercambiable sin tocar controllers. |
| **I** — Segregación de interfaces | Interfaces pequeñas por propósito: `FuenteMercado` (elecdb) ≠ `FuenteRegulacion` (CREG); `Reportable` solo expone `render()`. |
| **D** — Inversión de dependencias | Controllers/Views dependen de **abstracciones** (`FuenteDatos`, `RepositorioKPI`), nunca de psycopg2/requests directamente; las dependencias se inyectan (constructor/DI simple). |

### 4.4 Stack técnico
- **Python 3.11+** · `psycopg2`/`psycopg` (PostgreSQL elecdb) · `requests`/`httpx` (API CREG) · `dataclasses` para entidades · pruebas con `pytest`.
- Sin frameworks web; MVC como patrón de **código organizado** (no Django/Flask, a menos que se requiera UI posterior).
- Conexión BD por variables de entorno (`DB_DSN`, `CREG_URL`) cargadas desde `config/` (`settings.py` + `.env`); sin credenciales en código.

---

## 5. Metodología por fases

> Las fases F0–F6 ya no consultan a la CREG (marco resuelto, sección 2). La columna "Línea base" indica qué hallazgo regulatorio (H1–H5) guía la **interpretación** de cada KPI.

| Fase | Objetivo | Línea base normativa | Función elecdb | KPIs resultantes |
|------|----------|----------------------|----------------|------------------|
| **F-1** | Segmentar la población por tamaño | — | `fact_hourly_agente` (DemaCome H1-2026) + `segmentacion.py` | segmento GRANDE/MEDIANO/PEQUEÑO por agente (los 65); muestra estratificada (25) |
| **F0** | Contexto de mercado | H4 (precio de escasez = techo riesgo) | `fn_estudio_c13_informe_mercado('2024-01-01','2026-07-01')` | PBM prom/máx/mín, precio escasez, demanda SIN |
| **F1** | Perfil de cartera y tamaño | H2 (contratos vs bolsa) | C01, C02, C03 (+ `CompContEnerSICEP`) | GWh comprados bolsa vs contratos; posición neta; % compras reg. con registro SICEP |
| **F2** | Cobertura/exposición | H2 + H5 (exposición = riesgo de garantías) | C04, C15 | % cobertura contratos; % exposición bolsa |
| **F3** | Timing pico/valle | H3 (R/restricciones, CREE en CV) | C05 | rol neto por bloque PICO (18-22h) vs fuera de pico |
| **F4** | Mix de mercado objetivo | H1 (umbral 0,1 MW / 55 MWh-mes) | C01, C15 (por agente); C06/C07 solo contexto SIN; C08 | % demanda regulada vs no regulada **por agente**; pérdidas % |
| **F5** | Precio y margen | H3 (G define spread; CV margen regulado) + H5 | C13, C15, C10 (contexto), C16–C18 (modelo) | spread contratos–bolsa **de mercado** (sistema); costo energía est.; garantía/cartera est. — **no hay margen real por agente** |
| **F6** | Síntesis de patrones | H1–H5 integradas | Cruce de resultados (muestra 25) | arquetipos + matriz comparada **por segmento** + estrategias recomendadas por segmento |

**Regla de ejecución:** siempre filtrar por rango de fechas (tablas de ~11–17 M filas) y respetar la convención de fin exclusivo/inclusivo (sección 3: C01–C14 `fin` exclusivo → pasar `fin+1 día`; C15/C16–C18 `fin` inclusivo). Ejecutar **F-1 (segmentación) antes de F0–F6** para fijar la muestra y los segmentos sobre datos. Los valores COP de C15/C16–C18 son **estimaciones = volumen del agente × precio promedio de sistema** (no hay precio horario ni precio por agente en elecdb; no sustituyen liquidaciones XM). Cada fase se implementa como un controlador (`controllers/fase_*.py`) que consume repositorios del modelo y alimenta a la vista.

### 5.1 Hipótesis regulatorias contrastables con los datos
Cada hipótesis conecta un hallazgo del `analisis_regulatorio.md` con un umbral medible en elecdb (guía de F6 para tipificar patrones):

| Hipótesis | Derivada de | Contrastación empírica (elecdb) |
|-----------|-------------|--------------------------------|
| R0: El **tamaño condiciona la estrategia**: los GRANDE (70 % del mercado) combinan regulado y no regulado con cobertura de contratos alta; los MEDIANO son regionales regulados o traders mixtos; los PEQUEÑO son traders no regulado (mix invertido) con mayor exposición spot | Segmentación (sección 3.1) | Comparación **por segmento** de C01 (mix reg/no-reg), C04 (cobertura/exposición) y C05 (rol neto); estadística descriptiva (media/mediana/rango) dentro de cada segmento |
| R1: El **no regulado es el segmento de mayor apetito de riesgo**: mayor % no regulado se asocia a mayor exposición a bolsa y rol neto distinto en spot | H1 (Q1) | Correlación: % demanda no regulada **por agente** (C01) vs % exposición bolsa (C04) y rol neto (C05). **No** se mide margen: el precio de venta por agente no existe en elecdb |
| R2: A mayor exposición a bolsa, mayor garantía estimada y capital de trabajo | H5 (Q5) | C04 (% exposición) vs C16 (garantía estimada, modelo) por agente (C16 es lineal en volumen × precio de sistema; la correlación es estructural) |
| R3 (reformulada): La proporción de compras reguladas **con registro SICEP** distingue renovación de cartera; el **tope del 10 % de autocontratación no es medible** (sin contraparte) | H2 (Q2) | `CompContEnerSICEP`/`CompContEnerReg` por agente. Preliminar H1-2026: EPMC 97 %, ENDC 90 %, CMMC 93 %, ESSC 96 %, EMSC 82 %, EMIC 62 %, **CSIC 30 %** → CSIC señal (cartera antigua fuera de convocatoria) |
| R4: En eventos de escasez (precio > precio de escasez), el descalce de cobertura explica resultados de comercializadores con alta exposición (caso CSIC) | H4 (Q4) | C13 (meses con PBM>escasez) × C15 (posición neta y exposición) por agente |
| R5 (reformulada): Menores **pérdidas (PR)** se asocian a mayor eficiencia de la red integrada (mayor % regulado servido) | H3 (Q3) | C08 (% pérdidas por agente) vs % regulado (C01) y % exposición (C04). **No** contrastable contra margen: no existe margen real por agente |

> Nota: R0–R5 son **contrastaciones descriptivas** sobre comportamiento pasado en la ventana del plan (2024–2026), no relaciones causales probadas.

---

## 6. Matriz de benchmark (plantilla de salida)

| Segmento | Agente | Demanda GWh (H1-26) | % Regulado | % Cobertura contratos | % Exposición bolsa | % Compras reg. SICEP | Pérdidas % | Costo energía est. (COP/kWh)⁺ | Garantía est. (COP)† | Arquetipo |
|----------|--------|--------------------:|-----------:|----------------------:|-------------------:|---------------------:|-----------:|------------------------------:|---------------------:|-----------|
| GRANDE   | ENDC   | … | … | … | … | … | … | … | … | … |
| MEDIANO  | NEUC   | … | … | … | … | … | … | … | … | … |
| PEQUEÑO  | FERC   | … | … | … | … | … | … | … | … | … |

⁺ Costo energía estimado = egreso COP (C15) / energía comprada; usa el precio promedio **de sistema**, idéntico para todos los agentes → **no** es señal de eficiencia de compra.
† Garantía estimada por el modelo C16 (25 % de exposición neta valorada a precio de sistema); proxy de riesgo, no obligación real ante XM.

> La matriz se genera para la **muestra estratificada (25 agentes)** y se reporta con estadísticas **por segmento** (media, mediana, mín–máx), no solo filas individuales: el objetivo es comparar segmentos, no rankear agentes.

> **El spread contratos–bolsa y el "margen neto COP/kWh" se retiran de la matriz por agente:** solo existen a nivel de **sistema** (C10) o como artefacto de modelado (C18). Se reportan como contexto de mercado en F0/F5, nunca como columna por agente.

### Arquetipos a tipificar (lógica en `services/tipificacion.py`) — por segmento
Discriminadores normativos → empíricos (R0–R5, sección 5.1):
- **GRANDE · Integrado de red** (ENDC, EPMC, EPSC…): % regulado alto, cobertura de contratos alta, compras reguladas mayoritariamente con registro SICEP (señal de convocatoria). El **tope del 10 % de autocontratación** (H2) **no es verificable** con elecdb (sin contraparte).
- **GRANDE · Intervenido** (CSIC): baja proporción de compras SICEP (≈30 %) + descalce de cobertura en escasez (R4) — métricas de control/riesgo.
- **GRANDE/MEDIANO · Generador+comercializador solo no regulado** (GECC, ISGC; CHVC, DRUC): 100 % no regulado, rol de riesgo spot (R1).
- **MEDIANO · Regional regulado** (CNSC, GNCC, EMSC, HLAC, EBSC…): red + convocatoria, % regulado alto, exposición baja.
- **MEDIANO · Trader mixto** (NEUC, ETTC, BIAC…): mezcla regulado/no regulado, cobertura intermedia.
- **PEQUEÑO · Trader no regulado especializado** (FERC, FREC, EXIC, GAPC…): % no regulado alto, mayor exposición relativa, garantía nominal baja (R2).
- **PEQUEÑO · Frontera regulada** (EBPC, EGVC…): escala mínima, 100 % regulado, tarifa CREG.

### Columnas adicionales sugeridas para el informe F6
- **% compras reguladas con registro SICEP** (`CompContEnerSICEP`/`CompContEnerReg`): proxy de compra vía convocatoria pública (H2). Reemplaza a la autocontratación con integrados, que **no es medible** en elecdb.
- **Exposición máxima en meses de escasez** (PBM > precio de escasez) para identificar descalces tipo CSIC (H4/R4).
- **Estadísticas por segmento** (media/mediana/rango de cada KPI) para el contraste R0.

---

## 7. Riesgos y limitaciones
1. Las respuestas CREG del `analisis_regulatorio.md` son generadas por el asistente del gestor normativo; **verificar texto oficial** de cada resolución antes de uso jurídico/contractual (numeración y vigencia pueden variar).
2. **No hay precio de contratos por agente ni contraparte de contratos en elecdb.** C15 valora todo volumen al precio promedio **de sistema** (`PrecPromCont`/`PPPrecBolsNaci`, diarios): los valores COP, C16 y C18 son **volumen × precio único**; no contienen señal de precio, spread ni margen por agente.
3. **C18 (margen neto) es un modelo con parámetros fijos** (Pv=350 COP/kWh, cargo=76,1, 25 %, 2 %, 2 %, 33 %) → produce márgenes negativos artificiales en comercializadores regulados. **No usar como margen real**; a lo sumo como proxy de riesgo estructural (C16).
4. **La autocontratación con integrados (tope 10 %, H2) no es medible** (sin contraparte); se aproxima con la proporción de compras reguladas con registro SICEP.
5. C06/C07 no son por agente (`fact_hourly_ciiu` y `fact_hourly_mercadocomercializacion` carecen de `agente_code`): el % reg/no-reg por agente sale de C01/C15.
6. **Convención de fechas:** C01–C14 fin **exclusivo**; C15/C16–C18 fin **inclusivo**. Pasar `fin+1 día` a la familia C si se quiere incluir el último día.
7. C15 mezcla escalas: `pct_cob_cont`/`pct_expos_bolsa` en % (0–100); `pct_dema_reg`/`pct_dema_noreg`/`pct_perdidas` en fracción (0–1).
8. CSIC (intervenido) distorsiona promedios de mercado → analizarlo por separado.
9. `dim_agente.activity` usa acentos: `'COMERCIALIZACIÓN'`.
10. TIE (`CompBolsaTIEEner`) y AGPE (`ExcedenteAGPE`) salieron **NULL** en la muestra H1-2026 → verificar cobertura antes de usarlos como palancas (H4).
11. El ranking/segmento de agentes depende de la métrica y de la ventana (DemaCome H1-2026): agentes nuevos o con entrada tardía pueden tener demanda parcial → **verificar actividad** del agente antes de asignar segmento (F-1); umbrales parametrizables en `segmentacion.py`.
12. Los datos de **PEQUEÑO** son más ruidosos (volúmenes bajos, NULLs, entrada/salida dentro de la ventana); la segmentación no captura el número de clientes (no disponible en elecdb), solo volumen.
13. Agentes **limítrofes** al umbral (p. ej. EMIC 1 645 GWh vs 2 000) deben documentarse y probarse con sensibilidades (1 000 / 2 000 / 3 000 GWh) para verificar que los patrones no dependen del corte.
14. Resultados describen **comportamiento pasado**, no predicción.
15. R0–R5 (sección 5.1) son hipótesis descriptivas reformuladas a variables **medibles** (estructura, volumen, segmento), no a precio/margen por agente.

---

## 8. Entregables y cronograma
- **Entregable 1 (completado):** marco regulatorio → `docs/analisis_regulatorio.md` (Q1–Q5, hallazgos H1–H5, corrección de normas).
- **Entregable 2 (completado):** este documento metodológico (`plan_estrategias_comercializacion.md`), refinado con las hipótesis R0–R5 y la **segmentación GRANDE/MEDIANO/PEQUEÑO** (sección 3.1).
- **Entregable 3 (código, fase posterior):** estructura `config/` + `app/` con arquitectura MVC + SOLID (sección 4), `main.py` como punto de entrada, queries SQL parametrizadas en `sql/` y pruebas en `tests/` con `pytest` (incluye `services/segmentacion.py`).
- **Entregable 4 (resultado):** correr F-1 (segmentación) y F0–F6 y producir `docs/informe_estrategias_comercializacion.md` con la matriz del punto 6 llena **por segmento**, columnas adicionales de F6, estadísticas por segmento y arquetipos tipificados contrastando R0–R5.

### Checklist de ejecución (cuando se apruebe la fase de datos)
- [ ] Crear estructura `config/` + `app/` (models, controllers, views, services) + `sql/` + `tests/` + `main.py`
- [ ] Implementar repositorios `RepoElecdb` y `RepoCreg` tras interfaz `FuenteDatos` (inyección de dependencias)
- [ ] **F-1 segmentación:** asignar GRANDE/MEDIANO/PEQUEÑO a los 65 agentes (DemaCome H1-2026) + definir muestra estratificada (25) y sensibilidades de umbral
- [ ] F0 contexto de mercado (C13) → tabla resumen + meses con PBM > precio de escasez (R4)
- [ ] F1–F3 por agente (C01–C05, C15) → 3 tablas (respetar fin exclusivo/inclusivo, sección 3)
- [ ] F4 mix por agente (C01, C15, C08; C06/C07 solo contexto SIN) → 1 tabla + análisis CIIU (R1)
- [ ] F5 precio/margen (C13, C15, C10 contexto, C16–C18 modelo de riesgo) → 1 tabla financiera (R2, R4, R5) **sin** "margen neto real" por agente
- [ ] F6 síntesis → matriz punto 6 **por segmento** + columnas F6 + arquetipos + contraste R0–R5
- [ ] Pruebas `pytest` de cada fase, de la segmentación (F-1) y de la tipificación de arquetipos
