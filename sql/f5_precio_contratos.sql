-- F5: Spread de mercado contratos–bolsa (nivel SISTEMA, C10).
-- Nota: fn_estudio_c10_precio_contratos está rota en la BD (columnas
-- PrecPromContRegu/NoRegu inexistentes); se resuelve con consulta directa
-- sobre fact_daily_sistema (solo columnas existentes).
-- Params: %(ini)s, %(fin)s
SELECT to_char(ds.fecha, 'YYYY-MM') AS mes,
       ROUND(AVG(ds."PrecPromCont")::numeric, 2)   AS prec_contratos_prom_cop,
       ROUND(AVG(ds."PPPrecBolsNaci")::numeric, 2) AS prec_bolsa_prom_cop,
       ROUND((AVG(ds."PrecPromCont") - AVG(ds."PPPrecBolsNaci"))::numeric, 2) AS spread_contratos_vs_bolsa
FROM fact_daily_sistema ds
WHERE ds.fecha >= %(ini)s
  AND ds.fecha <  %(fin)s
  AND ds."PrecPromCont" IS NOT NULL
  AND ds."PPPrecBolsNaci" IS NOT NULL
GROUP BY to_char(ds.fecha, 'YYYY-MM')
ORDER BY mes;