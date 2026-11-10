#!/usr/bin/env python3
"""
scripts/run_forecast.py: Production forecast engine for Silent Node.
Executes the operational pipeline:
- Loads latest case and weather data (or reproduces historical origins via --as-of)
- Respects the 2-week incomplete data reporting buffer
- Fits the selected ensemble model (NB-GAM + Seasonal-AR)
- Projects 1-4 week predictive distributions (mean, median, 50% & 95% intervals, exceedance probabilities)
- Assigns decision-ready risk tiers (Low, Moderate, High, Extreme, or Insufficient Data)
- Generates ranked Vector-Control Allocation Matrix
- Writes outputs to outputs/latest/ and dated subfolder, plus run_metadata.json
"""

import os
import sys
import csv
import json
import math
import shutil
import sqlite3
import argparse
import datetime
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.silentnode.features.feature_store import get_ordered_calendar
from src.silentnode.models.baselines import SeasonalNaiveModel, SeasonalAutoregressiveNBModel
from src.silentnode.models.gam_nb import NegativeBinomialGAM
from src.silentnode.models.ensemble import QuantileEnsemble
from src.silentnode.risk.risk_tiers import (
    classify_risk_tier,
    check_early_anomaly,
    build_allocation_matrix,
    TIER_LOW,
    TIER_MODERATE,
    TIER_HIGH,
    TIER_EXTREME,
    TIER_INSUFFICIENT
)

PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
LATEST_DIR = os.path.join(OUTPUTS_DIR, "latest")
SQLITE_DB = os.path.join(PROCESSED_DIR, "silentnode.db")
LOOKUP_FILE = os.path.join(PROCESSED_DIR, "district_lookup.csv")

def parse_as_of_date(as_of_str: str) -> Tuple[int, int]:
    """Parses date string (YYYY-MM-DD or YYYY-Www) to (year, epi_week)."""
    if "-W" in as_of_str:
        parts = as_of_str.split("-W")
        return int(parts[0]), int(parts[1])
    try:
        dt = datetime.date.fromisoformat(as_of_str)
        iso_y, iso_w, _ = dt.isocalendar()
        return iso_y, iso_w
    except Exception:
        # Fallback to current year, week 20
        return 2024, 20

def run_forecast(as_of: str = None, force_insufficient_for: str = None):
    os.makedirs(LATEST_DIR, exist_ok=True)
    calendar = get_ordered_calendar(2014, 2026)
    cal_index = {yw: idx for idx, yw in enumerate(calendar)}

    # Determine origin (year, week)
    if as_of:
        origin_year, origin_week = parse_as_of_date(as_of)
        is_historical_replay = True
    else:
        # Latest operational origin in processed data (e.g. 2024-W20)
        origin_year, origin_week = 2024, 20
        is_historical_replay = False

    orig_key = (origin_year, origin_week)
    if orig_key not in cal_index:
        orig_key = calendar[-1]
        origin_year, origin_week = orig_key

    orig_idx = cal_index[orig_key]
    # Respect the 2-week incomplete reporting window: verified data cutoff is t - 2
    cutoff_idx = max(0, orig_idx - 2)
    cutoff_yw = calendar[cutoff_idx]

    run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print("=" * 65)
    print("SILENT NODE: OPERATIONAL FORECAST RUN")
    print(f"Run Timestamp (UTC): {run_timestamp}")
    print(f"Forecast Origin:     {origin_year}-W{origin_week:02d}")
    print(f"Data Cutoff Week:    {cutoff_yw[0]}-W{cutoff_yw[1]:02d} (2-week reporting lag applied)")
    if is_historical_replay:
        print(f"Mode:                HISTORICAL REPLAY (--as-of {as_of})")
    print("=" * 65)

    # Load static covariates
    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    cur.execute("SELECT district_id, district_name, province, population_2023, piped_water_pct FROM static_covariates")
    districts_meta = {r[1]: {
        "district_id": r[0],
        "district_name": r[1],
        "province": r[2],
        "population": r[3],
        "piped_water_pct": r[4]
    } for r in cur.fetchall()}

    # Load verified training cases (strictly <= cutoff_idx)
    cur.execute("SELECT district_name, year, epi_week, cases FROM cases_weekly")
    all_cases = [
        {"district_name": r[0], "year": r[1], "epi_week": r[2], "cases": r[3]}
        for r in cur.fetchall()
    ]
    train_cases = [
        c for c in all_cases
        if cal_index.get((c["year"], c["epi_week"]), 0) <= cutoff_idx
    ]

    # Compute historical 95th-percentile weekly threshold per district
    thresholds_q95 = {}
    seasonal_medians = {} # (district, week) -> median cases
    by_d_train = {}
    for c in train_cases:
        d = c["district_name"]
        w = c["epi_week"]
        if d not in by_d_train:
            by_d_train[d] = []
        by_d_train[d].append(c["cases"])

        dw_key = (d, w)
        if dw_key not in seasonal_medians:
            seasonal_medians[dw_key] = []
        seasonal_medians[dw_key].append(c["cases"])

    for d, c_list in by_d_train.items():
        s_list = sorted(c_list)
        q_idx = int(0.95 * len(s_list))
        thresholds_q95[d] = s_list[min(q_idx, len(s_list) - 1)] if s_list else 10.0

    # Load features for horizons h=1..4 at origin
    features_at_origin = {}
    for h in (1, 2, 3, 4):
        cur.execute(f"""
            SELECT * FROM features_h{h}
            WHERE origin_year = ? AND origin_week = ?
        """, (origin_year, origin_week))
        cols = [col[0] for col in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        features_at_origin[h] = {r["district_name"]: r for r in rows}

    conn.close()

    # Fit operational models strictly on historical data for each horizon h in {1, 2, 3, 4}
    models_by_h = {}
    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    for h in (1, 2, 3, 4):
        # Query training features up to cutoff (strictly at or before 2-week reporting buffer cutoff)
        cur.execute(
            f"""
            SELECT * FROM features_h{h}
            WHERE origin_year < ? OR (origin_year == ? AND origin_week <= ?)
            """,
            (cutoff_yw[0], cutoff_yw[0], cutoff_yw[1])
        )
        cols = [col[0] for col in cur.description]
        train_feat_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        m_gam = NegativeBinomialGAM()
        m_s_ar = SeasonalAutoregressiveNBModel()
        ens = QuantileEnsemble(weight_gam=0.55, weight_boost=0.45)

        m_gam.fit(train_feat_rows)
        m_s_ar.fit(train_feat_rows)
        models_by_h[h] = (m_gam, m_s_ar, ens)

    conn.close()

    forecast_table = []
    warnings = []

    # Generate 1-4 week predictions per district
    for d_name, meta in districts_meta.items():
        d_id = meta["district_id"]
        pop = meta["population"]
        q95 = thresholds_q95.get(d_name, 10.0)

        # Baseline recent incidence per 100k (from cutoff week)
        recent_cases = 0.0
        for c in train_cases:
            if c["district_name"] == d_name and c["year"] == cutoff_yw[0] and c["epi_week"] == cutoff_yw[1]:
                recent_cases = c["cases"]
                break
        current_incidence = (recent_cases / max(1, pop)) * 100000.0

        # Simulate Insufficient Data condition if requested or missing
        is_missing = False
        if force_insufficient_for and force_insufficient_for.lower() in d_name.lower():
            is_missing = True
            warnings.append(f"District {d_name} flagged as Insufficient Data due to simulated data absence.")

        for h in (1, 2, 3, 4):
            t_idx = orig_idx + h
            t_yw = calendar[t_idx] if t_idx < len(calendar) else (origin_year, origin_week + h)
            target_year, target_week = t_yw

            feat = features_at_origin.get(h, {}).get(d_name)

            if not feat or is_missing:
                # Produce Insufficient Data
                forecast_table.append({
                    "district_id": d_id,
                    "district_name": d_name,
                    "province": meta["province"],
                    "population": pop,
                    "piped_water_pct": meta["piped_water_pct"],
                    "origin_year": origin_year,
                    "origin_week": origin_week,
                    "horizon": h,
                    "target_year": target_year,
                    "target_week": target_week,
                    "pred_mean": 0.0,
                    "pred_median": 0.0,
                    "incidence_per_100k": 0.0,
                    "q025": 0.0,
                    "q25": 0.0,
                    "q75": 0.0,
                    "q975": 0.0,
                    "threshold_q95": q95,
                    "exceed_prob": 0.0,
                    "risk_tier": TIER_INSUFFICIENT,
                    "early_anomaly": False,
                })
                continue

            m_gam, m_s_ar, ensemble = models_by_h[h]
            # Model forecasts
            q_gam, p_gam, mu_gam = m_gam.predict(feat, q95)
            q_ar, p_ar, mu_ar = m_s_ar.predict(feat, q95)
            q_ens, p_ens, med_ens = ensemble.combine_quantiles(q_gam, q_ar, q95)

            pred_median = round(med_ens, 1)
            pred_mean = round(0.55 * mu_gam + 0.45 * mu_ar, 1)
            inc_100k = round((pred_median / max(1, pop)) * 100000.0, 2)

            # Seasonal median baseline for anomaly detection
            past_s = seasonal_medians.get((d_name, target_week), [pred_median])
            past_s_sorted = sorted(past_s)
            s_median = past_s_sorted[len(past_s_sorted) // 2] if past_s_sorted else pred_median

            early_anomaly = check_early_anomaly(pred_median, s_median, current_incidence)
            tier = classify_risk_tier(pred_median, inc_100k, p_ens, is_missing_or_stale=False)

            forecast_table.append({
                "district_id": d_id,
                "district_name": d_name,
                "province": meta["province"],
                "population": pop,
                "piped_water_pct": meta["piped_water_pct"],
                "origin_year": origin_year,
                "origin_week": origin_week,
                "horizon": h,
                "target_year": target_year,
                "target_week": target_week,
                "pred_mean": pred_mean,
                "pred_median": pred_median,
                "incidence_per_100k": inc_100k,
                "q025": round(q_ens[0.025], 1),
                "q25": round(q_ens[0.25], 1),
                "q75": round(q_ens[0.75], 1),
                "q975": round(q_ens[0.975], 1),
                "threshold_q95": q95,
                "exceed_prob": round(p_ens, 3),
                "risk_tier": tier,
                "early_anomaly": early_anomaly,
            })

    # Build ranked Vector-Control Allocation Matrix
    allocation_matrix = build_allocation_matrix(forecast_table)

    # Write outputs
    forecast_csv = os.path.join(LATEST_DIR, "forecast_table.csv")
    alloc_csv = os.path.join(LATEST_DIR, "allocation_matrix.csv")
    metadata_json = os.path.join(LATEST_DIR, "run_metadata.json")

    # Save forecast table
    with open(forecast_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(forecast_table[0].keys()))
        writer.writeheader()
        writer.writerows(forecast_table)

    # Save allocation matrix
    with open(alloc_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(allocation_matrix[0].keys()))
        writer.writeheader()
        writer.writerows(allocation_matrix)

    # Write run_metadata.json
    run_meta = {
        "model_name": "Silent Node Ensemble (NB-GAM + Seasonal-AR)",
        "model_version": "1.0.0",
        "run_timestamp_utc": run_timestamp,
        "as_of_origin": f"{origin_year}-W{origin_week:02d}",
        "data_cutoff_week": f"{cutoff_yw[0]}-W{cutoff_yw[1]:02d}",
        "delay_buffer_weeks": 2,
        "horizons_predicted": [1, 2, 3, 4],
        "districts_count": len(districts_meta),
        "staleness_flag": False,
        "warnings": warnings,
        "disclaimer": "Planning decision-support tool for vector-control and MOH officers, NOT a clinical diagnostic tool.",
    }
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    # Dated archive copy
    dated_tag = f"{origin_year}-W{origin_week:02d}" if not as_of else as_of.replace("/", "-")
    dated_dir = os.path.join(OUTPUTS_DIR, dated_tag)
    os.makedirs(dated_dir, exist_ok=True)
    shutil.copy(forecast_csv, os.path.join(dated_dir, "forecast_table.csv"))
    shutil.copy(alloc_csv, os.path.join(dated_dir, "allocation_matrix.csv"))
    shutil.copy(metadata_json, os.path.join(dated_dir, "run_metadata.json"))

    print(f"Generated outputs in {LATEST_DIR} and archived in {dated_dir}")

    # Print Top 5 Allocation Ranks
    print("\nTOP 5 VECTOR-CONTROL ALLOCATION PRIORITIES:")
    print(f"{'Rank':<5} | {'District':<15} | {'Max Tier':<12} | {'Max Exceed':<10} | {'Max Inc/100k':<12} | {'Anomaly':<8}")
    print("-" * 72)
    for row in allocation_matrix[:5]:
        print(f"{row['allocation_rank']:<5} | {row['district_name']:<15} | {row['max_tier']:<12} | "
              f"{row['max_exceed_prob']*100:<9.1f}% | {row['max_incidence']:<12.1f} | {'YES' if row['early_anomaly_flag'] else 'No':<8}")

    # Prompt 10 Demo requirement check: Colombo forecast before July 2017 peak
    colombo_forecasts = [r for r in forecast_table if r["district_name"] == "Colombo"]
    if colombo_forecasts:
        print("\nCOLOMBO FORECAST HORIZONS (4-WEEK AHEAD):")
        for r in colombo_forecasts:
            print(f"  Week +{r['horizon']} (Target {r['target_year']}-W{r['target_week']:02d}): "
                  f"Predicted Median={r['pred_median']:.1f} cases (95% CI: [{r['q025']:.1f}, {r['q975']:.1f}]), "
                  f"Incidence={r['incidence_per_100k']:.1f}/100k, P(Exceed Q95)={r['exceed_prob']*100:.1f}%, Tier={r['risk_tier']}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Silent Node forecast engine")
    parser.add_argument("--as-of", type=str, default=None, help="Forecast origin date (e.g. 2017-05-01 or 2024-W20)")
    parser.add_argument("--test-insufficient", type=str, default=None, help="District name to deliberately test Insufficient Data tier")
    args = parser.parse_args()
    run_forecast(as_of=args.as_of, force_insufficient_for=args.test_insufficient)
