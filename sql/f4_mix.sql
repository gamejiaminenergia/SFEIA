-- F4: Mix de mercado objetivo — pérdidas por agente (C08) + contexto CIIU (C06).
-- Params: %(ini)s, %(fin)s
SELECT * FROM fn_estudio_c08_perdidas(%(ini)s, %(fin)s);

-- Contexto SIN: demanda no regulada por sector CIIU (no es por agente).
-- Nota: fn_estudio_c06_ciiu está rota en la BD (columna description inexistente)
-- y dim_ciiu no tiene nombres (ciiu_name NULL); se etiqueta con el código CIIU.
SELECT COALESCE(c.ciiu_name, c.ciiu_code) AS sector_ciiu,
       ROUND((SUM(hc."DemaComeNoReg") / 1e6)::numeric, 1) AS dema_noreg_gwh
FROM fact_hourly_ciiu hc
JOIN dim_ciiu c ON hc.ciiu_code = c.ciiu_code
WHERE hc.fecha_hora >= %(ini)s
  AND hc.fecha_hora <  %(fin)s
GROUP BY c.ciiu_name, c.ciiu_code
ORDER BY dema_noreg_gwh DESC
LIMIT 10;