# Silent Node Architecture

Silent Node is an operational, 4-week-ahead dengue risk forecasting and field resource allocation system for Sri Lanka's 26 reporting units. It is structured into four sequential, leakage-safe pipeline stages.

```
       [ Stage 1: Ingestion & Validation ]
       - R denguedatahub (srilanka_weekly_data: 2006-2026)
       - Open-Meteo ERA5 Reanalysis & Climatology
       - OCHA COD-PS 2023 Population & CPH-2024 Piped Water
       - Queen-contiguity spatial neighbor structure (26 units)
                         │
                         ▼
       [ Stage 2: Leakage-Safe Feature Store ]
       - Strict direct multi-horizon design (h = 1, 2, 3, 4)
       - Autoregressive lags at t-2..t-5 (2-week reporting delay buffer)
       - Distributed rainfall lags (4-12 weeks) & temperature/humidity
       - Harmonic seasonality & SW/NE monsoon phase flags
       - Queen-neighbor spatial autoregression
                         │
                         ▼
       [ Stage 3: Ensemble Forecasting & Evaluation ]
       - Rolling-origin backtest 2022-2024 (WIS, Coverage, ROC-AUC)
       - Baseline: Seasonal-Naive, Last-Value, Seasonal-AR
       - Negative-Binomial GAM per district with spline terms
       - Quantile Ensemble with isotonic non-crossing projection
       - Fallback Gate: Reverts to Seasonal-AR if climate models fail
                         │
                         ▼
       [ Stage 4: Decision-Support & Allocation Engine ]
       - Risk tier classification: Low, Moderate, High, Extreme
       - 'Insufficient Data' fail-safe (never defaults to Low)
       - Early anomaly detection (predicted surge before hospital visibility)
       - Vector-Control Allocation Matrix (1-4 week operational rankings)
       - Interactive Officer Dashboard & CSV Export
```

## Stage 1: Ingestion & Spatial Structure
- **Epidemiological Surveillance**: Ingests weekly district counts from `denguedatahub` (26,311 records spanning 2006-W52 to 2026-W20). Validates 26 reporting units, zero negative cases, and verifies the July 2017 national peak at exactly 10,590 cases/week.
- **Weather Climatology**: Centroid coordinates for all 26 units with ERA5 daily temperature, rainfall, and relative humidity aggregated to ISO epidemiological weeks.
- **Static Covariates**: OCHA COD-PS 2023 district populations (exposure offset) and CPH-2024 piped-water access share (national 41.4% / Colombo 84.4%).
- **Spatial Topology**: Row-standardized Queen contiguity weight matrix covering all 26 units, with Kalmunai connected to Ampara, Batticaloa, and Monaragala.

## Stage 2: Leakage-Safe Feature Store
- Every feature for forecast origin $t$ is computed **strictly from data available at $t$**.
- Applies a **2-week operational reporting delay buffer**: recent cases at $t$ and $t-1$ are treated as incomplete; autoregressive features are anchored to $t-2$.
- Leakage invariance assertion passes: perturbing future data ($> t$) produces zero change in origin features.

## Stage 3: Models & Rolling Backtest
- Evaluates models on rolling origins from 2022 to 2024 against Weighted Interval Score (WIS) across 11 quantile levels.
- **Fallback Rule**: If the multi-horizon climate ensemble does not beat Seasonal-Naive on WIS at horizon $h=2$, the operational model automatically reverts to the Calibrated Seasonal-Autoregressive model.
- Non-crossing quantile projection prevents crossed prediction bands.

## Stage 4: Risk Tiers & Allocation Matrix
- Computes exceedance probability $P(Y_{t+h} > Q_{95}^{\text{train}})$ against historical 95th-percentile thresholds.
- Classifies districts into Low, Moderate, High, Extreme, or Insufficient Data.
- Early anomaly flag signals when a district's forecast is $\ge 2.0\times$ seasonal baseline while current incidence is $< 15$ per 100k.
- Vector-Control Allocation Matrix ranks districts by risk score to guide MOH field team deployment 2 to 4 weeks ahead.
