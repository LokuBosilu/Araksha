#!/usr/bin/env python3
"""
scripts/build_static_covariates.py: Generates district centroids, static covariates,
and row-standardized Queen-contiguity spatial weights for Sri Lanka's 26 reporting units.
"""

import os
import csv
import json
import math
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOOKUP_FILE = os.path.join(PROCESSED_DIR, "district_lookup.csv")
CENTROIDS_FILE = os.path.join(PROCESSED_DIR, "district_centroids.csv")
STATIC_FILE = os.path.join(PROCESSED_DIR, "static_covariates.csv")
SPATIAL_FILE = os.path.join(PROCESSED_DIR, "spatial_weights.json")
SQLITE_DB_FILE = os.path.join(PROCESSED_DIR, "silentnode.db")

# Queen-contiguity neighbor topology for Sri Lanka's 26 reporting units
# (25 administrative districts + Kalmunai health zone)
QUEEN_NEIGHBORS = {
    "Colombo": ["Gampaha", "Kalutara", "Kegalle"],
    "Gampaha": ["Colombo", "Kalutara", "Kegalle", "Kurunegala", "Puttalam"],
    "Kalutara": ["Colombo", "Kegalle", "Ratnapura", "Galle"],
    "Kandy": ["Matale", "Kurunegala", "Kegalle", "Nuwara Eliya", "Badulla", "Ampara"],
    "Matale": ["Anuradhapura", "Polonnaruwa", "Badulla", "Kandy", "Kurunegala"],
    "Nuwara Eliya": ["Kandy", "Kegalle", "Ratnapura", "Badulla"],
    "Galle": ["Kalutara", "Ratnapura", "Matara"],
    "Matara": ["Galle", "Ratnapura", "Hambantota"],
    "Hambantota": ["Matara", "Ratnapura", "Monaragala", "Ampara"],
    "Jaffna": ["Kilinochchi"],
    "Kilinochchi": ["Jaffna", "Mullaitivu", "Mannar"],
    "Mannar": ["Kilinochchi", "Mullaitivu", "Vavuniya", "Anuradhapura", "Puttalam"],
    "Vavuniya": ["Mannar", "Mullaitivu", "Anuradhapura"],
    "Mullaitivu": ["Kilinochchi", "Mannar", "Vavuniya", "Trincomalee"],
    "Batticaloa": ["Polonnaruwa", "Ampara", "Kalmunai", "Trincomalee"],
    "Ampara": ["Batticaloa", "Kalmunai", "Monaragala", "Badulla", "Kandy"],
    "Kalmunai": ["Ampara", "Batticaloa", "Monaragala"],
    "Trincomalee": ["Mullaitivu", "Anuradhapura", "Polonnaruwa", "Batticaloa"],
    "Kurunegala": ["Puttalam", "Anuradhapura", "Matale", "Kandy", "Kegalle", "Gampaha"],
    "Puttalam": ["Mannar", "Anuradhapura", "Kurunegala", "Gampaha"],
    "Anuradhapura": ["Mannar", "Vavuniya", "Trincomalee", "Polonnaruwa", "Matale", "Kurunegala", "Puttalam"],
    "Polonnaruwa": ["Anuradhapura", "Trincomalee", "Batticaloa", "Ampara", "Badulla", "Matale"],
    "Badulla": ["Polonnaruwa", "Ampara", "Monaragala", "Nuwara Eliya", "Kandy", "Matale", "Ratnapura"],
    "Monaragala": ["Badulla", "Ampara", "Kalmunai", "Hambantota", "Ratnapura"],
    "Ratnapura": ["Kegalle", "Nuwara Eliya", "Badulla", "Monaragala", "Hambantota", "Matara", "Galle", "Kalutara"],
    "Kegalle": ["Kurunegala", "Kandy", "Nuwara Eliya", "Ratnapura", "Colombo", "Gampaha"],
}

def build_covariates_and_weights():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    districts = []
    with open(LOOKUP_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            districts.append(r)

    # 1. District Centroids CSV
    with open(CENTROIDS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["district_id", "district_name", "lat", "lon"])
        writer.writeheader()
        for d in districts:
            writer.writerow({
                "district_id": d["district_id"],
                "district_name": d["district_name"],
                "lat": d["lat"],
                "lon": d["lon"],
            })
    print(f"Generated {CENTROIDS_FILE}")

    # 2. Static Covariates CSV
    static_rows = []
    total_pop = 0
    weighted_water = 0
    for d in districts:
        name = d["district_name"]
        pop = int(d["population_2023"])
        water_pct = float(d["piped_water_pct"])
        nbrs = QUEEN_NEIGHBORS.get(name, [])
        log_pop = round(math.log(pop), 4)

        total_pop += pop
        weighted_water += pop * (water_pct / 100.0)

        static_rows.append({
            "district_id": d["district_id"],
            "district_name": name,
            "province": d["province"],
            "is_health_zone": d["is_health_zone"],
            "parent_district": d.get("parent_district", ""),
            "population_2023": pop,
            "log_population": log_pop,
            "piped_water_pct": water_pct,
            "num_neighbours": len(nbrs),
        })

    national_piped_share = (weighted_water / total_pop) * 100.0
    colombo_piped = next(r["piped_water_pct"] for r in static_rows if r["district_name"] == "Colombo")

    print(f"National average piped-water share: {national_piped_share:.1f}% (Expected ~38.9%)")
    print(f"Colombo piped-water share: {colombo_piped:.1f}% (Expected ~84.4%)")

    with open(STATIC_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(static_rows[0].keys()))
        writer.writeheader()
        writer.writerows(static_rows)
    print(f"Generated {STATIC_FILE}")

    # 3. Spatial Weights Matrix (Row-Standardized Queen Contiguity)
    name_to_id = {d["district_name"]: d["district_id"] for d in districts}
    all_names = [d["district_name"] for d in districts]
    weights_matrix = {}
    islands = []

    for name in all_names:
        nbrs = QUEEN_NEIGHBORS.get(name, [])
        if not nbrs:
            islands.append(name)
            weights_matrix[name] = {}
        else:
            w_val = round(1.0 / len(nbrs), 6)
            weights_matrix[name] = {nbr: w_val for nbr in nbrs}

    print(f"Island check: Found {len(islands)} isolated units without neighbours.")
    if islands:
        print(f"Isolated units: {islands}")

    spatial_data = {
        "metadata": {
            "type": "Queen-contiguity row-standardized",
            "units_count": len(all_names),
            "kalmunai_handled": True,
            "islands": islands,
        },
        "district_names": all_names,
        "weights": weights_matrix,
    }

    with open(SPATIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(spatial_data, f, indent=2)
    print(f"Generated {SPATIAL_FILE}")

    # Save to SQLite
    conn = sqlite3.connect(SQLITE_DB_FILE)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS static_covariates")
    c.execute("""
        CREATE TABLE static_covariates (
            district_id TEXT PRIMARY KEY,
            district_name TEXT,
            province TEXT,
            is_health_zone INTEGER,
            parent_district TEXT,
            population_2023 INTEGER,
            log_population REAL,
            piped_water_pct REAL,
            num_neighbours INTEGER
        )
    """)
    for r in static_rows:
        c.execute("""
            INSERT INTO static_covariates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["district_id"],
            r["district_name"],
            r["province"],
            1 if str(r["is_health_zone"]).lower() == "true" else 0,
            r["parent_district"],
            r["population_2023"],
            r["log_population"],
            r["piped_water_pct"],
            r["num_neighbours"]
        ))
    conn.commit()
    conn.close()
    print("Stored static covariates in SQLite.")

if __name__ == "__main__":
    build_covariates_and_weights()
