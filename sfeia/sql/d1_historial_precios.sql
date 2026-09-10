-- D1 (auxiliar del asistente): histórico completo de precios de sistema.
-- Sirve para medir la frecuencia histórica de escasez (contexto donde la
-- política de clonación normalmente no tiene datos).
SELECT fecha,
       "PrecPromCont"   AS prec_cont,
       "PPPrecBolsNaci" AS prec_bolsa,
       "PrecEsca"       AS prec_escasez
FROM fact_daily_sistema
ORDER BY fecha;