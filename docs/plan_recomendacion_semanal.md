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
- Arma el veredicto OPERAR/NO OPERAR y el reporte compacto.
- Salidas: `docs/recomendacion_semanal.md` + `data/recomendacion_semanal.csv`.

### 4.3 Nuevos archivos
- `sfeia/app/controllers/fase_semanal.py` — armado del reporte; veredicto como lógica pura testeable.
- `sfeia/app/views/informe_semanal_md.py` — render del Markdown compacto.
- `exportar_csv.py` — `exportar_semanal` (CSV).
- `sfeia/tests/test_semanal.py` — veredicto OPERAR/NO OPERAR y resolución del ancla.
- Config `asistente.semanal: {dias_estudio: 90, dias_impacto: 7, salida: docs/recomendacion_semanal.md}`.

### 4.4 Docs
- README y AGENTS: default = lo actual; `--semanal` = canal cliente; 2025 = histórico explícito.

## 5. Qué diría hoy (con los datos actuales)

Anclado a 2026-07-31 → estudio ~2026-04-27..2026-07-24, validación ~2026-07-25..2026-07-31 →
**NO OPERAR** (régimen de escasez; las 108 ventanas 2025–2026 no validan). El informe mostraría el régimen y
el perfil defensivo; cambiaría a OPERAR automáticamente cuando el régimen sea imitable o llegue ground truth XM.

## 6. Verificación

- `./.venv/bin/python -m pytest -q` verde.
- `./.venv/bin/python -m sfeia.main` → informe del estado actual (ancla dinámica), sin errores.
- `./.venv/bin/python -m sfeia.main --semanal` → `docs/recomendacion_semanal.md` con veredicto coherente.
- Determinismo byte-a-byte (N0) y commit por fase.

## 7. Criterio de aceptación de este plan

- `python -m sfeia.main` (sin flags) corre sobre el borde de datos y produce el informe actual honesto.
- `--semanal` entrega veredicto + perfil + régimen; si no valida, NO OPERAR prominente.
- 2025 sigue disponible explícitamente; `--aceptacion` y `--walk-forward` intactos.