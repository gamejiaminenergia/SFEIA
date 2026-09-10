# Plan — Recomendación rodante "lo actual y el futuro" (ancla al borde de datos)

> Proyecto: SFEIA · Fecha: 2026-09-10 · Estado: **pendiente de aprobación**
> Documentos relacionados: `docs/plan_aceptacion_imitador.md` (harness y veredicto),
> `docs/scorecard_aceptacion.md` (evidencia), `docs/plan_agente_xxxc_asistente.md` (asistente),
> `docs/investigacion_imitacion_traders_profesionales.md` (metodología).

---

## 1. Problema de negocio

El harness de aceptación demostró que el imitador es **operable por régimen** (Comercializador regulado /
Trader no regulado, 2015–2021) y **NO operable en el régimen de escasez reciente** (2023–2026: 0 de 108
ventanas pasan los gates; EV negativo en todas las combinaciones). El cliente, sin embargo, paga por **lo
actual y el futuro**, no por un análisis histórico.

Decisión acordada:
- **Criterio estricto "solo operar si gana":** si ninguna combinación supera los gates en la ventana vigente,
  el veredicto es **NO OPERAR** (prominente), con perfil defensivo solo informativo. No se relajan umbrales.
- **Entrega rodante semanal:** cada semana se re-entrena con los últimos 90 días y se valida contra la última
  semana **cerrada**; la recomendación se despliega la siguiente semana asumiendo continuidad del régimen.
- **Ancla por defecto al borde de datos:** `python -m sfeia.main` deja de apuntar a 2025 y pasa a resolver
  dinámicamente `foco_fin = fecha_max_sistema()` (2026-07-31 hoy). 2025 queda solo para análisis histórico vía
  `--estudio-ini/--impacto-fin` explícitos.
- **Dashboard HTML como canal de entrega:** el entregable principal de la recomendación semanal es un
  **dashboard HTML autocontenido** (CSS+JS inline, sin CDN ni build) con KPI, gráficas, tablas, tips,
  warnings y conclusiones. Las tablas solas no bastan para juzgar si la recomendación es correcta.

## 2. La verdad de diseño (caveat honesto)

No se puede validar contra datos que aún no existen. Lo máximo verificable es: **validar la selección y la
política contra la última semana con datos cerrados** y asumir continuidad del régimen para la semana siguiente.
El informe semanal lo declara explícitamente.

## 3. Criterio de la recomendación semanal

Dada la ventana vigente (estudio = últimos `dias_estudio` días, impacto = última semana con datos):

| Condición | Veredicto |
|---|---|
| ≥1 combinación confirmada pasa N1+N2 (topN o arquetipo) | **OPERAR** con el perfil recomendado (cobertura/exposición/SICEP) de la mejor combinación |
| Ninguna pasa | **NO OPERAR** prominente + régimen (spread, embalses, escasez) + perfil defensivo informativo |

Gates N1+N2 (los mismos del scorecard): bootstrap p≤0.05 · N efectivo ≥3 · holdout ≥50 % · réplica ≥0.5 ·
DSR ≥0.95 · E1 ≥60 % · EV histórico ≥0 · sin kill-switch · capacidad ≤5 %.

## 4. Cambios técnicos

### 4.1 Ancla dinámica (`main.py`, `config.yaml`)
- `ventana.foco_ini/fin` pasan a `null`.
- En `main.py`, tras crear el repo: si `foco_fin` es `null` → `foco_fin = repo.fecha_max_sistema()` y
  `foco_ini = foco_fin − 180 días`. Así `FaseAsistente._resolver_fechas` produce estudio = últimos 90 d e
  impacto = última semana dentro del rango de datos (validable).
- Afecta a `python -m sfeia.main` y `--semanal`; `--aceptacion` y `--walk-forward` ya usan el borde.

### 4.2 Modo `--semanal [--fecha …]`
- Ancla = `--fecha` (para pruebas) o el borde de datos.
- Corre el flujo completo topN (`FaseAsistente.ejecutar`) y el modo arquetipo como control.
- Arma el veredicto OPERAR/NO OPERAR y el reporte (dashboard).
- Salidas: `docs/recomendacion_semanal.html` (dashboard, **único entregable**) +
  `data/recomendacion_semanal.csv`.

### 4.3 Nuevos archivos
- `sfeia/app/controllers/fase_semanal.py` — armado del reporte; veredicto como lógica pura testeable.
- `sfeia/app/views/dashboard_semanal_html.py` — render del dashboard HTML autocontenido
  (CSS+JS inline, helpers SVG propios, sin dependencias externas).
- `exportar_csv.py` — `exportar_semanal` (CSV).
- `sfeia/tests/test_semanal.py` — veredicto OPERAR/NO OPERAR, resolución del ancla y render del
  dashboard (JSON embebido válido, escape de HTML, determinismo byte-a-byte).
- Config `asistente.semanal: {dias_estudio: 90, dias_impacto: 7, salida_html: docs/recomendacion_semanal.html}`.

### 4.4 Docs
- README y AGENTS: default = lo actual; `--semanal` = canal cliente; 2025 = histórico explícito.

## 5. Dashboard HTML — entregable principal

`docs/recomendacion_semanal.html`: **un solo archivo autocontenido** (HTML + CSS + JS inline, sin CDN,
sin build): se abre con doble clic y **sin internet**. Los datos viajan embebidos como JSON
(`window.SEMANAL = {...}`) y las gráficas se dibujan con SVG/JS propio (helpers `line/bar/donut/area`
mínimos). Es el **único entregable** de la recomendación semanal (junto al CSV de historial).

### 5.1 Estructura (top → down, lenguaje de negocio: cero jerga interna)
1. **Header**: segmento, estrategia y semana evaluada.
2. **Veredicto**: badge gigante **OPERAR / NO OPERAR** (semáforo) + «¿Por qué?» en una frase de negocio
   (sin nombres de gates: el cliente no lee DSR, bootstrap ni holdout).
3. **Cómo operar (perfil recomendado)**: barras de % de la demanda (contratos, bolsa, no regulados, SICEP),
   recomendado vs. lo que hicieron los agentes de referencia; nota si la recomendación es defensiva.
4. **La estrategia en números (última semana)**: 8 KPI cards con etiquetas de negocio (resultado medio,
   días que gana al mercado, confianza de que no es suerte, probabilidad de que sea suerte, agentes imitados,
   peor caída, ganancia esperada, embalses).
5. **Contexto del mercado**: brecha bolsa–contratos, situación de precios, embalses, escasez histórica y
   de la semana.
6. **Gráficas** (SVG): resultado diario vs. mercado · pérdida acumulada · brecha de precios con rango del
   modelo · embalses · distribución de resultados.
7. **¿En qué se basa esta recomendación?**: criterios en lenguaje de negocio (ventaja comprobada, base de
   agentes, consistencia, freno de seguridad, ganancia esperada, tamaño operable) con ✓/✗ y metas.
8. **Agentes de referencia (los que se imitan)**: tabla de empresas con resultado medio, ventaja sobre el
   mercado, % días con pérdida y peor caída.
9. **Si aun así quiere operar esta semana**: la opción menos mala observada (sin relajar la regla).
10. **Notas honestas**: cifras estimadas (no liquidaciones reales), retrospectiva, perfil defensivo.
11. **Qué hacer esta semana**: 3 conclusiones accionables en lenguaje de negocio.

### 5.2 Reglas de diseño
- **Self-contained**: sin CDN ni `fetch` externo; fuentes del sistema; colores de semáforo
  (verde/ámbar/rojo) consistentes con los gates.
- **Una sola fuente de verdad**: todo valor numérico sale del JSON embebido; no se recalcula en JS.
- **Escape HTML** de nombres/códigos de agentes (vienen de BD).
- **Print-friendly** (`@media print`) y responsive simple (grid CSS).
- **Determinista**: el HTML generado con los mismos datos es byte-a-byte idéntico (N0.2).

### 5.3 Implementación
- `views/dashboard_semanal_html.py`: función pura `render(resultado_semanal: dict) -> str`; serializa
  `resultado_semanal` a JSON embebido y arma el esqueleto HTML con los helpers JS/SVG.
- `fase_semanal.py`: arma `resultado_semanal` (veredicto + KPIs + series + tablas + tips/warnings +
  conclusiones) como lógica pura testeable, y llama al render.
- Sin dependencias nuevas: Python stdlib (`json`, `html`).

## 6. Qué diría hoy (con los datos actuales)

Anclado a 2026-07-31 → estudio ~2026-04-27..2026-07-24, validación ~2026-07-25..2026-07-31 →
**NO OPERAR** (régimen de escasez; las 108 ventanas 2025–2026 no validan). El dashboard mostraría el
veredicto NO OPERAR prominente, el régimen, las gráficas de margen/spread/embalses y el perfil defensivo
informativo; cambiaría a OPERAR automáticamente cuando el régimen sea imitable o llegue ground truth XM.

## 7. Verificación

- `./.venv/bin/python -m pytest -q` verde (incluye tests del render HTML: JSON embebido válido, escape de
  HTML, determinismo byte-a-byte).
- `./.venv/bin/python -m sfeia.main` → informe del estado actual (ancla dinámica), sin errores.
- `./.venv/bin/python -m sfeia.main --semanal` → `docs/recomendacion_semanal.html` + CSV.
- Apertura del dashboard sin internet (doble clic): todas las secciones visibles, gráficas dibujadas,
  semáforos correctos. Smoke test con Playwright sobre el archivo generado.
- Determinismo byte-a-byte (N0) y commit por fase.

## 8. Criterio de aceptación de este plan

- `python -m sfeia.main` (sin flags) corre sobre el borde de datos y produce el informe actual honesto.
- `--semanal` entrega el **dashboard HTML autocontenido** (KPI, gráficas, tablas, tips/warnings,
  conclusiones) que abre sin internet; si no valida, NO OPERAR prominente.
- El `.html` es el único entregable del cliente (el CSV queda para historial interno).
- 2025 sigue disponible explícitamente; `--aceptacion` y `--walk-forward` intactos.