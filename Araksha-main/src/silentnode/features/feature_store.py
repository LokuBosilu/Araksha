"""
src/silentnode/features/feature_store.py: Leakage-safe direct multi-horizon feature matrix generator.
Calculates features strictly at forecast origin t for horizons h in {1, 2, 3, 4}.
Target is cases at t+h.
"""

import os
import csv
import json
import math
import sqlite3
from typing import Dict, List, Tuple, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
SQLITE_DB = os.path.join(PROCESSED_DIR, "silentnode.db")
SPATIAL_FILE = os.path.join(PROCESSED_DIR, "spatial_weights.json")
STATIC_FILE = os.path.join(PROCESSED_DIR, "static_covariates.csv")

def get_ordered_calendar(min_year=2014, max_year=2026) -> List[Tuple[int, int]]:
    """Returns chronologically ordered list of (year, epi_week)."""
    cal = []
    for y in range(min_year, max_year + 1):
        # 52 weeks standard, 53 weeks in occasional leap years (e.g., 2015, 2020)
        max_w = 53 if y in (2015, 2020) else 52
        for w in range(1, max_w + 1):
            cal.append((y, w))
    return cal

def build_feature_store(horizons=(1, 2, 3, 4), min_origin_year=2015, max_origin_year=2026, db_path=SQLITE_DB):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load static covariates
    cur.execute("SELECT district_id, district_name, population_2023, log_population, piped_water_pct FROM static_covariates")
    static_rows = cur.fetchall()
    district_static = {r[1]: {
        "district_id": r[0],
        "district_name": r[1],
        "population": r[2],
        "log_population": r[3],
        "piped_water_pct": r[4]
    } for r in static_rows}

    # Load spatial weights
    spatial_weights = {}
    if os.path.exists(SPATIAL_FILE):
        with open(SPATIAL_FILE, "r", encoding="utf-8") as f:
            spatial_weights = json.load(f).get("weights", {})

    # Load cases: key = (district_name, year, epi_week)
    cur.execute("SELECT district_name, year, epi_week, cases FROM cases_weekly")
    cases_dict = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}

    # Load weather: key = (district_name, year, epi_week)
    cur.execute("SELECT district_name, year, epi_week, rainfall_sum_mm, temp_mean_c, humidity_mean_pct FROM weather_weekly")
    weather_dict = {(r[0], r[1], r[2]): (r[3], r[4], r[5]) for r in cur.fetchall()}

    calendar = get_ordered_calendar(2012, 2026)
    cal_index = {yw: idx for idx, yw in enumerate(calendar)}

    # Build features for each horizon h in {1, 2, 3, 4}
    for h in horizons:
        features_list = []
        # Origin t index
        for t_idx, (y_orig, w_orig) in enumerate(calendar):
            if y_orig < min_origin_year or y_orig > max_origin_year:
                continue

            target_idx = t_idx + h
            target_yw = calendar[target_idx] if target_idx < len(calendar) else None

            # Harmonic terms for seasonality at origin week
            w_norm = (w_orig / 52.0) * 2 * math.pi
            sin_1 = math.sin(w_norm)
            cos_1 = math.cos(w_norm)
            sin_2 = math.sin(2 * w_norm)
            cos_2 = math.cos(2 * w_norm)

            # Monsoon flags
            is_sw_monsoon = 1 if 20 <= w_orig <= 39 else 0
            is_ne_monsoon = 1 if (w_orig >= 48 or w_orig <= 8) else 0

            # Reporting delay flag: latest 2 weeks considered provisional
            is_reporting_provisional = 1 if (y_orig == 2026 and w_orig >= 18) else 0

            for d_name, stat in district_static.items():
                d_id = stat["district_id"]

                # Target cases at origin + h
                target_cases = None
                if target_yw:
                    target_cases = cases_dict.get((d_name, target_yw[0], target_yw[1]))

                # 1. Autoregressive lags: t - k for k in 0..5
                # Under the 2-week reporting delay buffer at operational origin,
                # weeks t and t-1 may be marked or lag features anchored to t-2
                ar_lags = []
                for k in range(6):
                    lag_idx = t_idx - k
                    if lag_idx >= 0:
                        yw_k = calendar[lag_idx]
                        c_val = cases_dict.get((d_name, yw_k[0], yw_k[1]), 0)
                    else:
                        c_val = 0
                    ar_lags.append(round(math.log1p(max(0, c_val)), 4))

                ar_rolling_3 = round(sum(ar_lags[:3]) / 3.0, 4)
                ar_rolling_6 = round(sum(ar_lags) / 6.0, 4)

                # 2. Rainfall lags 4..12 + 3-week smoothed rolling windows
                rain_lags = []
                for k in range(4, 13):
                    lag_idx = t_idx - k
                    if lag_idx >= 0:
                        yw_k = calendar[lag_idx]
                        w_tuple = weather_dict.get((d_name, yw_k[0], yw_k[1]))
                        r_val = w_tuple[0] if w_tuple else 15.0
                    else:
                        r_val = 15.0
                    rain_lags.append(r_val)

                # Smoothed 3-week rainfall windows: lags (4-6), (7-9), (10-12)
                rain_smooth_4_6 = round(sum(rain_lags[0:3]) / 3.0, 2)
                rain_smooth_7_9 = round(sum(rain_lags[3:6]) / 3.0, 2)
                rain_smooth_10_12 = round(sum(rain_lags[6:9]) / 3.0, 2)

                # 3. Temperature and humidity lags 8..14 + smoothed
                temp_lags = []
                rh_lags = []
                for k in range(8, 15):
                    lag_idx = t_idx - k
                    if lag_idx >= 0:
                        yw_k = calendar[lag_idx]
                        w_tuple = weather_dict.get((d_name, yw_k[0], yw_k[1]))
                        t_val = w_tuple[1] if w_tuple else 27.5
                        rh_val = w_tuple[2] if w_tuple else 75.0
                    else:
                        t_val, rh_val = 27.5, 75.0
                    temp_lags.append(t_val)
                    rh_lags.append(rh_val)

                temp_smooth_8_11 = round(sum(temp_lags[0:4]) / 4.0, 2)
                temp_smooth_12_14 = round(sum(temp_lags[4:7]) / 3.0, 2)
                rh_smooth_8_11 = round(sum(rh_lags[0:4]) / 4.0, 2)
                rh_smooth_12_14 = round(sum(rh_lags[4:7]) / 3.0, 2)

                # 4. Spatial neighbour-weighted cases at lags 0..3 (Queen weights)
                nbr_weights = spatial_weights.get(d_name, {})
                spatial_lags = []
                for k in range(4):
                    lag_idx = t_idx - k
                    if lag_idx >= 0:
                        yw_k = calendar[lag_idx]
                        weighted_sum = 0.0
                        for nbr_name, weight in nbr_weights.items():
                            nbr_c = cases_dict.get((nbr_name, yw_k[0], yw_k[1]), 0)
                            weighted_sum += weight * nbr_c
                        spatial_lags.append(round(math.log1p(weighted_sum), 4))
                    else:
                        spatial_lags.append(0.0)

                feat = {
                    "district_id": d_id,
                    "district_name": d_name,
                    "origin_year": y_orig,
                    "origin_week": w_orig,
                    "horizon": h,
                    "target_year": target_yw[0] if target_yw else None,
                    "target_week": target_yw[1] if target_yw else None,
                    "target_cases": target_cases,
                    # Exposure offset
                    "log_population": stat["log_population"],
                    # Autoregressive
                    "ar_lag0": ar_lags[0],
                    "ar_lag1": ar_lags[1],
                    "ar_lag2": ar_lags[2],
                    "ar_lag3": ar_lags[3],
                    "ar_lag4": ar_lags[4],
                    "ar_lag5": ar_lags[5],
                    "ar_rolling_3": ar_rolling_3,
                    "ar_rolling_6": ar_rolling_6,
                    # Climate smoothed lags
                    "rain_smooth_4_6": rain_smooth_4_6,
                    "rain_smooth_7_9": rain_smooth_7_9,
                    "rain_smooth_10_12": rain_smooth_10_12,
                    "temp_smooth_8_11": temp_smooth_8_11,
                    "temp_smooth_12_14": temp_smooth_12_14,
                    "rh_smooth_8_11": rh_smooth_8_11,
                    "rh_smooth_12_14": rh_smooth_12_14,
                    # Seasonality
                    "sin_harmonic_1": round(sin_1, 4),
                    "cos_harmonic_1": round(cos_1, 4),
                    "sin_harmonic_2": round(sin_2, 4),
                    "cos_harmonic_2": round(cos_2, 4),
                    "is_sw_monsoon": is_sw_monsoon,
                    "is_ne_monsoon": is_ne_monsoon,
                    # Spatial
                    "spatial_lag0": spatial_lags[0],
                    "spatial_lag1": spatial_lags[1],
                    "spatial_lag2": spatial_lags[2],
                    "spatial_lag3": spatial_lags[3],
                    # Static
                    "piped_water_pct": stat["piped_water_pct"],
                    # Quality
                    "is_reporting_provisional": is_reporting_provisional,
                }
                features_list.append(feat)

        table_name = f"features_h{h}"
        csv_path = os.path.join(PROCESSED_DIR, f"{table_name}.csv")

        # Save to CSV only if writing to primary production DB
        if features_list and db_path == SQLITE_DB:
            fieldnames = list(features_list[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(features_list)
            print(f"Saved {len(features_list)} records for horizon {h} to {csv_path}")

        # Store in SQLite table
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        cols_sql = ", ".join([
            f"{k} REAL" if k not in ("district_id", "district_name", "origin_year", "origin_week", "horizon", "target_year", "target_week", "target_cases", "is_sw_monsoon", "is_ne_monsoon", "is_reporting_provisional")
            else f"{k} INTEGER" if k in ("origin_year", "origin_week", "horizon", "target_year", "target_week", "target_cases", "is_sw_monsoon", "is_ne_monsoon", "is_reporting_provisional")
            else f"{k} TEXT"
            for k in features_list[0].keys()
        ])
        cur.execute(f"CREATE TABLE {table_name} ({cols_sql})")
        placeholders = ", ".join([f":{k}" for k in features_list[0].keys()])
        cur.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", features_list)
        conn.commit()
        print(f"Created SQLite table {table_name}")

    conn.close()

if __name__ == "__main__":
    build_feature_store()
