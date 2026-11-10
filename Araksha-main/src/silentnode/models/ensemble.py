"""
src/silentnode/models/ensemble.py: Quantile ensemble combining NB-GAM with Quantile Boosting.
Enforces non-crossing monotonic quantiles and checks empirical coverage calibration.
"""

from typing import Dict, List, Tuple
from src.silentnode.models.distributions import QUANTILE_LEVELS

class QuantileEnsemble:
    def __init__(self, weight_gam: float = 0.55, weight_boost: float = 0.45):
        self.w_gam = weight_gam
        self.w_boost = weight_boost

    def combine_quantiles(
        self,
        q_gam: Dict[float, float],
        q_boost: Dict[float, float],
        threshold_q95: float
    ) -> Tuple[Dict[float, float], float, float]:
        """
        Combines two predictive quantile distributions using convex combination,
        followed by monotonic isotonic sorting to prevent crossing quantiles.
        """
        combined = {}
        sorted_levels = sorted(QUANTILE_LEVELS)

        # 1. Weighted linear combination per quantile level
        for p in sorted_levels:
            val_gam = q_gam[p]
            val_boost = q_boost[p]
            c_val = self.w_gam * val_gam + self.w_boost * val_boost
            combined[p] = max(0.0, c_val)

        # 2. Strict isotonic monotonic projection (prevents quantile crossing)
        for i in range(1, len(sorted_levels)):
            p_prev = sorted_levels[i - 1]
            p_curr = sorted_levels[i]
            if combined[p_curr] < combined[p_prev]:
                combined[p_curr] = combined[p_prev]

        # Median prediction
        pred_median = combined[0.5]

        # Exceedance probability estimated from empirical upper tail
        # Count fraction of quantile levels strictly above threshold_q95
        if threshold_q95 <= 0:
            exceed_prob = 1.0
        else:
            # Interpolate exceedance probability from monotonic quantiles
            if combined[sorted_levels[-1]] <= threshold_q95:
                exceed_prob = 0.005
            elif combined[sorted_levels[0]] >= threshold_q95:
                exceed_prob = 0.995
            else:
                # Find bracket
                exceed_prob = 0.05
                for i in range(len(sorted_levels) - 1):
                    p1 = sorted_levels[i]
                    p2 = sorted_levels[i + 1]
                    q1 = combined[p1]
                    q2 = combined[p2]
                    if q1 <= threshold_q95 <= q2:
                        frac = (threshold_q95 - q1) / max(1e-6, q2 - q1)
                        p_interp = p1 + frac * (p2 - p1)
                        exceed_prob = round(1.0 - p_interp, 4)
                        break

        return combined, exceed_prob, pred_median

def check_calibration(eval_results: List[Dict]) -> Dict[str, float]:
    """Computes empirical 50% and 95% coverage against nominal targets."""
    if not eval_results:
        return {"cov_50": 0.50, "cov_95": 0.95}

    cov50_hits = 0
    cov95_hits = 0
    n = len(eval_results)

    for item in eval_results:
        y = item["y_true"]
        # 50% central interval: [q0.25, q0.75]
        q_low50 = q[0.25]
        q_high50 = q[0.75]
        if q_low50 <= y <= q_high50:
            cov50_hits += 1

        # 95% central interval: [q0.025, q0.975]
        q_low95 = q[0.025]
        q_high95 = q[0.975]
        if q_low95 <= y <= q_high95:
            cov95_hits += 1

    return {
        "count": n,
        "empirical_cov_50": round(cov50_hits / n, 3),
        "target_cov_50": 0.50,
        "empirical_cov_95": round(cov95_hits / n, 3),
        "target_cov_95": 0.95,
    }
