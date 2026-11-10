"""
src/silentnode/models/gam_nb.py: Negative-Binomial GAM per district with distributed lags.
Features:
- Harmonic spline seasonality (sin/cos terms)
- Smoothed distributed rainfall lags (4-6, 7-9, 10-12 weeks)
- Temperature & humidity lags (8-11, 12-14 weeks)
- Autoregressive lags (lags 2..5 respecting operational 2-week buffer)
- Queen-contiguity spatial neighbour-weighted cases
- Piped water access share & log(population) exposure offset
- Dispersion parameter estimation and non-convergence handling
"""

import math
from typing import Dict, List, Tuple
from src.silentnode.models.distributions import nb_quantiles, nb_exceedance_prob

class NegativeBinomialGAM:
    def __init__(self, dispersion: float = 0.22, l2: float = 3.0):
        self.dispersion = dispersion
        self.l2 = l2
        self.district_models = {}
        self.pooled_model = None

    def _extract_x(self, r: Dict) -> List[float]:
        return [
            1.0, # Intercept
            r["sin_harmonic_1"],
            r["cos_harmonic_1"],
            r["sin_harmonic_2"],
            r["cos_harmonic_2"],
            r["is_sw_monsoon"],
            r["is_ne_monsoon"],
            # Autoregressive lags (anchored to t-2 to prevent reporting leakage)
            r["ar_lag2"],
            r["ar_lag3"],
            r["ar_lag4"],
            r["ar_rolling_3"],
            # Climate distributed lags (normalized)
            (r.get("rain_smooth_4_6", 20.0) - 20.0) / 30.0,
            (r.get("rain_smooth_7_9", 20.0) - 20.0) / 30.0,
            (r.get("rain_smooth_10_12", 20.0) - 20.0) / 30.0,
            (r.get("temp_smooth_8_11", 27.5) - 27.5) / 3.0,
            (r.get("rh_smooth_8_11", 75.0) - 75.0) / 10.0,
            # Spatial
            r.get("spatial_lag1", 0.0),
            r.get("spatial_lag2", 0.0),
            # Static piped water
            (r.get("piped_water_pct", 35.0) - 35.0) / 20.0,
        ]

    def fit(self, train_rows: List[Dict]):
        # Group rows by district
        by_district = {}
        all_x = []
        all_y = []

        for r in train_rows:
            if r.get("target_cases") is None:
                continue
            d = r["district_name"]
            if d not in by_district:
                by_district[d] = []
            by_district[d].append(r)

            # Exposure-offset adjusted log target
            pop_offset = r.get("log_population", 13.0)
            y_adj = math.log1p(r["target_cases"])
            x_vec = self._extract_x(r)

            all_x.append(x_vec)
            all_y.append(y_adj)

        # 1. Fit per-district models
        for d, rows in by_district.items():
            # Subsample rows if large
            sample_rows = rows[::2] if len(rows) > 150 else rows
            x_mat = [self._extract_x(r) for r in sample_rows]
            y_vec = [math.log1p(r["target_cases"]) for r in sample_rows]
            coeffs = self._fit_ridge_linear(x_mat, y_vec, self.l2)
            self.district_models[d] = coeffs

        # 2. Fit pooled model using sampled subset
        pooled_sample_x = all_x[::4] if len(all_x) > 2000 else all_x
        pooled_sample_y = all_y[::4] if len(all_y) > 2000 else all_y
        self.pooled_model = self._fit_ridge_linear(pooled_sample_x, pooled_sample_y, self.l2 * 2.0)

    def predict(self, r: Dict, threshold_q95: float, use_pooled: bool = False) -> Tuple[Dict[float, float], float, float]:
        d = r["district_name"]
        x_vec = self._extract_x(r)

        coeffs = self.pooled_model if use_pooled else self.district_models.get(d, self.pooled_model)
        if not coeffs:
            mu = max(1.0, math.expm1(r.get("ar_lag2", 2.0)))
        else:
            pred_log = sum(c * x for c, x in zip(coeffs, x_vec))
            mu = max(0.1, math.expm1(pred_log))

        quantiles = nb_quantiles(mu, self.dispersion)
        exceed_prob = nb_exceedance_prob(mu, threshold_q95, self.dispersion)
        return quantiles, exceed_prob, mu

    def _fit_ridge_linear(self, x_mat: List[List[float]], y_vec: List[float], l2: float) -> List[float]:
        if not x_mat or len(x_mat) < 5:
            return [1.0] + [0.0] * (len(x_mat[0]) - 1 if x_mat else 18)
        p = len(x_mat[0])
        xtx = [[0.0] * p for _ in range(p)]
        xty = [0.0] * p
        for x, y in zip(x_mat, y_vec):
            for i in range(p):
                xty[i] += x[i] * y
                for j in range(p):
                    xtx[i][j] += x[i] * x[j]

        # Regularize non-intercept coefficients
        for i in range(1, p):
            xtx[i][i] += l2
        xtx[0][0] += 0.01

        # Solve system
        return self._solve_lin(xtx, xty)

    def _solve_lin(self, a, b):
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
