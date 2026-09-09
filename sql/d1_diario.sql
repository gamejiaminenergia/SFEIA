-- D1: Estrategia diaria — agregación por agente y día + precios de sistema.
-- Una fila por (fecha, agente) para TODOS los comercializadores. Incluye las
-- ventas de bolsa/contratos (necesarias para la exposición neta del modelo
-- financiero diario) y los precios de sistema (contratos, bolsa, escasez).
-- Params: %(ini)s, %(fin)s (fin EXCLUSIVO, familia C01–C14)
SELECT date(ha.fecha_hora)          AS dia,
       ha.agente_code               AS agente,
       SUM(ha."DemaCome")           AS dema_kwh,
       SUM(ha."DemaComeReg")        AS dema_reg_kwh,
       SUM(ha."DemaComeNoReg")      AS dema_noreg_kwh,
       SUM(ha."CompContEner")       AS comp_cont_kwh,
       SUM(ha."CompContEnerReg")    AS comp_cont_reg_kwh,
       SUM(ha."VentContEner")       AS vent_cont_kwh,
       SUM(ha."CompBolsNaciEner")   AS comp_bolsa_kwh,
       SUM(ha."VentBolsNaciEner")   AS vent_bolsa_kwh,
       SUM(ha."CompContEnerSICEP")  AS comp_sicep_kwh,
       AVG(ds."PrecPromCont")       AS prec_cont_cop_kwh,
       AVG(ds."PPPrecBolsNaci")     AS prec_bolsa_cop_kwh,
       AVG(ds."PrecEsca")           AS prec_escasez_cop_kwh
FROM fact_hourly_agente ha
JOIN dim_agente a ON ha.agente_code = a.agente_code AND a.activity = 'COMERCIALIZACIÓN'
JOIN fact_daily_sistema ds ON ds.fecha = date(ha.fecha_hora)
WHERE ha.fecha_hora >= %(ini)s
  AND ha.fecha_hora <  %(fin)s
GROUP BY date(ha.fecha_hora), ha.agente_code
HAVING SUM(ha."DemaCome") > 0
ORDER BY dia, agente;