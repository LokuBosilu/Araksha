# Project Brief: Silent Node

You are building "Silent Node", a weekly-updated, 4-week-ahead dengue risk
forecasting system for Sri Lanka's 26 reporting units (25 districts plus the
Kalmunai health zone). Users are district vector-control officers / MOH
officers who plan field teams 2 to 4 weeks ahead. It is a planning decision-support tool, NOT a clinical tool.

## BRIEF

- **Cases**: R package denguedatahub (Talagala), object srilanka_weekly_data, weekly district counts, 2006-W52 to 2026-W20.
- **Weather**: Open-Meteo ERA5 archive + 14-day forecast at district centroids; CHIRPS as rainfall fallback.
- **Climate indices**: NOAA ONI and BoM DMI, lagged 3-6 months (tested by ablation only).
- **Static**: OCHA COD-PS 2023 population (exposure offset, incidence per 100k), CPH-2024 piped-water share, OCHA COD-AB boundaries for queen-contiguity weights.
- **Models**: negative-binomial GAM per district with distributed lags + LightGBM ensemble. AR terms 1-6 weeks, precipitation lags 4-12 weeks, temperature/humidity lags 8-14 weeks, harmonic seasonality, neighbour-weighted cases at 1-4 week lags.
- **Outputs per district**: 1-4 week predictive distribution, 50%/95% intervals, probability of exceeding that district's historical 95th-percentile weekly threshold, risk tier (Low/Moderate/High/Extreme), or 'Insufficient Data'.
- **Evaluation**: rolling-origin backtest 2022-2026, WIS and ROC-AUC, against seasonal-naive, last-value and autoregressive baselines.
- **Fallback rule**: if climate models do not beat seasonal-naive on WIS at the 2-week horizon, ship the calibrated seasonal-autoregressive model.
- **Stack**: Python (pandas, statsmodels, scikit-learn, LightGBM), DuckDB, GeoPandas, Streamlit, GitHub Actions.

## My Decisions (Resolved Baseline)

1. **Kalmunai Health Zone Mapping**:
   - Kalmunai is maintained as its own distinct epidemiological time series (the 26th reporting unit) matching Sri Lanka Epidemiology Unit and `denguedatahub` standards.
   - For weather and climate coordinates, Kalmunai maps to its coastal administrative center (7.416° N, 81.825° E) distinct from Ampara town inland (7.291° N, 81.672° E).
   - Population is split based on Regional Directorate of Health Services (RDHS) divisions: Ampara RDHS accounts for ~335,000, and Kalmunai RDHS accounts for ~415,000 of the district's ~750,000 total.
   - For Queen-contiguity spatial weights, Kalmunai shares borders with Ampara (inland), Batticaloa (north), and Monaragala (southwest).

2. **GAM Tooling & Inference Pipeline**:
   - Python-first implementation utilizing statsmodels GLM (NegativeBinomial family with log link) and B-spline bases for harmonic seasonality and smoothed distributed climate lags.
   - Standalone fallback estimation using maximum likelihood negative binomial dispersion estimation ensuring zero R dependency for production deployments and cross-platform reproducibility.

3. **Evaluation Test Window**:
   - Rolling origin backtest explicitly spans 2022-W01 to 2026-W20, covering both inter-epidemic periods and the significant 2023 nationwide dengue surge.
   - Training history strictly precedes each forecast origin $t$, withholding the most recent 2 weeks as incomplete reporting buffer.

4. **Risk-Tier Cutoffs**:
   - Calibrated via rolling-origin backtest hit rates:
     - **Low**: Exceedance probability $P(Y_{t+h} > Q_{95}) < 0.15$ and projected weekly incidence $< 10$ per 100k.
     - **Moderate**: $0.15 \le P(Y_{t+h} > Q_{95}) < 0.50$ or projected weekly incidence $10 - 25$ per 100k.
     - **High**: $0.50 \le P(Y_{t+h} > Q_{95}) < 0.80$ or projected weekly incidence $25 - 50$ per 100k.
     - **Extreme**: $P(Y_{t+h} > Q_{95}) \ge 0.80$ or projected weekly incidence $\ge 50$ per 100k.
     - **Insufficient Data**: Missing recent case or weather inputs, or non-converged model. Never defaults to Low.

5. **Success Definition & Fallback Trigger**:
   - **Pass Rule**: The distributed lag / LightGBM ensemble must achieve lower Weighted Interval Score (WIS) than the Seasonal-Naive baseline at the 2-week horizon ($h=2$) across the 2022-2026 backtest.
   - **Fallback Rule**: If the pass criterion is not met, the operational model automatically reverts to the calibrated Seasonal-Autoregressive Negative-Binomial model.
