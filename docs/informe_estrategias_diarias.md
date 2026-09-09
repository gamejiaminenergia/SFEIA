# Estrategias Diarias de Comercialización en el MEM — Ranking de Desempeño por Arquetipo (Ene–Jul 2026)

> Proyecto SFEIA · Ventana **2026-01-01 → 2026-07-31** · Población: **65 comercializadores** · **13555 agentes-día** en **212 días** · K-Means pooled (k=5, semilla=42).

> Estudio **híbrido**: reemplaza al benchmark por segmento y al k-means de H1-2026. Toma del no supervisado la agrupación en arquetipos (sin umbrales ni reglas manuales) y del benchmark el modelo financiero (margen estimado por kWh) como métrica de desempeño, todo a granularidad **diaria**. Archivo único de salida del proyecto.

## Resumen ejecutivo

Ranking final de estrategias del período (mediana del margen estimado diario por kWh, en COP):

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 3 | 212 | -19.2 | 108 | 65.6% | 2.5 |
| 2 | Integrado/regional regulado | 1 | 212 | -46.6 | 76 | 100.0% | 1.7 |
| 3 | Comercializador regulado | 2 | 212 | -68.7 | 1 | 89.6% | 2.8 |
| 4 | Trader con sobrecobertura de contratos | 4 | 210 | -125.0 | 27 | 34.3% | 3.6 |
| 5 | Trader no regulado | 0 | 212 | -158.0 | 0 | 10.8% | 4.3 |

La estrategia que mejor funcionó en el período fue **Trader expuesto a bolsa (sin cobertura)** (mediana de -19.19 COP/kWh/día, 108 días en el 1.er puesto). La de peor desempeño fue **Trader no regulado** (-157.97 COP/kWh/día). El margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo); sirve para comparar estrategias, no como margen real del negocio.

## 1. Metodología

**Población y granularidad.** Todos los comercializadores con demanda en la ventana (65) se observan **por día** (~212 días → ~13 800 agentes-día). Cada agente puede cambiar de estrategia de un día a otro; la agrupación sale de los datos, no de reglas a priori.

**Segmentación de la población (F-1).** Cada comercializador se clasifica en GRANDE/MEDIANO/PEQUEÑO por su **demanda comercial total (DemaCome) de la ventana**, con los umbrales de `config/config.yaml` (`segmentacion:`). Es una clasificación por **volumen**, no por número de clientes ni por estrategia; el segmento se usa como **variable de análisis** (no entra al k-means), para que los tamaños no compitan entre sí en el ranking.

| Segmento | Criterio (DemaCome GWh/semestre) | Agentes | Demanda (GWh) | % mercado | % regulado |
|---|---|---|---|---|---|
| GRANDE | ≥ 2 000 | 7 | 35 322.4 | 70.1 | 67.1 |
| MEDIANO | 100 – <2 000 | 28 | 14 255.6 | 28.3 | 76.0 |
| PEQUEÑO | < 100 | 30 | 802.9 | 1.6 | 37.1 |

#### 1.1 Comercializadores por segmento

| Segmento | Código | Comercializador | Demanda (GWh) | % Regulado | % No regulado |
|---|---|---|---|---|---|
| GRANDE | ENDC | ENEL COLOMBIA SA ESP | 8 620.5 | 75.0 | 25.0 |
| GRANDE | EPMC | EMPRESAS PUBLICAS DE MEDELLIN E.S.P. | 7 522.1 | 63.4 | 36.6 |
| GRANDE | CSIC | AIR- E S.A.S. E.S.P. - INTERVENIDO | 5 953.9 | 92.5 | 7.5 |
| GRANDE | CMMC | CARIBEMAR DE LA COSTA S.A.S. E.S.P. | 5 910.1 | 90.0 | 10.0 |
| GRANDE | EPSC | CELSIA COLOMBIA S.A. E.S.P. | 2 522.9 | 65.5 | 34.5 |
| GRANDE | GECC | GENERADORA Y COMERCIALIZADORA DE ENERGIA DEL CARIBE S.A. E.S.P. | 2 439.2 | 0.0 | 100.0 |
| GRANDE | ISGC | ISAGEN S.A. E.S.P. | 2 353.7 | 0.0 | 100.0 |
| MEDIANO | EMIC | EMPRESAS MUNICIPALES DE CALI E.I.C.E. E.S.P. | 1 928.4 | 77.4 | 22.6 |
| MEDIANO | ESSC | ELECTRIFICADORA DE SANTANDER S.A. E.S.P. | 1 467.5 | 100.0 | 0.0 |
| MEDIANO | CNSC | CENTRALES ELECTRICAS DEL NORTE DE SANTANDER S.A. E.S.P. | 1 051.5 | 100.0 | 0.0 |
| MEDIANO | GNCC | VATIA S.A. E.S.P. | 1 041.8 | 90.2 | 9.8 |
| MEDIANO | EMSC | ELECTRIFICADORA DEL META S.A. E.S.P. | 777.7 | 89.5 | 10.5 |
| MEDIANO | SOEC | SOUTH32 ENERGY S.A.S E.S.P | 743.6 | 0.0 | 100.0 |
| MEDIANO | CHCC | CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. BENEFICIO E INTERES COLECTIVO | 635.5 | 100.0 | 0.0 |
| MEDIANO | CDNC | CENTRALES ELECTRICAS DE NARIÑO S.A. E.S.P. | 634.8 | 75.1 | 24.9 |
| MEDIANO | HLAC | ELECTRIFICADORA DEL HUILA S.A. E.S.P. | 592.3 | 83.7 | 16.3 |
| MEDIANO | EBSC | EMPRESA DE ENERGIA DE BOYACA S.A. E.S.P. | 575.0 | 91.3 | 8.7 |
| MEDIANO | EEPC | EMPRESA DE ENERGIA DE PEREIRA S.A. E.S.P. | 539.8 | 73.7 | 26.3 |
| MEDIANO | CEOC | COMPAÑIA ENERGETICA DE OCCIDENTE S.A.S. ESP | 488.6 | 85.0 | 15.0 |
| MEDIANO | NEUC | NEU ENERGY S.A.S E.S.P | 422.2 | 47.3 | 52.7 |
| MEDIANO | ETTC | ENERTOTAL S.A. E.S.P. | 350.4 | 53.4 | 46.6 |
| MEDIANO | CASC | EMPRESA DE ENERGIA DE CASANARE S.A. ESP | 342.7 | 99.5 | 0.5 |
| MEDIANO | BIAC | BIA ENERGY S.A.S. E.S.P | 320.2 | 49.0 | 51.0 |
| MEDIANO | EDQC | EMPRESA DE ENERGIA DEL QUINDIO S.A. E.S.P. | 289.3 | 100.0 | 0.0 |
| MEDIANO | CHVC | AES COLOMBIA & CIA. S.C.A. E.S.P. | 271.9 | 0.0 | 100.0 |
| MEDIANO | RTQC | RUITOQUE S.A. E.S.P. | 221.6 | 32.8 | 67.2 |
| MEDIANO | TENC | TRANSACCIONES ENERGÉTICAS S.A.S. EMPRESA DE SERVICIOS PÚBLICOS E.S.P | 218.7 | 19.5 | 80.5 |
| MEDIANO | ENIC | EMPRESA DE ENERGÍA DE ARAUCA E.S.P. | 197.4 | 100.0 | 0.0 |
| MEDIANO | CQTC | ELECTRIFICADORA DEL CAQUETA S.A. E.S.P. | 187.8 | 100.0 | 0.0 |
| MEDIANO | DRUC | DRUMMOND POWER S.A.S. E.S.P. | 186.2 | 0.0 | 100.0 |
| MEDIANO | QIEC | QI ENERGY S.A.S. E.S.P. | 184.5 | 91.2 | 8.8 |
| MEDIANO | EDPC | EMPRESA DISTRIBUIDORA DEL PACIFICO S.A. E.S.P. | 170.5 | 100.0 | 0.0 |
| MEDIANO | CMXC | CEMEX ENERGY S.A.S E.S.P. | 163.9 | 0.0 | 100.0 |
| MEDIANO | CETC | COMPAÑIA DE ELECTRICIDAD DE TULUA S.A. E.S.P. | 131.2 | 86.6 | 13.4 |
| MEDIANO | EXEC | ENEL X COLOMBIA S.A.S ESP | 120.6 | 100.0 | 0.0 |
| PEQUEÑO | ITLC | ITALCOL ENERGIA S.A. E.S.P. | 94.2 | 0.0 | 100.0 |
| PEQUEÑO | ENBC | ENERBIT S.A.S. E.S.P. | 79.9 | 88.0 | 12.0 |
| PEQUEÑO | FERC | FUENTES DE ENERGIAS RENOVABLES S.A.S. E.S.P. | 71.2 | 0.0 | 100.0 |
| PEQUEÑO | EXIC | ENERXIA COLOMBIA SAS ESP | 63.4 | 0.0 | 100.0 |
| PEQUEÑO | EBPC | EMPRESA DE ENERGIA DEL BAJO PUTUMAYO S.A. E.S.P. | 55.1 | 100.0 | 0.0 |
| PEQUEÑO | TPLC | TERPEL ENERGÍA S.A.S. E.S.P. | 54.4 | 13.3 | 86.7 |
| PEQUEÑO | EGVC | EMPRESA DE ENERGIA ELECTRICA DEL DEPARTAMENTO DEL GUAVIARE S.A. E.S.P. | 54.4 | 100.0 | 0.0 |
| PEQUEÑO | EPTC | EMPRESA DE ENERGIA DEL PUTUMAYO S.A. E.S.P. | 49.8 | 98.3 | 1.7 |
| PEQUEÑO | FREC | FRANCA ENERGIA SA ESP | 47.8 | 0.0 | 100.0 |
| PEQUEÑO | GAPC | GAP ENERGY GROUP SAS ESP | 40.7 | 0.0 | 100.0 |
| PEQUEÑO | CBNC | COLOMBINA ENERGIA SAS ESP | 35.7 | 0.0 | 100.0 |
| PEQUEÑO | LESC | MESSER ENERGY SERVICES SAS ESP | 23.2 | 0.0 | 100.0 |
| PEQUEÑO | VESC | VOLTAJE EMPRESARIAL S.A.S. E.S.P. | 19.7 | 0.0 | 100.0 |
| PEQUEÑO | ASCC | A.S.C. INGENIERIA S.A. E.S.P. | 17.7 | 69.9 | 30.1 |
| PEQUEÑO | BEIC | BEAM ENERGY INNOVATION S.A.S. E.S.P. | 15.0 | 11.8 | 88.2 |
| PEQUEÑO | EMEC | EMPRESA MUNICIPAL DE ENERGIA ELECTRICA S.A. E.S.P. | 14.4 | 40.1 | 59.9 |
| PEQUEÑO | GNYC | GREENYELLOW COMERCIALIZADORA S.A.S. E.S.P. | 14.2 | 0.0 | 100.0 |
| PEQUEÑO | EMPC | EMPRESA MUNICIPAL DE SERVICIOS PUBLICOS DE CARTAGENA DEL CHAIRA | 10.0 | 100.0 | 0.0 |
| PEQUEÑO | SCEC | SOL & CIELO ENERGIA S.A.S. E.S.P | 8.6 | 71.7 | 28.3 |
| PEQUEÑO | EVSC | EMPRESA DE ENERGIA DEL VALLE DE SIBUNDOY S.A. E.S.P. | 8.4 | 100.0 | 0.0 |
| PEQUEÑO | HIMC | GESTION ENERGETICA S.A. E.S.P. | 6.8 | 100.0 | 0.0 |
| PEQUEÑO | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 5.9 | 0.0 | 100.0 |
| PEQUEÑO | ESOC | EMPRESA DE SERVICIOS PÚBLICOS DEL OCCIDENTE COLOMBIANO | 3.3 | 100.0 | 0.0 |
| PEQUEÑO | DLRC | DICELER S.A. E.S.P. | 2.8 | 100.0 | 0.0 |
| PEQUEÑO | ESVC | EMPRESA SIGLO XXI EICE ESP | 2.7 | 100.0 | 0.0 |
| PEQUEÑO | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 1.8 | 100.0 | 0.0 |
| PEQUEÑO | PEEC | PROFESIONALES EN ENERGIA S.A. E.S.P. | 1.1 | 0.0 | 100.0 |
| PEQUEÑO | BCCC | BCCY CORDOBA S.A.S. E.S.P. | 0.3 | 0.0 | 100.0 |
| PEQUEÑO | TRPC | TERMOPIEDRAS S.A. E.S.P. | 0.2 | 0.0 | 100.0 |
| PEQUEÑO | GSAC | GENERSA S.A.S. E.S.P. | 0.2 | 0.0 | 100.0 |


**Features diarias** (mismas 6 del estudio k-means, calculadas por agente y día; cobertura/exposición entran log1p a la matriz, cobertura clip 300 %):

| Feature | Descripción |
|---|---|
| log_dema | Tamaño (log1p demanda diaria, GWh) |
| pct_noreg | Mercado objetivo (D2): % demanda no regulada del día |
| pct_cobertura | Abastecimiento (D1): % cobertura con contratos (log1p, clip 300 %) |
| pct_exposicion | Riesgo spot (D4): % exposición a bolsa (log1p) |
| pct_sicep | Convocatoria (D2): % compras reguladas con registro SICEP |
| tiene_sicep | 1 si compra regulado, 0 si puro no regulado |

**Clustering.** K-Means (scikit-learn) sobre la matriz pooled escalada con **standard**; elección de k por **silhouette** en k∈[2,10] sobre una submuestra determinista de 5000 filas (silhouette es O(n²)); el k elegido se aplica a toda la matriz. `random_state=42`, `n_init=10`. Los nombres de arquetipo son etiquetas interpretativas post-hoc sobre los centroides.

**Desempeño diario.** Por agente y día se estima el **margen por kWh** con la lógica del modelo financiero (C16–C18) sobre los agregados diarios de C15: compras/ventas valoradas con el precio promedio **de sistema** del día (contratos `PrecPromCont` y bolsa `PPPrecBolsNaci`). No existe precio ni margen real por agente en elecdb: el margen diferencia a los agentes por su **mix diario** contratos/bolsa y reg/no-reg. Cada día se agrupa a los agentes por estrategia y se ordenan las estrategias por la **mediana** de su margen diario (empates por media).

**Guardas de robustez (config `diario:`).** (a) El margen se **winsoriza** a ±500 COP/kWh: los traders con volumen transado muy superior a su demanda producen márgenes por kWh desproporcionados (artefacto del denominador). (b) Las estrategias presentes en menos del **20 %** de los días se reportan como **casos atípicos** y se excluyen del ranking (no son representativas del período). (c) `pct_sicep` se techa en 100 % (SICEP puede incluir compras no reguladas).

**Ranking y balance.** Se construye el ranking de estrategias para cada uno de los 212 días y se consolida: mediana/media del margen diario, días en 1.er puesto, % de días top-3, rango promedio y tendencia (diferencia 2.ª mitad − 1.ª mitad del período).

> **Matiz de transparencia:** features, escalado, k y la métrica de desempeño siguen siendo decisiones del analista (todo reproducible desde `config/config.yaml`). El k-means describe comportamiento **pasado**; no es causal ni predictivo.

## 2. Elección de k

| k | Silhouette medio | Inercia |
|---|---|---|
| 2 | 0.4 | 19 520.4 |
| 3 | 0.4 | 14 803.9 |
| 4 | 0.4 | 12 152.9 |
| 5 | 0.4 | 10 419.4 |
| 6 | 0.3 | 9 314.0 |
| 7 | 0.4 | 8 417.5 |
| 8 | 0.4 | 7 424.8 |
| 9 | 0.4 | 6 768.5 |
| 10 | 0.4 | 6 108.9 |

Se selecciona **k=5** (máximo silhouette medio sobre la submuestra; los demás k se reportan para sensibilidad).

## 3. Arquetipos diarios

Cada estrategia (arquetipo) es un grupo de agentes que el día a día se comporta igual en su abastecimiento (contratos vs bolsa), su mercado objetivo (regulado vs no regulado) y su exposición al precio spot. A continuación, qué significa cada una en lenguaje de negocio:

| Estrategia | Qué hace | Cuándo le va mejor | Riesgo principal |
|---|---|---|---|
| **Trader no regulado** (E0) | Intermediario del mercado no regulado (industria y comercio): compra y vende energía en contratos y bolsa en volúmenes muy superiores a su propia demanda (rol de trading). Sin base regulada. | Le va bien cuando la bolsa es barata (spread contratos–bolsa favorable) y puede revender con margen. | Exposición al spot y necesidad de garantías por el alto volumen transado frente a su demanda. |
| **Integrado/regional regulado** (E1) | Grandes grupos con red de distribución (ENDC, EPMC, CELSIA…): base regulada servida por convocatoria pública, cobertura de contratos amplia y exposición a bolsa muy baja. Llevan años de mercado y fuertes garantías. | El más estable: rinde bien casi todos los días y domina cuando la bolsa está cara (tiene contratos que valen menos que el spot). | Poco margen por kWh (modelo regulado); su resultado depende del enorme volumen y de renovar su cartera por convocatoria. |
| **Comercializador regulado** (E2) | Base de clientes regulados (residencial y pequeños negocios) atendidos con tarifa CREG. Compra la mayor parte de su energía con contratos, preferiblemente vía convocatoria pública (SICEP alto) y suele cubrir más de lo que demanda. | Le va bien cuando el precio de bolsa sube: sus contratos lo protegen y no paga el sobrecosto del spot. | Margen regulado fijo (CV) con poco margen de maniobra; gana por volumen, no por spread. |
| **Trader expuesto a bolsa (sin cobertura)** (E3) | Compra casi toda su energía en la bolsa, sin contratos de cobertura; mezcla clientes regulados y no regulados y es de menor tamaño. Acepta el precio spot a cambio de no pagar la prima de los contratos. | El que mejor rinde cuando la bolsa está barata (Ene–Jun): compra al costo spot y no asume sobrecosto de contratos. | Máxima exposición: en días de escasez (Jul) el precio de bolsa se dispara y es el que más pierde. |
| **Trader con sobrecobertura de contratos** (E4) | Comercializador no regulado que compra contratos muy por encima de su demanda y revende el excedente; casi no usa bolsa. Actúa como arbitrajista de contratos. | Domina los días de escasez (bolsa cara): su energía comprada por contrato a precio fijo se vuelve muy valiosa frente al spot. | Descalce de cobertura y garantías por volumen; si el contrato se vuelve más caro que la bolsa, pierde. |

### E0 — Trader no regulado (2104 agentes-día, 24 agentes únicos)

Composición por segmento F-1: GRANDE: 174; MEDIANO: 315; PEQUEÑO: 1615.

| Feature | Media diaria |
|---|---|
| log_dema | 0.42 |
| pct_noreg | 97 |
| pct_cobertura | 7 110 |
| pct_exposicion | 335 |
| pct_sicep | 0 |
| tiene_sicep | 0 |

Agentes representativos: **GECC, GNCC, NEUC, CHVC, BIAC**.

### E1 — Integrado/regional regulado (1758 agentes-día, 9 agentes únicos)

Composición por segmento F-1: GRANDE: 1038; MEDIANO: 720.

| Feature | Media diaria |
|---|---|
| log_dema | 2.80 |
| pct_noreg | 17 |
| pct_cobertura | 88 |
| pct_exposicion | 14 |
| pct_sicep | 82 |
| tiene_sicep | 1 |

Agentes representativos: **ENDC, EPMC, CSIC, CMMC, EPSC**.

### E2 — Comercializador regulado (6324 agentes-día, 37 agentes únicos)

Composición por segmento F-1: MEDIANO: 3970; PEQUEÑO: 2354.

| Feature | Media diaria |
|---|---|
| log_dema | 0.67 |
| pct_noreg | 20 |
| pct_cobertura | 163 |
| pct_exposicion | 20 |
| pct_sicep | 86 |
| tiene_sicep | 1 |

Agentes representativos: **GNCC, CNSC, EMSC, HLAC, CDNC**.

### E3 — Trader expuesto a bolsa (sin cobertura) (1316 agentes-día, 47 agentes únicos)

Composición por segmento F-1: GRANDE: 26; MEDIANO: 177; PEQUEÑO: 1113.

| Feature | Media diaria |
|---|---|
| log_dema | 0.21 |
| pct_noreg | 42 |
| pct_cobertura | 1 |
| pct_exposicion | 140 |
| pct_sicep | 0 |
| tiene_sicep | 0 |

Agentes representativos: **CSIC, EPSC, GECC, EMIC, ENDC**.

### E4 — Trader con sobrecobertura de contratos (2053 agentes-día, 21 agentes únicos)

Composición por segmento F-1: GRANDE: 245; MEDIANO: 728; PEQUEÑO: 1080.

| Feature | Media diaria |
|---|---|
| log_dema | 0.71 |
| pct_noreg | 84 |
| pct_cobertura | 2 336 |
| pct_exposicion | 1 |
| pct_sicep | 0 |
| tiene_sicep | 0 |

Agentes representativos: **ISGC, GECC, SOEC, ETTC, NEUC**.

## 4. Ranking diario

Número de días que cada estrategia ocupó cada puesto (1.º = mejor margen del día):

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader no regulado | 0 | 0 | 23 | 99 | 90 | 212 |
| Integrado/regional regulado | 76 | 129 | 7 | 0 | 0 | 212 |
| Comercializador regulado | 1 | 63 | 126 | 16 | 6 | 212 |
| Trader expuesto a bolsa (sin cobertura) | 108 | 10 | 21 | 20 | 53 | 212 |
| Trader con sobrecobertura de contratos | 27 | 10 | 35 | 77 | 61 | 210 |

### 4.1 Matriz de puestos por segmento

La misma distribución pero **por segmento** (GRANDE/MEDIANO/PEQUEÑO): cada segmento compite dentro de sí mismo, no contra los demás.

**GRANDE** — 7 agentes · 3 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader no regulado | 113 | 50 | 11 | 0 | 0 | 174 |
| Integrado/regional regulado | 63 | 142 | 7 | 0 | 0 | 212 |
| Trader expuesto a bolsa (sin cobertura) | 1 | 8 | 0 | 0 | 0 | 9 |
| Trader con sobrecobertura de contratos | 35 | 12 | 163 | 0 | 0 | 210 |

**MEDIANO** — 28 agentes · 4 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader no regulado | 14 | 31 | 34 | 125 | 4 | 208 |
| Integrado/regional regulado | 110 | 79 | 14 | 0 | 0 | 203 |
| Comercializador regulado | 0 | 80 | 97 | 35 | 0 | 212 |
| Trader expuesto a bolsa (sin cobertura) | 9 | 3 | 0 | 1 | 0 | 13 |
| Trader con sobrecobertura de contratos | 79 | 19 | 67 | 41 | 0 | 206 |

**PEQUEÑO** — 30 agentes · 4 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader no regulado | 2 | 49 | 100 | 59 | 0 | 210 |
| Comercializador regulado | 73 | 108 | 24 | 5 | 0 | 210 |
| Trader expuesto a bolsa (sin cobertura) | 133 | 39 | 17 | 23 | 0 | 212 |
| Trader con sobrecobertura de contratos | 4 | 14 | 69 | 122 | 0 | 209 |

### 4.2 Días destacados (bolsa cara)

Días con mayor precio de bolsa (señal de escasez; el spread bolsa−contrato define quién gana):

| Fecha | Bolsa (COP/kWh) | Contratos (COP/kWh) | Spread | Estrategia ganadora |
|---|---|---|---|---|
| 2026-07-30 | 977.3 | 335.8 | 641.5 | Trader con sobrecobertura de contratos |
| 2026-07-31 | 975.5 | 336.0 | 639.5 | Trader con sobrecobertura de contratos |
| 2026-07-23 | 971.2 | 337.4 | 633.8 | Trader con sobrecobertura de contratos |
| 2026-07-22 | 957.2 | 332.5 | 624.7 | Trader con sobrecobertura de contratos |
| 2026-07-15 | 892.2 | 331.8 | 560.4 | Trader con sobrecobertura de contratos |
| 2026-07-14 | 870.3 | 330.5 | 539.8 | Trader con sobrecobertura de contratos |
| 2026-07-17 | 865.3 | 331.8 | 533.5 | Trader con sobrecobertura de contratos |
| 2026-07-24 | 859.6 | 333.5 | 526.1 | Integrado/regional regulado |

Días de escasez (bolsa > precio de escasez): **19** de 212 días. En esos días la estrategia ganadora fue, por frecuencia:

| Estrategia | Días ganados |
|---|---|
| Trader con sobrecobertura de contratos | 13 |
| Integrado/regional regulado | 6 |

## 5. Ranking y balance por segmento

El ranking pooled mezcla segmentos de tamaños muy distintos. Aquí cada segmento se analiza **por separado** (los GRANDE no compiten contra los PEQUEÑO), para ver qué estrategia funciona mejor dentro de cada uno — especialmente en MEDIANO y PEQUEÑO, donde la estructura es menos homogénea que en GRANDE.

### 5.1 — GRANDE

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader no regulado | 0 | 174 | -37.1 | 113 | 100.0% | 1.4 |
| 2 | Integrado/regional regulado | 1 | 212 | -47.3 | 63 | 100.0% | 1.7 |
| 3 | Trader con sobrecobertura de contratos | 4 | 210 | -133.9 | 35 | 100.0% | 2.6 |

La mejor estrategia del segmento **GRANDE** fue **Trader no regulado** (mediana -37.06 COP/kWh/día, 113 días en 1.º).
 Casos atípicos del segmento: Trader expuesto a bolsa (sin cobertura) (E3, 9 días).

### 5.2 — MEDIANO

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Integrado/regional regulado | 1 | 203 | -46.7 | 110 | 100.0% | 1.5 |
| 2 | Comercializador regulado | 2 | 212 | -57.0 | 0 | 83.5% | 2.8 |
| 3 | Trader con sobrecobertura de contratos | 4 | 206 | -60.8 | 79 | 80.1% | 2.3 |
| 4 | Trader no regulado | 0 | 208 | -83.5 | 14 | 38.0% | 3.4 |

La mejor estrategia del segmento **MEDIANO** fue **Integrado/regional regulado** (mediana -46.66 COP/kWh/día, 110 días en 1.º).
 Casos atípicos del segmento: Trader expuesto a bolsa (sin cobertura) (E3, 13 días).

### 5.3 — PEQUEÑO

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 3 | 212 | -19.2 | 133 | 89.2% | 1.7 |
| 2 | Comercializador regulado | 2 | 210 | -134.9 | 73 | 97.6% | 1.8 |
| 3 | Trader no regulado | 0 | 210 | -345.1 | 2 | 71.9% | 3.0 |
| 4 | Trader con sobrecobertura de contratos | 4 | 209 | -497.2 | 4 | 41.6% | 3.5 |

La mejor estrategia del segmento **PEQUEÑO** fue **Trader expuesto a bolsa (sin cobertura)** (mediana -19.19 COP/kWh/día, 133 días en 1.º).

### 5.4 Matriz estrategia × segmento (mediana del margen, COP/kWh)

Cada celda es la mediana del **margen diario** de esa estrategia dentro de ese segmento (días = días presentes), la misma métrica del ranking por segmento. En **negrita**, la mejor estrategia de cada columna (segmento); las estrategias atípicas del segmento se marcan y no se cuentan:

| Estrategia | GRANDE | MEDIANO | PEQUEÑO |
|---|---|---|---|
| **Trader no regulado** | **-37.1 (174 días)** | -83.5 (208 días) | -345.1 (210 días) |
| **Integrado/regional regulado** | -47.3 (212 días) | **-46.7 (203 días)** | — |
| **Comercializador regulado** | — | -57.0 (212 días) | -134.9 (210 días) |
| **Trader expuesto a bolsa (sin cobertura)** | 227.5 (9 días) (atípico) | 113.2 (13 días) (atípico) | **-19.2 (212 días)** |
| **Trader con sobrecobertura de contratos** | -133.9 (210 días) | -60.8 (206 días) | -497.2 (209 días) |

> **Cómo leerlo:** el ranking pooled (sección 6) lo encabezan estrategias que funcionan bien combinando todos los tamaños. Para el análisis de negocio importa la **columna de cada segmento**: en GRANDE suele dominar la cobertura de contratos (integrados con red, años de mercado y garantías), mientras que en MEDIANO y PEQUEÑO compiten traders y regulados con estructuras distintas. Si un segmento tiene **0 días** en una estrategia, esa estrategia no aparece en su balance.

## 6. Balance del período

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Media margen | Días 1.º | % top-3 | Rango prom. | Tendencia 2.ª−1.ª mitad |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 3 | 212 | -19.2 | -105.4 | 108 | 65.6% | 2.5 | -284.2 |
| 2 | Integrado/regional regulado | 1 | 212 | -46.6 | -50.7 | 76 | 100.0% | 1.7 | -43.7 |
| 3 | Comercializador regulado | 2 | 212 | -68.7 | -96.3 | 1 | 89.6% | 2.8 | -78.5 |
| 4 | Trader con sobrecobertura de contratos | 4 | 210 | -125.0 | -124.3 | 27 | 34.3% | 3.6 | -20.0 |
| 5 | Trader no regulado | 0 | 212 | -158.0 | -203.7 | 0 | 10.8% | 4.3 | -109.4 |

La estrategia **Trader expuesto a bolsa (sin cobertura)** dominó el período: mediana de -19.19 COP/kWh/día, 108 días en el 1.er puesto (65.6 % de días top-3), rango promedio 2.53. Perfil: 1316 agentes-día de 47 agentes; no regulado 42 %, cobertura 1 %, exposición 140 %. Su tendencia fue **negativa** (empeoró en la 2.ª mitad del período). En segundo lugar, **Integrado/regional regulado** (-46.65 COP/kWh/día, 76 días en 1.º). El resultado es un artefacto del modelo (Pv=350 fijo) y sirve para comparar estrategias, no como margen real del negocio.

## 7. Limitaciones

1. **No hay precio ni margen real por agente** en elecdb: todo valor COP es volumen × precio promedio de sistema del día; el margen es un artefacto de modelado (Pv=350 COP/kWh fijo).
2. **K-Means es descriptivo**: asume esfericidad/varianza similar; k, features y escalado son decisiones del analista; resultados dependen de la ventana.
3. **Agentes diminutos** (volúmenes < 0,01 GWh/día) producen features ruidosas y márgenes extremos; se mitigan con log1p y clip, pero distorsionan las medianas de su estrategia.
4. **SICEP diario** es 0 imputado en puros no regulados (no compran regulado); `tiene_sicep` distingue '0 % convocatoria' de 'no aplica'.
5. **Sin precios de contrato por agente**: el margen solo capta el mix y el nivel de precio de sistema; no hay señal de negociación individual ni de contraparte.
6. Resultados describen **comportamiento pasado** (Ene–Jul 2026), no predicción.
