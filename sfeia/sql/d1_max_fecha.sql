-- D1 (auxiliar del asistente imitador): última fecha con datos de precios de
-- sistema. Marca el límite para las ventanas de estudio e impacto.
SELECT max(fecha) AS max_fecha FROM fact_daily_sistema;