-- F5: Agente enriquecido (C15) — base para KPIs de precio/margen y del
-- modelo financiero C16–C18 (computado en Python con la misma lógica).
-- Params: %(ini)s, %(fin)s (fin INCLUSIVO), %(agente)s
SELECT * FROM fn_estudio_agente_enriquecido(%(ini)s, %(fin)s, %(agente)s);