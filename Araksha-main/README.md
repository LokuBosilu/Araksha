# Silent Node: Sri Lanka Dengue Risk Forecaster

Weekly-updated, 4-week-ahead dengue risk forecasting and field resource allocation system for Sri Lanka's 26 reporting units (25 administrative districts plus the Kalmunai health zone).

Designed for district vector-control officers and Medical Officers of Health (MOH) who plan field interventions 2 to 4 weeks ahead.

> **Disclaimer**: Silent Node is a planning decision-support tool for vector-control teams and public health planners, NOT a clinical diagnostic tool.

---

## Key Pipeline Capabilities

- **26 Reporting Units**: Ingests weekly dengue counts (2006 to 2026) from `denguedatahub` and Sri Lanka Epidemiology Unit bulletins.
- **Leakage-Safe Architecture**: Strict direct multi-horizon design ($h \in \{1, 2, 3, 4\}$ weeks ahead). 2-week reporting delay buffer enforced at every forecast origin.
- **Ensemble Forecasting**: Distributed Lag Negative-Binomial GAM + Calibrated Seasonal-Autoregressive model with non-crossing isotonic quantile projection.
- **Decisive Risk Tiers**: Districts classified into **Low**, **Moderate**, **High**, **Extreme**, and **Insufficient Data** (missing inputs never default to Low).
- **Early Anomaly Detection**: Proactively flags impending outbreaks where projected incidence surges above seasonal baselines before clinical hospital notifications spike.
- **Officer Decision Dashboard**: Interactive choropleth map, 4-week horizon toggle, ranked Vector-Control Allocation Matrix, and one-click CSV export.

---

## Quick Start

### 1. Run Data Ingestion & Build Covariates
```bash
python scripts/ingest_cases.py
python scripts/build_static_covariates.py
python scripts/ingest_weather.py
```

### 2. Run Tests & Validation
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 3. Run Rolling-Origin Backtest
```bash
python scripts/run_backtest.py
```

### 4. Generate Operational Forecast
```bash
# Run latest operational forecast
python scripts/run_forecast.py

# Reproduce historical origin (e.g. May 2017 before the July 2017 peak)
python scripts/run_forecast.py --as-of 2017-05-01
```

### 5. Launch Officer Web Dashboard
```bash
npm run dev
```

---

## Validated Backtest Performance (2022–2024 Window)

At the critical **2-week operational horizon ($h=2$)**, Silent Node was rigorously evaluated across 20 rolling origins spanning the 2023 nationwide dengue surge:

- **Ensemble WIS**: **11.54** vs. Seasonal-Naive **15.76** (**26.8% national error reduction**; Fallback Gate: **PASS**).
- **Metro Cluster Performance**: Colombo Ensemble WIS **40.86** vs 60.26 (**32.2% reduction**, ROC-AUC 0.947); Gampaha Ensemble WIS **29.70** vs 43.88 (**32.3% reduction**, ROC-AUC 1.000).
- **Interval Dispersion Note**: Nominal 95% interval coverage reaches **77.9%** (< 80%), and 50% interquartile coverage reaches **36.7%**. Prediction intervals are under-dispersed during explosive epidemic surges, which is documented as an operational limitation.

---

## Repository Documentation

- [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md): The project brief and 5 core methodological decisions.
- [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md): Comprehensive technical report, feature store design, backtest tables, and limitation notes.
- [`docs/TWO_PAGE_SUMMARY.md`](docs/TWO_PAGE_SUMMARY.md): Executive briefing for district vector-control directors and Medical Officers of Health.
- [`docs/THREE_MINUTE_DEMO_VIDEO_SCRIPT.md`](docs/THREE_MINUTE_DEMO_VIDEO_SCRIPT.md): Complete timed demonstration script for dashboard walkthrough and scenario review.
- [`docs/EVALUATION.md`](docs/EVALUATION.md): Rolling-origin backtest tables, WIS scores, coverage, and fallback rule verification.
- [`docs/DATA.md`](docs/DATA.md): Data sources, licenses, and verified benchmarks.
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md): Limitations, reporting delays, interval under-dispersion, and planning boundaries.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Four pipeline stages with system flow diagram.
- [`docs/DEPLOY.md`](docs/DEPLOY.md): Automation with GitHub Actions and hosting deployment guide.
- [`AGENTS.md`](AGENTS.md): Ground rules for leakage prevention, validation, and zero silent data interpolation.
