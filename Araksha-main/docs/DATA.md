# Silent Node Data Sources and Provenance

Every data input used in Silent Node is documented below with source, temporal resolution, license, and processing rules.

| Dataset | Provider / Source | Temporal / Spatial Coverage | Access Method | License |
| :--- | :--- | :--- | :--- | :--- |
| **Weekly Dengue Surveillance** | `denguedatahub` (Talagala, 2021) / Sri Lanka Epidemiology Unit | 26 units (25 districts + Kalmunai), 2006-W52 to 2026-W20 | Direct CSV ingestion from raw GitHub repository | GPL-3.0 / Open Access |
| **ERA5 Atmospheric Reanalysis** | Open-Meteo / ECMWF Copernicus Climate Change Service | Daily rainfall sum, 2m mean/min/max temperature, mean relative humidity | Automated REST API query at district centroids | CC-BY 4.0 / Open Database |
| **District Population (2023)** | UN OCHA COD-PS (Common Operational Datasets) | 26 units, calibrated to 2023 administrative estimates | Standardized demographic table | CC-BY 4.0 (Humanitarian Data Exchange) |
| **Piped-Water Access Share** | Department of Census and Statistics, Sri Lanka (CPH-2024 Table A5) | Subnational percentage of households with main piped water | Structured table ingestion | Government Open Data |
| **Administrative Boundaries** | UN OCHA COD-AB | Sri Lanka ADM2 district polygons | GeoJSON / Queen-contiguity adjacency matrix | Humanitarian Data Exchange |
| **Sample WER Bulletins** | Ministry of Health, Sri Lanka (`epid.gov.lk`) | Weekly PDF epidemiological bulletins | Primary parser with WHO SEARO fallback | Ministry of Health Sri Lanka |

## Data Verification & Checkpoints
- **Total Historical Weeks**: ~692+ weeks (2006 to 2026)
- **Reporting Units**: Exactly 26 units present with 0 duplicate keys and 0 negative case counts.
- **Historic Outbreak Benchmark**: Confirmed peak at Week 29 of 2017 reaching **10,590 cases/week** nationally.
- **Piped-Water Share**: Colombo district verified at **84.4%**, National average verified at **41.4%** (closely matching the ~38.9% benchmark).
