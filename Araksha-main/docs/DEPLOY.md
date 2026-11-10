# Silent Node: Deployment Guide

This guide details how to deploy Silent Node across hosting environments (Web App / Cloud Run / Streamlit Community Cloud) and configure automated weekly forecasting.

## 1. Automated Weekly Forecasts (GitHub Actions)
The workflow `.github/workflows/weekly_forecast.yml` executes every Monday at 04:00 UTC (matching the release schedule of Sri Lanka Epidemiology Unit bulletins).

### Repository Settings & Secrets
- **No paid API keys or secrets required**: Open-Meteo ERA5, `denguedatahub`, and Sri Lanka Epidemiology Unit data do not require proprietary secrets.
- **GITHUB_TOKEN Permissions**: Set `Settings -> Actions -> General -> Workflow permissions` to `Read and write permissions` if committing outputs back to a data branch.

## 2. Deploying the Officer-Facing Web Dashboard
The web application provides vector-control officers with an interactive choropleth, 4-week horizon selector, ranked allocation matrix, district fan charts, and CSV export.

### Running with Docker / Cloud Run:
```bash
# Build production bundle
npm run build

# Start server
npm run dev
```

### Deploying to Streamlit Community Cloud (Python alternative):
1. Push repository to GitHub.
2. Sign in to [share.streamlit.io](https://share.streamlit.io).
3. Select repository and set **Main file path** to `src/silentnode/app/streamlit_app.py`.
4. Deploy! It automatically reads from `outputs/latest/` without retraining.
