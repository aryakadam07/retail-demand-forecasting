"""
Retail Demand Forecasting & Inventory Optimization — Premium Executive Dashboard
Provides interactive visualization for demand forecasts, model evaluation, inventory optimization, and what-if pricing scenarios.
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup Root Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient

# ----------------------------------------------------
# PAGE CONFIGURATION & THEME
# ----------------------------------------------------
st.set_page_config(
    page_title="Retail Demand Intelligence & Replenishment Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS for Glassmorphism, Micro-Animations, and Modern Typography
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', 'Inter', sans-serif;
        background-color: #F8FAFC;
    }
    
    /* Header Hero Section */
    .hero-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 40%, #312E81 70%, #4338CA 100%);
        padding: 2.2rem 2.5rem;
        border-radius: 20px;
        color: #FFFFFF;
        box-shadow: 0 20px 35px -10px rgba(49, 46, 129, 0.35);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(0, 0, 0, 0) 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.4rem;
        background: linear-gradient(90deg, #FFFFFF 0%, #E0E7FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        font-weight: 400;
        color: #A5B4FC;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .status-pill {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        padding: 0.2rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #34D399;
        border-radius: 50%;
        box-shadow: 0 0 8px #34D399;
    }

    /* Glassmorphism KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.25rem;
        margin-bottom: 1.8rem;
    }
    .kpi-card-glass {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(16px);
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.4rem;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .kpi-card-glass:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px -4px rgba(15, 23, 42, 0.1);
        border-color: #C7D2FE;
    }
    .kpi-card-glass::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
    }
    .kpi-card-indigo::before { background: linear-gradient(180deg, #6366F1 0%, #4338CA 100%); }
    .kpi-card-emerald::before { background: linear-gradient(180deg, #10B981 0%, #059669 100%); }
    .kpi-card-rose::before { background: linear-gradient(180deg, #F43F5E 0%, #E11D48 100%); }
    .kpi-card-amber::before { background: linear-gradient(180deg, #F59E0B 0%, #D97706 100%); }

    .kpi-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .kpi-number {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    .kpi-footnote {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    /* Styled Badges */
    .badge-pill-high {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
        font-weight: 700;
        padding: 0.3rem 0.85rem;
        border-radius: 20px;
        font-size: 0.78rem;
    }
    .badge-pill-med {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
        font-weight: 700;
        padding: 0.3rem 0.85rem;
        border-radius: 20px;
        font-size: 0.78rem;
    }
    .badge-pill-low {
        background-color: #D1FAE5;
        color: #065F46;
        border: 1px solid #6EE7B7;
        font-weight: 700;
        padding: 0.3rem 0.85rem;
        border-radius: 20px;
        font-size: 0.78rem;
    }

    /* Section Cards */
    .content-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px -3px rgba(15, 23, 42, 0.04);
        margin-bottom: 1.5rem;
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Tab overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        font-weight: 600;
        color: #475569;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #4F46E5 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_warehouse_client():
    return WarehouseClient()


def generate_mock_data():
    """Generates rich demonstration datasets when database tables are initializing."""
    dates_hist = pd.date_range(end=pd.Timestamp.today(), periods=90)
    dates_fcst = pd.date_range(start=pd.Timestamp.today() + pd.Timedelta(days=1), periods=30)
    
    stores = ["HOBBIES_1_CA_1", "FOODS_3_CA_1", "HOUSEHOLD_1_TX_1", "HOBBIES_2_WI_1"]
    items = ["HOBBIES_1_001", "FOODS_3_090", "HOUSEHOLD_1_001", "HOBBIES_1_002"]
    categories = ["HOBBIES", "FOODS", "HOUSEHOLD", "HOBBIES"]
    
    hist_rows = []
    for s_idx, s in enumerate(stores):
        for d in dates_hist:
            base_sales = 18 + s_idx * 6 + np.sin(d.dayofweek) * 5
            hist_rows.append({
                "date": d,
                "store_id": s,
                "item_id": items[s_idx],
                "category": categories[s_idx],
                "sales": max(0, int(np.random.poisson(lam=max(2, base_sales))))
            })
    hist_df = pd.DataFrame(hist_rows)

    fcst_rows = []
    for s_idx, s in enumerate(stores):
        for d in dates_fcst:
            fcst_val = 20 + s_idx * 5 + np.sin(d.dayofweek) * 4
            fcst_rows.append({
                "forecast_date": d,
                "store_id": s,
                "item_id": items[s_idx],
                "category": categories[s_idx],
                "predicted_demand": max(0.0, float(np.random.normal(loc=fcst_val, scale=2.5)))
            })
    fcst_df = pd.DataFrame(fcst_rows)

    inv_rows = []
    for s_idx, s in enumerate(stores):
        risk = "HIGH" if s_idx % 2 == 0 else "LOW"
        inv_rows.append({
            "store_id": s,
            "item_id": items[s_idx],
            "category": categories[s_idx],
            "safety_stock": 28 + s_idx * 4,
            "reorder_point": 65 + s_idx * 10,
            "available_inventory": 30 if risk == "HIGH" else 85,
            "recommended_order_quantity": 45 if risk == "HIGH" else 0,
            "stockout_risk": risk
        })
    inv_df = pd.DataFrame(inv_rows)

    eval_df = pd.DataFrame([
        {"Model Architecture": "Prophet", "MAE": 2.20, "RMSE": 2.73, "sMAPE (%)": 37.3, "Status": "🏆 Winner"},
        {"Model Architecture": "LightGBM", "MAE": 2.23, "RMSE": 2.79, "sMAPE (%)": 37.6, "Status": "Runner-Up"}
    ])

    return hist_df, fcst_df, inv_df, eval_df


@st.cache_data(ttl=600)
def load_dashboard_data():
    client = get_warehouse_client()
    dataset = client.dataset_id

    try:
        hist_df = client.query(f"SELECT * FROM {dataset}.mart_sales_forecasting")
        hist_df["date"] = pd.to_datetime(hist_df["date"])
    except Exception:
        hist_df = pd.DataFrame()

    try:
        fcst_df = client.query(f"SELECT * FROM {dataset}.forecast_results")
        fcst_df["forecast_date"] = pd.to_datetime(fcst_df["forecast_date"])
    except Exception:
        fcst_df = pd.DataFrame()

    try:
        inv_df = client.query(f"SELECT * FROM {dataset}.inventory_recommendations")
    except Exception:
        inv_df = pd.DataFrame()

    try:
        eval_df = client.query(f"SELECT * FROM {dataset}.model_evaluation_metrics")
    except Exception:
        eval_df = pd.DataFrame()

    if fcst_df.empty or inv_df.empty:
        return generate_mock_data()

    return hist_df, fcst_df, inv_df, eval_df


def calculate_z_score(service_level_pct: float) -> float:
    try:
        from scipy.stats import norm
        return float(norm.ppf(service_level_pct / 100.0))
    except Exception:
        sl_map = {
            80.0: 0.8416, 85.0: 1.0364, 90.0: 1.2816, 95.0: 1.6449,
            98.0: 2.0537, 99.0: 2.3263, 99.5: 2.5758, 99.9: 3.0902
        }
        closest = min(sl_map.keys(), key=lambda k: abs(k - service_level_pct))
        return sl_map[closest]


def main():
    # Hero Header Banner
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">Retail Demand Intelligence & Replenishment Portal</div>
        <div class="hero-subtitle">
            <span>Automated Walmart M5 Time-Series Forecasting & Inventory Optimization System</span>
            <span class="status-pill"><span class="pulse-dot"></span> SYSTEM LIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    hist_df, fcst_df, inv_df, eval_df = load_dashboard_data()

    if "category" not in fcst_df.columns and not hist_df.empty and "category" in hist_df.columns:
        meta_df = hist_df[["item_id", "store_id", "category"]].drop_duplicates()
        fcst_df = fcst_df.merge(meta_df, on=["item_id", "store_id"], how="left")
        inv_df = inv_df.merge(meta_df, on=["item_id", "store_id"], how="left")

    # ----------------------------------------------------
    # SIDEBAR CONTROLS
    # ----------------------------------------------------
    st.sidebar.markdown("## ⚙️ Hierarchy & Filters")

    stores = ["All Stores"] + sorted(list(fcst_df["store_id"].dropna().unique()))
    selected_store = st.sidebar.selectbox("🏪 Select Store Location", stores)

    cat_df = fcst_df[fcst_df["store_id"] == selected_store] if selected_store != "All Stores" else fcst_df
    categories = ["All Categories"]
    if "category" in cat_df.columns:
        categories += sorted(list(cat_df["category"].dropna().unique()))
    selected_cat = st.sidebar.selectbox("📦 Select Category", categories)

    item_df = cat_df[cat_df["category"] == selected_cat] if (selected_cat != "All Categories" and "category" in cat_df.columns) else cat_df
    items = ["All Items"] + sorted(list(item_df["item_id"].dropna().unique()))
    selected_item = st.sidebar.selectbox("🏷️ Select Specific SKU Item", items)

    # Apply Filter Logic
    filtered_fcst = fcst_df.copy()
    filtered_hist = hist_df.copy() if not hist_df.empty else pd.DataFrame()
    filtered_inv = inv_df.copy()

    if selected_store != "All Stores":
        filtered_fcst = filtered_fcst[filtered_fcst["store_id"] == selected_store]
        if not filtered_hist.empty:
            filtered_hist = filtered_hist[filtered_hist["store_id"] == selected_store]
        filtered_inv = filtered_inv[filtered_inv["store_id"] == selected_store]

    if selected_cat != "All Categories" and "category" in filtered_fcst.columns:
        filtered_fcst = filtered_fcst[filtered_fcst["category"] == selected_cat]
        if not filtered_hist.empty and "category" in filtered_hist.columns:
            filtered_hist = filtered_hist[filtered_hist["category"] == selected_cat]
        if "category" in filtered_inv.columns:
            filtered_inv = filtered_inv[filtered_inv["category"] == selected_cat]

    if selected_item != "All Items":
        filtered_fcst = filtered_fcst[filtered_fcst["item_id"] == selected_item]
        if not filtered_hist.empty:
            filtered_hist = filtered_hist[filtered_hist["item_id"] == selected_item]
        filtered_inv = filtered_inv[filtered_inv["item_id"] == selected_item]

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🛠️ Live Simulation Parameters")
    
    lead_time_days = st.sidebar.slider("Supplier Lead Time (Days)", 1, 30, 7, help="Days required for stock replenishment")
    service_level_pct = st.sidebar.slider("Target Service Level (%)", 80.0, 99.9, 95.0, 0.5, help="Target probability of non-stockout")
    stock_multiplier = st.sidebar.slider("Initial Stock Factor (%)", 10, 200, 100, 10, help="Simulate starting warehouse inventory") / 100.0

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🏷️ Price Elasticity What-If")
    price_scenario = st.sidebar.select_slider(
        "Unit Price Shift",
        options=["-10%", "0%", "+10%"],
        value="0%",
        help="Simulate demand response (Elasticity e = -1.2)"
    )

    price_mult = 1.12 if price_scenario == "-10%" else (0.88 if price_scenario == "+10%" else 1.0)
    filtered_fcst["predicted_demand"] = filtered_fcst["predicted_demand"] * price_mult

    # Recalculate Inventory Simulation
    z_score = calculate_z_score(service_level_pct)
    if not filtered_fcst.empty and not filtered_inv.empty:
        series_fcst = filtered_fcst.groupby(["store_id", "item_id"])["predicted_demand"].agg(["mean", "std"]).reset_index()
        series_fcst["std"] = series_fcst["std"].fillna(series_fcst["mean"] * 0.20)
        
        recalc_inv = filtered_inv.copy()
        recalc_inv = recalc_inv.drop(columns=["safety_stock", "reorder_point", "recommended_order_quantity", "stockout_risk"], errors="ignore")
        recalc_inv = recalc_inv.merge(series_fcst, on=["store_id", "item_id"], how="left")
        
        recalc_inv["mean"] = recalc_inv["mean"].fillna(6.0)
        recalc_inv["std"] = recalc_inv["std"].fillna(1.2)
        
        recalc_inv["safety_stock"] = (z_score * recalc_inv["std"] * np.sqrt(lead_time_days)).round(0).astype(int)
        recalc_inv["reorder_point"] = ((recalc_inv["mean"] * lead_time_days) + recalc_inv["safety_stock"]).round(0).astype(int)
        recalc_inv["available_inventory"] = (recalc_inv["available_inventory"] * stock_multiplier).round(0).astype(int)
        recalc_inv["recommended_order_quantity"] = np.maximum(0, recalc_inv["reorder_point"] - recalc_inv["available_inventory"])
        
        recalc_inv["stockout_risk"] = recalc_inv.apply(
            lambda r: "HIGH" if r["available_inventory"] < r["reorder_point"] else ("MEDIUM" if r["available_inventory"] < r["reorder_point"] * 1.25 else "LOW"),
            axis=1
        )
        filtered_inv = recalc_inv

    # ----------------------------------------------------
    # EXECUTIVE KPI CARDS
    # ----------------------------------------------------
    tot_fcst = filtered_fcst["predicted_demand"].sum() if not filtered_fcst.empty else 0.0
    avg_daily_fcst = filtered_fcst.groupby("forecast_date")["predicted_demand"].sum().mean() if not filtered_fcst.empty else 0.0
    high_risk_cnt = (filtered_inv["stockout_risk"] == "HIGH").sum() if not filtered_inv.empty else 0
    tot_roq = filtered_inv["recommended_order_quantity"].sum() if not filtered_inv.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card-glass kpi-card-indigo">
            <div class="kpi-label"><span>Total 30-Day Demand</span> 📊</div>
            <div class="kpi-number">{tot_fcst:,.0f}</div>
            <div class="kpi-footnote">Units Projected Across Scope</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card-glass kpi-card-emerald">
            <div class="kpi-label"><span>Daily Sales Run-Rate</span> ⚡</div>
            <div class="kpi-number">{avg_daily_fcst:,.1f}</div>
            <div class="kpi-footnote">Units / Day Velocity</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card-glass kpi-card-rose">
            <div class="kpi-label"><span>High Stockout Risk SKUs</span> 🚨</div>
            <div class="kpi-number" style="color: {'#E11D48' if high_risk_cnt > 0 else '#10B981'};">{high_risk_cnt}</div>
            <div class="kpi-footnote">Target Service Level: {service_level_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card-glass kpi-card-amber">
            <div class="kpi-label"><span>Total Reorder Qty (ROQ)</span> 📦</div>
            <div class="kpi-number">{tot_roq:,.0f}</div>
            <div class="kpi-footnote">Lead Time Window: {lead_time_days} Days</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # TABBED INTERACTIVE SECTIONS
    # ----------------------------------------------------
    tab1, tab2, tab3 = st.tabs([
        "📈 Demand Forecast & Timeline",
        "📦 Inventory Replenishment & Risk",
        "🏆 ML Model Accuracy Benchmark"
    ])

    # ----------------------------------------------------
    # TAB 1: DEMAND FORECAST & TIMELINE
    # ----------------------------------------------------
    with tab1:
        st.markdown('<div class="section-header"><span>📈 Historical Demand vs. 30-Day Future Forecast</span></div>', unsafe_allow_html=True)
        
        fig = go.Figure()
        if not filtered_hist.empty:
            hist_d = filtered_hist.groupby("date")["sales"].sum().reset_index()
            fig.add_trace(go.Scatter(
                x=hist_d["date"], y=hist_d["sales"],
                mode="lines", name="Historical Actual Sales",
                line=dict(color="#4338CA", width=2.5),
                fill='tozeroy', fillcolor='rgba(99, 102, 241, 0.08)'
            ))

        fcst_d = filtered_fcst.groupby("forecast_date")["predicted_demand"].sum().reset_index()
        fig.add_trace(go.Scatter(
            x=fcst_d["forecast_date"], y=fcst_d["predicted_demand"],
            mode="lines+markers", name=f"30-Day Forecast ({price_scenario} Price Shift)",
            line=dict(color="#10B981", width=3.5, dash="dash"),
            marker=dict(size=6, color="#059669")
        ))

        fig.update_layout(
            xaxis_title="Date", yaxis_title="Units Demanded",
            hovermode="x unified", template="plotly_white",
            height=440, margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown("### 🗓️ Daily Forecast Schedule")
            fcst_tab = fcst_d.rename(columns={"forecast_date": "Date", "predicted_demand": "Projected Demand"})
            fcst_tab["Projected Demand"] = fcst_tab["Projected Demand"].round(2)
            st.dataframe(fcst_tab, use_container_width=True, height=320)
            
            st.download_button(
                "📥 Export 30-Day Forecast CSV",
                fcst_tab.to_csv(index=False).encode('utf-8'),
                "demand_forecast_30day.csv",
                "text/csv"
            )

        with col_b:
            if not filtered_fcst.empty and "category" in filtered_fcst.columns:
                st.markdown("### 📊 Demand Breakdown by Category")
                cat_chart_df = filtered_fcst.groupby("category")["predicted_demand"].sum().reset_index()
                fig_cat = px.bar(
                    cat_chart_df, x="category", y="predicted_demand",
                    color="category", text_auto=".0f",
                    color_discrete_sequence=["#6366F1", "#10B981", "#F59E0B", "#EC4899"]
                )
                fig_cat.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_cat, use_container_width=True)

    # ----------------------------------------------------
    # TAB 2: INVENTORY REPLENISHMENT & RISK MATRIX
    # ----------------------------------------------------
    with tab2:
        st.markdown('<div class="section-header"><span>📦 Inventory Replenishment & Stockout Risk Engine</span></div>', unsafe_allow_html=True)
        
        r1, r2 = st.columns([1.5, 1])
        with r1:
            st.markdown("### 📋 Recommended Order Quantities (ROQ)")
            disp_cols = ["item_id", "store_id", "safety_stock", "reorder_point", "available_inventory", "recommended_order_quantity", "stockout_risk"]
            disp_df = filtered_inv[[c for c in disp_cols if c in filtered_inv.columns]].copy()
            disp_df = disp_df.rename(columns={
                "item_id": "SKU Item", "store_id": "Store",
                "safety_stock": "Safety Stock", "reorder_point": "Reorder Point (ROP)",
                "available_inventory": "Current Stock", "recommended_order_quantity": "Order Qty (ROQ)",
                "stockout_risk": "Risk Status"
            })
            st.dataframe(disp_df, use_container_width=True, height=350)
            
            st.download_button(
                "📥 Export Replenishment Plan CSV",
                disp_df.to_csv(index=False).encode('utf-8'),
                "inventory_replenishment_plan.csv",
                "text/csv"
            )

        with r2:
            st.markdown("### 🚨 Stockout Risk Distribution")
            if not filtered_inv.empty and "stockout_risk" in filtered_inv.columns:
                risk_counts = filtered_inv["stockout_risk"].value_counts().reset_index()
                risk_counts.columns = ["Risk Category", "Item Count"]
                fig_donut = px.pie(
                    risk_counts, names="Risk Category", values="Item Count",
                    hole=0.55, color="Risk Category",
                    color_discrete_map={"HIGH": "#F43F5E", "MEDIUM": "#F59E0B", "LOW": "#10B981"}
                )
                fig_donut.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_donut, use_container_width=True)

    # ----------------------------------------------------
    # TAB 3: MODEL ACCURACY BENCHMARK
    # ----------------------------------------------------
    with tab3:
        st.markdown('<div class="section-header"><span>🏆 Forecasting Model Accuracy & Temporal Validation</span></div>', unsafe_allow_html=True)
        
        e1, e2 = st.columns([1, 1.2])
        with e1:
            st.markdown("### 📐 Validation Benchmark Table")
            st.dataframe(eval_df, use_container_width=True)
            
            st.info("""
            **Validation Methodology**:
            - **Temporal Cutoff**: Out-of-sample temporal train/val split strictly enforced to prevent lookahead bias.
            - **Metric Standard**: MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), sMAPE (Symmetric Mean Absolute Percentage Error).
            - **Automated Selection**: System automatically picks the model achieving the lowest RMSE to generate the 30-day future forecast.
            """)

        with e2:
            if not eval_df.empty and "RMSE" in eval_df.columns:
                st.markdown("### 📊 Model Error Comparison (Lower = Better)")
                model_col = "Model Architecture" if "Model Architecture" in eval_df.columns else ("Model" if "Model" in eval_df.columns else "model")
                fig_eval = px.bar(
                    eval_df, x=model_col,
                    y="RMSE", color="RMSE",
                    text_auto=".2f",
                    color_continuous_scale="Viridis"
                )
                fig_eval.update_layout(template="plotly_white", height=340, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_eval, use_container_width=True)


if __name__ == "__main__":
    main()
