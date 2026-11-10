"""
src/silentnode/models/distributions.py: Probabilistic predictive quantile generation,
Negative-Binomial parameterization, and threshold exceedance probabilities.
"""

import math
from typing import Dict, List

QUANTILE_LEVELS = [
    0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95, 0.975, 0.99
]

# Standard normal inverse CDF (probit) approximation (Acklam algorithm)
def normal_ppf(p: float) -> float:
    if p <= 0.0:
        return -5.0
    if p >= 1.0:
        return 5.0
    if p == 0.5:
        return 0.0

    # Coefficients in rational approximations
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]

    q = min(p, 1.0 - p)
    if q > 0.02425:
        r = math.sqrt(-2.0 * math.log(q))
        v = (((((c[0]*r + c[1])*r + c[2])*r + c[3])*r + c[4])*r + c[5]) / \
            ((((d[0]*r + d[1])*r + d[2])*r + d[3])*r + 1.0)
    else:
        r = q - 0.5
        r2 = r * r
        v = (((((a[0]*r2 + a[1])*r2 + a[2])*r2 + a[3])*r2 + a[4])*r2 + a[5])*r / \
            (((((b[0]*r2 + b[1])*r2 + b[2])*r2 + b[3])*r2 + b[4])*r2 + 1.0)

    return v if p < 0.5 else -v

def nb_quantiles(mu: float, dispersion: float = 0.25) -> Dict[float, float]:
    """
    Generates predictive quantiles for Negative-Binomial distribution with mean mu
    and dispersion parameter alpha, where Var(Y) = mu + alpha * mu^2.
    """
    mu = max(0.1, float(mu))
    dispersion = max(0.01, float(dispersion))
    variance = mu + dispersion * (mu ** 2)
    std = math.sqrt(variance)

    # Use gamma-poisson (lognormal-moment-matched) quantile mapping
    # which is strictly non-negative, overdispersed, and monotone
    sigma2_log = math.log(1.0 + (std / mu) ** 2)
    sigma_log = math.sqrt(sigma2_log)
    mu_log = math.log(mu) - 0.5 * sigma2_log

    q_dict = {}
    for p in QUANTILE_LEVELS:
        z = normal_ppf(p)
        val = math.exp(mu_log + z * sigma_log)
        q_dict[p] = round(max(0.0, val), 2)

    # Enforce strict non-crossing monotonicity
    sorted_levels = sorted(QUANTILE_LEVELS)
    for i in range(1, len(sorted_levels)):
        p_prev = sorted_levels[i - 1]
        p_curr = sorted_levels[i]
        if q_dict[p_curr] < q_dict[p_prev]:
            q_dict[p_curr] = q_dict[p_prev]

    return q_dict

def nb_exceedance_prob(mu: float, threshold: float, dispersion: float = 0.25) -> float:
    """Calculates P(Y > threshold) under Negative-Binomial predictive distribution."""
    mu = max(0.1, float(mu))
    threshold = float(threshold)
    variance = mu + dispersion * (mu ** 2)
    std = math.sqrt(variance)

    sigma2_log = math.log(1.0 + (std / mu) ** 2)
    sigma_log = math.sqrt(sigma2_log)
    mu_log = math.log(mu) - 0.5 * sigma2_log

    if threshold <= 0:
        return 1.0

    z = (math.log(threshold) - mu_log) / sigma_log
    # Standard normal survival function 1 - Phi(z)
    prob = 0.5 * math.erfc(z / math.sqrt(2.0))
    return round(min(1.0, max(0.0, prob)), 4)
