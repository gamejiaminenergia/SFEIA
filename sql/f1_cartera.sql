-- F1: Perfil de cartera por agente (demanda, bolsa, contratos, SICEP).
-- Params: %(ini)s, %(fin)s (fin EXCLUSIVO para C01–C03)
SELECT * FROM fn_estudio_c01_demanda_comercial(%(ini)s, %(fin)s);

SELECT * FROM fn_estudio_c02_compras_ventas_bolsa(%(ini)s, %(fin)s);

SELECT * FROM fn_estudio_c03_contratos(%(ini)s, %(fin)s);

-- Compras de contratos reguladas con registro SICEP (proxy de convocatoria).
SELECT a.name AS agente,
       SUM(ha."CompContEnerReg")   / 1e6 AS cont_reg_gwh,
       SUM(ha."CompContEnerSICEP") / 1e6 AS cont_sicep_gwh
FROM fact_hourly_agente ha
JOIN dim_agente a ON ha.agente_code = a.agente_code
WHERE ha.fecha_hora >= %(ini)s
  AND ha.fecha_hora <  %(fin)s
  AND a.activity = 'COMERCIALIZACIÓN'
GROUP BY a.name;