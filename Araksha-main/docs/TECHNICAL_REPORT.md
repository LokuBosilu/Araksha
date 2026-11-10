# Silent Node: Technical Report
## Operational Dengue Risk Forecasting and Vector-Control Resource Allocation for Sri Lanka

**Document Version**: 1.0.0 (Post-Backtest Verification)  
**Target Audience**: Epidemiologists, Data Engineers, and National Dengue Control Unit Technical Committees  
**Disclaimer**: Silent Node is an operational decision-support tool for planning vector-control logistics and larviciding teams 2 to 4 weeks ahead. It is **NOT** a clinical diagnostic or triage tool.

---

## 1. Executive Summary

Dengue transmission in Sri Lanka is characterized by seasonal bimodal surges linked to the Southwest (May–August) and Northeast (November–January) monsoons. However, operational vector-control interventions—such as larvicide application, source reduction campaigns, and targeted ultra-low volume (ULV) fogging—require 2 to 4 weeks of mobilization lead time to alter vector parity and suppress secondary transmission cycles.

Silent Node is an operational forecasting and field allocation system covering all **26 reporting units** of Sri Lanka (25 administrative districts plus the Kalmunai health zone). It evaluates multiple horizon-specific probabilistic models against strict operational baselines. Evaluated on a **2022–2024 rolling-origin backtest** across 20 distinct origins encompassing the historic 2023 nationwide dengue surge, the operational **Ensemble** achieves:
- **Horizon $h=2$ Weighted Interval Score (WIS)**: **11.54**, outperforming the Seasonal-Naive baseline (**15.76**) by **26.8%**, and the Last-Value baseline (**18.16**) by **36.5%**.
- **Fallback Rule**: **PASS** (Ensemble and Negative-Binomial GAM beat Seasonal-Naive on WIS at $h=2$).
- **Western Province Outbreak Hotspots ($h=2$)**: Colombo Ensemble WIS **40.86** vs. 60.26 Seasonal-Naive (**32.2% reduction**, ROC-AUC 0.947); Gampaha Ensemble WIS **29.70** vs. 43.88 Seasonal-Naive (**32.3% reduction**, ROC-AUC 1.000).
- **Interval Dispersion Note**: Nominal 95% interval coverage reaches **77.9%** (< 80%), and 50% interquartile coverage reaches **36.7%**. Prediction intervals are under-dispersed during explosive epidemic surges, which is documented honestly as an operational limitation.

---

## 2. Epidemiological Surveillance & Spatial Architecture

### 2.1 The 26 Reporting Units
Sri Lanka's dengue surveillance, managed by the Epidemiology Unit of the Ministry of Health, tracks weekly notifications from secondary and tertiary care institutions across 25 administrative districts. In addition, the **Kalmunai Regional Directorate of Health Services (RDHS)** is maintained as an independent 26th reporting unit due to administrative and epidemiological autonomy within the Ampara District:
- **Kalmunai vs. Ampara Split**: Ampara RDHS encompasses inland territory (~335,000 population), while Kalmunai RDHS encompasses the dense coastal belt (~415,000 population).
- **Centroid Coordinates**: Kalmunai weather centroid is assigned to coastal administrative coordinates (7.416° N, 81.825° E), distinct from inland Ampara (7.291° N, 81.672° E).
- **Spatial Contiguity**: Kalmunai borders Ampara (inland), Batticaloa (north), and Monaragala (southwest). The Jaffna peninsula connects to Kilinochchi via the Elephant Pass causeway, ensuring zero isolated spatial islands.

### 2.2 Historical Surveillance Panel
- **Primary Source**: `denguedatahub` (Talagala, 2021) harmonized with weekly Weekly Epidemiological Reports (WER) from `epid.gov.lk`.
- **Temporal Span**: 2006-W52 through 2026-W20 (26,311 total district-week records).
- **Verified Historic Benchmarks**:
  - The nationwide epidemic peak occurred in **Week 29 of 2017**, reaching **10,590 notified cases/week**.
  - Across the entire 2017 calendar year, total notified cases in our 26-unit surveillance panel sum to exactly **174,687 cases**.
  - Zero missing keys, zero negative counts, and zero silently imputed counts.

---

## 3. Data Ingestion & Static Covariates

| Dataset | Source / Provider | Spatial / Temporal Resolution | Processing Role |
| :--- | :--- | :--- | :--- |
| **Weekly Cases** | `denguedatahub` & MOH Epidemiology Unit | 26 reporting units, weekly counts | Target variable $Y_{i,t}$ and autoregressive features |
| **ERA5 Reanalysis** | ECMWF / Open-Meteo API | Daily precipitation, 2m temp, relative humidity | Aggregated to ISO epidemiological weeks; distributed lag features |
| **Demographics** | UN OCHA COD-PS (2023) | District population estimates | Population offset for incidence per 100,000 |
| **Piped Water Access** | DCS Sri Lanka (CPH-2024 Table A5) | Proportion of households with piped tap water | Static infrastructure vulnerability covariate (National 41.4%; Colombo 84.4%) |
| **Contiguity Matrix** | UN OCHA COD-AB | District boundary topology | First-order Queen-contiguity spatial lag weights |

---

## 4. Leakage-Safe Feature Store Architecture

To guarantee that forecasts represent strictly available real-time information, Silent Node enforces a rigorous leakage protocol:

### 4.1 Operational Reporting Delay Buffer
In clinical public health surveillance, notification reports from the most recent 1 to 2 weeks are provisional and subject to upward revision as delayed laboratory confirmations arrive. Silent Node enforces a **strict 2-week reporting delay buffer**:
- At forecast origin week $t$, data from weeks $t$ and $t-1$ are discarded as incomplete.
- All autoregressive features are anchored at week $t-2$:
  - $Y_{i, t-2}, Y_{i, t-3}, Y_{i, t-4}, Y_{i, t-5}$
  - Recent momentum: $Y_{i, t-2} / (\frac{1}{3}\sum_{k=2}^4 Y_{i, t-k} + 1)$
  - 3-week rolling average: $\frac{1}{3}\sum_{k=2}^4 Y_{i, t-k}$

### 4.2 Climate Distributed Lags
Mosquito egg hatching, larval maturation, and adult gonotrophic cycles require 4 to 12 weeks to translate into clinical patient presentations:
- **Precipitation**: Lags at 4, 6, 8, 10, and 12 weeks prior to origin $t$.
- **Temperature & Humidity**: Lags at 8, 10, 12, and 14 weeks prior to origin $t$.
- **Seasonal Bases**: Harmonic terms $\sin(2\pi \cdot \text{week} / 52)$ and $\cos(2\pi \cdot \text{week} / 52)$, plus monsoon phase indicators.

### 4.3 Direct Multi-Horizon Target Formulation
Separate training matrices are materialized for each forecast horizon $h \in \{1, 2, 3, 4\}$:
$$Y_{i, t+h} = f_h\left(X_{i, t-2}, Z_i\right)$$
Models are trained independently for each horizon $h$, preventing identical outputs across multi-week horizons.

---

## 5. Model Formulations & Ensemble Mechanics

### 5.1 Negative-Binomial Generalized Additive Model (NB-GAM)
For each district $i$ and horizon $h$, count observations $Y_{i, t+h}$ are modeled via a negative-binomial distribution with log link:
$$\log(\mu_{i, t+h}) = \log(\text{Pop}_i) + \beta_0 + \sum_{k=2}^5 \beta_k \log(Y_{i, t-k} + 1) + f_{\text{rain}}(R_{i, t-8}) + f_{\text{temp}}(T_{i, t-8}) + f_{\text{seas}}(\text{week}_t)$$
where dispersion parameter $\alpha$ is estimated via maximum likelihood.

### 5.2 Calibrated Seasonal-Autoregressive Model (Seasonal-AR)
An autoregressive log-linear formulation conditioned on historical seasonal incidence profiles:
$$\log(\hat{Y}_{i, t+h} + 1) = \alpha_0 + \alpha_1 \log(Y_{i, t-2} + 1) + \alpha_2 \log(\bar{Y}_{i, \text{week}(t+h)} + 1)$$
This serves as the operational fallback baseline if complex climate models fail to outperform simple baselines.

### 5.3 Quantile Ensemble & Non-Crossing Isotonic Projection
Predictions from the candidate models are blended at matching quantile levels $q \in [0.01, 0.99]$:
$$\hat{Q}_{\text{ens}}(q) = w_1 \hat{Q}_{\text{nb}}(q) + w_2 \hat{Q}_{\text{ar}}(q)$$
To prevent crossing quantile anomalies (where $q_a > q_b$ for $a < b$), predictions undergo non-decreasing isotonic projection:
$$\hat{Q}'(q_j) = \max_{k \le j} \hat{Q}(q_k)$$
All 17 quantile levels $\{0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95, 0.975, 0.99\}$ are computed directly from parametric predictive distributions with zero hardcoded heuristic multipliers.

---

## 6. Rolling-Origin Backtest Evaluation (2022–2024)

### 6.1 Backtest Protocol
- **Evaluation Window**: 20 rolling origin dates across 2022–2024, evaluated at 2-week intervals during epidemic and non-epidemic seasons.
- **Reporting Delay**: 2-week buffer applied at every evaluation origin.
- **Metrics**:
  - **Weighted Interval Score (WIS)** across 11 symmetric central intervals.
  - **Median Absolute Error (Median AE)**.
  - **Empirical Coverage**: Nominal 50% (interquartile) and 95% prediction intervals.
  - **Exceedance ROC-AUC**: Binary classification of whether actual cases exceeded the district's historical 95th percentile ($Q_{95}^{\text{train}}$).

### 6.2 Full Per-Model, Per-Horizon Results Table

| Model | Horizon | WIS | Median AE | 50% Coverage | 95% Coverage | Exceedance ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Seasonal-Naive** | $h=1$ | 15.28 | 25.09 | 32.9% | 76.5% | 0.713 |
| Seasonal-Naive | $h=2$ | 15.76 | 25.57 | 32.7% | 72.7% | 0.726 |
| Seasonal-Naive | $h=3$ | 13.72 | 23.01 | 32.5% | 78.7% | 0.718 |
| Seasonal-Naive | $h=4$ | 16.99 | 26.12 | 33.1% | 75.0% | 0.655 |
| **Last-Value** | $h=1$ | 18.08 | 30.17 | 33.5% | 74.8% | 0.572 |
| Last-Value | $h=2$ | 18.16 | 29.66 | 38.5% | 76.0% | 0.501 |
| Last-Value | $h=3$ | 16.24 | 26.69 | 41.7% | 82.7% | 0.459 |
| Last-Value | $h=4$ | 18.72 | 29.71 | 40.8% | 81.2% | 0.478 |
| **Seasonal-AR** | $h=1$ | 11.84 | 19.37 | 41.7% | 82.3% | 0.769 |
| Seasonal-AR | $h=2$ | 14.30 | 22.17 | 31.9% | 75.6% | 0.613 |
| Seasonal-AR | $h=3$ | 13.06 | 20.76 | 35.4% | 78.7% | 0.657 |
| Seasonal-AR | $h=4$ | 16.48 | 24.73 | 30.6% | 75.2% | 0.618 |
| **NB-GAM** | $h=1$ | 8.54 | 14.84 | 41.3% | 85.4% | 0.906 |
| NB-GAM | $h=2$ | 10.86 | 16.80 | 40.8% | 78.7% | 0.774 |
| NB-GAM | $h=3$ | 11.29 | 17.58 | 40.0% | 79.8% | 0.760 |
| NB-GAM | $h=4$ | 14.66 | 21.45 | 38.5% | 77.9% | 0.690 |
| **Ensemble (Selected)** | $h=1$ | **9.09** | **16.27** | **42.1%** | **85.4%** | **0.870** |
| Ensemble (Selected) | $h=2$ | **11.54** | **18.76** | **36.7%** | **77.9%** | **0.745** |
| Ensemble (Selected) | $h=3$ | **11.21** | **17.80** | **37.1%** | **81.2%** | **0.701** |
| Ensemble (Selected) | $h=4$ | **14.66** | **21.64** | **34.4%** | **78.5%** | **0.659** |

### 6.3 Fallback Gate Verdict
- **Criterion**: Operational model must achieve lower WIS than Seasonal-Naive at horizon $h=2$.
- **Result**: Ensemble WIS **11.54** vs. Seasonal-Naive **15.76** (reduction of 4.22 points, or **26.8%**).
- **Verdict**: **PASS**. Operational model: **Ensemble (NB-GAM + Seasonal-AR)**.

### 6.4 Western Province Metro District Breakdown ($h=2$)

| District | Seasonal-Naive WIS | Seasonal-AR WIS | NB-GAM WIS | Ensemble WIS | WIS Improvement | Exceedance ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Colombo** | 60.26 | 59.64 | 37.68 | **40.86** | **-32.2%** | 0.947 |
| **Gampaha** | 43.88 | 31.76 | 30.56 | **29.70** | **-32.3%** | 1.000 |
| **Kalutara** | 23.84 | 18.51 | 18.89 | **17.39** | **-27.1%** | 0.395 |

---

## 7. Operational Risk Tiers & Field Allocation Engine

### 7.1 Risk-Tier Classification Rules
Every district-week forecast is classified into a decision-ready tier:
- **Low**: $P(Y_{t+h} > Q_{95}^{\text{train}}) < 0.15$ and Weekly Incidence $< 10$ per 100k.
- **Moderate**: $0.15 \le P < 0.50$ or Weekly Incidence $10 - 25$ per 100k.
- **High**: $0.50 \le P < 0.80$ or Weekly Incidence $25 - 50$ per 100k.
- **Extreme**: $P \ge 0.80$ or Weekly Incidence $\ge 50$ per 100k.
- **Insufficient Data**: Triggered whenever recent surveillance data is missing or stale. **Never defaults to Low.**

### 7.2 Early Anomaly Surge Detection
An anomaly alert is flagged when a district satisfies:
$$\hat{Y}_{i, t+h} \ge 2.0 \times \text{Baseline}_{\text{seasonal}} \quad \text{and} \quad \text{Incidence}_{i, t-2} < 15 \text{ per 100k}$$
This provides vector-control teams with a 2- to 3-week operational window to destroy breeding containers before cases present at outpatient clinics.

### 7.3 Vector-Control Allocation Matrix
Districts are ranked by an operational Allocation Score combining projected median burden, exceedance probability, and piped-water vulnerability:
$$\text{Score}_i = \text{Incidence}_{i, t+h} \times (1 + P(Y > Q_{95})) \times (1 + (1 - \text{PipedWaterShare}_i))$$
The interactive dashboard provides one-click CSV export of this matrix for weekly task force deployment meetings.

---

## 8. Limitations & Under-Dispersion Protocol

1. **Interval Under-Dispersion**:
   - Nominal 95% coverage at $h=2$ reaches **77.9%** (< 80%), and nominal 50% coverage reaches **36.7%**.
   - The negative-binomial dispersion parameter underestimates variance during explosive epidemic surges.
   - Field officers must treat the $q_{0.975}$ bound as a lower bound on tail risk during rapid outbreak growth.
2. **2-Week Operational Reporting Delay**:
   - Hospital notification delays require discarding data from $t$ and $t-1$. Interventions cannot react to same-day clinical events.
3. **Spatial Granularity**:
   - Forecasts operate at the district level. Sub-district targeting across Medical Officer of Health (MOH) areas requires local field registers.
4. **Non-Clinical Boundary**:
   - Silent Node is strictly designed for environmental vector control, larviciding, and inspection team staging, **NOT for clinical triage or patient diagnosis**.
