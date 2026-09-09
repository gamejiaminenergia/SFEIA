# Funciones rotas en la BD elecdb — inventario y correcciones propuestas

> Documento de soporte para corregir la base de datos elecdb (PostgreSQL). Método: smoke test ejecutado el **2026-09-09** sobre las 33 funciones analíticas (`fn_estudio_*` y `fn_agente_*`) y 15 funciones generales.
> **Las funciones no se modificaron en la BD**: el proyecto SFEIA solo hizo consultas SELECT y bypasseó las rotas con queries directas en `sql/`. Este documento indica qué corregir y cómo.

---

## 1. Resumen del smoke test

Ventana de prueba usada: `('2026-06-01','2026-06-08')` para estudios; `'ENDC'` para funciones por agente.

### 1.1 Estado de `fn_estudio_*` y `fn_agente_*` (33)

| Estado | Funciones |
|--------|-----------|
| ✅ OK (25) | `fn_agente_garantias_exigidas`, `fn_agente_margen_comercializacion`, `fn_agente_provision_cartera`, `fn_estudio_agente_enriquecido`, `fn_estudio_c01_demanda_comercial`, `c02_compras_ventas_bolsa`, `c03_contratos`, `c04_exposicion_bolsa`, `c05_posicion_neta`, `c08_perdidas`, `c11_demanda_no_atendida`, `c13_informe_mercado`, `g01_ofertas_precios`, `g02_disponibilidad`, `g03_desempeno_generacion`, `g04_desviaciones`, `g05_reconciliaciones`, `g06_marginalidad`, `g07_oef_enf`, `g08_cumplimiento_oef`, `g09_emisiones`, `g11_embalses`, `g12_rachas_rios`, `g13_tie`, `g14_seguridad`, `g15_costos_restricciones`, `g16_rendimiento_solar` |
| ❌ ROTAS (6) | `fn_estudio_c06_ciiu`, `fn_estudio_c07_mercados`, `fn_estudio_c10_precio_contratos`, `fn_estudio_c14_upme_vs_real`, `fn_estudio_g10_combustibles` |
| ⚠️ Vacía (1) | `fn_estudio_c09_agpe` (OK pero devuelve 0 filas: columna `ExcedenteAGPE` sin datos) |

### 1.2 Funciones generales (15 probadas)

Todas ✅ OK: `fn_precios_energia`, `fn_demanda_comercial_top`, `fn_generacion_por_tipo`, `fn_estado_embalses`, `fn_factor_emision`, `fn_pct_marginal_agente`, `fn_encontrar_agente`, `fn_buscar`, `fn_analisis_concentracion_mercado`, `fn_analisis_fazni_sistema`, `fn_get_existing_columns`, `fn_count_rows`, `fn_estadisticas_bolsa_mensual_agente`, `fn_cobertura_comprador_mensual_agente`, `fn_finanzas_resumen_mensual_agente`.

---

## 2. Funciones rotas — detalle y corrección

Patrón común de error: **referencia a columnas inexistentes** (dimensiones renombradas o columnas que viven en otra tabla). Corrección con `CREATE OR REPLACE FUNCTION` (idempotente).

### 2.1 `fn_estudio_c06_ciiu(date, date)`

- **Error:** `column c.description does not exist`
- **Causa:** `dim_ciiu` no tiene `description`; tiene `ciiu_code`, `ciiu_name`, `sector`.
- **Problema de datos asociado (importante):** `dim_ciiu` está **vacía de nombres** (381 filas, todas `ciiu_name` NULL y `sector` NULL). Corregir la función no basta para etiquetar sectores; ver sección 3.1.
- **Workaround actual en el proyecto:** `sql/f4_mix.sql` consulta directa agrupando por `ciiu_code`.
- **Corrección propuesta:**

```sql
CREATE OR REPLACE FUNCTION public.fn_estudio_c06_ciiu(
    fecha_inicio date DEFAULT '2026-01-01', fecha_fin date DEFAULT '2026-07-01')
RETURNS TABLE(codigo_ciiu text, sector_ciiu text, mes text, dema_noreg_gwh numeric)
LANGUAGE plpgsql STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT c.ciiu_code::TEXT AS codigo_ciiu,
           COALESCE(c.ciiu_name, c.ciiu_code)::TEXT AS sector_ciiu,
           to_char(date_trunc('month', hc.fecha_hora), 'YYYY-MM')::TEXT AS mes,
           ROUND((SUM(hc."DemaComeNoReg")/1e6)::numeric, 2)::NUMERIC AS dema_noreg_GWh
    FROM public.fact_hourly_ciiu hc
    JOIN public.dim_ciiu c ON hc.ciiu_code = c.ciiu_code
    WHERE hc.fecha_hora >= fecha_inicio
      AND hc.fecha_hora <  fecha_fin
      AND hc."DemaComeNoReg" IS NOT NULL
    GROUP BY c.ciiu_code, c.ciiu_name, date_trunc('month', hc.fecha_hora)
    ORDER BY date_trunc('month', hc.fecha_hora), dema_noreg_GWh DESC NULLS LAST;
END;
$function$;
```

### 2.2 `fn_estudio_c07_mercados(date, date)`

- **Error:** `column m.name does not exist`
- **Causa (doble):**
  1. `dim_mercado` usa `mercado_name`, no `name`.
  2. `fact_hourly_mercadocomercializacion` **solo tiene** `DemaCome` (no `DemaComeReg`/`DemaComeNoReg`) → la función también fallaría tras corregir el nombre.
- **Workaround actual:** el proyecto no la usa (el plan la cita como contexto; F4 usa C01/C08).
- **Corrección propuesta** (elimina reg/no-reg por ausencia de datos a nivel mercado):

```sql
CREATE OR REPLACE FUNCTION public.fn_estudio_c07_mercados(
    fecha_inicio date DEFAULT '2026-01-01', fecha_fin date DEFAULT '2026-07-01')
RETURNS TABLE(mercado text, mes text, dema_gwh numeric)
LANGUAGE plpgsql STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT m.mercado_name::TEXT AS mercado,
           to_char(date_trunc('month', hm.fecha_hora), 'YYYY-MM')::TEXT AS mes,
           ROUND((SUM(hm."DemaCome")/1e6)::numeric, 1)::NUMERIC AS dema_gwh
    FROM public.fact_hourly_mercadocomercializacion hm
    JOIN public.dim_mercado m ON hm.mercadocomercializacion_code = m.mercado_code
    WHERE hm.fecha_hora >= fecha_inicio
      AND hm.fecha_hora <  fecha_fin
      AND hm."DemaCome" IS NOT NULL
    GROUP BY m.mercado_name, date_trunc('month', hm.fecha_hora)
    ORDER BY date_trunc('month', hm.fecha_hora), dema_gwh DESC NULLS LAST;
END;
$function$;
```

### 2.3 `fn_estudio_c10_precio_contratos(date, date)`

- **Error:** `column ds.PrecPromContRegu does not exist` (y también `PrecPromContNoRegu`)
- **Causa:** `fact_daily_sistema` solo tiene `PrecPromCont` (promedio general de contratos). No existe precio de contratos por tipo (reg/no-reg) en el esquema.
- **Workaround actual en el proyecto:** `sql/f5_precio_contratos.sql` consulta directa con `PrecPromCont` y `PPPrecBolsNaci`.
- **Corrección propuesta** (elimina reg/no-reg y conserva el spread general):

```sql
CREATE OR REPLACE FUNCTION public.fn_estudio_c10_precio_contratos(
    fecha_inicio date DEFAULT '2026-01-01', fecha_fin date DEFAULT '2026-07-01')
RETURNS TABLE(mes text, prec_contratos_prom_cop numeric, prec_bolsa_prom_cop numeric, spread_contratos_vs_bolsa numeric)
LANGUAGE plpgsql STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT to_char(ds.fecha, 'YYYY-MM')::TEXT AS mes,
           ROUND(AVG(ds."PrecPromCont")::numeric, 2)     AS prec_contratos_prom_cop,
           ROUND(AVG(ds."PPPrecBolsNaci")::numeric, 2)   AS prec_bolsa_prom_cop,
           ROUND((AVG(ds."PrecPromCont") - AVG(ds."PPPrecBolsNaci"))::numeric, 2) AS spread_contratos_vs_bolsa
    FROM public.fact_daily_sistema ds
    WHERE ds.fecha >= fecha_inicio
      AND ds.fecha <  fecha_fin
      AND ds."PrecPromCont" IS NOT NULL
      AND ds."PPPrecBolsNaci" IS NOT NULL
    GROUP BY date_trunc('month', ds.fecha), to_char(ds.fecha, 'YYYY-MM')
    ORDER BY date_trunc('month', ds.fecha);
END;
$function$;
```

### 2.4 `fn_estudio_c14_upme_vs_real(date, date)`

- **Error:** `column ds.EscDemUPMEAlto does not exist`
- **Causa:** los escenarios de demanda UPME (`EscDemUPMEAlto/Medio/Bajo`) viven en `fact_monthly_sistema`, **no** en `fact_daily_sistema`. La función lee de la tabla equivocada.
- **Workaround actual:** el proyecto no la usa.
- **Corrección propuesta** (agrega `fact_monthly_sistema` vía `date_trunc('month', ...)`):

```sql
CREATE OR REPLACE FUNCTION public.fn_estudio_c14_upme_vs_real(
    fecha_inicio date DEFAULT '2026-01-01', fecha_fin date DEFAULT '2026-07-01')
RETURNS TABLE(mes text, dema_real_gwh numeric, upme_alto_gwh numeric, upme_medio_gwh numeric, upme_bajo_gwh numeric, desvio_vs_medio_gwh numeric)
LANGUAGE plpgsql STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT to_char(d.fecha, 'YYYY-MM')::TEXT AS mes,
           ROUND((SUM(d."DemaSIN")/1e6)::numeric, 1)      AS dema_real_gwh,
           ROUND((SUM(m."EscDemUPMEAlto")/1e6)::numeric, 1)  AS upme_alto_gwh,
           ROUND((SUM(m."EscDemUPMEMedio")/1e6)::numeric, 1) AS upme_medio_gwh,
           ROUND((SUM(m."EscDemUPMEBajo")/1e6)::numeric, 1)  AS upme_bajo_gwh,
           ROUND(((SUM(d."DemaSIN") - SUM(m."EscDemUPMEMedio"))/1e6)::numeric, 1) AS desvio_vs_medio_gwh
    FROM public.fact_daily_sistema d
    JOIN public.fact_monthly_sistema m
      ON date_trunc('month', d.fecha) = m.fecha
    WHERE d.fecha >= fecha_inicio
      AND d.fecha <  fecha_fin
      AND d."DemaSIN" IS NOT NULL
    GROUP BY to_char(d.fecha, 'YYYY-MM')
    ORDER BY to_char(d.fecha, 'YYYY-MM');
END;
$function$;
```

### 2.5 `fn_estudio_g10_combustibles(date, date)`

- **Error:** `column c.name does not exist`
- **Causa:** `dim_combustible` usa `combustible_name`, no `name`.
- **Workaround actual:** el proyecto no la usa.
- **Corrección propuesta:**

```sql
CREATE OR REPLACE FUNCTION public.fn_estudio_g10_combustibles(
    fecha_inicio date DEFAULT '2026-01-01', fecha_fin date DEFAULT '2026-07-01')
RETURNS TABLE(codigo_combustible text, combustible text, mes text, consumo_mbtu numeric)
LANGUAGE plpgsql STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT c.combustible_code::TEXT AS codigo_combustible,
           c.combustible_name::TEXT AS combustible,
           to_char(date_trunc('month', hc.fecha_hora), 'YYYY-MM')::TEXT AS mes,
           ROUND(SUM(hc."ConsCombustibleMBTU")::numeric, 1)::NUMERIC AS consumo_mbtu
    FROM public.fact_hourly_combustible hc
    JOIN public.dim_combustible c ON hc.combustible_code = c.combustible_code
    WHERE hc.fecha_hora >= fecha_inicio
      AND hc.fecha_hora <  fecha_fin
      AND hc."ConsCombustibleMBTU" IS NOT NULL
    GROUP BY c.combustible_code, c.combustible_name, date_trunc('month', hc.fecha_hora)
    ORDER BY date_trunc('month', hc.fecha_hora), consumo_mbtu DESC NULLS LAST;
END;
$function$;
```

---

## 3. Problemas de datos (no son errores de las funciones)

### 3.1 `dim_ciiu` sin nombres
- `SELECT COUNT(*), COUNT(ciiu_name), COUNT(sector) FROM dim_ciiu;` → `381, 0, 0`.
- Todas las filas tienen `ciiu_name` y `sector` NULL. Impacto: C06 (aún corregida) etiqueta con el código. **Acción recomendada:** poblar `ciiu_name`/`sector` desde el catálogo CIIU de la DIAN (o desde el portal XM), o usar el fallback `COALESCE(ciiu_name, ciiu_code)` del punto 2.1.

### 3.2 `fn_estudio_c09_agpe` sin datos
- Ejecuta OK pero devuelve 0 filas: la columna `ExcedenteAGPE` de `fact_hourly_agente` está NULL en la ventana probada. Verificar si el ETL carga esa métrica antes de usarla (H4/AGPE del plan).

### 3.3 `CompBolsaTIEEner` / `CompBolsaIntEner` (TIE)
- También salieron NULL en la muestra H1-2026 del proyecto. Verificar carga ETL si se requiere usar TIE como palanca.

---

## 4. Funciones OK pero con mejoras recomendadas (no son bugs)

| Función | Situación | Recomendación |
|---------|-----------|---------------|
| `fn_agente_margen_comercializacion(ag, ini, fin)` | Correcta pero lenta (≈26 s/agente: re-escanea C15 3 veces) y con **parámetros fijos quemados** (Pv=350, cargo=76,1, impuesto 33%) | Parametrizar `pv`/`cargo`/`impuesto` como argumentos (como ya hace C16/C17 con factor/tasa); exponerlos. El "margen" actual es un artefacto de modelado, no el margen real |
| `fn_estudio_agente_enriquecido` (C15) | OK | Escalas inconsistentes: `pct_cob_cont`/`pct_expos_bolsa` en % (0–100), pero `pct_dema_reg`/`pct_dema_noreg`/`pct_perdidas` en fracción (0–1). Unificar a % para evitar errores de consumo |
| `fn_estudio_c05_posicion_neta` | OK | Bloque PICO 18–22h (5 h). El pico real del SIN suele ser 18–21h; validar si el bloque es intencional |

---

## 5. Cómo verificar después de corregir

Re-ejecutar el smoke test (reemplazar DSN si aplica):

```bash
./.venv/bin/python - <<'PY'
import psycopg2, time
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
conn.autocommit = True
cur = conn.cursor()
nombres = ["fn_estudio_c06_ciiu","fn_estudio_c07_mercados","fn_estudio_c10_precio_contratos",
           "fn_estudio_c14_upme_vs_real","fn_estudio_g10_combustibles"]
for n in nombres:
    t0 = time.time()
    try:
        cur.execute(f"SELECT * FROM {n}('2026-06-01','2026-06-08')")
        print(f"OK   {n:42} {len(cur.fetchall())} filas en {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"ROTA {n:42} {str(e).splitlines()[0][:90]}")
cur.close(); conn.close()
PY
```

Checklist de acciones para la BD (en orden):
- [ ] Aplicar `CREATE OR REPLACE FUNCTION` de C06, C07, C10, C14 y G10 (sección 2).
- [ ] Poblar `dim_ciiu` (`ciiu_name`, `sector`) o confirmar fallback por código.
- [ ] Verificar carga de `ExcedenteAGPE` y TIE si se usarán.
- [ ] (Opcional) Parametrizar C18 y unificar escalas de C15 (sección 4).
- [ ] Re-ejecutar el smoke test de la sección 5 y `./.venv/bin/python main.py` del proyecto.