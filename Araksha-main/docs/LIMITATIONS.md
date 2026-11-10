# Silent Node: Methodological Limitations and Operational Constraints

To ensure responsible operational deployment by vector-control and public health decision-makers, this document details the primary scientific and structural limitations of Silent Node.

## 1. Moderate Climate Correlations
- While temperature and precipitation govern vector biology (*Aedes aegypti* and *Aedes albopictus* development cycles), empirical correlation between weekly district rainfall and clinical case incidence is moderate (peak Pearson $r \approx +0.18$ at 8-week lag in Colombo).
- Climate features provide signal for epidemic timing and seasonal elevation, but local human behavior (water storage practices, discarded containers, construction site pooling) frequently overrides macroeconomic climate forcing.
- Therefore, climate variables are regularized via distributed spline terms and must never be interpreted as deterministic drivers.

## 2. Reporting Delays & Incomplete Recent Data
- Dengue cases reported in weekly epidemiological bulletins represent cases diagnosed and notified through hospital surveillance.
- A **2-week reporting lag buffer** is strictly enforced because data from the most recent 1 to 2 weeks is subject to reporting delays and upward retroactive revisions.
- Treating the most recent weeks as complete introduces optimistic bias and artificially deflates uncertainty.

## 3. Spatial Granularity (District vs. MOH Division)
- Silent Node forecasts at the level of Sri Lanka's 26 primary reporting units (25 administrative districts plus the Kalmunai health zone).
- In reality, dengue transmission is hyper-localized: within Colombo district, transmission may cluster in specific Medical Officer of Health (MOH) areas (e.g., Colombo Municipal Council MOH areas vs. Homagama).
- District-level forecasts guide inter-district resource allocation and mobile fogging unit staging, but sub-district prioritization requires local MOH inspection registers.

## 4. Static Census-Snapshot Covariates
- Piped-water access share is derived from the CPH-2024 census snapshot, and population denominators are drawn from the 2023 UN OCHA COD-PS demographic tables.
- Rapid urban expansion, informal settlements, and temporary inter-district migration (e.g., daily commuters into Colombo and Kandy) are not captured in static snapshots.

## 5. The Kalmunai Reporting Zone Decision
- Kalmunai operates as an independent Regional Directorate of Health Services (RDHS) reporting unit despite residing within the geographic boundaries of Ampara District.
- In Silent Node, Kalmunai is preserved as an independent time series to match historical epidemiological surveillance bulletins. Weather covariates are assigned to its coastal administrative coordinates (7.416° N, 81.825° E), distinct from inland Ampara.
- When cross-referencing with purely administrative GIS boundaries, Kalmunai must be re-aggregated with Ampara.

## 6. Planning Tool Disclaimer
- **Silent Node is a planning decision-support tool, NOT a clinical diagnostic tool.**
- It is designed to assist vector-control officers, MOH staff, and task forces in staging larvicide, fogging teams, and community source reduction 2 to 4 weeks ahead. It must not be used for individual clinical diagnosis or triage.

## 7. Interval Under-Dispersion during Epidemic Surges
- In the rolling-origin backtest, empirical coverage for the nominal 95% prediction interval at the 2-week operational horizon ($h=2$) is **77.9%** (< 80%), and 50% interquartile coverage is **36.7%**.
- While the models provide superior central accuracy (WIS 11.54 vs. 15.76 for Seasonal-Naive, representing a 26.8% national error reduction), the negative-binomial dispersion parameter tends to under-estimate tail variance during sudden explosive transmission surges (such as the 2017 and 2023 peaks).
- Field officers must treat the $q_{0.975}$ upper bound as a conservative estimate of worst-case caseloads during sudden epidemic takeoff.
