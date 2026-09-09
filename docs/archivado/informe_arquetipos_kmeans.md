# Arquetipos Emergentes de Comercializadores del MEM — Segmentación no supervisada (K-Means, H1-2026)

> Proyecto SFEIA · Generado 2026-01-01 → 2026-06-30 (H1-2026) · Población: **65 comercializadores** · K-Means de scikit-learn (k=3, semilla=42).

> Estudio **complementario e independiente** del benchmark por segmento (docs/informe_estrategias_comercializacion.md). No modifica la segmentación F-1 ni la tipificación F6.

## Resumen ejecutivo

- **Clúster 0 · Trader expuesto a bolsa (sin cobertura)** (5 agentes): composición PEQUEÑO: 5.
- **Clúster 1 · Trader no regulado** (17 agentes): composición GRANDE: 2; MEDIANO: 4; PEQUEÑO: 11.
- **Clúster 2 · Comercializador regulado** (43 agentes): composición GRANDE: 5; MEDIANO: 24; PEQUEÑO: 14.
- Silhouette medio (k=3): **0.4592**. ARI vs segmento F-1: **0.0545**; ARI vs arquetipo por reglas (muestra 25): **0.209**.

## 1. Metodología

Features por agente (perfil reportado en escala original; la matriz de clustering usa transformaciones documentadas):

| Feature | Dimensión | Descripción |
|---|---|---|
| log_dema | Tamaño | log1p(DemaCome semestral, GWh) |
| pct_noreg | Mercado objetivo (D2) | % de demanda no regulada |
| pct_cobertura | Abastecimiento (D1) | % cobertura con contratos — log1p en la matriz (clip 300 %) |
| pct_exposicion | Riesgo spot (D4) | % exposición a bolsa — log1p en la matriz |
| pct_sicep | Convocatoria (D2) | % compras reguladas con registro SICEP (NaN → 0) |
| tiene_sicep | Convocatoria (D2) | 1 si compra regulado, 0 si puro no regulado |

Escalado: **standard**; elección de k por **silhouette** sobre k∈[2,10]; `random_state=42`, `n_init=10`.

**Features evaluadas y excluidas:** `pct_perdidas` e `intensidad_pico` se probaron y se descartaron por silhouette inferior y ruido extremo en agentes diminutos (posición neta/venta desproporcionada a su demanda). Todo el conjunto es reproducible desde `config/config.yaml`.

> **Matiz de transparencia:** el k-means no está *libre de sesgo*: la selección de features, el escalado, la imputación de SICEP y el número de clústeres siguen siendo decisiones del analista. Lo que elimina es el etiquetado/umbralización manual de arquetipos. Todo es reproducible desde `config/config.yaml`.

## 2. Elección de k

| k | Silhouette medio | Inercia |
|---|---|---|
| 2 | 0.4 | 243.3 |
| 3 | 0.5 | 180.0 |
| 4 | 0.4 | 152.4 |
| 5 | 0.4 | 133.7 |
| 6 | 0.3 | 113.5 |
| 7 | 0.3 | 101.2 |
| 8 | 0.3 | 88.3 |
| 9 | 0.3 | 74.8 |
| 10 | 0.4 | 66.3 |

Se selecciona **k=3** (máximo silhouette medio; los demás k se reportan para sensibilidad).

## 3. Perfiles por clúster

### Clúster 0 — Trader expuesto a bolsa (sin cobertura) (5 agentes)

Miembros: GSAC, HIMC, RPEC, TRPC, VICC

Composición por segmento F-1: PEQUEÑO: 5.

| Feature | Media | Mediana |
|---|---|---|
| log_dema | 1.0 | 0.9 |
| pct_noreg | 40.0% | 0.0% |
| pct_cobertura | 0.0% | 0.0% |
| pct_exposicion | 78.6% | 100.0% |
| pct_sicep | 0.0% | 0.0% |
| tiene_sicep | 0.2 | 0.0 |

Agentes representativos (mayor demanda): **HIMC, RPEC, VICC, TRPC, GSAC**.

### Clúster 1 — Trader no regulado (17 agentes)

Miembros: BCCC, BEIC, CBNC, CHVC, CMXC, DRUC, EXIC, FERC, FREC, GAPC, GECC, GNYC, ISGC, LESC, PEEC, SOEC, VESC

Composición por segmento F-1: GRANDE: 2; MEDIANO: 4; PEQUEÑO: 11.

| Feature | Media | Mediana |
|---|---|---|
| log_dema | 4.0 | 3.7 |
| pct_noreg | 99.3% | 100.0% |
| pct_cobertura | 816.9% | 118.8% |
| pct_exposicion | 24.7% | 16.8% |
| pct_sicep | 0.0% | 0.0% |
| tiene_sicep | 0.1 | 0.0 |

Agentes representativos (mayor demanda): **GECC, ISGC, SOEC, CHVC, DRUC**.

### Clúster 2 — Comercializador regulado (43 agentes)

Miembros: ASCC, BIAC, CASC, CDNC, CEOC, CETC, CHCC, CMMC, CNSC, CQTC, CSIC, DLRC, EBPC, EBSC, EDPC, EDQC, EEPC, EGVC, EMEC, EMIC, EMPC, EMSC, ENBC, ENDC, ENIC, EPMC, EPSC, EPTC, ESOC, ESSC, ESVC, ETTC, EVSC, EXEC, GNCC, HLAC, ITLC, NEUC, QIEC, RTQC, SCEC, TENC, TPLC

Composición por segmento F-1: GRANDE: 5; MEDIANO: 24; PEQUEÑO: 14.

| Feature | Media | Mediana |
|---|---|---|
| log_dema | 5.2 | 5.2 |
| pct_noreg | 20.7% | 10.1% |
| pct_cobertura | 136.8% | 95.8% |
| pct_exposicion | 18.9% | 11.0% |
| pct_sicep | 80.3% | 93.4% |
| tiene_sicep | 1.0 | 1.0 |

Agentes representativos (mayor demanda): **ENDC, EPMC, CSIC, CMMC, EPSC**.

## 4. Arquetipos emergentes (interpretación)

**Trader expuesto a bolsa (sin cobertura)** (Clúster 0): compra la mayor parte de su energía en bolsa (sin cobertura de contratos); máxima exposición al precio spot. — no regulado 40% · cobertura 0% · exposición 79% · SICEP 0%
**Trader no regulado** (Clúster 1): concentra la demanda no regulada y compite por spread spot–contrato; riesgo de capital de trabajo en escasez. — no regulado 99% · cobertura 817% · exposición 25% · SICEP 0%
**Comercializador regulado** (Clúster 2): base regulada con tarifa CREG y exposición contenida. — no regulado 21% · cobertura 137% · exposición 19% · SICEP 80%

## 5. Contrapunto y validación

### 5.1 Clúster × segmento F-1

| Clúster | GRANDE | MEDIANO | PEQUEÑO |
|---|---|---|---|
| C0 | 0 | 0 | 5 |
| C1 | 2 | 4 | 11 |
| C2 | 5 | 24 | 14 |

**ARI (clúster vs segmento por tamaño): 0.0545.** Un valor bajo indica que el tamaño no es la única dimensión que separa a los agentes (hipótesis M0).

### 5.2 Clúster × arquetipo por reglas (muestra 25)

| Clúster | Distribuidor en intervención | Frontera regulada | Generador+comercializador solo no regulado | Integrado de red | Regional regulado | Trader mixto | Trader no regulado especializado |
|---|---|---|---|---|---|---|---|
| C1 | 0 | 0 | 4 | 0 | 0 | 0 | 5 |
| C2 | 1 | 2 | 0 | 4 | 2 | 6 | 1 |

**ARI (clúster vs tipificación por reglas, n=25): 0.209.**

Casos donde el arquetipo por reglas no coincide con el mayoritario del clúster:

| Agente | Arquetipo por reglas | Arquetipo del clúster |
|---|---|---|
| CHVC | Generador+comercializador solo no regulado | Trader no regulado especializado |
| CMMC | Integrado de red | Trader mixto |
| CNSC | Regional regulado | Trader mixto |
| CSIC | Distribuidor en intervención | Trader mixto |
| DRUC | Generador+comercializador solo no regulado | Trader no regulado especializado |
| EBPC | Frontera regulada | Trader mixto |
| EGVC | Frontera regulada | Trader mixto |
| ENDC | Integrado de red | Trader mixto |
| EPMC | Integrado de red | Trader mixto |
| EPSC | Integrado de red | Trader mixto |
| GECC | Generador+comercializador solo no regulado | Trader no regulado especializado |
| GNCC | Regional regulado | Trader mixto |
| ISGC | Generador+comercializador solo no regulado | Trader no regulado especializado |
| TPLC | Trader no regulado especializado | Trader mixto |

## 6. Estrategias por arquetipo

- **Trader expuesto a bolsa (sin cobertura)** (Clúster 0): reducir exposición con contratos escalonados y dimensionar garantías (R2): es el arquetipo más vulnerable al spot.
- **Trader no regulado** (Clúster 1): dimensionar garantías y cobertura de contratos antes de crecer en no regulado; margen en spread spot.
- **Comercializador regulado** (Clúster 2): disciplina de compras reguladas y gestión de exposición; monitorear señal SICEP.

## 7. Limitaciones

1. **K-means asume esfericidad y varianza similar** por clúster; el resultado depende del escalado (standard/robust) y de transformaciones (log/clip).
2. **n=65 es pequeño**: los clústeres son frágiles ante cambios de features o de un agente; k se elige por silhouette pero no existe un 'k verdadero'.
3. **El 'sin sesgo' es parcial**: features, escalado, imputación y k son decisiones del analista; nombrar arquetipos es una interpretación humana (sección 1).
4. **SICEP es 0 imputado** en puros no regulados (no compran regulado); `tiene_sicep` distingue '0% convocatoria' de 'no aplica'.
5. **pct_perdidas e intensidad_pico se excluyeron** por silhouette inferior y ruido extremo en agentes diminutos; `pct_cobertura` > 100 % (sobrecobertura por trading) se mitiga con clip (300 %) y log1p en la matriz.
6. **No hay precio ni margen por agente** (D3 no entra): los arquetipos describen estructura de compra/venta, no desempeño financiero real.
7. Resultados describen **comportamiento pasado** (H1-2026), no predicción.
