"""
tests/test_risk_tiers.py: Unit tests for risk tier classification and the 'Insufficient Data' rule.
Verifies that blanked or stale data produces 'Insufficient Data' and never defaults to Low.
"""

import unittest
from src.silentnode.risk.risk_tiers import (
    classify_risk_tier,
    check_early_anomaly,
    TIER_LOW,
    TIER_MODERATE,
    TIER_HIGH,
    TIER_EXTREME,
    TIER_INSUFFICIENT,
)

class TestRiskTiers(unittest.TestCase):

    def test_blanked_data_produces_insufficient_data(self):
        # Even if predicted numbers look like zero/low, missing data must yield Insufficient Data!
        tier = classify_risk_tier(
            pred_median=0.0,
            incidence_per_100k=0.0,
            exceed_prob=0.0,
            is_missing_or_stale=True,
            model_fit_failed=False
        )
        self.assertEqual(tier, TIER_INSUFFICIENT, "Missing data MUST produce Insufficient Data")
        self.assertNotEqual(tier, TIER_LOW, "Must NEVER default to Low")

    def test_model_failure_produces_insufficient_data(self):
        tier = classify_risk_tier(
            pred_median=12.0,
            incidence_per_100k=5.0,
            exceed_prob=0.05,
            is_missing_or_stale=False,
            model_fit_failed=True
        )
        self.assertEqual(tier, TIER_INSUFFICIENT)

    def test_tier_threshold_boundaries(self):
        # Low tier
        self.assertEqual(classify_risk_tier(10, 5.0, 0.08), TIER_LOW)

        # Moderate tier
        self.assertEqual(classify_risk_tier(30, 15.0, 0.20), TIER_MODERATE)

        # High tier
        self.assertEqual(classify_risk_tier(80, 30.0, 0.60), TIER_HIGH)

        # Extreme tier
        self.assertEqual(classify_risk_tier(300, 75.0, 0.88), TIER_EXTREME)

    def test_early_anomaly_flag(self):
        # Scenario: current incidence is low (8.0/100k), but forecast (150 cases)
        # is 2.5x seasonal baseline median (60 cases)
        flag = check_early_anomaly(
            pred_median=150.0,
            seasonal_baseline_median=60.0,
            current_incidence_per_100k=8.0
        )
        self.assertTrue(flag, "Should trigger early anomaly flag")

        # Not triggered if forecast matches seasonal baseline
        self.assertFalse(check_early_anomaly(65.0, 60.0, 8.0))

if __name__ == "__main__":
    unittest.main()
