"""
tests/test_distributions.py: Unit tests for normal_ppf and Negative-Binomial predictive quantiles.
"""

import unittest
from src.silentnode.models.distributions import normal_ppf, nb_quantiles, QUANTILE_LEVELS


class TestDistributions(unittest.TestCase):

    def test_normal_ppf_standard_quantiles(self):
        """Assert normal_ppf at required prob levels matches standard normal quantiles within 1e-4."""
        expected = {
            0.01: -2.3262,
            0.025: -1.9600,
            0.05: -1.6449,
            0.5: 0.0,
            0.95: 1.6449,
            0.975: 1.9600,
            0.99: 2.3262,
        }
        for p, exp in expected.items():
            val = normal_ppf(p)
            self.assertAlmostEqual(
                val,
                exp,
                delta=1e-4,
                msg=f"normal_ppf({p}) = {val:.6f} does not match expected {exp:.6f} within 1e-4",
            )

    def test_normal_ppf_symmetry(self):
        """Assert symmetry: normal_ppf(p) == -normal_ppf(1-p)."""
        test_probs = [0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.49]
        for p in test_probs:
            val_p = normal_ppf(p)
            val_1mp = normal_ppf(1.0 - p)
            self.assertAlmostEqual(
                val_p,
                -val_1mp,
                places=10,
                msg=f"Symmetry failed at p={p}: {val_p} != -{val_1mp}",
            )

    def test_normal_ppf_monotonic_increase(self):
        """Assert strict monotonic increase across p in [0.01, 0.99]."""
        p_values = [round(0.01 + 0.01 * i, 4) for i in range(99)]
        for i in range(len(p_values) - 1):
            p_curr = p_values[i]
            p_next = p_values[i + 1]
            self.assertLess(
                normal_ppf(p_curr),
                normal_ppf(p_next),
                msg=f"Monotonicity failed between p={p_curr} and p={p_next}",
            )

    def test_nb_quantiles_ordering_and_bounds(self):
        """Assert nb_quantiles(326.7, 0.22) returns strictly increasing values with q975 > q025, and q025 < 326.7 < q975."""
        mu = 326.7
        dispersion = 0.22
        quantiles = nb_quantiles(mu, dispersion)

        q025 = quantiles[0.025]
        q975 = quantiles[0.975]

        # Assert bounds and ordering
        self.assertGreater(q975, q025, f"Expected q975 ({q975}) > q025 ({q025})")
        self.assertLess(q025, mu, f"Expected q025 ({q025}) < mu ({mu})")
        self.assertGreater(q975, mu, f"Expected q975 ({q975}) > mu ({mu})")

        # Assert strictly increasing across all levels
        sorted_levels = sorted(quantiles.keys())
        for i in range(len(sorted_levels) - 1):
            p_prev = sorted_levels[i]
            p_curr = sorted_levels[i + 1]
            self.assertLess(
                quantiles[p_prev],
                quantiles[p_curr],
                msg=f"Quantiles not strictly increasing between {p_prev} ({quantiles[p_prev]}) and {p_curr} ({quantiles[p_curr]})",
            )


if __name__ == "__main__":
    unittest.main()
