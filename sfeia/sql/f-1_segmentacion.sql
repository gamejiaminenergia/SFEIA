-- F-1: Población de comercializadores con demanda en la ventana (para segmentar).
-- Params: %(ini)s, %(fin)s (fin EXCLUSIVO)
SELECT a.agente_code,
       a.name,
       a.activity,
       SUM(ha."DemaCome")     / 1e6 AS dema_come_gwh,
       SUM(ha."DemaComeReg")  / 1e6 AS reg_gwh,
       SUM(ha."DemaComeNoReg")/ 1e6 AS noreg_gwh
FROM fact_hourly_agente ha
JOIN dim_agente a ON ha.agente_code = a.agente_code
WHERE ha.fecha_hora >= %(ini)s
  AND ha.fecha_hora <  %(fin)s
  AND a.activity = 'COMERCIALIZACIÓN'
GROUP BY a.agente_code, a.name, a.activity
HAVING SUM(ha."DemaCome") > 0
ORDER BY dema_come_gwh DESC;