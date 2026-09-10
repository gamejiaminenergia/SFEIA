-- Contexto hidrológico diario del SIN: nivel agregado de embalses.
-- Energía ponderada: sum(volumen útil) / sum(capacidad útil) por día, el mismo
-- indicador agregado que reporta XM. Fuente: v_embalses_diario (2015 al límite de datos).
SELECT fecha::date AS fecha,
       SUM(volumen_util_gwh) / NULLIF(SUM(capacidad_util_gwh), 0) * 100.0 AS nivel_agregado_pct
FROM v_embalses_diario
WHERE fecha::date >= %(ini)s AND fecha::date < %(fin)s
GROUP BY fecha::date
ORDER BY fecha::date;