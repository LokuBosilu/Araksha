"""
tests/test_validation.py: Tests for case dataset validation, 26 reporting units,
continuity, and static covariates integrity.
"""

import os
import csv
import sqlite3
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOOKUP_FILE = os.path.join(PROCESSED_DIR, "district_lookup.csv")
CASES_FILE = os.path.join(PROCESSED_DIR, "cases_weekly.csv")
STATIC_FILE = os.path.join(PROCESSED_DIR, "static_covariates.csv")
SPATIAL_FILE = os.path.join(PROCESSED_DIR, "spatial_weights.json")

class TestValidation(unittest.TestCase):

    def test_26_reporting_units_present(self):
        self.assertTrue(os.path.exists(LOOKUP_FILE), "district_lookup.csv must exist")
        with open(LOOKUP_FILE, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(len(reader), 26, "Must contain exactly 26 reporting units")

        names = [r["district_name"] for r in reader]
        self.assertIn("Kalmunai", names, "Kalmunai health zone must be present")
        self.assertIn("Colombo", names, "Colombo district must be present")
        self.assertIn("Gampaha", names, "Gampaha district must be present")

    def test_cases_non_negative_and_no_duplicates(self):
        self.assertTrue(os.path.exists(CASES_FILE), "cases_weekly.csv must exist")
        seen_keys = set()
        districts_in_cases = set()

        with open(CASES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = (r["district_id"], r["year"], r["epi_week"])
                self.assertNotIn(key, seen_keys, f"Duplicate found: {key}")
                seen_keys.add(key)

                cases = int(r["cases"])
                self.assertGreaterEqual(cases, 0, f"Negative cases found: {r}")
                districts_in_cases.add(r["district_name"])

        self.assertEqual(len(districts_in_cases), 26, "All 26 units must have case records")

    def test_july_2017_peak_confirmation(self):
        """Confirm July 2017 peak reaches approx 10,590 cases/week."""
        tot = 0
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if int(r["year"]) == 2017 and int(r["epi_week"]) == 29:
                    tot += int(r["cases"])
        self.assertEqual(tot, 10590, f"Expected 10,590 cases at 2017-W29, got {tot}")

    def test_static_covariates_national_and_colombo(self):
        self.assertTrue(os.path.exists(STATIC_FILE), "static_covariates.csv must exist")
        with open(STATIC_FILE, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 26)

        colombo_row = next(r for r in rows if r["district_name"] == "Colombo")
        colombo_piped = float(colombo_row["piped_water_pct"])
        self.assertAlmostEqual(colombo_piped, 84.4, delta=1.0, msg="Colombo piped water ~84.4%")

if __name__ == "__main__":
    unittest.main()
