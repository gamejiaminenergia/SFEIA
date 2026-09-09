# Estrategias Diarias de Comercialización en el MEM — Ranking de Desempeño por Arquetipo (Ene–Jul 2025)

> Proyecto SFEIA · Ventana **2025-01-01 → 2025-07-31** · Población: **65 comercializadores** · **13374 agentes-día** en **212 días** · K-Means pooled (k=5, semilla=42).

> Estudio **híbrido**: reemplaza al benchmark por segmento y al k-means de H1-2026. Toma del no supervisado la agrupación en arquetipos (sin umbrales ni reglas manuales) y del benchmark el modelo financiero (margen estimado por kWh) como métrica de desempeño, todo a granularidad **diaria**. Archivo único de salida del proyecto.

## Resumen ejecutivo

Ranking final de estrategias del período (mediana del margen estimado diario por kWh, en COP):

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 0 | 212 | 64.7 | 168 | 82.5% | 1.7 |
| 2 | Comercializador regulado | 3 | 212 | -12.5 | 36 | 99.5% | 1.8 |
| 3 | Integrado/regional regulado | 2 | 212 | -50.0 | 1 | 90.1% | 3.0 |
| 4 | Trader no regulado | 1 | 212 | -86.4 | 2 | 17.0% | 4.0 |
| 5 | Trader con sobrecobertura de contratos | 4 | 212 | -245.3 | 5 | 10.8% | 4.6 |

La estrategia que mejor funcionó en el período fue **Trader expuesto a bolsa (sin cobertura)** (mediana de 64.65 COP/kWh/día, 168 días en el 1.er puesto). La de peor desempeño fue **Trader con sobrecobertura de contratos** (-245.26 COP/kWh/día). El margen es un **artefacto de modelado** (Pv=350 COP/kWh fijo); sirve para comparar estrategias, no como margen real del negocio.

## 1. Metodología

**Población y granularidad.** Todos los comercializadores con demanda en la ventana (65) se observan **por día** (~212 días → ~13 800 agentes-día). Cada agente puede cambiar de estrategia de un día a otro; la agrupación sale de los datos, no de reglas a priori.

**Segmentación de la población (F-1).** Cada comercializador se clasifica en GRANDE/MEDIANO/PEQUEÑO por su **demanda comercial total (DemaCome) de la ventana**, con los umbrales de `config/config.yaml` (`segmentacion:`). Es una clasificación por **volumen**, no por número de clientes ni por estrategia; el segmento se usa como **variable de análisis** (no entra al k-means), para que los tamaños no compitan entre sí en el ranking.

| Segmento | Criterio (DemaCome GWh/semestre) | Agentes | Demanda (GWh) | % mercado | % regulado |
|---|---|---|---|---|---|
| GRANDE | ≥ 2 000 | 7 | 34 165.0 | 71.1 | 66.0 |
| MEDIANO | 100 – <2 000 | 27 | 13 120.2 | 27.3 | 78.2 |
| PEQUEÑO | < 100 | 31 | 740.6 | 1.5 | 40.6 |

#### 1.1 Comercializadores por segmento

| Segmento | Código | Comercializador | Demanda (GWh) | % Regulado | % No regulado |
|---|---|---|---|---|---|
| GRANDE | ENDC | ENEL COLOMBIA SA ESP | 8 927.2 | 70.4 | 29.6 |
| GRANDE | EPMC | EMPRESAS PUBLICAS DE MEDELLIN E.S.P. | 7 217.0 | 63.3 | 36.7 |
| GRANDE | CSIC | AIR- E S.A.S. E.S.P. - INTERVENIDO | 5 626.8 | 90.8 | 9.2 |
| GRANDE | CMMC | CARIBEMAR DE LA COSTA S.A.S. E.S.P. | 5 533.7 | 90.7 | 9.3 |
| GRANDE | EPSC | CELSIA COLOMBIA S.A. E.S.P. | 2 388.8 | 65.9 | 34.1 |
| GRANDE | ISGC | ISAGEN S.A. E.S.P. | 2 245.2 | 0.0 | 100.0 |
| GRANDE | GECC | GENERADORA Y COMERCIALIZADORA DE ENERGIA DEL CARIBE S.A. E.S.P. | 2 226.3 | 0.0 | 100.0 |
| MEDIANO | EMIC | EMPRESAS MUNICIPALES DE CALI E.I.C.E. E.S.P. | 1 871.7 | 76.3 | 23.7 |
| MEDIANO | ESSC | ELECTRIFICADORA DE SANTANDER S.A. E.S.P. | 1 427.7 | 100.0 | 0.0 |
| MEDIANO | CNSC | CENTRALES ELECTRICAS DEL NORTE DE SANTANDER S.A. E.S.P. | 1 018.2 | 100.0 | 0.0 |
| MEDIANO | GNCC | VATIA S.A. E.S.P. | 956.7 | 90.0 | 10.0 |
| MEDIANO | SOEC | SOUTH32 ENERGY S.A.S E.S.P | 750.2 | 0.0 | 100.0 |
| MEDIANO | EMSC | ELECTRIFICADORA DEL META S.A. E.S.P. | 745.9 | 88.8 | 11.2 |
| MEDIANO | CHCC | CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. BENEFICIO E INTERES COLECTIVO | 604.8 | 100.0 | 0.0 |
| MEDIANO | HLAC | ELECTRIFICADORA DEL HUILA S.A. E.S.P. | 580.1 | 84.2 | 15.8 |
| MEDIANO | EBSC | EMPRESA DE ENERGIA DE BOYACA S.A. E.S.P. | 572.8 | 90.6 | 9.4 |
| MEDIANO | EEPC | EMPRESA DE ENERGIA DE PEREIRA S.A. E.S.P. | 512.8 | 76.0 | 24.0 |
| MEDIANO | CDNC | CENTRALES ELECTRICAS DE NARIÑO S.A. E.S.P. | 475.4 | 94.7 | 5.3 |
| MEDIANO | CEOC | COMPAÑIA ENERGETICA DE OCCIDENTE S.A.S. ESP | 426.9 | 93.3 | 6.7 |
| MEDIANO | CASC | EMPRESA DE ENERGIA DE CASANARE S.A. ESP | 319.5 | 99.6 | 0.4 |
| MEDIANO | ETTC | ENERTOTAL S.A. E.S.P. | 313.9 | 56.7 | 43.3 |
| MEDIANO | BIAC | BIA ENERGY S.A.S. E.S.P | 282.3 | 47.0 | 53.0 |
| MEDIANO | EDQC | EMPRESA DE ENERGIA DEL QUINDIO S.A. E.S.P. | 277.5 | 100.0 | 0.0 |
| MEDIANO | NEUC | NEU ENERGY S.A.S E.S.P | 275.7 | 65.4 | 34.6 |
| MEDIANO | CHVC | AES COLOMBIA & CIA. S.C.A. E.S.P. | 257.2 | 0.0 | 100.0 |
| MEDIANO | ENIC | EMPRESA DE ENERGÍA DE ARAUCA E.S.P. | 186.4 | 100.0 | 0.0 |
| MEDIANO | CMXC | CEMEX ENERGY S.A.S E.S.P. | 183.0 | 0.0 | 100.0 |
| MEDIANO | DRUC | DRUMMOND POWER S.A.S. E.S.P. | 175.4 | 0.0 | 100.0 |
| MEDIANO | CQTC | ELECTRIFICADORA DEL CAQUETA S.A. E.S.P. | 175.1 | 100.0 | 0.0 |
| MEDIANO | RTQC | RUITOQUE S.A. E.S.P. | 170.0 | 28.4 | 71.6 |
| MEDIANO | QIEC | QI ENERGY S.A.S. E.S.P. | 163.2 | 89.7 | 10.3 |
| MEDIANO | EDPC | EMPRESA DISTRIBUIDORA DEL PACIFICO S.A. E.S.P. | 154.9 | 100.0 | 0.0 |
| MEDIANO | CETC | COMPAÑIA DE ELECTRICIDAD DE TULUA S.A. E.S.P. | 126.3 | 80.3 | 19.7 |
| MEDIANO | EXEC | ENEL X COLOMBIA S.A.S ESP | 116.6 | 100.0 | 0.0 |
| PEQUEÑO | ITLC | ITALCOL ENERGIA S.A. E.S.P. | 84.2 | 0.0 | 100.0 |
| PEQUEÑO | EXIC | ENERXIA COLOMBIA SAS ESP | 63.2 | 0.0 | 100.0 |
| PEQUEÑO | TPLC | TERPEL ENERGÍA S.A.S. E.S.P. | 55.0 | 12.1 | 87.9 |
| PEQUEÑO | ENBC | ENERBIT S.A.S. E.S.P. | 52.9 | 89.6 | 10.4 |
| PEQUEÑO | EBPC | EMPRESA DE ENERGIA DEL BAJO PUTUMAYO S.A. E.S.P. | 51.4 | 100.0 | 0.0 |
| PEQUEÑO | EGVC | EMPRESA DE ENERGIA ELECTRICA DEL DEPARTAMENTO DEL GUAVIARE S.A. E.S.P. | 50.2 | 100.0 | 0.0 |
| PEQUEÑO | FERC | FUENTES DE ENERGIAS RENOVABLES S.A.S. E.S.P. | 48.1 | 0.0 | 100.0 |
| PEQUEÑO | EPTC | EMPRESA DE ENERGIA DEL PUTUMAYO S.A. E.S.P. | 46.7 | 100.0 | 0.0 |
| PEQUEÑO | FREC | FRANCA ENERGIA SA ESP | 44.9 | 0.0 | 100.0 |
| PEQUEÑO | TENC | TRANSACCIONES ENERGÉTICAS S.A.S. EMPRESA DE SERVICIOS PÚBLICOS E.S.P | 40.5 | 100.0 | 0.0 |
| PEQUEÑO | GAPC | GAP ENERGY GROUP SAS ESP | 39.5 | 0.0 | 100.0 |
| PEQUEÑO | CBNC | COLOMBINA ENERGIA SAS ESP | 38.5 | 0.0 | 100.0 |
| PEQUEÑO | LESC | MESSER ENERGY SERVICES SAS ESP | 24.2 | 0.0 | 100.0 |
| PEQUEÑO | ASCC | A.S.C. INGENIERIA S.A. E.S.P. | 17.0 | 71.5 | 28.5 |
| PEQUEÑO | EMEC | EMPRESA MUNICIPAL DE ENERGIA ELECTRICA S.A. E.S.P. | 14.7 | 37.6 | 62.4 |
| PEQUEÑO | GNYC | GREENYELLOW COMERCIALIZADORA S.A.S. E.S.P. | 12.3 | 0.0 | 100.0 |
| PEQUEÑO | EMPC | EMPRESA MUNICIPAL DE SERVICIOS PUBLICOS DE CARTAGENA DEL CHAIRA | 8.8 | 100.0 | 0.0 |
| PEQUEÑO | EVSC | EMPRESA DE ENERGIA DEL VALLE DE SIBUNDOY S.A. E.S.P. | 8.2 | 100.0 | 0.0 |
| PEQUEÑO | HIMC | GESTION ENERGETICA S.A. E.S.P. | 6.8 | 100.0 | 0.0 |
| PEQUEÑO | SCEC | SOL & CIELO ENERGIA S.A.S. E.S.P | 6.7 | 76.4 | 23.6 |
| PEQUEÑO | VESC | VOLTAJE EMPRESARIAL S.A.S. E.S.P. | 6.1 | 0.0 | 100.0 |
| PEQUEÑO | RPEC | RIOPAILA ENERGÍA S.A.S. E.S.P. | 5.6 | 0.0 | 100.0 |
| PEQUEÑO | BEIC | BEAM ENERGY INNOVATION S.A.S. E.S.P. | 3.6 | 40.6 | 59.4 |
| PEQUEÑO | ESOC | EMPRESA DE SERVICIOS PÚBLICOS DEL OCCIDENTE COLOMBIANO | 3.1 | 100.0 | 0.0 |
| PEQUEÑO | DLRC | DICELER S.A. E.S.P. | 2.7 | 100.0 | 0.0 |
| PEQUEÑO | ESVC | EMPRESA SIGLO XXI EICE ESP | 2.4 | 100.0 | 0.0 |
| PEQUEÑO | VICC | EMPRESA DE ENERGÍA ELÉCTRICA DEL DEPARTAMENTO DEL VICHADA | 1.8 | 100.0 | 0.0 |
| PEQUEÑO | PEEC | PROFESIONALES EN ENERGIA S.A. E.S.P. | 1.4 | 1.3 | 98.7 |
| PEQUEÑO | TRPC | TERMOPIEDRAS S.A. E.S.P. | 0.1 | 0.0 | 100.0 |
| PEQUEÑO | BCCC | BCCY CORDOBA S.A.S. E.S.P. | 0.0 | 0.0 | 100.0 |
| PEQUEÑO | GSAC | GENERSA S.A.S. E.S.P. | 0.0 | 0.0 | 100.0 |


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
| 2 | 0.4 | 19 172.0 |
| 3 | 0.4 | 15 754.4 |
| 4 | 0.4 | 13 115.3 |
| 5 | 0.4 | 10 341.4 |
| 6 | 0.4 | 8 708.6 |
| 7 | 0.4 | 7 450.9 |
| 8 | 0.4 | 6 384.5 |
| 9 | 0.4 | 5 603.6 |
| 10 | 0.4 | 5 064.2 |

Se selecciona **k=5** (máximo silhouette medio sobre la submuestra; los demás k se reportan para sensibilidad).

## 3. Arquetipos diarios

Cada estrategia (arquetipo) es un grupo de agentes que el día a día se comporta igual en su abastecimiento (contratos vs bolsa), su mercado objetivo (regulado vs no regulado) y su exposición al precio spot. A continuación, qué significa cada una en lenguaje de negocio:

| Estrategia | Qué hace | Cuándo le va mejor | Riesgo principal |
|---|---|---|---|
| **Trader expuesto a bolsa (sin cobertura)** (E0) | Compra casi toda su energía en la bolsa, sin contratos de cobertura; mezcla clientes regulados y no regulados y es de menor tamaño. Acepta el precio spot a cambio de no pagar la prima de los contratos. | El que mejor rinde cuando la bolsa está barata (Ene–Jun): compra al costo spot y no asume sobrecosto de contratos. | Máxima exposición: en días de escasez (Jul) el precio de bolsa se dispara y es el que más pierde. |
| **Trader no regulado** (E1) | Intermediario del mercado no regulado (industria y comercio): compra y vende energía en contratos y bolsa en volúmenes muy superiores a su propia demanda (rol de trading). Sin base regulada. | Le va bien cuando la bolsa es barata (spread contratos–bolsa favorable) y puede revender con margen. | Exposición al spot y necesidad de garantías por el alto volumen transado frente a su demanda. |
| **Integrado/regional regulado** (E2) | Grandes grupos con red de distribución (ENDC, EPMC, CELSIA…): base regulada servida por convocatoria pública, cobertura de contratos amplia y exposición a bolsa muy baja. Llevan años de mercado y fuertes garantías. | El más estable: rinde bien casi todos los días y domina cuando la bolsa está cara (tiene contratos que valen menos que el spot). | Poco margen por kWh (modelo regulado); su resultado depende del enorme volumen y de renovar su cartera por convocatoria. |
| **Comercializador regulado** (E3) | Base de clientes regulados (residencial y pequeños negocios) atendidos con tarifa CREG. Compra la mayor parte de su energía con contratos, preferiblemente vía convocatoria pública (SICEP alto) y suele cubrir más de lo que demanda. | Le va bien cuando el precio de bolsa sube: sus contratos lo protegen y no paga el sobrecosto del spot. | Margen regulado fijo (CV) con poco margen de maniobra; gana por volumen, no por spread. |
| **Trader con sobrecobertura de contratos** (E4) | Comercializador no regulado que compra contratos muy por encima de su demanda y revende el excedente; casi no usa bolsa. Actúa como arbitrajista de contratos. | Domina los días de escasez (bolsa cara): su energía comprada por contrato a precio fijo se vuelve muy valiosa frente al spot. | Descalce de cobertura y garantías por volumen; si el contrato se vuelve más caro que la bolsa, pierde. |

### E0 — Trader expuesto a bolsa (sin cobertura) (839 agentes-día, 13 agentes únicos)

Composición por segmento F-1: MEDIANO: 12; PEQUEÑO: 827.

| Feature | Media diaria |
|---|---|
| log_dema | 0.05 |
| pct_noreg | 32 |
| pct_cobertura | 7 |
| pct_exposicion | 96 |
| pct_sicep | 0 |
| tiene_sicep | 0 |

Agentes representativos: **ENIC, EBPC, EGVC, RPEC, EMEC**.

### E1 — Trader no regulado (2961 agentes-día, 19 agentes únicos)

Composición por segmento F-1: GRANDE: 424; MEDIANO: 637; PEQUEÑO: 1900.

| Feature | Media diaria |
|---|---|
| log_dema | 0.63 |
| pct_noreg | 98 |
| pct_cobertura | 566 |
| pct_exposicion | 16 |
| pct_sicep | 0 |
| tiene_sicep | 0 |

Agentes representativos: **ISGC, GECC, SOEC, CHVC, DRUC**.

### E2 — Integrado/regional regulado (6058 agentes-día, 32 agentes únicos)

Composición por segmento F-1: MEDIANO: 3742; PEQUEÑO: 2316.

| Feature | Media diaria |
|---|---|
| log_dema | 0.63 |
| pct_noreg | 15 |
| pct_cobertura | 122 |
| pct_exposicion | 11 |
| pct_sicep | 84 |
| tiene_sicep | 1 |

Agentes representativos: **GNCC, HLAC, EMSC, CHCC, EBSC**.

### E3 — Comercializador regulado (1860 agentes-día, 11 agentes únicos)

Composición por segmento F-1: GRANDE: 1060; MEDIANO: 800.

| Feature | Media diaria |
|---|---|
| log_dema | 2.70 |
| pct_noreg | 17 |
| pct_cobertura | 86 |
| pct_exposicion | 15 |
| pct_sicep | 64 |
| tiene_sicep | 1 |

Agentes representativos: **ENDC, EPMC, CSIC, CMMC, EPSC**.

### E4 — Trader con sobrecobertura de contratos (1656 agentes-día, 15 agentes únicos)

Composición por segmento F-1: MEDIANO: 533; PEQUEÑO: 1123.

| Feature | Media diaria |
|---|---|
| log_dema | 0.28 |
| pct_noreg | 60 |
| pct_cobertura | 58 924 |
| pct_exposicion | 1 |
| pct_sicep | 5 |
| tiene_sicep | 1 |

Agentes representativos: **ETTC, CHVC, RTQC, EBPC, ITLC**.

## 4. Ranking diario

Número de días que cada estrategia ocupó cada puesto (1.º = mejor margen del día):

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader expuesto a bolsa (sin cobertura) | 168 | 4 | 3 | 18 | 19 | 212 |
| Trader no regulado | 2 | 1 | 33 | 146 | 30 | 212 |
| Integrado/regional regulado | 1 | 27 | 163 | 20 | 1 | 212 |
| Comercializador regulado | 36 | 174 | 1 | 1 | 0 | 212 |
| Trader con sobrecobertura de contratos | 5 | 6 | 12 | 27 | 162 | 212 |

### 4.1 Matriz de puestos por segmento

La misma distribución pero **por segmento** (GRANDE/MEDIANO/PEQUEÑO): cada segmento compite dentro de sí mismo, no contra los demás.

**GRANDE** — 7 agentes · 2 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader no regulado | 165 | 47 | 0 | 0 | 0 | 212 |
| Comercializador regulado | 47 | 165 | 0 | 0 | 0 | 212 |

**MEDIANO** — 27 agentes · 4 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader expuesto a bolsa (sin cobertura) | 7 | 0 | 2 | 3 | 0 | 12 |
| Trader no regulado | 1 | 33 | 62 | 112 | 4 | 212 |
| Integrado/regional regulado | 0 | 78 | 108 | 26 | 0 | 212 |
| Comercializador regulado | 170 | 23 | 13 | 6 | 0 | 212 |
| Trader con sobrecobertura de contratos | 34 | 78 | 27 | 65 | 8 | 212 |

**PEQUEÑO** — 31 agentes · 4 estrategias en el ranking

| Estrategia | 1.º | 2.º | 3.º | 4.º | 5.º | Total días |
|---|---|---|---|---|---|---|
| Trader expuesto a bolsa (sin cobertura) | 174 | 15 | 20 | 3 | 0 | 212 |
| Trader no regulado | 1 | 40 | 146 | 25 | 0 | 212 |
| Integrado/regional regulado | 35 | 155 | 22 | 0 | 0 | 212 |
| Trader con sobrecobertura de contratos | 2 | 2 | 24 | 184 | 0 | 212 |

### 4.2 Días destacados (bolsa cara)

Días con mayor precio de bolsa (señal de escasez; el spread bolsa−contrato define quién gana):

| Fecha | Bolsa (COP/kWh) | Contratos (COP/kWh) | Spread | Estrategia ganadora |
|---|---|---|---|---|
| 2025-01-29 | 765.9 | 315.2 | 450.7 | Trader con sobrecobertura de contratos |
| 2025-01-26 | 760.3 | 316.2 | 444.2 | Comercializador regulado |
| 2025-02-06 | 740.3 | 312.3 | 428.1 | Comercializador regulado |
| 2025-01-28 | 740.8 | 316.2 | 424.6 | Comercializador regulado |
| 2025-01-27 | 738.1 | 315.7 | 422.4 | Trader no regulado |
| 2025-01-23 | 738.2 | 316.4 | 421.8 | Trader no regulado |
| 2025-01-25 | 722.1 | 314.6 | 407.5 | Comercializador regulado |
| 2025-02-05 | 711.0 | 314.1 | 396.8 | Integrado/regional regulado |

Días de escasez (bolsa > precio de escasez): **0** de 212 días. En esos días la estrategia ganadora fue, por frecuencia:

_Sin días de escasez en la ventana._

## 5. Ranking y balance por segmento

El ranking pooled mezcla segmentos de tamaños muy distintos. Aquí cada segmento se analiza **por separado** (los GRANDE no compiten contra los PEQUEÑO), para ver qué estrategia funciona mejor dentro de cada uno — especialmente en MEDIANO y PEQUEÑO, donde la estructura es menos homogénea que en GRANDE.

### 5.1 — GRANDE

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader no regulado | 1 | 212 | -5.1 | 165 | 100.0% | 1.2 |
| 2 | Comercializador regulado | 3 | 212 | -17.9 | 47 | 100.0% | 1.8 |

La mejor estrategia del segmento **GRANDE** fue **Trader no regulado** (mediana -5.06 COP/kWh/día, 165 días en 1.º).

### 5.2 — MEDIANO

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Comercializador regulado | 3 | 212 | -4.8 | 170 | 97.2% | 1.3 |
| 2 | Integrado/regional regulado | 2 | 212 | -39.9 | 0 | 87.7% | 2.8 |
| 3 | Trader con sobrecobertura de contratos | 4 | 212 | -45.3 | 34 | 65.6% | 2.7 |
| 4 | Trader no regulado | 1 | 212 | -67.2 | 1 | 45.3% | 3.4 |

La mejor estrategia del segmento **MEDIANO** fue **Comercializador regulado** (mediana -4.82 COP/kWh/día, 170 días en 1.º).
 Casos atípicos del segmento: Trader expuesto a bolsa (sin cobertura) (E0, 12 días).

### 5.3 — PEQUEÑO

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Días 1.º | % top-3 | Rango prom. |
|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 0 | 212 | 64.7 | 174 | 98.6% | 1.3 |
| 2 | Integrado/regional regulado | 2 | 212 | -59.7 | 35 | 100.0% | 1.9 |
| 3 | Trader no regulado | 1 | 212 | -253.2 | 1 | 88.2% | 2.9 |
| 4 | Trader con sobrecobertura de contratos | 4 | 212 | -500 | 2 | 13.2% | 3.8 |

La mejor estrategia del segmento **PEQUEÑO** fue **Trader expuesto a bolsa (sin cobertura)** (mediana 64.65 COP/kWh/día, 174 días en 1.º).

### 5.4 Matriz estrategia × segmento (mediana del margen, COP/kWh)

Cada celda es la mediana del **margen diario** de esa estrategia dentro de ese segmento (días = días presentes), la misma métrica del ranking por segmento. En **negrita**, la mejor estrategia de cada columna (segmento); las estrategias atípicas del segmento se marcan y no se cuentan:

| Estrategia | GRANDE | MEDIANO | PEQUEÑO |
|---|---|---|---|
| **Trader expuesto a bolsa (sin cobertura)** | — | -9.4 (12 días) (atípico) | **64.7 (212 días)** |
| **Trader no regulado** | **-5.1 (212 días)** | -67.2 (212 días) | -253.2 (212 días) |
| **Integrado/regional regulado** | — | -39.9 (212 días) | -59.7 (212 días) |
| **Comercializador regulado** | -17.9 (212 días) | **-4.8 (212 días)** | — |
| **Trader con sobrecobertura de contratos** | — | -45.3 (212 días) | -500.0 (212 días) |

> **Cómo leerlo:** el ranking pooled (sección 6) lo encabezan estrategias que funcionan bien combinando todos los tamaños. Para el análisis de negocio importa la **columna de cada segmento**: en GRANDE suele dominar la cobertura de contratos (integrados con red, años de mercado y garantías), mientras que en MEDIANO y PEQUEÑO compiten traders y regulados con estructuras distintas. Si un segmento tiene **0 días** en una estrategia, esa estrategia no aparece en su balance.

## 6. Balance del período

| Pos. | Estrategia | Clúster | Días | Mediana margen (COP/kWh) | Media margen | Días 1.º | % top-3 | Rango prom. | Tendencia 2.ª−1.ª mitad |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Trader expuesto a bolsa (sin cobertura) | 0 | 212 | 64.7 | -5.2 | 168 | 82.5% | 1.7 | 194.1 |
| 2 | Comercializador regulado | 3 | 212 | -12.5 | -28.6 | 36 | 99.5% | 1.8 | 45.9 |
| 3 | Integrado/regional regulado | 2 | 212 | -50.0 | -61.4 | 1 | 90.1% | 3.0 | 29.9 |
| 4 | Trader no regulado | 1 | 212 | -86.4 | -100.2 | 2 | 17.0% | 4.0 | 20.2 |
| 5 | Trader con sobrecobertura de contratos | 4 | 212 | -245.3 | -275.5 | 5 | 10.8% | 4.6 | 15.1 |

La estrategia **Trader expuesto a bolsa (sin cobertura)** dominó el período: mediana de 64.65 COP/kWh/día, 168 días en el 1.er puesto (82.5 % de días top-3), rango promedio 1.66. Perfil: 839 agentes-día de 13 agentes; no regulado 32 %, cobertura 7 %, exposición 96 %. Su tendencia fue **positiva** (mejoró en la 2.ª mitad del período). En segundo lugar, **Comercializador regulado** (-12.47 COP/kWh/día, 36 días en 1.º). El resultado es un artefacto del modelo (Pv=350 fijo) y sirve para comparar estrategias, no como margen real del negocio.

## 7. Limitaciones

1. **No hay precio ni margen real por agente** en elecdb: todo valor COP es volumen × precio promedio de sistema del día; el margen es un artefacto de modelado (Pv=350 COP/kWh fijo).
2. **K-Means es descriptivo**: asume esfericidad/varianza similar; k, features y escalado son decisiones del analista; resultados dependen de la ventana.
3. **Agentes diminutos** (volúmenes < 0,01 GWh/día) producen features ruidosas y márgenes extremos; se mitigan con log1p y clip, pero distorsionan las medianas de su estrategia.
4. **SICEP diario** es 0 imputado en puros no regulados (no compran regulado); `tiene_sicep` distingue '0 % convocatoria' de 'no aplica'.
5. **Sin precios de contrato por agente**: el margen solo capta el mix y el nivel de precio de sistema; no hay señal de negociación individual ni de contraparte.
6. Resultados describen **comportamiento pasado** (Ene–Jul 2026), no predicción.
