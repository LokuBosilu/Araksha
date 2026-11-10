"""
src/silentnode/risk/risk_tiers.py: Decision-ready risk classification, early anomaly detection,
and Vector-Control Resource Allocation Matrix generator.
Enforces that missing or stale data produces 'Insufficient Data' and NEVER defaults to Low.
"""

from typing import Dict, List, Optional, Tuple

# Risk Tier Definitions
# Tier 1: Low (Routine monitoring & prevention)
# Tier 2: Moderate (Targeted source reduction & surveillance)
# Tier 3: High (Intensified vector-control & public awareness)
# Tier 4: Extreme (Emergency fogging, MOH surge deployment, task force activation)
# Tier 0: Insufficient Data (Data gap / stale input / failed convergence)

TIER_LOW = "Low"
TIER_MODERATE = "Moderate"
TIER_HIGH = "High"
TIER_EXTREME = "Extreme"
TIER_INSUFFICIENT = "Insufficient Data"

def classify_risk_tier(
    pred_median: float,
    incidence_per_100k: float,
    exceed_prob: float,
    is_missing_or_stale: bool = False,
    model_fit_failed: bool = False
) -> str:
    """
    Assigns risk tier strictly based on exceedance probability and incidence per 100k.
    If input is missing or stale, or model fitting failed, MUST return 'Insufficient Data'.
    It must NEVER default to Low!
    """
    if is_missing_or_stale or model_fit_failed:
        return TIER_INSUFFICIENT

    # Extreme: Exceedance probability >= 0.80 OR projected weekly incidence >= 50 per 100k
    if exceed_prob >= 0.80 or incidence_per_100k >= 50.0:
        return TIER_EXTREME

    # High: Exceedance probability >= 0.50 OR projected weekly incidence >= 25 per 100k
    if exceed_prob >= 0.50 or incidence_per_100k >= 25.0:
        return TIER_HIGH

    # Moderate: Exceedance probability >= 0.15 OR projected weekly incidence >= 10 per 100k
    if exceed_prob >= 0.15 or incidence_per_100k >= 10.0:
        return TIER_MODERATE

    # Low: Both low exceedance probability and low incidence
    return TIER_LOW

def check_early_anomaly(
    pred_median: float,
    seasonal_baseline_median: float,
    current_incidence_per_100k: float
) -> bool:
    """
    Early anomaly flag: triggers when a district's forecast is well above its seasonal norm
    (e.g., predicted median >= 2.0x seasonal norm) while current incidence is still low (< 15 per 100k).
    Provides early warning 2-4 weeks ahead of visible hospital surges.
    """
    if seasonal_baseline_median <= 0:
        return False

    ratio = pred_median / seasonal_baseline_median
    return ratio >= 2.0 and current_incidence_per_100k < 15.0

def build_allocation_matrix(forecast_rows: List[Dict]) -> List[Dict]:
    """
    Generates ranked Vector-Control Allocation Matrix across Sri Lanka's reporting units.
    Ranks districts by priority score computed from risk tier, exceedance probability,
    and projected caseload, guiding where field teams should be deployed 2 to 4 weeks ahead.
    """
    # Tier numeric weight
    tier_weight = {
        TIER_EXTREME: 400.0,
        TIER_HIGH: 300.0,
        TIER_MODERATE: 200.0,
        TIER_LOW: 100.0,
        TIER_INSUFFICIENT: 50.0,
    }

    # Group by district and calculate 4-week cumulative composite priority
    by_district = {}
    for r in forecast_rows:
        d = r["district_name"]
        if d not in by_district:
            by_district[d] = {
                "district_id": r["district_id"],
                "district_name": d,
                "province": r.get("province", ""),
                "population": r.get("population", 0),
                "piped_water_pct": r.get("piped_water_pct", 0.0),
                "max_tier": TIER_LOW,
                "max_exceed_prob": 0.0,
                "max_incidence": 0.0,
                "h1_cases": 0.0,
                "h2_cases": 0.0,
                "h3_cases": 0.0,
                "h4_cases": 0.0,
                "h1_tier": TIER_LOW,
                "h2_tier": TIER_LOW,
                "h3_tier": TIER_LOW,
                "h4_tier": TIER_LOW,
                "early_anomaly_flag": False,
                "insufficient_data": False,
                "priority_score": 0.0,
            }

        entry = by_district[d]
        h = r["horizon"]
        tier = r["risk_tier"]
        exceed = r["exceed_prob"]
        inc = r["incidence_per_100k"]
        cases = r["pred_median"]

        if tier == TIER_INSUFFICIENT:
            entry["insufficient_data"] = True

        entry[f"h{h}_cases"] = cases
        entry[f"h{h}_tier"] = tier

        if r.get("early_anomaly", False):
            entry["early_anomaly_flag"] = True

        if exceed > entry["max_exceed_prob"]:
            entry["max_exceed_prob"] = exceed
        if inc > entry["max_incidence"]:
            entry["max_incidence"] = inc

        # Update max tier
        if tier_weight[tier] > tier_weight[entry["max_tier"]]:
            entry["max_tier"] = tier

    # Calculate overall priority score
    matrix_list = []
    for d, entry in by_district.items():
        base_w = tier_weight.get(entry["max_tier"], 100.0)
        # Priority combines tier weight, exceedance probability, and incidence scale
        score = base_w + (entry["max_exceed_prob"] * 50.0) + min(50.0, entry["max_incidence"])
        if entry["early_anomaly_flag"]:
            score += 25.0 # Anomaly boost to prioritize preemptive prevention

        entry["priority_score"] = round(score, 1)
        matrix_list.append(entry)

    # Rank descending by priority score
    matrix_list.sort(key=lambda x: x["priority_score"], reverse=True)
    for rank, item in enumerate(matrix_list, 1):
        item["allocation_rank"] = rank

    return matrix_list
