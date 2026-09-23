"""
Supply Chain & Inventory Analytics - Streamlit App
====================================================
Run with:  streamlit run app.py
Make sure you have run analysis.py at least once first to generate the
outputs/charts/ and outputs/tables/ files.
"""

import os
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from PIL import Image

warnings.filterwarnings("ignore")

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supply Chain & Inventory Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(BASE_DIR, "data", "supply_chain_dataset.csv")
CHARTS_DIR = os.path.join(BASE_DIR, "outputs", "charts")
TABLES_DIR = os.path.join(BASE_DIR, "outputs", "tables")

# ── CSS tweaks ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .kpi-card {
        background: #f7f8fa;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 18px 20px;
        text-align: center;
    }
    .kpi-label { font-size: 12px; color: #57606a; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 26px; font-weight: 700; color: #1f2328; }
    .kpi-sub   { font-size: 11px; color: #57606a; margin-top: 2px; }
    .section-title { font-size: 20px; font-weight: 700; color: #1f2328; margin-top: 24px; margin-bottom: 4px; }
    .divider { border-top: 1px solid #e5e7eb; margin: 12px 0 20px 0; }
    .insight-box {
        background: #f0f7ff;
        border-left: 4px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #1f2328;
    }
    .warn-box {
        background: #fff7ed;
        border-left: 4px solid #f59e0b;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #1f2328;
    }
</style>
""", unsafe_allow_html=True)

# ── data loading ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading data …")
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True)
    num_cols = ["Units_Sold", "Inventory_Level", "Supplier_Lead_Time_Days",
                "Reorder_Point", "Order_Quantity", "Unit_Cost", "Unit_Price",
                "Demand_Forecast"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Promotion_Flag"] = df["Promotion_Flag"].astype(int)
    invalid_mask = (
        (df["Units_Sold"]      < 0) |
        (df["Inventory_Level"] < 0) |
        (df["Unit_Cost"]       <= 0) |
        (df["Unit_Price"]      <= 0)
    )
    df = df[~invalid_mask].copy()
    df["Revenue"]         = df["Units_Sold"]      * df["Unit_Price"]
    df["COGS"]            = df["Units_Sold"]      * df["Unit_Cost"]
    df["Gross_Profit"]    = df["Revenue"]         - df["COGS"]
    df["Margin_Pct"]      = df["Gross_Profit"]    / df["Revenue"] * 100
    df["Inventory_Value"] = df["Inventory_Level"] * df["Unit_Cost"]
    df["Forecast_Error"]  = df["Units_Sold"]      - df["Demand_Forecast"]
    df["YearMonth"]       = df["Date"].dt.to_period("M").astype(str)
    df["Month"]           = df["Date"].dt.month
    df["DayOfWeek"]       = df["Date"].dt.day_name()
    df["DOI"]             = df["Inventory_Level"] / df["Units_Sold"].replace(0, np.nan)
    df["Below_ROP"]       = (df["Inventory_Level"] < df["Reorder_Point"]).astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_tables():
    tables = {}
    for name in ["sku_summary", "monthly_trends", "warehouse_summary",
                 "supplier_summary", "region_summary", "kpi_snapshot",
                 "abcxyz_matrix", "reorder_recommendations"]:
        path = os.path.join(TABLES_DIR, f"{name}.csv")
        if os.path.exists(path):
            tables[name] = pd.read_csv(path)
    return tables


def load_chart(filename):
    path = os.path.join(CHARTS_DIR, filename)
    if os.path.exists(path):
        return Image.open(path)
    return None


df     = load_data()
tables = load_tables()

# ── sidebar filters ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/warehouse.png", width=60)
    st.title("📦 Supply Chain\nAnalytics")
    st.markdown("---")

    st.subheader("🔍 Filters")

    all_skus  = sorted(df["SKU_ID"].unique())
    all_whs   = sorted(df["Warehouse_ID"].unique())
    all_sups  = sorted(df["Supplier_ID"].unique())
    all_regs  = sorted(df["Region"].unique())

    sel_skus = st.multiselect("SKU(s)", all_skus,
                               default=all_skus, key="f_sku")
    sel_whs  = st.multiselect("Warehouse(s)", all_whs,
                               default=all_whs, key="f_wh")
    sel_sups = st.multiselect("Supplier(s)", all_sups,
                               default=all_sups, key="f_sup")
    sel_regs = st.multiselect("Region(s)", all_regs,
                               default=all_regs, key="f_reg")
    date_min = df["Date"].min().date()
    date_max = df["Date"].max().date()
    sel_dates = st.date_input("Date Range",
                              value=(date_min, date_max),
                              min_value=date_min,
                              max_value=date_max)
    if isinstance(sel_dates, (list, tuple)) and len(sel_dates) == 2:
        d0, d1 = pd.Timestamp(sel_dates[0]), pd.Timestamp(sel_dates[1])
    else:
        d0, d1 = pd.Timestamp(date_min), pd.Timestamp(date_max)

    st.markdown("---")
    st.caption("© 2024 Supply Chain Analytics")

# ── apply filters ───────────────────────────────────────────────────────────────
dff = df[
    (df["SKU_ID"].isin(sel_skus)) &
    (df["Warehouse_ID"].isin(sel_whs)) &
    (df["Supplier_ID"].isin(sel_sups)) &
    (df["Region"].isin(sel_regs)) &
    (df["Date"] >= d0) &
    (df["Date"] <= d1)
].copy()

if dff.empty:
    st.warning("No data matches the current filters. Please adjust the sidebar.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📦 Supply Chain & Inventory Analytics Dashboard")
st.markdown(
    f"**Dataset:** {len(df):,} daily records across "
    f"{df['SKU_ID'].nunique()} SKUs · "
    f"{df['Warehouse_ID'].nunique()} Warehouses · "
    f"{df['Supplier_ID'].nunique()} Suppliers · "
    f"{df['Region'].nunique()} Regions | "
    f"Period: **{df['Date'].min().date()} → {df['Date'].max().date()}**"
)

filtered_note = f"_Showing **{len(dff):,}** filtered rows_"
st.markdown(filtered_note)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 KPIs & Overview",
    "📈 Demand & Trends",
    "🏷 Product Performance",
    "📦 Inventory & Risk",
    "🚚 Supplier Analysis",
    "🔖 ABC / XYZ",
    "💡 Insights & Actions",
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — KPIs & OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-title">Key Performance Indicators</div>', unsafe_allow_html=True)

    total_rev   = dff["Revenue"].sum()
    total_units = int(dff["Units_Sold"].sum())
    avg_margin  = dff["Margin_Pct"].mean()
    inv_val     = dff["Inventory_Value"].sum()
    avg_lt      = dff["Supplier_Lead_Time_Days"].mean()

    sku_s = tables.get("sku_summary", pd.DataFrame())
    if not sku_s.empty and "Inventory_Turnover" in sku_s.columns:
        avg_turn = sku_s["Inventory_Turnover"].mean()
        avg_doi  = sku_s["Avg_DOI"].mean()
    else:
        avg_turn = avg_doi = float("nan")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">${total_rev/1e6:.2f}M</div>
            <div class="kpi-sub">Filtered period</div></div>""",
            unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Units Sold</div>
            <div class="kpi-value">{total_units:,}</div>
            <div class="kpi-sub">Total units</div></div>""",
            unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Gross Margin</div>
            <div class="kpi-value">{avg_margin:.1f}%</div>
            <div class="kpi-sub">Avg across all SKUs</div></div>""",
            unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Inventory Value</div>
            <div class="kpi-value">${inv_val/1e6:.1f}M</div>
            <div class="kpi-sub">At cost</div></div>""",
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    with col6:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Avg Lead Time</div>
            <div class="kpi-value">{avg_lt:.1f} days</div>
            <div class="kpi-sub">Across all suppliers</div></div>""",
            unsafe_allow_html=True)
    with col7:
        val = f"{avg_turn:.2f}×" if not np.isnan(avg_turn) else "N/A"
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Inv. Turnover</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">COGS / avg inventory value</div></div>""",
            unsafe_allow_html=True)
    with col8:
        val = f"{avg_doi:.0f} days" if not np.isnan(avg_doi) else "N/A"
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Days of Inventory</div>
            <div class="kpi-value">{val}</div>
            <div class="kpi-sub">Avg across SKUs</div></div>""",
            unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.subheader("Dataset at a Glance")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Unique SKUs",       dff["SKU_ID"].nunique())
        st.metric("Unique Warehouses", dff["Warehouse_ID"].nunique())
    with col_b:
        st.metric("Unique Suppliers",  dff["Supplier_ID"].nunique())
        st.metric("Unique Regions",    dff["Region"].nunique())

    img = load_chart("01_monthly_revenue_units_trend.png")
    if img:
        st.image(img, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — DEMAND & TRENDS
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Demand & Sales Trends</div>', unsafe_allow_html=True)

    # Interactive monthly trend from filtered data
    monthly_f = (
        dff.groupby("YearMonth")
           .agg(Revenue=("Revenue", "sum"),
                Units_Sold=("Units_Sold", "sum"),
                Avg_Inventory=("Inventory_Level", "mean"))
           .reset_index()
    )

    fig, ax1 = plt.subplots(figsize=(12, 4))
    ax2 = ax1.twinx()
    ax1.bar(monthly_f["YearMonth"], monthly_f["Revenue"] / 1e6,
            color="#3b82f6", alpha=0.65, label="Revenue (M$)")
    ax2.plot(monthly_f["YearMonth"], monthly_f["Units_Sold"] / 1e3,
             color="#f59e0b", linewidth=2.2, marker="o", markersize=4,
             label="Units (K)")
    ax1.set_ylabel("Revenue (M $)", color="#3b82f6")
    ax2.set_ylabel("Units Sold (K)", color="#f59e0b")
    plt.xticks(rotation=45, ha="right")
    lines1, lab1 = ax1.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lab1 + lab2, loc="upper left")
    ax1.set_title("Monthly Revenue & Units Sold (filtered)", fontweight="bold")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("#### Average Units Sold by Day of Week")
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow = dff.groupby("DayOfWeek")["Units_Sold"].mean().reindex(dow_order)
    fig2, ax2_ = plt.subplots(figsize=(9, 3))
    ax2_.bar(dow.index, dow.values, color="#3b82f6")
    ax2_.set_ylabel("Avg Units / day")
    ax2_.set_title("Day-of-Week Demand Pattern", fontweight="bold")
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close()

    st.markdown("#### Promotion Impact")
    img = load_chart("09_promotion_impact.png")
    if img:
        st.image(img, use_container_width=True)

    st.markdown("#### Monthly Data Table")
    st.dataframe(monthly_f.rename(columns={
        "YearMonth": "Month",
        "Revenue": "Revenue ($)",
        "Units_Sold": "Units Sold",
        "Avg_Inventory": "Avg Inventory Level"
    }).style.format({
        "Revenue ($)": "${:,.0f}",
        "Units Sold":  "{:,.0f}",
        "Avg Inventory Level": "{:.0f}",
    }), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — PRODUCT PERFORMANCE
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Product / SKU Performance</div>', unsafe_allow_html=True)

    img = load_chart("02_top15_sku_revenue.png")
    if img:
        st.image(img, use_container_width=True)

    st.markdown("#### SKU Performance Table")
    sku_s = tables.get("sku_summary", pd.DataFrame())
    if not sku_s.empty:
        display_cols = [c for c in [
            "SKU_ID", "Total_Revenue", "Total_Units_Sold", "Gross_Profit",
            "Margin_Pct", "Inventory_Turnover", "Avg_DOI", "ABC_Class", "XYZ_Class"
        ] if c in sku_s.columns]
        show_sku = sku_s[display_cols].copy()
        fmt = {}
        if "Total_Revenue"       in show_sku.columns: fmt["Total_Revenue"]       = "${:,.0f}"
        if "Gross_Profit"        in show_sku.columns: fmt["Gross_Profit"]        = "${:,.0f}"
        if "Margin_Pct"          in show_sku.columns: fmt["Margin_Pct"]          = "{:.1f}%"
        if "Inventory_Turnover"  in show_sku.columns: fmt["Inventory_Turnover"]  = "{:.2f}×"
        if "Avg_DOI"             in show_sku.columns: fmt["Avg_DOI"]             = "{:.0f}d"
        st.dataframe(show_sku.style.format(fmt), use_container_width=True)

    st.markdown("#### Gross Margin Distribution")
    sku_margin = dff.groupby("SKU_ID")["Margin_Pct"].mean().sort_values(ascending=False)
    fig3, ax3 = plt.subplots(figsize=(12, 4))
    ax3.bar(sku_margin.index, sku_margin.values, color="#10b981")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    ax3.set_ylabel("Gross Margin (%)")
    ax3.set_title("Average Gross Margin by SKU (filtered)", fontweight="bold")
    fig3.tight_layout()
    st.pyplot(fig3)
    plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4 — INVENTORY & RISK
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">Inventory Levels & Risk</div>', unsafe_allow_html=True)

    img = load_chart("05_inventory_turnover.png")
    if img:
        st.image(img, use_container_width=True)

    img = load_chart("06_reorder_point_risk.png")
    if img:
        st.image(img, use_container_width=True)

    img = load_chart("10_inventory_risk.png")
    if img:
        st.image(img, use_container_width=True)

    st.markdown("#### SKUs Currently Below Reorder Point")
    below_rop = dff[dff["Below_ROP"] == 1].groupby("SKU_ID").agg(
        Days_Below_ROP = ("Below_ROP",       "sum"),
        Avg_Inventory  = ("Inventory_Level",  "mean"),
        Reorder_Point  = ("Reorder_Point",    "first"),
        Supplier       = ("Supplier_ID",      "first"),
        Avg_Lead_Time  = ("Supplier_Lead_Time_Days", "mean"),
    ).sort_values("Days_Below_ROP", ascending=False).reset_index()
    st.dataframe(below_rop.style.format({
        "Avg_Inventory": "{:.0f}",
        "Reorder_Point": "{:.0f}",
        "Avg_Lead_Time": "{:.1f}d",
    }), use_container_width=True)

    st.markdown("#### Reorder Recommendations")
    reorder = tables.get("reorder_recommendations", pd.DataFrame())
    if not reorder.empty:
        st.dataframe(reorder.style.format({
            "Avg_Lead_Time":  "{:.1f}d",
            "Avg_Inventory":  "{:.0f}",
            "Reorder_Point":  "{:.0f}",
        }), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 5 — SUPPLIER ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-title">Supplier & Lead-Time Analysis</div>', unsafe_allow_html=True)

    img = load_chart("07_supplier_lead_time.png")
    if img:
        st.image(img, use_container_width=True)

    img = load_chart("08_revenue_region_warehouse.png")
    if img:
        st.image(img, use_container_width=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### Supplier Summary")
        sup_s = tables.get("supplier_summary", pd.DataFrame())
        if not sup_s.empty:
            st.dataframe(sup_s.style.format({
                "Avg_Lead_Time": "{:.1f}d",
                "Total_Revenue": "${:,.0f}",
            }), use_container_width=True)
    with col_s2:
        st.markdown("#### Warehouse Summary")
        wh_s = tables.get("warehouse_summary", pd.DataFrame())
        if not wh_s.empty:
            st.dataframe(wh_s.style.format({
                "Total_Revenue": "${:,.0f}",
                "Avg_Inventory": "{:.0f}",
                "Avg_Lead_Time": "{:.1f}d",
            }), use_container_width=True)

    st.markdown("#### Region Summary")
    reg_s = tables.get("region_summary", pd.DataFrame())
    if not reg_s.empty:
        st.dataframe(reg_s.style.format({
            "Total_Revenue": "${:,.0f}",
        }), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 6 — ABC / XYZ
# ──────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-title">ABC & XYZ Inventory Classification</div>', unsafe_allow_html=True)

    st.markdown("""
**ABC Classification** groups SKUs by revenue contribution:
- **Class A** — Top 70% of revenue (typically ~20% of SKUs) — prioritise service level & monitoring
- **Class B** — Next 20% of revenue — moderate attention
- **Class C** — Bottom 10% — simplify or consolidate

**XYZ Classification** groups SKUs by demand variability (Coefficient of Variation):
- **X** (CoV ≤ 20%) — highly predictable demand — lean replenishment
- **Y** (CoV 20–50%) — moderately variable — safety stock buffer
- **Z** (CoV > 50%) — highly variable / erratic — review policies carefully
""")

    col_abc, col_xyz = st.columns(2)
    with col_abc:
        img = load_chart("03_abc_classification.png")
        if img:
            st.image(img, use_container_width=True)
    with col_xyz:
        img = load_chart("04_xyz_classification.png")
        if img:
            st.image(img, use_container_width=True)

    st.markdown("#### ABC × XYZ Matrix — SKU Detail")
    axyz = tables.get("abcxyz_matrix", pd.DataFrame())
    if not axyz.empty:
        # pivot counts
        if "ABC_Class" in axyz.columns and "XYZ_Class" in axyz.columns:
            pivot = axyz.pivot_table(
                index="ABC_Class", columns="XYZ_Class",
                values="SKU_ID", aggfunc="count", fill_value=0
            )
            st.markdown("**SKU count per ABC × XYZ cell:**")
            st.dataframe(pivot, use_container_width=False)

        st.markdown("**Full SKU detail:**")
        fmt2 = {}
        if "Total_Revenue"       in axyz.columns: fmt2["Total_Revenue"]       = "${:,.0f}"
        if "Inventory_Turnover"  in axyz.columns: fmt2["Inventory_Turnover"]  = "{:.2f}×"
        if "Avg_DOI"             in axyz.columns: fmt2["Avg_DOI"]             = "{:.0f}d"
        if "CoV"                 in axyz.columns: fmt2["CoV"]                 = "{:.1f}%"
        st.dataframe(axyz.style.format(fmt2), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 7 — INSIGHTS & ACTIONS
# ──────────────────────────────────────────────────────────────────────────────
with tab7:
    st.markdown('<div class="section-title">Business Insights & Replenishment Actions</div>', unsafe_allow_html=True)

    # Compute live insight values from filtered data
    sku_s   = tables.get("sku_summary", pd.DataFrame())
    top_rev = sku_s.nlargest(1, "Total_Revenue")["SKU_ID"].values[0] if not sku_s.empty else "N/A"

    a_skus  = sku_s[sku_s["ABC_Class"] == "A"]["SKU_ID"].tolist() if not sku_s.empty else []
    z_skus  = sku_s[sku_s["XYZ_Class"] == "Z"]["SKU_ID"].tolist() if not sku_s.empty else []

    high_lt = tables.get("supplier_summary", pd.DataFrame())
    top_lt_sup = high_lt.nlargest(1, "Avg_Lead_Time")["Supplier_ID"].values[0] if not high_lt.empty else "N/A"
    bot_lt_sup = high_lt.nsmallest(1, "Avg_Lead_Time")["Supplier_ID"].values[0] if not high_lt.empty else "N/A"

    below_rop_cnt = int(dff.groupby("SKU_ID")["Below_ROP"].max().sum())

    promo_uplift_avg = 0.0
    if "Promotion_Flag" in dff.columns:
        promo_avg = dff.groupby("Promotion_Flag")["Units_Sold"].mean()
        if 0 in promo_avg.index and 1 in promo_avg.index and promo_avg[0] > 0:
            promo_uplift_avg = (promo_avg[1] - promo_avg[0]) / promo_avg[0] * 100

    insights = [
        ("📈", "Demand Trend",
         "Sales patterns vary across the year, with higher and lower revenue periods visible in the dataset. "
"Replenishment planning should account for periods of elevated demand identified in the analysis."),
        ("🏆", "Top Revenue SKU",
         f"**{top_rev}** is the highest-revenue SKU. "
         "Ensure it has the highest service-level priority and a dedicated safety-stock buffer."),
        ("🔑", "Class-A SKUs",
         f"**{len(a_skus)} SKUs** (Class A) generate 70% of total revenue: "
         f"{', '.join(a_skus[:5])}{'…' if len(a_skus) > 5 else ''}. "
         "These should be reviewed weekly and monitored closely to maintain product availability."),
        ("⚠️", "Erratic Demand (Class Z)",
         f"**{len(z_skus)} SKUs** have highly erratic demand (XYZ Class Z, CoV > 50%). "
         "Consider increasing safety stock buffers or switching to a min-max replenishment policy."),
        ("🚨", "Below Reorder Point",
         f"**{below_rop_cnt} SKUs** have spent at least one day below their reorder point in the "
         "filtered window — see the Inventory & Risk tab for the full list and recommended actions."),
        ("🚚", "Lead-Time Variance",
         f"Supplier **{top_lt_sup}** has the longest average lead time. "
         f"Supplier **{bot_lt_sup}** is the fastest. "
         "Consider dual-sourcing critical Class A SKUs with long lead-time suppliers."),
        ("🎁", "Promotion Effectiveness",
         f"Promotional days drive an average **{promo_uplift_avg:+.1f}%** change in units sold. "
         "Review inventory levels ahead of promotions to maintain product availability during higher-demand periods."),
        ("📦", "Inventory Turnover",
         "SKUs with turnover < 2× per year are over-stocked. "
         "Review ordering quantities and consider promotional clearance to reduce carrying costs."),
    ]

    for icon, title, body in insights:
        st.markdown(
            f'<div class="insight-box"><strong>{icon} {title}:</strong> {body}</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("#### 🔧 Replenishment Recommendations")

    actions = [
        ("Immediate", "Place replenishment orders for all SKUs currently below their reorder point. "
          "Prioritise Class A SKUs first."),
        ("Short-term", "Increase safety stock for Class Z (erratic demand) SKUs by 20–30% to buffer against forecast error."),
        ("Short-term", "Pre-build inventory for Class A / promotional SKUs ahead of Q3 peak season."),
        ("Medium-term", "Negotiate lead-time reductions with the highest-lead-time supplier to bring it in line with the fleet average."),
        ("Medium-term", "Implement weekly demand review cycles for Class A+Z SKUs (high-revenue + erratic demand)."),
        ("Long-term", "Consider VMI (Vendor Managed Inventory) arrangements with reliable, low-lead-time suppliers for Class C SKUs to reduce internal admin overhead."),
    ]

    for horizon, action in actions:
        box_class = "warn-box" if horizon == "Immediate" else "insight-box"
        st.markdown(
            f'<div class="{box_class}"><strong>[{horizon}]</strong> {action}</div>',
            unsafe_allow_html=True
        )
