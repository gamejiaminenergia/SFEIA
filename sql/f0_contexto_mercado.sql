-- F0: Contexto de mercado — informe mensual de sistema.
-- Params: %(ini)s, %(fin)s
SELECT * FROM fn_estudio_c13_informe_mercado(%(ini)s, %(fin)s);