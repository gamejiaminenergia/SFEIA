# Análisis Regulatorio — Estrategias de Comercialización en el MEM

> Marco normativo CREG aplicable al plan `docs/plan_estrategias_comercializacion.md`, elaborado con consultas al Gestor Normativo de la CREG (asistente CREG AI) el **2026-09-09**.
> Proyecto: SFEIA · Fuente: skill `creg-ai-client` → API `localhost:3000`

---

## 1. Metodología

Se consultó el asistente normativo de la CREG con las **5 preguntas regulatorias (Q1–Q5)** definidas en el plan metodológico. Cada respuesta se contrasta con la dimensión estratégica (D1–D5) del plan y se traduce en una **implicación para la estrategia de comercialización**.

| # | Pregunta regulatoria | Dimensión | Longitud respuesta |
|---|----------------------|-----------|-------------------|
| Q1 | Mercado regulado vs no regulado (Res. 015/2018), umbrales y contratos de largo plazo | D2 | ~5.6 K |
| Q2 | Contratos bilaterales: tipos, registro ASIC, respaldo/cobertura, convocatorias | D1, D4 | ~5.7 K |
| Q3 | Costo Unitario (CU): componentes G, T, D, CV, PR, R, CF, CREE | D3 | ~6.6 K |
| Q4 | Opciones de compra: bolsa, contratos, cargo por confiabilidad/OEF, AGPE, TIE | D1 | ~6.2 K |
| Q5 | Garantías ante ASIC/XM: exposición neta, normas, consecuencias por mora | D4 | ~6.4 K |

> **Advertencia metodológica:** el asistente CREG genera respuestas fundamentadas con citas; antes de uso contractual o litigioso debe verificarse el texto oficial de cada resolución en el gestor normativo. Este documento es insumo de análisis estratégico, no asesoría legal.

---

## 2. Q1 — Mercado regulado vs no regulado (D2)

### Hallazgo
- **Mercado regulado:** compras sujetas a tarifas fijadas por la CREG (Ley 143/1994).
- **Mercado no regulado:** negociación **libre de precios** con comercializadores/generadores.
- **Umbral de usuario no regulado (Res. CREG 131/1998 mod. 183/2009):** demanda máxima > **0,1 MW** o consumo ≥ **55 MWh/mes** en un solo sitio, medidos en los últimos 6 meses; requiere **telemedida** horaria (Código de Medida) y manifestación expresa de voluntad.
- La Res. CREG 015/2018 es la **metodología de remuneración de la actividad de distribución** (no la norma del mercado regulado/no regulado); sus modificatorias (085/2018, 036/2019, 199/2019, 167/2020, 195/2020, 222/2021) fijan estructura tarifaria de distribución.
- Contratos de largo plazo para demanda regulada requieren **convocatoria pública** (Res. 079/2019 y 130/2019) con reglas de neutralidad y topes de contratación propia con integrados (→ máx **10 % de la demanda regulada en 2025**).
- Contratos FNCER ≥ 10 años deben registrarse ante el ASIC para cumplir obligación de compra de fuentes renovables.

### Implicación estratégica
El **segmento no regulado es la palanca de margen**: ahí se compite por precio/servicio sin fórmula tarifaria. El **regulado** es volumen cautivo pero con compras vía convocatoria pública, lo que define el costo de energía como precio de mercado descubierto. La capacidad de ganar y fidelizar clientes no regulados (>0,1 MW / 55 MWh-mes, con telemedida) determina la diferenciación estratégica (dimensión D2).

---

## 3. Q2 — Contratos bilaterales, respaldo y cobertura (D1, D4)

### Hallazgo
- **Tipos básicos:** *Pague lo Contratado* (CPLC: paga la cantidad contratada sin importar consumo) y *Pague lo Demandado* (paga la energía efectivamente demandada hasta el tope). Variables según necesidades.
- **Registro ASIC obligatorio** de todo contrato bilateral con reglas claras para determinar hora a hora cantidades y precios; formato del ASIC y código de convocatoria cuando aplique.
- **Respaldo/cobertura:** no registrar contratos cuando la energía vendida supere la capacidad de respaldo (variables **CROM1/CROM2**); garantías ante XM/contraparte; requisitos patrimoniales para vender a no regulados a precio fijo.
- **Convocatorias para demanda regulada (Res. 020/1996 y 130/2019):** procedimiento público, único criterio de adjudicación el **precio**, ofertas parciales, subasta de **sobre cerrado de primer precio**, registro del contrato resultante con código de convocatoria, y **límite decreciente a la contratación con integrados (máx 10 % en 2025)**.
- Contratos de convocatoria: precio fijo **COP/kWh** determinable ex ante, **no indexado a bolsa**, cantidad en función de la demanda del comercializador.
- **SICEP:** plataforma centralizada de publicidad/trazabilidad de convocatorias (transparencia y entrada de nuevos agentes).

### Implicación estratégica
La arquitectura de contratos define el costo y el riesgo: **CPLC da certeza de compra pero rigidez**; *Pague lo Demandado* alinea costo con demanda pero deja hueco de cobertura. Los topes de autocontratación con integrados (10 %) fuerzan a los grupos verticales a **comprar en mercado** una parte relevante de su demanda regulada — oportunidad para generadores/comercializadores independientes. Las convocatorias públicas (precio único, no indexado a bolsa) son el canal dominante para atender regulado y determinan el costo base del portafolio (D1).

---

## 4. Q3 — Costo Unitario y fórmula tarifaria (D3)

### Hallazgo (fórmula general Res. CREG 119/2007)
| Componente | Concepto |
|-----------|----------|
| **G** | Costo de compra de energía (contratos + bolsa) |
| **T** | Cargo por uso del STN |
| **D** | Cargo por uso del STR/SDL (según nivel de tensión) |
| **CV** | Margen de comercialización (facturación, lectura, atención; indexado a IPC) |
| **PR** | Costo de compra, transporte y reducción de **pérdidas** |
| **R** | Restricciones y servicios asociados a generación |
| **Cargo por confiabilidad** | Se traslada vía componente de restricciones (R), se activa en eventos críticos (El Niño) |
| **CREE/SSPD** | Contribución a CREG y SSPD (doceava parte anual), incluida en el componente de comercialización |

El CU = componente variable ($/kWh) + componente fijo ($/factura, hoy cero). Puede incluir subsidios (estratos 1–3) y contribuciones (5, 6, industria y comercio) por Ley 142/1994. La CREG define fórmula y metodología; **no aprueba el valor exacto** por comercializador.

### Implicación estratégica
Para el regulado, el comercializador es esencialmente un **passthrough regulado**: el costo de energía (G) se traslada y el ingreso propio está acotado al **margen CV** (regulado, indexado a IPC) — el margen no se "gana" en el CU sino en gestión de costos y pérdidas (PR) y en eficiencia operativa. Por eso la rentabilidad de atender regulado depende de: eficiencia en pérdidas, costos de compra G por debajo del costo reconocido y escala. La estrategia de **precio libre solo existe en el no regulado** (D3 ligado a D2).

---

## 5. Q4 — Opciones de compra de energía (D1)

### Hallazgo
| Opción | Característica regulatoria |
|--------|----------------------------|
| **Bolsa (spot)** | Mercado diario/horario; precio = última planta despachada (costo marginal); corto plazo, exposición a volatilidad |
| **Contratos bilaterales** | Libre pacto de condiciones; **cobertura de precio**, no requieren entrega física |
| **Cargo por confiabilidad / OEF** | Subastas de OEF; los generadores con OEF entregan energía cuando el precio de bolsa supera el **precio de escasez**; los comercializadores pagan el cargo vía tarifa, recaudado por el ASIC; tope al precio máximo pagado en escasez |
| **AGPE** | Obligación de recibir y remunerar excedentes de autogeneración a pequeña escala (precio de bolsa o créditos de energía según capacidad y fuente) |
| **TIE** | Transacciones internacionales, incl. contratos bilaterales financieros como cobertura de riesgo |

### Implicación estratégica
El **portafolio óptimo combina cobertura (contratos), precio (bolsa solo en la medida del apetito de riesgo) y mecanismos complementarios**: AGPE y TIE financiero diversifican sin exposición física. El **precio de escasez** actúa como "seguro catastrófico" del sistema que limita el alza máxima que un comercializador enfrenta en el spot en eventos críticos — clave para dimensionar la exposición máxima aceptable (D1 y D4).

---

## 6. Q5 — Garantías ante ASIC/XM (D4)

### Hallazgo
- **Obligación mínima de participación** (Res. CREG 024/1995 y Anexo C): garantías que respalden compras en bolsa, cargos CND/ASIC, uso del SIN, reconciliaciones, servicios complementarios y cualquier concepto liquidado por ASIC/LAC.
- **Monto:** función de la **exposición neta** (saldo de compras en bolsa); debe cubrir un estimado de liquidaciones por **mínimo 3 meses** siguientes al mes de operación (Res. 116/1998 y 019/2006).
- **Requisitos de los instrumentos:** cubrir todo el estimado, en moneda nacional, irrevocables e incondicionales a favor del ASIC, líquidos y de realización inmediata.
- **Mecanismos admitidos:** garantía bancaria, aval, carta de crédito Stand-By, cesión de derechos, prepagos mensuales/semanales, fiducia de garantía, pignoración de ingresos.
- **Otras normas:** Res. 070/1999 (pagos anticipados semanales), 144/2010 (garantizar todas las transacciones, límite al patrimonio técnico), CREG 101 029 de 2022 (garantías adicionales por diferimiento de pagos).
- **Consecuencias por incumplimiento/mora:** pagos anticipados forzosos → ejecución de garantías → oficio a la SSPD para investigación y sanciones → **retiro del mercado** (pérdida de asignaciones OEF y remuneración). El riesgo no cubierto se **redistribuye entre los demás agentes** proporcional a sus transacciones en bolsa.

### Implicación estratégica
La exposición a bolsa tiene **costo directo de capital de trabajo**: cada GWh descubierto exige garantía líquida por ~3 meses de liquidaciones. Estrategias agresivas (alta exposición spot) requieren fondeo/garantías proporcionalmente mayores y elevan el riesgo de iliquidez — como evidencian los comercializadores intervenidos (caso AIR-E/CSIC del plan). El análisis elecdb C16 (`fn_agente_garantias_exigidas`, 25 % de exposición neta + 2 % anual) es el puente entre esta norma y la métrica de riesgo del benchmark (D4).

---

## 7. Síntesis transversal: implicaciones regulatorias sobre la estrategia

1. **El margen se juega en el no regulado; el regulado es volumen con margen regulado (CV).** La estrategia debe decidir el *mix* D2 conociendo que solo el no regulado admite precio libre.
2. **La cobertura (contratos) es a la vez palanca de costo y de riesgo.** CPLC vs *Pague lo Demandado* y los topes del 10 % de autocontratación definen cuánta energía debe comprarse en convocatorias y cuánta exposición spot es inevitable.
3. **La exposición a bolsa es una decisión financiera, no solo comercial:** garantías por ~3 meses de liquidaciones (Q5) + riesgo de precio (Q4). Alto apetito spot exige músculo de garantías; bajo apetito = cobertura casi total (contratos) a costo de menor flexibilidad.
4. **El cargo por confiabilidad y el precio de escasez son el "techo" del riesgo sistémico:** permiten dimensionar la máxima pérdida teórica de un portafolio sin cobertura en eventos críticos (aporta a F2 del plan).
5. **Normas núcleo para el plan:** Ley 142 y 143/1994 · Res. 024/1995 (garantías/contratos) · Res. 131/1998 y 183/2009 (umbral no regulado) · Res. 116/1998, 019/2006, 070/1999, 144/2010, 101 029/2022 (garantías) · Res. 119/2007 (fórmula CU) · Res. 015/2018 y mod. (distribución) · Res. 020/1996, 079/2019, 130/2019 (convocatorias) · Res. 071/2006 (cargo por confiabilidad).

---

## 8. Mapa a la fase de datos (elecdb)

| Hallazgo regulatorio | Función elecdb del plan | KPI |
|----------------------|-------------------------|-----|
| Mix regulado/no regulado (Q1) | C01, C06, C07 | % demanda regulada vs no regulada, CIIU |
| Cobertura y exposición (Q2, Q4) | C04, C15 | % cobertura contratos; % exposición bolsa |
| Rol neto pico/valle y contratos (Q2) | C02, C03, C05 | compras/ventas bolsa y contratos; rol por bloque |
| Costo de energía y spread (Q3, Q4) | C10, C13, C15 | precio contratos vs bolsa; spread |
| Garantías y margen (Q5) | C16–C18 | garantía exigida, provisión cartera, margen neto COP/kWh |

---

## 9. Limitaciones
1. Las respuestas provienen del asistente del gestor normativo CREG; **verificar texto oficial** de cada resolución antes de decisiones jurídicas o contractuales.
2. Posibles variaciones de numeración/estado de normas tras actualizaciones regulatorias posteriores a la fecha de consulta.
3. El análisis conecta lo normativo con lo empírico (elecdb), pero la conducta de mercado (F0–F6 del plan) no se ejecuta en este documento.
