"""
tests/test_leakage.py: Leakage assertion test.
Perturbs all case and weather data occurring strictly after forecast origin week t
and asserts that the feature vector computed at origin t is strictly unchanged.
"""

import os
import copy
import sqlite3
import tempfile
import unittest

from src.silentnode.features.feature_store import build_feature_store, get_ordered_calendar

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
SQLITE_DB = os.path.join(PROCESSED_DIR, "silentnode.db")

class TestLeakage(unittest.TestCase):

    def test_future_perturbation_does_not_affect_origin_features(self):
        """
        Creates a temporary copy of the database, extracts baseline features at origin (2018, 20),
        then drastically corrupts/perturbs all data after week (2018, 20).
        Verifies that features at (2018, 20) do not change by even a single bit.
        """
        origin_year = 2018
        origin_week = 20

        # Read unperturbed features from baseline table features_h2
        conn = sqlite3.connect(SQLITE_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM features_h2
            WHERE origin_year = ? AND origin_week = ? AND district_name = 'Colombo'
        """, (origin_year, origin_week))
        baseline_row = cur.fetchone()
        col_names = [d[0] for d in cur.description]
        conn.close()

        self.assertIsNotNone(baseline_row, "Baseline row must exist at (2018, 20)")
        baseline_dict = dict(zip(col_names, baseline_row))

        # Create temporary database with perturbed future data
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = tmp_db.name

        try:
            # Copy tables to temp db
            src_conn = sqlite3.connect(SQLITE_DB)
            dst_conn = sqlite3.connect(tmp_db_path)
            src_conn.backup(dst_conn)
            src_conn.close()

            # Perturb future data (year > 2018 or (year == 2018 and week > 20))
            dst_cur = dst_conn.cursor()
            dst_cur.execute("""
                UPDATE cases_weekly
                SET cases = cases + 99999
                WHERE year > 2018 OR (year == 2018 AND epi_week > 20)
            """)
            dst_cur.execute("""
                UPDATE weather_weekly
                SET rainfall_sum_mm = 888.8, temp_mean_c = 45.0, humidity_mean_pct = 99.0
                WHERE year > 2018 OR (year == 2018 AND epi_week > 20)
            """)
            dst_conn.commit()
            dst_conn.close()

            # Rebuild feature store on perturbed database
            build_feature_store(
                horizons=[2],
                min_origin_year=2018,
                max_origin_year=2018,
                db_path=tmp_db_path
            )

            # Read recomputed features at origin
            test_conn = sqlite3.connect(tmp_db_path)
            test_cur = test_conn.cursor()
            test_cur.execute("""
                SELECT * FROM features_h2
                WHERE origin_year = ? AND origin_week = ? AND district_name = 'Colombo'
            """, (origin_year, origin_week))
            perturbed_row = test_cur.fetchone()
            test_conn.close()

            perturbed_dict = dict(zip(col_names, perturbed_row))

            # Exclude target_cases (since target is t+h, which is intentionally in the future)
            feature_keys_to_compare = [
                k for k in col_names if k not in ("target_cases", "target_year", "target_week")
            ]

            mismatches = []
            for k in feature_keys_to_compare:
                val_base = baseline_dict[k]
                val_pert = perturbed_dict[k]
                if val_base != val_pert:
                    mismatches.append((k, val_base, val_pert))

            self.assertEqual(
                len(mismatches), 0,
                f"Data leakage detected! The following features changed when future data was perturbed: {mismatches}"
            )
            print(f"Leakage Test PASS: All {len(feature_keys_to_compare)} origin features remained invariant.")

        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)

if __name__ == "__main__":
    unittest.main()
