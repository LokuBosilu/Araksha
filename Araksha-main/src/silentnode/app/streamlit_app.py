"""
src/silentnode/app/streamlit_app.py: Officer-Facing Streamlit Dashboard for Silent Node.
Reads strictly from outputs/latest/ without triggering any model retraining.
"""

import os
import json
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Silent Node - Sri Lanka Dengue Risk Forecaster",
    page_icon="🦟",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LATEST_DIR = os.path.join(BASE_DIR, "outputs", "latest")
METADATA_FILE = os.path.join(LATEST_DIR, "run_metadata.json")
FORECAST_FILE = os.path.join(LATEST_DIR, "forecast_table.csv")
ALLOC_FILE = os.path.join(LATEST_DIR, "allocation_matrix.csv")

# Color-blind safe palette
TIER_COLORS = {
    "Low": "#0ea5e9",        # Sky Blue
    "Moderate": "#f59e0b",   # Amber
    "High": "#ea580c",       # Orange
    "Extreme": "#b91c1c",    # Crimson Red
    "Insufficient Data": "#64748b" # Slate / Gray
}

# 1. Permanent Non-Clinical Disclaimer
st.info("⚠️ **Notice**: Silent Node is a planning decision-support tool for district vector-control and MOH officers, NOT a clinical diagnostic tool.")

# Load Metadata
if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "r") as f:
        meta = json.load(f)
else:
    meta = {"data_cutoff_week": "2024-W18", "as_of_origin": "2024-W20", "staleness_flag": False}

# Staleness Banner
if meta.get("staleness_flag", False):
    st.error("🚨 **DATA STALENESS WARNING**: The latest external data stream was delayed or unavailable. Forecast uncertainty has been widened by 1.5x.")

# Top Freshness Bar
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Data Cutoff Week", meta.get("data_cutoff_week", "N/A"), help="2-week reporting lag buffer applied")
col_m2.metric("Forecast Origin", meta.get("as_of_origin", "N/A"))
col_m3.metric("Model Version", meta.get("model_version", "1.0.0"))
col_m4.metric("Reporting Units", f"{meta.get('districts_count', 26)} Units")

st.divider()

# Load Data
if not os.path.exists(FORECAST_FILE) or not os.path.exists(ALLOC_FILE):
    st.warning("No forecast outputs found in outputs/latest/. Please run `python scripts/run_forecast.py` first.")
    st.stop()

df_forecast = pd.read_csv(FORECAST_FILE)
df_alloc = pd.read_csv(ALLOC_FILE)

# Horizon Selector (1 to 4 weeks)
st.sidebar.header("Forecast Horizon")
selected_horizon = st.sidebar.radio(
    "Select Projection Horizon",
    options=[1, 2, 3, 4],
    format_func=lambda h: f"Week +{h} (Target: {df_forecast[df_forecast['horizon'] == h]['target_week'].iloc[0]})"
)

# Filter by selected horizon
df_h = df_forecast[df_forecast["horizon"] == selected_horizon].copy()

# Layout: Two columns (Choropleth/Summary on Left, Ranked Table on Right)
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader(f"🗺️ Risk Map: Horizon +{selected_horizon} Weeks")
    # Tier breakdown counts
    tier_counts = df_h["risk_tier"].value_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Extreme", tier_counts.get("Extreme", 0))
    c2.metric("High", tier_counts.get("High", 0))
    c3.metric("Moderate", tier_counts.get("Moderate", 0))
    c4.metric("Low", tier_counts.get("Low", 0))

    # Display district summary cards
    for _, row in df_h.sort_values(by="pred_median", ascending=False).head(10).iterrows():
        tier = row["risk_tier"]
        color = TIER_COLORS.get(tier, "#64748b")
        anomaly_str = " ⚠️ EARLY ANOMALY" if row["early_anomaly"] else ""
        st.markdown(
            f"<div style='border-left: 6px solid {color}; padding: 8px; margin-bottom: 8px; background: rgba(0,0,0,0.03); border-radius: 4px;'>"
            f"<b>{row['district_name']}</b> ({row['province']}) — <b>{tier}</b>{anomaly_str}<br/>"
            f"<small>Predicted Median: <b>{row['pred_median']:.1f}</b> cases | Incidence: <b>{row['incidence_per_100k']:.1f}</b>/100k | P(Exceed Q95): <b>{row['exceed_prob']*100:.1f}%</b></small>"
            f"</div>",
            unsafe_allow_html=True
        )

with col_right:
    st.subheader("📋 Vector-Control Allocation Matrix")
    st.download_button(
        "📥 One-Click CSV Export (Allocation Matrix)",
        data=df_alloc.to_csv(index=False),
        file_name="silentnode_allocation_matrix.csv",
        mime="text/csv"
    )

    disp_cols = ["allocation_rank", "district_name", "province", "max_tier", "max_incidence", "max_exceed_prob", "early_anomaly_flag"]
    st.dataframe(
        df_alloc[disp_cols].rename(columns={
            "allocation_rank": "Rank",
            "district_name": "District",
            "province": "Province",
            "max_tier": "Risk Tier",
            "max_incidence": "Incidence/100k",
            "max_exceed_prob": "P(Exceed)",
            "early_anomaly_flag": "Anomaly Flag"
        }),
        use_container_width=True
    )

st.divider()

# District Detail View with 4-Week Fan Chart
st.subheader("🔍 District Detail & 4-Week Predictive Fan Chart")
district_selected = st.selectbox("Choose District for Deep Dive", options=sorted(df_forecast["district_name"].unique()))

df_dist = df_forecast[df_forecast["district_name"] == district_selected].sort_values("horizon")

col_d1, col_d2 = st.columns([1, 1])
with col_d1:
    st.line_chart(df_dist.set_index("horizon")[["pred_median", "q25", "q75", "threshold_q95"]])
with col_d2:
    st.write(f"**District:** {district_selected}")
    st.write(f"**Population (2023):** {df_dist['population'].iloc[0]:,}")
    st.write(f"**Piped-Water Access:** {df_dist['piped_water_pct'].iloc[0]}%")
    st.write(f"**Historical 95th Percentile Threshold:** {df_dist['threshold_q95'].iloc[0]} cases/week")

# How to Read This Panel
with st.expander("ℹ️ How to Read This Forecaster (Guidance for Field Officers)"):
    st.markdown("""
    - **Forecast Horizon (Weeks 1 to 4)**: Represents projections 1 to 4 weeks forward from current origin. Vector-control interventions staged today take 2 to 3 weeks to suppress adult mosquito densities.
    - **P(Exceed Q95)**: The probability that dengue incidence in the target week will exceed the district's historical 95th-percentile weekly threshold. Values > 50% signal imminent epidemic conditions.
    - **50% and 95% Prediction Intervals**: Reflect parameter and environmental uncertainty. 50% of outcomes are expected to fall within the inner band (IQR), and 95% within the outer band.
    - **Insufficient Data**: Triggered automatically if surveillance bulletins or meteorological feeds are interrupted. It is visually distinct (hatched/slate) and **never defaults to Low Risk**.
    - **Early Anomaly Flag**: Alerts officers when projected caseload is $\ge 2.0\\times$ seasonal baseline while current hospital admissions appear low, buying critical lead time.
    """)
