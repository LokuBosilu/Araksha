#!/usr/bin/env python3
"""
scripts/ingest_cases.py: Ingest dengue weekly counts for Sri Lanka 26 reporting units.
Source: R package denguedatahub (Talagala), object srilanka_weekly_data.
"""

import os
import sys
import csv
import json
import sqlite3
import datetime
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOOKUP_FILE = os.path.join(PROCESSED_DIR, "district_lookup.csv")
RAW_CSV_FILE = os.path.join(RAW_DIR, "srilanka_weekly_data.csv")
PROCESSED_CSV_FILE = os.path.join(PROCESSED_DIR, "cases_weekly.csv")
SQLITE_DB_FILE = os.path.join(PROCESSED_DIR, "silentnode.db")
INGEST_LOG_FILE = os.path.join(RAW_DIR, "ingest_log.json")

GITHUB_RAW_URL = "https://raw.githubusercontent.com/thiyangt/denguedatahub/master/data-raw/srilanka_weekly_data.csv"

# Alias mapping from raw dataset to canonical district names
RAW_NAME_ALIASES = {
    "kalmune": "Kalmunai",
    "kalmunai": "Kalmunai",
    "hambanthota": "Hambantota",
    "hambantota": "Hambantota",
    "nuwaraeliya": "Nuwara Eliya",
    "nuwara eliya": "Nuwara Eliya",
}

def load_canonical_districts():
    lookup = {}
    if not os.path.exists(LOOKUP_FILE):
        raise FileNotFoundError(f"Missing lookup file at {LOOKUP_FILE}")
    with open(LOOKUP_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_name = row["district_name"].strip()
            lookup[d_name.lower()] = {
                "district_id": row["district_id"].strip(),
                "district_name": d_name,
                "province": row["province"].strip(),
                "is_health_zone": row["is_health_zone"].lower() == "true",
                "pop_2023": int(row["population_2023"]),
            }
    return lookup

def download_raw_data():
    os.makedirs(RAW_DIR, exist_ok=True)
    utc_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"Downloading srilanka_weekly_data from {GITHUB_RAW_URL}...")
    req = urllib.request.Request(GITHUB_RAW_URL, headers={"User-Agent": "SilentNode/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()

    with open(RAW_CSV_FILE, "wb") as f:
        f.write(content)

    log_entry = {
        "url": GITHUB_RAW_URL,
        "timestamp_utc": utc_now,
        "bytes_downloaded": len(content),
        "status": "success",
    }
    logs = []
    if os.path.exists(INGEST_LOG_FILE):
        try:
            with open(INGEST_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(log_entry)
    with open(INGEST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    print(f"Downloaded {len(content)} bytes to {RAW_CSV_FILE} at {utc_now}")

def process_and_standardize():
    if not os.path.exists(RAW_CSV_FILE):
        download_raw_data()

    canonical_map = load_canonical_districts()
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    rows = []
    unmapped_districts = set()
    national_weekly = defaultdict(int)

    with open(RAW_CSV_FILE, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_district = r["district"].strip()
            raw_d_lower = raw_district.lower()

            canonical_name = RAW_NAME_ALIASES.get(raw_d_lower, raw_district)
            lookup_entry = canonical_map.get(canonical_name.lower())

            if not lookup_entry:
                unmapped_districts.add(raw_district)
                continue

            try:
                year = int(r["year"])
                epi_week = int(r["week"])
            except ValueError:
                continue

            cases_str = r.get("cases", "").strip()
            if cases_str == "" or cases_str.upper() == "NA":
                cases = 0
            else:
                try:
                    cases = int(float(cases_str))
                except ValueError:
                    cases = 0

            # Normalize week start date
            start_date_str = r.get("start.date", "").strip()
            norm_date = ""
            if start_date_str:
                parts = start_date_str.split("/")
                if len(parts) == 3:
                    m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                    norm_date = f"{y:04d}-{m:02d}-{d:02d}"

            rows.append({
                "district_id": lookup_entry["district_id"],
                "district_name": lookup_entry["district_name"],
                "year": year,
                "epi_week": epi_week,
                "week_start_date": norm_date,
                "cases": cases,
            })
            national_weekly[(year, epi_week)] += cases

    if unmapped_districts:
        print(f"WARNING: Found unmapped raw districts: {unmapped_districts}")

    # Sort deterministically: year, epi_week, district_name
    rows.sort(key=lambda x: (x["year"], x["epi_week"], x["district_name"]))

    # Validation Checks
    district_set = set(r["district_name"] for r in rows)
    print(f"Validation: {len(district_set)} / 26 units present in parsed data.")
    assert len(district_set) == 26, f"Expected 26 units, found {len(district_set)}"

    seen_keys = set()
    duplicates = []
    negatives = []
    for r in rows:
        key = (r["district_id"], r["year"], r["epi_week"])
        if key in seen_keys:
            duplicates.append(key)
        seen_keys.add(key)
        if r["cases"] < 0:
            negatives.append((key, r["cases"]))

    print(f"Validation: Duplicates found: {len(duplicates)}")
    print(f"Validation: Negative counts found: {len(negatives)}")
    assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate keys"
    assert len(negatives) == 0, f"Found {len(negatives)} negative counts"

    # Save to CSV
    fieldnames = ["district_id", "district_name", "year", "epi_week", "week_start_date", "cases"]
    with open(PROCESSED_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} standardized records to {PROCESSED_CSV_FILE}")

    # Store in SQLite
    conn = sqlite3.connect(SQLITE_DB_FILE)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS cases_weekly")
    c.execute("""
        CREATE TABLE cases_weekly (
            district_id TEXT,
            district_name TEXT,
            year INTEGER,
            epi_week INTEGER,
            week_start_date TEXT,
            cases INTEGER,
            PRIMARY KEY (district_id, year, epi_week)
        )
    """)
    c.executemany("""
        INSERT INTO cases_weekly (district_id, district_name, year, epi_week, week_start_date, cases)
        VALUES (:district_id, :district_name, :year, :epi_week, :week_start_date, :cases)
    """, rows)
    conn.commit()
    conn.close()
    print(f"Stored records in SQLite at {SQLITE_DB_FILE}")

    # Peak confirmation: July 2017 peak (~10,590 cases/week)
    peak_2017_w29 = national_weekly.get((2017, 29), 0)
    print(f"Confirmation: National weekly total for 2017-W29 is {peak_2017_w29} cases/week.")
    print("July 2017 epidemic peak confirmation:", "PASS" if peak_2017_w29 == 10590 else f"NOTE: {peak_2017_w29}")

if __name__ == "__main__":
    process_and_standardize()
