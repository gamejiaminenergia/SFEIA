# Plan — Agente hipotético XXXC: búsqueda del mejor perfil + asistente de decisiones

> Objetivo: usar los datos del estudio híbrido diario (5 arquetipos, segmentos GRANDE/MEDIANO/PEQUEÑO, precios
> diarios de sistema y modelo financiero C16–C18) para (1) encontrar automáticamente la **mejor configuración**
> para un agente nuevo **XXXC** (que aún no existe) de un segmento dado, por criterio **riesgo-ajustado**, y
> (2) construir un **asistente CLI** que lea las condiciones de mercado de la BD y recomiende a XXXC qué
> estrategia/acción tomar.
> Proyecto: SFEIA · Fecha: 2026-09-09 · Estado: **plan propuesto (pendiente de implementación)**
> Documentos relacionados: `docs/plan_estrategias_diarias.md` (estudio activo, se reutiliza) · `docs/informe_estrategias_diarias.md` (salida del estudio)

---

## 1. Motivación y decisiones de diseño (acordadas)

| Decisión | Elección |
|---|---|
| Definición de XXXC | **Búsqueda automática del mejor perfil**: el sistema explora candidatos (arquetipos × variaciones de cobertura/exposición) y dice cuál es la mejor configuración para un segmento objetivo. |
| Métrica de "mejor" | **Riesgo-ajustado**: `score = mediana_margen − κ·IQR` (robusta a outliers y a márgenes negativos). Se reportan también garantía, peor día (p5) y % días ganando al mejor arquetipo. |
| Forma del asistente | **CLI de recomendación**: un script que corre bajo demanda y recomienda la estrategia/acción para hoy. |
| Entrada del asistente | **Condiciones de mercado desde la BD** (`fact_daily_sistema`: `PrecPromCont`, `PPPrecBolsNaci`, `PrecEsca`). |

## 2. Parte 1 — Simulador y búsqueda del mejor perfil (`app/services/simulador.py`)

- **Candidatos anclados a los arquetipos:** para el segmento objetivo (por defecto PEQUEÑO), se genera una
  cuadrícula sobre cada arquetipo variando sus dos palancas `pct_cobertura` y `pct_exposicion` (niveles
  configurables, p. ej. 5×5); `pct_noreg` y `pct_sicep` heredan del arquetipo base. La demanda diaria se fija en
  la **mediana diaria del segmento** (o un valor pasado por CLI).
- **Simulación diaria:** por candidato y día se construye el agregado diario `ad` (compras contratos/bolsa =
  demanda × cobertura/exposición; ventas = 0, coherente con el modelo del estudio) y se calcula el margen con la
  **misma lógica** de `diario.desempeno_diario` (reusa `kpi_cartera.modelo_financiero`) sobre los precios reales
  del día → serie de ~212 márgenes diarios por candidato.
- **Métrica riesgo-ajustado:** `score = mediana_margen − κ·IQR` (κ configurable). Contexto: mediana de garantía,
  percentil 5 % (peor día) y % de días en que el candidato supera al mejor arquetipo.
- **Salida:** ranking de candidatos → **mejor perfil para XXXC** (cobertura, exposición, mix reg/no-reg, SICEP,
  arquetipo más cercano, margen y riesgo esperados).

## 3. Parte 2 — Asistente CLI (`app/services/asesor.py` + `asesor.py`)

- **Condiciones de mercado desde BD:** se lee de `fact_daily_sistema` el día indicado (o el último de la ventana):
  precio bolsa, contratos, escasez → `spread = bolsa − contratos` y flag de escasez.
- **Contexto → estrategia:** se binifica el spread (p. ej. «bolsa muy barata / barata / neutral / cara / escasez»);
  para el segmento de XXXC se usa el **ranking diario histórico por segmento** (`datos["diario"]["ranking_por_segmento"]`)
  para saber qué estrategia **ganó más días** dentro de ese bin → estrategia recomendada.
- **Estrategia → acción:** se traduce el perfil de la estrategia recomendada a acciones concretas frente al perfil
  actual de XXXC (p. ej. «sube cobertura a 80 %, baja exposición a 30 %»), con justificación (spread actual,
  escasez, antecedente histórico).
- **CLI:**
  ```
  asesor.py perfil --segmento PEQUEÑO [--demanda-dia 0.5]
  asesor.py recomendar [--segmento PEQUEÑO] [--fecha 2026-07-23]
  ```
  Ambos subcomandos ejecutan F-1 + `FaseDiaria` (reutilizan los datos del estudio) y responden sobre XXXC.

## 4. Arquitectura (MVC, aditiva — no toca el estudio)

| Archivo | Rol |
|---|---|
| `app/services/simulador.py` | Lógica pura: generación de candidatos, simulación diaria, métricas riesgo-ajustado, ranking. |
| `app/services/asesor.py` | Lógica pura: contexto de mercado, binificación del spread, recomendación estrategia/acción. |
| `app/controllers/fase_asesor.py` | Lee precios diarios de BD (reusa `repo.diario`) y orquesta perfil/recomendación. |
| `asesor.py` (raíz) | CLI: subcomandos `perfil` y `recomendar` (patrón de `main.py`). |
| `config/config.yaml` | Sección nueva `asesor:` (segmento por defecto, niveles de cuadrícula, κ, bins de spread). |
| `tests/test_simulador.py` | Pruebas sin BD (generación de candidatos, simulación, métrica, ranking). |
| `tests/test_asesor.py` | Pruebas sin BD (bins de spread, recomendación en contexto). |

Flujo MVC: `asesor.py` (controller) → consulta precios al repo → lógica pura en `services` (simulación/ranking o
recomendación) → imprime el resultado en consola. Views/BD: sin cambios en el estudio diario.

## 5. Config propuesta (`config/config.yaml`, sección `asesor:`)

```yaml
asesor:
  segmento_por_defecto: PEQUEÑO      # segmento objetivo de XXXC
  dema_dia_gwh: null                 # null -> mediana diaria del segmento
  cobertura_vals: [0, 20, 50, 80, 110, 150, 200]
  exposicion_vals: [0, 10, 30, 60, 100]
  k_riesgo: 1.0                      # score = mediana_margen - k*IQR
  bins_spread:
    muy_barata: [-inf, -50]
    barata: [-50, 0]
    neutral: [0, 50]
    cara: [50, 150]
    escasez: [150, inf]
```

## 6. Verificación (cuando se implemente)

- `./.venv/bin/python asesor.py perfil --segmento PEQUEÑO` → muestra el mejor perfil para XXXC.
- `./.venv/bin/python asesor.py recomendar` → recomendación con las condiciones del último día de la ventana.
- `./.venv/bin/python -m pytest -q` → todo verde (39 existentes + nuevos).

## 7. Limitaciones a documentar

1. El margen es **artefacto de modelado** (Pv=350 fijo): «mejor» es relativo entre candidatos, no un margen real.
2. El simulador no modela **reventa** del excedente ni clientes reales; la sobrecobertura sale penalizada por
   diseño (coherente con el estudio).
3. El asistente opera sobre la **ventana histórica** de la BD; para un «hoy» real habría que alimentar precios
   actuales (mejora futura).
4. Resultados describen **comportamiento pasado**; la recomendación es un patrón histórico, no predicción.