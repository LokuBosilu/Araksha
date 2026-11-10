"""
tests/test_wis.py: Unit tests for Weighted Interval Score (WIS) against hand-computed examples.
"""

import unittest
from src.silentnode.eval.metrics import interval_score, weighted_interval_score, INTERVAL_PAIRS

class TestWIS(unittest.TestCase):

    def test_hand_computed_interval_score(self):
        # 1. Observation falls inside interval [40, 60] with alpha=0.2 (80% interval)
        score_inside = interval_score(lower=40.0, upper=60.0, alpha=0.2, y=50.0)
        # Inside: dispersion = 60 - 40 = 20, no penalties
        self.assertEqual(score_inside, 20.0)

        # 2. Observation falls above interval (y=70 > upper=60)
        # IS = (60 - 40) + (2 / 0.2) * (70 - 60) = 20 + 10 * 10 = 120.0
        score_above = interval_score(lower=40.0, upper=60.0, alpha=0.2, y=70.0)
        self.assertEqual(score_above, 120.0)

        # 3. Observation falls below interval (y=25 < lower=40)
        # IS = (60 - 40) + (2 / 0.2) * (40 - 25) = 20 + 10 * 15 = 170.0
        score_below = interval_score(lower=40.0, upper=60.0, alpha=0.2, y=25.0)
        self.assertEqual(score_below, 170.0)

    def test_hand_computed_wis(self):
        # Hand-constructed symmetric forecast centered at 100
        quantiles = {
            0.5: 100.0,
            # Pair 1: alpha=0.02 (0.01, 0.99) -> [50, 150]
            0.01: 50.0, 0.99: 150.0,
            # Pair 2: alpha=0.05 (0.025, 0.975) -> [60, 140]
            0.025: 60.0, 0.975: 140.0,
            # Pair 3: alpha=0.10 (0.05, 0.95) -> [70, 130]
            0.05: 70.0, 0.95: 130.0,
            # Pair 4: alpha=0.20 (0.10, 0.90) -> [80, 120]
            0.10: 80.0, 0.90: 120.0,
            # Pair 5: alpha=0.40 (0.20, 0.80) -> [85, 115]
            0.20: 85.0, 0.80: 115.0,
            # Pair 6: alpha=0.60 (0.30, 0.70) -> [90, 110]
            0.30: 90.0, 0.70: 110.0,
            # Pair 7: alpha=0.80 (0.40, 0.60) -> [95, 105]
            0.40: 95.0, 0.60: 105.0,
        }

        # Suppose observed y = 100 (exact hit at median)
        # Absolute error = 0.5 * |100 - 100| = 0
        # All intervals contain y=100, so each IS_k is simply width:
        # k=1: 0.02/2 * (150-50) = 0.01 * 100 = 1.0
        # k=2: 0.05/2 * (140-60) = 0.025 * 80 = 2.0
        # k=3: 0.10/2 * (130-70) = 0.05 * 60 = 3.0
        # k=4: 0.20/2 * (120-80) = 0.10 * 40 = 4.0
        # k=5: 0.40/2 * (115-85) = 0.20 * 30 = 6.0
        # k=6: 0.60/2 * (110-90) = 0.30 * 20 = 6.0
        # k=7: 0.80/2 * (105-95) = 0.40 * 10 = 4.0
        # Sum of terms = 0 + 1 + 2 + 3 + 4 + 6 + 6 + 4 = 26.0
        # K = 7, denominator = 7 + 0.5 = 7.5
        # Expected WIS = 26.0 / 7.5 = 3.46666...
        wis = weighted_interval_score(quantiles, y=100.0)
        expected_wis = 26.0 / 7.5
        self.assertAlmostEqual(wis, expected_wis, places=4)

if __name__ == "__main__":
    unittest.main()
