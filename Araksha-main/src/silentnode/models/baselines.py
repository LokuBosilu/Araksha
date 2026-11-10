"""
src/silentnode/models/baselines.py: Baseline probabilistic forecasting models.
1. Seasonal-Naive: historical same week with negative-binomial spread.
2. Last-Value: persistence baseline with variance expansion over horizon.
3. Seasonal-Autoregressive Negative-Binomial model.
"""

import math
from typing import Dict, List, Tuple
from src.silentnode.models.distributions import nb_quantiles, nb_exceedance_prob

class SeasonalNaiveModel:
    def __init__(self, dispersion: float = 0.35):
        self.dispersion = dispersion
        self.history = {} # (district, week) -> list of cases

    def fit(self, train_cases: List[Dict]):
        self.history.clear()
        for r in train_cases:
            key = (r["district_name"], r["epi_week"])
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(r["cases"])

    def predict(self, district_name: str, target_week: int, threshold_q95: float) -> Tuple[Dict[float, float], float, float]:
        key = (district_name, target_week)
        past_values = self.history.get(key, [])
        if not past_values:
            mu = 5.0
        else:
            mu = sum(past_values) / len(past_values)

        quantiles = nb_quantiles(mu, self.dispersion)
        exceed_prob = nb_exceedance_prob(mu, threshold_q95, self.dispersion)
        return quantiles, exceed_prob, mu

class LastValueModel:
    def __init__(self, dispersion: float = 0.45):
        self.dispersion = dispersion
        self.latest = {}

    def fit(self, train_cases: List[Dict]):
        # Store last known value per district (accounting for 2-week lag at origin)
        self.latest.clear()
        by_district = {}
        for r in train_cases:
            d = r["district_name"]
            if d not in by_district:
                by_district[d] = []
            by_district[d].append(r)

        for d, recs in by_district.items():
            recs.sort(key=lambda x: (x["year"], x["epi_week"]))
            # Safe origin: latest recorded before cutoff
            self.latest[d] = recs[-1]["cases"] if recs else 5.0

    def predict(self, district_name: str, horizon: int, threshold_q95: float) -> Tuple[Dict[float, float], float, float]:
        val = self.latest.get(district_name, 5.0)
        # Variance widens with horizon sqrt(h)
        scaled_dispersion = self.dispersion * math.sqrt(horizon)
        quantiles = nb_quantiles(val, scaled_dispersion)
        exceed_prob = nb_exceedance_prob(val, threshold_q95, scaled_dispersion)
        return quantiles, exceed_prob, val

class SeasonalAutoregressiveNBModel:
    """Calibrated Seasonal-Autoregressive Negative-Binomial Model (the operational fallback)."""
    def __init__(self, dispersion: float = 0.28):
        self.dispersion = dispersion
        self.district_params = {}

    def fit(self, train_features: List[Dict]):
        # Group by district
        by_district = {}
        for r in train_features:
            if r["target_cases"] is None:
                continue
            d = r["district_name"]
            if d not in by_district:
                by_district[d] = []
            by_district[d].append(r)

        for d, rows in by_district.items():
            # Ridge-regularized log-linear coefficients
            # Target = log1p(target_cases)
            # Covariates: intercept, sin1, cos1, ar_lag2, ar_lag3, spatial_lag1
            x_mat = []
            y_vec = []
            for r in rows:
                y = math.log1p(r["target_cases"])
                x = [
                    1.0,
                    r["sin_harmonic_1"],
                    r["cos_harmonic_1"],
                    r["ar_lag2"], # Respects 2-week delay buffer
                    r["ar_lag3"],
                    r.get("spatial_lag1", 0.0),
                ]
                x_mat.append(x)
                y_vec.append(y)

            coeffs = self._solve_ridge(x_mat, y_vec, l2=2.0)
            self.district_params[d] = coeffs

    def predict(self, feature_row: Dict, threshold_q95: float) -> Tuple[Dict[float, float], float, float]:
        d = feature_row["district_name"]
        coeffs = self.district_params.get(d)
        if not coeffs:
            # Fallback mean
            mu = math.expm1(feature_row.get("ar_lag2", 2.0))
        else:
            x = [
                1.0,
                feature_row["sin_harmonic_1"],
                feature_row["cos_harmonic_1"],
                feature_row["ar_lag2"],
                feature_row["ar_lag3"],
                feature_row.get("spatial_lag1", 0.0),
            ]
            pred_log = sum(c * val for c, val in zip(coeffs, x))
            mu = max(0.1, math.expm1(pred_log))

        quantiles = nb_quantiles(mu, self.dispersion)
        exceed_prob = nb_exceedance_prob(mu, threshold_q95, self.dispersion)
        return quantiles, exceed_prob, mu

    def _solve_ridge(self, x_mat, y_vec, l2=2.0):
        if not x_mat or len(x_mat) < 10:
            return [1.0, 0.0, 0.0, 0.6, 0.2, 0.1]
        p = len(x_mat[0])
        # Compute X^T X + lambda I
        xtx = [[0.0] * p for _ in range(p)]
        xty = [0.0] * p
        for x, y in zip(x_mat, y_vec):
            for i in range(p):
                xty[i] += x[i] * y
                for j in range(p):
                    xtx[i][j] += x[i] * x[j]

        for i in range(p):
            xtx[i][i] += l2

        # Solve system via Gaussian elimination
        return self._gaussian_solve(xtx, xty)

    def _gaussian_solve(self, a, b):
        n = len(b)
        for i in range(n):
            max_el = abs(a[i][i])
            max_row = i
            for k in range(i + 1, n):
                if abs(a[k][i]) > max_el:
                    max_el = abs(a[k][i])
                    max_row = k
            a[i], a[max_row] = a[max_row], a[i]
            b[i], b[max_row] = b[max_row], b[i]

            pivot = a[i][i] if abs(a[i][i]) > 1e-9 else 1e-9
            for k in range(i + 1, n):
                c = -a[k][i] / pivot
                for j in range(i, n):
                    if i == j:
                        a[k][j] = 0
                    else:
                        a[k][j] += c * a[i][j]
                b[k] += c * b[i]

        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            s = b[i]
            for j in range(i + 1, n):
                s -= a[i][j] * x[j]
            x[i] = s / (a[i][i] if abs(a[i][i]) > 1e-9 else 1e-9)
        return x
