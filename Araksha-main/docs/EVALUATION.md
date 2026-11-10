# Silent Node: Rolling-Origin Backtest Evaluation Report

Evaluation Window: **2022 to 2024** (spanning the historic 2023 dengue outbreak)
Spatial Coverage: **All 26 reporting units of Sri Lanka**
Operational Delay Buffer: **2-week incomplete reporting exclusion**

## 1. Summary Performance by Horizon

| Model | Horizon | WIS | Median AE | 50% Coverage | 95% Coverage | Exceedance ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Seasonal-Naive | h=1 | 15.28 | 25.09 | 32.9% | 76.5% | 0.713 |
| Seasonal-Naive | h=2 | 15.76 | 25.57 | 32.7% | 72.7% | 0.726 |
| Seasonal-Naive | h=3 | 13.72 | 23.01 | 32.5% | 78.7% | 0.718 |
| Seasonal-Naive | h=4 | 16.99 | 26.12 | 33.1% | 75.0% | 0.655 |
| Last-Value | h=1 | 18.08 | 30.17 | 33.5% | 74.8% | 0.572 |
| Last-Value | h=2 | 18.16 | 29.66 | 38.5% | 76.0% | 0.501 |
| Last-Value | h=3 | 16.24 | 26.69 | 41.7% | 82.7% | 0.459 |
| Last-Value | h=4 | 18.72 | 29.71 | 40.8% | 81.2% | 0.478 |
| Seasonal-AR | h=1 | 11.84 | 19.37 | 41.7% | 82.3% | 0.769 |
| Seasonal-AR | h=2 | 14.30 | 22.17 | 31.9% | 75.6% | 0.613 |
| Seasonal-AR | h=3 | 13.06 | 20.76 | 35.4% | 78.7% | 0.657 |
| Seasonal-AR | h=4 | 16.48 | 24.73 | 30.6% | 75.2% | 0.618 |
| NB-GAM | h=1 | 8.54 | 14.84 | 41.3% | 85.4% | 0.906 |
| NB-GAM | h=2 | 10.86 | 16.80 | 40.8% | 78.7% | 0.774 |
| NB-GAM | h=3 | 11.29 | 17.58 | 40.0% | 79.8% | 0.760 |
| NB-GAM | h=4 | 14.66 | 21.45 | 38.5% | 77.9% | 0.690 |
| Ensemble | h=1 | 9.09 | 16.27 | 42.1% | 85.4% | 0.870 |
| Ensemble | h=2 | 11.54 | 18.76 | 36.7% | 77.9% | 0.745 |
| Ensemble | h=3 | 11.21 | 17.80 | 37.1% | 81.2% | 0.701 |
| Ensemble | h=4 | 14.66 | 21.64 | 34.4% | 78.5% | 0.659 |

> **Interval Dispersion Limitation**: Nominal 95% interval coverage reaches 77.9% at the 2-week operational horizon ($h=2$), remaining below the 80% threshold across horizons $h=2, 3, 4$ (and nominal 50% coverage reaches 36.7%). The probabilistic intervals are under-dispersed during explosive epidemic surges where variance expands non-linearly. This under-dispersion is explicitly recognized as an operational limitation; field officers should interpret interval bounds as lower bounds on uncertainty during rapid epidemic growth phases.

## 2. District-Level Results (2-Week Horizon h=2)

| District | Seasonal-Naive WIS | Seasonal-AR WIS | NB-GAM WIS | Ensemble WIS | Ensemble ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Colombo | 60.26 | 59.64 | 37.68 | 40.86 | 0.947 |
| Gampaha | 43.88 | 31.76 | 30.56 | 29.70 | 1.000 |
| Kalutara | 23.84 | 18.51 | 18.89 | 17.39 | 0.395 |

## 3. Fallback Rule Decision & Model Selection

> **Operational Selection**: PASS: Ensemble & NB-GAM beat Seasonal-Naive on WIS at 2-week horizon. Operational model: Ensemble (NB-GAM + Boosting).

### Ablation Findings
- **Climate Distributed Lags**: 8-week lagged rainfall and temperature contribute moderate predictive variance reduction in urban Western Province districts (Colombo, Gampaha) where vector breeding cycles directly mirror monsoon onset.
- **Autoregressive Terms**: Accounting for the 2-week reporting lag (anchoring at $t-2$) prevents optimistic bias. The 3-week rolling average stabilizes inter-week reporting fluctuations.
- **Spatial Contiguity**: Queen-neighbour weights provide significant uplift for border districts (Kalmunai-Ampara-Batticaloa corridor and Colombo-Gampaha metro belt).
