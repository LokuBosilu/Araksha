"""
src/silentnode/eval/metrics.py: Evaluation metrics for probabilistic dengue forecasts.
Includes Weighted Interval Score (WIS) (Bracher et al., 2021), interval coverage (50%, 95%),
median absolute error (MAE), and ROC-AUC for threshold exceedance.
"""

from typing import Dict, List, Tuple, Any

QUANTILE_LEVELS = [
    0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95, 0.975, 0.99
]

INTERVAL_PAIRS = [
    (0.02, 0.01, 0.99),   # 98% central interval
    (0.05, 0.025, 0.975), # 95% central interval
    (0.10, 0.05, 0.95),   # 90% central interval
    (0.20, 0.10, 0.90),   # 80% central interval
    (0.40, 0.20, 0.80),   # 60% central interval
    (0.60, 0.30, 0.70),   # 40% central interval
    (0.80, 0.40, 0.60),   # 20% central interval
]

def interval_score(lower: float, upper: float, alpha: float, y: float) -> float:
    """Computes interval score for interval [lower, upper] at nominal coverage 1 - alpha."""
    dispersion = upper - lower
    under_penalty = (2.0 / alpha) * (lower - y) if y < lower else 0.0
    over_penalty = (2.0 / alpha) * (y - upper) if y > upper else 0.0
    return dispersion + under_penalty + over_penalty

def weighted_interval_score(quantiles: Dict[float, float], y: float) -> float:
    """
    Computes Weighted Interval Score (WIS) (Bracher et al., 2021).
    quantiles: dictionary mapping quantile probability (e.g. 0.01, 0.5, 0.99) to value.
    y: true observed case count.
    """
    median = quantiles[0.5]
    k = len(INTERVAL_PAIRS)
    score_sum = 0.5 * abs(y - median)

    for alpha, q_low, q_up in INTERVAL_PAIRS:
        l = quantiles[q_low]
        u = quantiles[q_up]
        # Ensure proper ordering
        if l > u:
            l, u = u, l
        score_k = interval_score(l, u, alpha, y)
        score_sum += (alpha / 2.0) * score_k

    return score_sum / (k + 0.5)

def evaluate_predictions(predictions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Evaluates a collection of probabilistic forecasts.
    Each item must contain:
    - 'y_true': float
    - 'quantiles': Dict[float, float]
    - 'threshold_q95': float (from training data)
    - 'exceed_prob': float (predicted P(y > threshold_q95))
    """
    if not predictions:
        return {}

    wis_list = []
    mae_list = []
    cov50_list = []
    cov95_list = []
    y_true_exceed = []
    prob_exceed = []

    for p in predictions:
        y = float(p["y_true"])
        q = p["quantiles"]
        median = q[0.5]

        wis = weighted_interval_score(q, y)
        wis_list.append(wis)
        mae_list.append(abs(y - median))

        q25 = q[0.25]
        q75 = q[0.75]
        cov50_list.append(1.0 if q25 <= y <= q75 else 0.0)

        q025 = q[0.025]
        q975 = q[0.975]
        cov95_list.append(1.0 if q025 <= y <= q975 else 0.0)

        if "threshold_q95" in p and "exceed_prob" in p:
            y_true_exceed.append(1 if y > p["threshold_q95"] else 0)
            prob_exceed.append(float(p["exceed_prob"]))

    roc_auc = compute_roc_auc(y_true_exceed, prob_exceed) if y_true_exceed else 0.5

    return {
        "count": len(predictions),
        "mean_wis": round(sum(wis_list) / len(wis_list), 3),
        "median_ae": round(sum(mae_list) / len(mae_list), 3),
        "coverage_50": round(sum(cov50_list) / len(cov50_list), 3),
        "coverage_95": round(sum(cov95_list) / len(cov95_list), 3),
        "roc_auc": round(roc_auc, 3),
    }

def compute_roc_auc(y_true: List[int], y_score: List[float]) -> float:
    """Computes exact Area Under the ROC Curve without external dependencies."""
    pos = sum(y_true)
    neg = len(y_true) - pos
    if pos == 0 or neg == 0:
        return 0.5

    paired = sorted(zip(y_score, y_true), key=lambda x: x[0])
    rank_sum = 0
    i = 0
    n = len(paired)
    while i < n:
        start = i
        val = paired[i][0]
        while i < n and paired[i][0] == val:
            i += 1
        avg_rank = (start + 1 + i) / 2.0
        for j in range(start, i):
            if paired[j][1] == 1:
                rank_sum += avg_rank

    u = rank_sum - (pos * (pos + 1)) / 2.0
    return u / (pos * neg)
