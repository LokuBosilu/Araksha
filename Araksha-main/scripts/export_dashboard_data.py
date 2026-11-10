#!/usr/bin/env python3
"""
scripts/export_dashboard_data.py: Exports model output CSVs into src/data/forecast_data.json
for consumption by the React + Vite dashboard.

Executes three scenario runs:
  1. latest_2024: Default operational run (2024-W20 origin)
  2. replay_2017_outbreak: Historical replay (--as-of 2017-05-01)
  3. stale_data_failsafe: Data interruption test (--test-insufficient Kalmunai)

Snapshots outputs/latest into temporary directories, builds the consolidated JSON
matching the exact schema of src/data/forecast_data.json, and restores outputs/latest
to the 2024-W20 operational run.
"""

import os
import sys
import csv
import json
import shutil
import tempfile
import subprocess
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
LATEST_DIR = os.path.join(OUTPUTS_DIR, "latest")
CASES_CSV = os.path.join(BASE_DIR, "data", "processed", "cases_weekly.csv")
TARGET_JSON = os.path.join(BASE_DIR, "src", "data", "forecast_data.json")

def parse_forecast_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Parses forecast_table.csv into typed record dicts."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            early_anom = row["early_anomaly"]
            if isinstance(early_anom, str):
                early_anom_bool = early_anom.lower() in ("true", "1", "yes")
            else:
                early_anom_bool = bool(early_anom)

            records.append({
                "district_id": row["district_id"],
                "district_name": row["district_name"],
                "province": row["province"],
                "population": int(float(row["population"])),
                "piped_water_pct": float(row["piped_water_pct"]),
                "origin_year": int(row["origin_year"]),
                "origin_week": int(row["origin_week"]),
                "horizon": int(row["horizon"]),
                "target_year": int(row["target_year"]),
                "target_week": int(row["target_week"]),
                "pred_mean": float(row["pred_mean"]),
                "pred_median": float(row["pred_median"]),
                "incidence_per_100k": float(row["incidence_per_100k"]),
                "q025": float(row["q025"]),
                "q25": float(row["q25"]),
                "q75": float(row["q75"]),
                "q975": float(row["q975"]),
                "threshold_q95": float(row["threshold_q95"]),
                "exceed_prob": float(row["exceed_prob"]),
                "risk_tier": row["risk_tier"],
                "early_anomaly": early_anom_bool,
            })
    return records

def parse_allocation_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Parses allocation_matrix.csv into typed record dicts."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            early_anom = row["early_anomaly_flag"]
            if isinstance(early_anom, str):
                early_anom_bool = early_anom.lower() in ("true", "1", "yes")
            else:
                early_anom_bool = bool(early_anom)

            insufficient = row["insufficient_data"]
            if isinstance(insufficient, str):
                insufficient_bool = insufficient.lower() in ("true", "1", "yes")
            else:
                insufficient_bool = bool(insufficient)

            records.append({
                "district_id": row["district_id"],
                "district_name": row["district_name"],
                "province": row["province"],
                "population": int(float(row["population"])),
                "piped_water_pct": float(row["piped_water_pct"]),
                "max_tier": row["max_tier"],
                "max_exceed_prob": float(row["max_exceed_prob"]),
                "max_incidence": float(row["max_incidence"]),
                "h1_cases": float(row["h1_cases"]),
                "h2_cases": float(row["h2_cases"]),
                "h3_cases": float(row["h3_cases"]),
                "h4_cases": float(row["h4_cases"]),
                "h1_tier": row["h1_tier"],
                "h2_tier": row["h2_tier"],
                "h3_tier": row["h3_tier"],
                "h4_tier": row["h4_tier"],
                "early_anomaly_flag": early_anom_bool,
                "insufficient_data": insufficient_bool,
                "priority_score": float(row["priority_score"]),
                "allocation_rank": int(row["allocation_rank"]),
            })
    return records

def build_history_by_district(cases_csv_path: str) -> Dict[str, List[Dict[str, int]]]:
    """Builds historical surveillance counts by district for years 2017, 2023, 2024."""
    history: Dict[str, List[Dict[str, int]]] = {}
    with open(cases_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            if year in (2017, 2023, 2024):
                d_name = row["district_name"]
                history.setdefault(d_name, []).append({
                    "year": year,
                    "week": int(row["epi_week"]),
                    "cases": int(float(row["cases"])),
                })
    return history

def export_dashboard_data():
    print("=" * 65)
    print("SILENT NODE: EXPORTING DASHBOARD JSON DATA")
    print("=" * 65)

    # 1. Read existing JSON to inspect schema
    if not os.path.exists(TARGET_JSON):
        raise FileNotFoundError(f"Template JSON not found at {TARGET_JSON}")

    with open(TARGET_JSON, "r", encoding="utf-8") as f:
        old_data = json.load(f)

    scenario_specs = [
        {
            "key": "latest_2024",
            "label": "Latest Operational Forecast (2024-W20 Origin)",
            "description": old_data["scenarios"]["latest_2024"].get(
                "description",
                "Current live operational forecast using 2-week reporting delay buffer (cutoff 2024-W18)."
            ),
            "is_stale": False,
            "cmd": [sys.executable, os.path.join(BASE_DIR, "scripts", "run_forecast.py")],
        },
        {
            "key": "replay_2017_outbreak",
            "label": "Historical Replay: May 1, 2017 (--as-of 2017-05-01)",
            "description": old_data["scenarios"]["replay_2017_outbreak"].get(
                "description",
                "Replays the system origin at 2017-W18 before the historic July 2017 national peak (10,590 cases/week). Notice Colombo escalates to Extreme."
            ),
            "is_stale": False,
            "cmd": [sys.executable, os.path.join(BASE_DIR, "scripts", "run_forecast.py"), "--as-of", "2017-05-01"],
        },
        {
            "key": "stale_data_failsafe",
            "label": "Fail-Safe Mode: Data Interruption & Staleness Test",
            "description": old_data["scenarios"]["stale_data_failsafe"].get(
                "description",
                "Simulates surveillance bulletin interruption for Kalmunai health zone. Demonstrates Insufficient Data tier and 1.5x uncertainty expansion."
            ),
            "is_stale": True,
            "cmd": [sys.executable, os.path.join(BASE_DIR, "scripts", "run_forecast.py"), "--test-insufficient", "Kalmunai"],
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Run scenarios and snapshot outputs/latest
        for spec in scenario_specs:
            s_key = spec["key"]
            print(f"\nRunning forecast pipeline for scenario: {s_key} ...")
            subprocess.run(spec["cmd"], check=True)

            snap_dir = os.path.join(tmp_dir, s_key)
            os.makedirs(snap_dir, exist_ok=True)
            for fname in ("forecast_table.csv", "allocation_matrix.csv", "run_metadata.json"):
                src_f = os.path.join(LATEST_DIR, fname)
                shutil.copy(src_f, os.path.join(snap_dir, fname))
            print(f"Snapshotted outputs/latest -> {snap_dir}")

        # Restore outputs/latest to 2024-W20 operational run
        latest_snap = os.path.join(tmp_dir, "latest_2024")
        for fname in ("forecast_table.csv", "allocation_matrix.csv", "run_metadata.json"):
            shutil.copy(os.path.join(latest_snap, fname), os.path.join(LATEST_DIR, fname))

        # Confirm restored run
        with open(os.path.join(LATEST_DIR, "run_metadata.json"), "r", encoding="utf-8") as f:
            restored_meta = json.load(f)
        assert restored_meta["as_of_origin"] == "2024-W20", "Failed to restore outputs/latest to 2024-W20!"
        print("\nConfirmed: outputs/latest restored to operational 2024-W20 run.")

        # Build top-level objects from operational run
        with open(os.path.join(latest_snap, "run_metadata.json"), "r", encoding="utf-8") as f:
            top_metadata = json.load(f)
        top_forecasts = parse_forecast_csv(os.path.join(latest_snap, "forecast_table.csv"))
        top_allocation = parse_allocation_csv(os.path.join(latest_snap, "allocation_matrix.csv"))

        # Build history_by_district
        history_by_dist = build_history_by_district(CASES_CSV)

        # Build scenarios
        scenarios_dict = {}
        for spec in scenario_specs:
            s_key = spec["key"]
            s_dir = os.path.join(tmp_dir, s_key)

            with open(os.path.join(s_dir, "run_metadata.json"), "r", encoding="utf-8") as f:
                s_meta_raw = json.load(f)

            template_sc = old_data.get("scenarios", {}).get(s_key, {})
            template_meta = template_sc.get("metadata", {})

            # Format scenario metadata matching template key set
            scenario_meta = {}
            for k in template_meta.keys():
                if k == "staleness_flag":
                    scenario_meta[k] = spec["is_stale"]
                elif k == "data_cutoff_week" and spec["is_stale"]:
                    scenario_meta[k] = template_meta.get("data_cutoff_week", s_meta_raw.get("data_cutoff_week", ""))
                elif k in s_meta_raw:
                    scenario_meta[k] = s_meta_raw[k]
                else:
                    scenario_meta[k] = template_meta[k]

            s_forecasts = parse_forecast_csv(os.path.join(s_dir, "forecast_table.csv"))
            s_allocation = parse_allocation_csv(os.path.join(s_dir, "allocation_matrix.csv"))

            scenarios_dict[s_key] = {
                "label": spec["label"],
                "description": spec["description"],
                "metadata": scenario_meta,
                "forecasts": s_forecasts,
                "allocation": s_allocation,
                "is_stale": spec["is_stale"],
            }

        new_data = {
            "metadata": top_metadata,
            "forecasts": top_forecasts,
            "allocation_matrix": top_allocation,
            "history_by_district": history_by_dist,
            "scenarios": scenarios_dict,
        }

    # Verify key sets match old schema
    print("\nVerifying schema integrity against previous snapshot...")
    assert set(old_data.keys()) == set(new_data.keys()), "Top-level keys mismatch!"
    assert set(old_data["metadata"].keys()) == set(new_data["metadata"].keys()), "metadata keys mismatch!"
    assert set(old_data["scenarios"].keys()) == set(new_data["scenarios"].keys()), "scenarios keys mismatch!"

    for i in range(len(old_data["forecasts"])):
        assert set(old_data["forecasts"][i].keys()) == set(new_data["forecasts"][i].keys()), f"forecasts[{i}] keys mismatch!"

    for i in range(len(old_data["allocation_matrix"])):
        assert set(old_data["allocation_matrix"][i].keys()) == set(new_data["allocation_matrix"][i].keys()), f"allocation_matrix[{i}] keys mismatch!"

    for dk in old_data["history_by_district"]:
        assert dk in new_data["history_by_district"], f"District {dk} missing from history!"
        assert len(old_data["history_by_district"][dk]) == len(new_data["history_by_district"][dk]), f"history length mismatch for {dk}!"

    for sk in old_data["scenarios"]:
        assert set(old_data["scenarios"][sk].keys()) == set(new_data["scenarios"][sk].keys()), f"Scenario {sk} keys mismatch!"
        assert set(old_data["scenarios"][sk]["metadata"].keys()) == set(new_data["scenarios"][sk]["metadata"].keys()), f"Scenario {sk} metadata keys mismatch!"

    # Verify zero rows where q025 == q975 in forecasts
    eq_rows = [r for r in new_data["forecasts"] if r["q025"] == r["q975"]]
    assert len(eq_rows) == 0, f"Found {len(eq_rows)} forecast rows where q025 == q975!"

    # Write target JSON
    with open(TARGET_JSON, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2)

    print(f"\nSuccessfully wrote updated dashboard data to {TARGET_JSON} (size: {os.path.getsize(TARGET_JSON):,} bytes)")
    print("Schema verification: PASS")
    print(f"Zero q025 == q975 verification: PASS (0 rows out of {len(new_data['forecasts'])})")
    print("=" * 65)

if __name__ == "__main__":
    export_dashboard_data()
