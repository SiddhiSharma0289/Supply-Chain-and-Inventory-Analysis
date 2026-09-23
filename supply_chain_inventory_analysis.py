"""
Supply Chain & Inventory Analytics
====================================
Loads, cleans, analyses the dataset and saves all charts + summary tables.
Run this script once before launching the Streamlit app.
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "data", "supply_chain_dataset.csv")
CHARTS_DIR  = os.path.join(BASE_DIR, "outputs", "charts")
TABLES_DIR  = os.path.join(BASE_DIR, "outputs", "tables")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)

PALETTE  = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444",
            "#8b5cf6", "#06b6d4", "#f97316", "#ec4899",
            "#84cc16", "#6366f1"]
BG       = "#ffffff"
GRID_CLR = "#e5e7eb"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": "#d1d5db", "axes.grid": True,
    "grid.color": GRID_CLR, "grid.linestyle": "--", "grid.linewidth": 0.6,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
    "font.family": "DejaVu Sans",
})

def savefig(name: str):
    path = os.path.join(CHARTS_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  OK saved {name}")

print("\n[1] Loading data ...")
df = pd.read_csv(DATA_PATH, parse_dates=["Date"])

print(f"    Shape            : {df.shape}")
print(f"    Columns          : {list(df.columns)}")
print(f"    Date range       : {df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"    Unique SKUs      : {df['SKU_ID'].nunique()}")
print(f"    Unique Warehouses: {df['Warehouse_ID'].nunique()}")
print(f"    Unique Suppliers : {df['Supplier_ID'].nunique()}")
print(f"    Unique Regions   : {df['Region'].nunique()}")

print("\n[2] Cleaning data ...")
before = len(df)
df.drop_duplicates(inplace=True)
print(f"    Duplicates removed: {before - len(df)}")

missing = df.isnull().sum()
print(f"    Missing values:\n{missing[missing > 0].to_string() if missing.any() else '    None'}")
df.dropna(inplace=True)

num_cols = ["Units_Sold", "Inventory_Level", "Supplier_Lead_Time_Days",
            "Reorder_Point", "Order_Quantity", "Unit_Cost", "Unit_Price",
            "Demand_Forecast"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["Promotion_Flag"] = df["Promotion_Flag"].astype(int)

invalid_mask = (
    (df["Units_Sold"] < 0) | (df["Inventory_Level"] < 0) |
    (df["Unit_Cost"] <= 0) | (df["Unit_Price"] <= 0)
)
n_invalid = invalid_mask.sum()
df = df[~invalid_mask].copy()
print(f"    Invalid rows removed: {n_invalid}")
print(f"    Clean dataset shape : {df.shape}")

print("\n[3] Computing derived metrics ...")
df["Revenue"]          = df["Units_Sold"] * df["Unit_Price"]
df["COGS"]             = df["Units_Sold"] * df["Unit_Cost"]
df["Gross_Profit"]     = df["Revenue"] - df["COGS"]
df["Margin_Pct"]       = df["Gross_Profit"] / df["Revenue"] * 100
df["Inventory_Value"]  = df["Inventory_Level"] * df["Unit_Cost"]
df["Forecast_Error"]   = df["Units_Sold"] - df["Demand_Forecast"]
df["Forecast_Acc_Pct"] = (
    1 - df["Forecast_Error"].abs() / df["Units_Sold"].replace(0, np.nan)
) * 100
df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
df["Month"] = df["Date"].dt.month
df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
df["DayOfWeek"] = df["Date"].dt.day_name()
df["DOI"] = df["Inventory_Level"] / df["Units_Sold"].replace(0, np.nan)
df["Below_ROP"] = (df["Inventory_Level"] < df["Reorder_Point"]).astype(int)

print("\n[4] Building summary tables ...")
sku_summary = (
    df.groupby("SKU_ID").agg(
        Total_Units_Sold=("Units_Sold", "sum"),
        Total_Revenue=("Revenue", "sum"),
        Total_COGS=("COGS", "sum"),
        Avg_Inventory=("Inventory_Level", "mean"),
        Avg_Inventory_Value=("Inventory_Value", "mean"),
        Below_ROP_Days=("Below_ROP", "sum"),
        Avg_Lead_Time=("Supplier_Lead_Time_Days", "mean"),
        Promo_Days=("Promotion_Flag", "sum"),
        Avg_Unit_Cost=("Unit_Cost", "mean"),
        Avg_Unit_Price=("Unit_Price", "mean"),
        Avg_Forecast_Acc=("Forecast_Acc_Pct", "mean"),
        Total_Days=("Date", "count"),
    ).reset_index()
)
sku_summary["Gross_Profit"] = sku_summary["Total_Revenue"] - sku_summary["Total_COGS"]
sku_summary["Margin_Pct"] = sku_summary["Gross_Profit"] / sku_summary["Total_Revenue"] * 100
sku_summary["Inventory_Turnover"] = sku_summary["Total_COGS"] / sku_summary["Avg_Inventory_Value"].replace(0, np.nan)
sku_summary["Avg_DOI"] = 365 / sku_summary["Inventory_Turnover"].replace(0, np.nan)

sku_summary.sort_values("Total_Revenue", ascending=False, inplace=True)
sku_summary["Cumulative_Rev_Pct"] = (
    sku_summary["Total_Revenue"].cumsum() / sku_summary["Total_Revenue"].sum() * 100
)
def abc_class(pct):
    if pct <= 70: return "A"
    if pct <= 90: return "B"
    return "C"
sku_summary["ABC_Class"] = sku_summary["Cumulative_Rev_Pct"].apply(abc_class)

xyz = (
    df.groupby("SKU_ID")["Units_Sold"]
      .agg(["mean", "std"])
      .rename(columns={"mean": "Avg_Demand", "std": "Std_Demand"})
      .reset_index()
)
xyz["CoV"] = xyz["Std_Demand"] / xyz["Avg_Demand"].replace(0, np.nan) * 100
def xyz_class(cov):
    if cov <= 20: return "X"
    if cov <= 50: return "Y"
    return "Z"
xyz["XYZ_Class"] = xyz["CoV"].apply(xyz_class)
sku_summary = sku_summary.merge(xyz[["SKU_ID", "CoV", "XYZ_Class"]], on="SKU_ID", how="left")
sku_summary.to_csv(os.path.join(TABLES_DIR, "sku_summary.csv"), index=False)

monthly = (
    df.groupby("YearMonth").agg(
        Total_Units_Sold=("Units_Sold", "sum"),
        Total_Revenue=("Revenue", "sum"),
        Avg_Inventory=("Inventory_Level", "mean"),
        Below_ROP_Days=("Below_ROP", "sum"),
        Promo_Days=("Promotion_Flag", "sum"),
    ).reset_index()
)
monthly.to_csv(os.path.join(TABLES_DIR, "monthly_trends.csv"), index=False)

wh_summary = (
    df.groupby("Warehouse_ID").agg(
        Total_Revenue=("Revenue", "sum"),
        Total_Units=("Units_Sold", "sum"),
        Avg_Inventory=("Inventory_Level", "mean"),
        Below_ROP_Days=("Below_ROP", "sum"),
        Avg_Lead_Time=("Supplier_Lead_Time_Days", "mean"),
    ).reset_index()
)
wh_summary.to_csv(os.path.join(TABLES_DIR, "warehouse_summary.csv"), index=False)

sup_summary = (
    df.groupby("Supplier_ID").agg(
        Avg_Lead_Time=("Supplier_Lead_Time_Days", "mean"),
        Total_Units=("Units_Sold", "sum"),
        Total_Revenue=("Revenue", "sum"),
        SKUs_Supplied=("SKU_ID", "nunique"),
    ).reset_index()
)
sup_summary.to_csv(os.path.join(TABLES_DIR, "supplier_summary.csv"), index=False)

region_summary = (
    df.groupby("Region").agg(
        Total_Revenue=("Revenue", "sum"),
        Total_Units=("Units_Sold", "sum"),
        Below_ROP_Days=("Below_ROP", "sum"),
    ).reset_index()
)
region_summary.to_csv(os.path.join(TABLES_DIR, "region_summary.csv"), index=False)

kpi = {
    "total_revenue": round(df["Revenue"].sum(), 2),
    "total_units_sold": int(df["Units_Sold"].sum()),
    "avg_gross_margin_pct": round(df["Margin_Pct"].mean(), 2),
    "total_inventory_value": round(df["Inventory_Value"].sum(), 2),
    "avg_inventory_turnover": round(sku_summary["Inventory_Turnover"].mean(), 2),
    "avg_doi": round(sku_summary["Avg_DOI"].mean(), 2),
    "avg_lead_time_days": round(df["Supplier_Lead_Time_Days"].mean(), 2),
    "sku_count": df["SKU_ID"].nunique(),
    "warehouse_count": df["Warehouse_ID"].nunique(),
    "supplier_count": df["Supplier_ID"].nunique(),
}
pd.Series(kpi).to_csv(os.path.join(TABLES_DIR, "kpi_snapshot.csv"), header=["Value"])

print("\n[5] Generating charts ...")
def autolabel(ax, fmt="{:.0f}", rotation=0, fontsize=8):
    for bar in ax.patches:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01,
                    fmt.format(h), ha="center", va="bottom",
                    fontsize=fontsize, rotation=rotation)

fig, ax1 = plt.subplots(figsize=(13, 5))
ax2 = ax1.twinx()
ax1.bar(monthly["YearMonth"], monthly["Total_Revenue"] / 1e6, color=PALETTE[0], alpha=0.7, label="Revenue (M$)")
ax2.plot(monthly["YearMonth"], monthly["Total_Units_Sold"] / 1e3, color=PALETTE[1], linewidth=2.5, marker="o", markersize=5, label="Units Sold (K)")
ax1.set_xlabel("Month"); ax1.set_ylabel("Revenue (M $)", color=PALETTE[0]); ax2.set_ylabel("Units Sold (K)", color=PALETTE[1])
plt.xticks(rotation=45, ha="right")
lines1, labels1 = ax1.get_legend_handles_labels(); lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
ax1.set_title("Monthly Revenue & Units Sold Trend (2024)")
fig.tight_layout(); savefig("01_monthly_revenue_units_trend.png")

top15 = sku_summary.nlargest(15, "Total_Revenue")
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(top15["SKU_ID"][::-1], top15["Total_Revenue"][::-1] / 1e3, color=PALETTE[0])
ax.set_xlabel("Total Revenue (K $)"); ax.set_title("Top 15 SKUs by Total Revenue")
for bar, val in zip(bars, top15["Total_Revenue"][::-1]):
    ax.text(bar.get_width() * 1.005, bar.get_y() + bar.get_height() / 2, f"${val/1e3:.1f}K", va="center", fontsize=8)
fig.tight_layout(); savefig("02_top15_sku_revenue.png")

abc_counts = sku_summary["ABC_Class"].value_counts().sort_index()
abc_rev = sku_summary.groupby("ABC_Class")["Total_Revenue"].sum()
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
axes[0].bar(abc_counts.index, abc_counts.values, color=[PALETTE[0], PALETTE[2], PALETTE[1]])
axes[0].set_title("ABC Classes — SKU Count"); axes[0].set_xlabel("ABC Class"); axes[0].set_ylabel("Number of SKUs")
for i, v in enumerate(abc_counts.values): axes[0].text(i, v + 0.3, str(v), ha="center", fontsize=9)
axes[1].pie(abc_rev.values, labels=abc_rev.index, autopct="%1.1f%%", startangle=90, colors=[PALETTE[0], PALETTE[2], PALETTE[1]])
axes[1].set_title("ABC Classes — Revenue Share")
fig.suptitle("ABC Inventory Classification (by Revenue Contribution)", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("03_abc_classification.png")

xyz_counts = sku_summary["XYZ_Class"].value_counts().sort_index()
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
axes[0].bar(xyz_counts.index, xyz_counts.values, color=[PALETTE[2], PALETTE[1], PALETTE[3]])
axes[0].set_title("XYZ Classes — SKU Count"); axes[0].set_xlabel("XYZ Class"); axes[0].set_ylabel("Number of SKUs")
for i, v in enumerate(xyz_counts.values): axes[0].text(i, v + 0.3, str(v), ha="center", fontsize=9)
axes[1].hist(sku_summary["CoV"].dropna(), bins=20, color=PALETTE[4], edgecolor="white")
axes[1].axvline(20, color=PALETTE[2], linestyle="--", label="X/Y boundary (20%)")
axes[1].axvline(50, color=PALETTE[3], linestyle="--", label="Y/Z boundary (50%)")
axes[1].set_xlabel("Coefficient of Variation (%)"); axes[1].set_ylabel("Number of SKUs"); axes[1].set_title("CoV Distribution Across SKUs"); axes[1].legend()
fig.suptitle("XYZ Demand Variability Classification", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("04_xyz_classification.png")

sku_turn = sku_summary.dropna(subset=["Inventory_Turnover"])
top10_turn = sku_turn.nlargest(10, "Inventory_Turnover"); bot10_turn = sku_turn.nsmallest(10, "Inventory_Turnover")
fig, axes = plt.subplots(1, 2, figsize=(13, 6))
axes[0].barh(top10_turn["SKU_ID"][::-1], top10_turn["Inventory_Turnover"][::-1], color=PALETTE[2])
axes[0].set_title("Top 10 — Highest Turnover"); axes[0].set_xlabel("Inventory Turnover (×)")
axes[1].barh(bot10_turn["SKU_ID"][::-1], bot10_turn["Inventory_Turnover"][::-1], color=PALETTE[3])
axes[1].set_title("Bottom 10 — Lowest Turnover"); axes[1].set_xlabel("Inventory Turnover (×)")
fig.suptitle("Inventory Turnover by SKU", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("05_inventory_turnover.png")

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
rop_risk = df.groupby("SKU_ID")["Below_ROP"].mean().mul(100).sort_values(ascending=False).head(15)
axes[0].barh(rop_risk.index[::-1], rop_risk.values[::-1], color=PALETTE[3])
axes[0].set_xlabel("% of Days Below Reorder Point"); axes[0].set_title("Top 15 SKUs — Below Reorder Point")
wh_rop = df.groupby("Warehouse_ID")["Below_ROP"].mean().mul(100).sort_values(ascending=False)
axes[1].bar(wh_rop.index, wh_rop.values, color=PALETTE[1])
axes[1].set_xlabel("Warehouse"); axes[1].set_ylabel("% of Days Below Reorder Point"); axes[1].set_title("Below-ROP Rate by Warehouse")
autolabel(axes[1], "{:.1f}")
fig.suptitle("Reorder Point Risk Analysis", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("06_reorder_point_risk.png")

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sup_lt = df.groupby("Supplier_ID")["Supplier_Lead_Time_Days"].mean().sort_values()
axes[0].barh(sup_lt.index, sup_lt.values, color=PALETTE[5])
axes[0].set_xlabel("Avg Lead Time (days)"); axes[0].set_title("Average Lead Time by Supplier")
for i, v in enumerate(sup_lt.values): axes[0].text(v + 0.1, i, f"{v:.1f}d", va="center", fontsize=8)
df["Supplier_Lead_Time_Days"].plot.hist(ax=axes[1], bins=20, color=PALETTE[5], edgecolor="white")
axes[1].set_xlabel("Lead Time (days)"); axes[1].set_title("Overall Lead-Time Distribution")
fig.suptitle("Supplier Lead-Time Analysis", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("07_supplier_lead_time.png")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
reg_rev = df.groupby("Region")["Revenue"].sum().sort_values(ascending=False)
axes[0].bar(reg_rev.index, reg_rev.values / 1e6, color=PALETTE[6]); axes[0].set_ylabel("Revenue (M $)"); axes[0].set_title("Revenue by Region"); autolabel(axes[0], "{:.1f}")
wh_rev = df.groupby("Warehouse_ID")["Revenue"].sum().sort_values(ascending=False)
axes[1].bar(wh_rev.index, wh_rev.values / 1e6, color=PALETTE[7]); axes[1].set_ylabel("Revenue (M $)"); axes[1].set_title("Revenue by Warehouse"); autolabel(axes[1], "{:.1f}")
fig.suptitle("Revenue Distribution by Region & Warehouse", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("08_revenue_region_warehouse.png")

promo_impact = (
    df.groupby(["SKU_ID", "Promotion_Flag"])["Units_Sold"].mean()
      .unstack(fill_value=0).rename(columns={0: "No Promo", 1: "Promo"})
)
promo_impact = promo_impact[(promo_impact["No Promo"] > 0) & (promo_impact["Promo"] > 0)]
promo_impact["Promo_Uplift_Pct"] = (promo_impact["Promo"] - promo_impact["No Promo"]) / promo_impact["No Promo"] * 100
promo_uplift = promo_impact["Promo_Uplift_Pct"].sort_values(ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(13, 6))
promo_uplift.head(15).plot.barh(ax=axes[0], color=PALETTE[2])
axes[0].axvline(0, color="black", linewidth=0.8); axes[0].set_xlabel("Uplift (%)"); axes[0].set_title("Top 15 SKUs — Promotion Sales Uplift")
avg_promo = df.groupby("Promotion_Flag")["Units_Sold"].mean()
labels = ["No Promotion", "Promotion Active"]
axes[1].bar(labels, avg_promo.values, color=[PALETTE[0], PALETTE[2]], width=0.5)
axes[1].set_ylabel("Avg Units Sold / day"); axes[1].set_title("Avg Daily Units Sold:\nPromotion vs No Promotion")
for i, v in enumerate(avg_promo.values): axes[1].text(i, v + 0.2, f"{v:.1f}", ha="center", fontsize=10)
fig.suptitle("Promotion Impact Analysis", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("09_promotion_impact.png")

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
abc_colors = {"A": PALETTE[0], "B": PALETTE[1], "C": PALETTE[3]}
for cls, grp in sku_summary.groupby("ABC_Class"):
    axes[0].scatter(grp["Inventory_Turnover"], grp["Avg_DOI"], label=f"Class {cls}", color=abc_colors[cls], s=60, alpha=0.8)
axes[0].set_xlabel("Inventory Turnover (×)"); axes[0].set_ylabel("Days of Inventory on Hand"); axes[0].set_title("Inventory Risk Matrix\n(Turnover vs DOI, coloured by ABC)"); axes[0].legend()
rop_risk = df.groupby("SKU_ID")["Below_ROP"].mean().mul(100).sort_values(ascending=False).head(15)
axes[1].barh(rop_risk.index[::-1], rop_risk.values[::-1], color=PALETTE[3])
axes[1].set_xlabel("% of Days Below Reorder Point"); axes[1].set_title("Top 15 SKUs — Days Below Reorder Point")
fig.suptitle("Inventory Risk Analysis", fontsize=13, fontweight="bold")
fig.tight_layout(); savefig("10_inventory_risk.png")

print("\n[6] Saving insight tables ...")
abcxyz = sku_summary[["SKU_ID", "Total_Revenue", "ABC_Class", "XYZ_Class", "CoV", "Inventory_Turnover", "Avg_DOI", "Below_ROP_Days"]].copy()
abcxyz.to_csv(os.path.join(TABLES_DIR, "abcxyz_matrix.csv"), index=False)

reorder = df[df["Below_ROP"] == 1].groupby("SKU_ID").agg(
    Below_ROP_Days=("Below_ROP", "sum"),
    Avg_Lead_Time=("Supplier_Lead_Time_Days", "mean"),
    Avg_Inventory=("Inventory_Level", "mean"),
    Reorder_Point=("Reorder_Point", "first"),
    Supplier=("Supplier_ID", "first"),
).reset_index().sort_values("Below_ROP_Days", ascending=False)
reorder.to_csv(os.path.join(TABLES_DIR, "reorder_recommendations.csv"), index=False)

print("    Insight tables saved")
print("\nDone  Analysis complete — all charts and tables are in outputs/")


"""
Supply Chain & Inventory Analytics - Streamlit App
====================================================
Run with: streamlit run supply_chain_inventory_analysis.py
"""

import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Supply Chain & Inventory Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Reuse the cleaned/analysed dataframe and generated outputs above.
st.markdown("""
<style>
    .kpi-card { background:#f7f8fa; border:1px solid #e5e7eb; border-radius:10px; padding:18px 20px; text-align:center; }
    .kpi-label { font-size:12px; color:#57606a; margin-bottom:4px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; }
    .kpi-value { font-size:26px; font-weight:700; color:#1f2328; }
    .kpi-sub { font-size:11px; color:#57606a; margin-top:2px; }
    .section-title { font-size:20px; font-weight:700; color:#1f2328; margin-top:24px; margin-bottom:4px; }
    .divider { border-top:1px solid #e5e7eb; margin:12px 0 20px 0; }
    .insight-box { background:#f0f7ff; border-left:4px solid #3b82f6; border-radius:0 8px 8px 0; padding:12px 16px; margin-bottom:10px; font-size:14px; color:#1f2328; }
    .warn-box { background:#fff7ed; border-left:4px solid #f59e0b; border-radius:0 8px 8px 0; padding:12px 16px; margin-bottom:10px; font-size:14px; color:#1f2328; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading data …")
def load_data():
    data = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    data.drop_duplicates(inplace=True)
    data.dropna(inplace=True)
    num_cols = ["Units_Sold","Inventory_Level","Supplier_Lead_Time_Days",
                "Reorder_Point","Order_Quantity","Unit_Cost","Unit_Price",
                "Demand_Forecast"]
    for c in num_cols:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data["Promotion_Flag"] = data["Promotion_Flag"].astype(int)
    invalid_mask = (
        (data["Units_Sold"] < 0) | (data["Inventory_Level"] < 0) |
        (data["Unit_Cost"] <= 0) | (data["Unit_Price"] <= 0)
    )
    data = data[~invalid_mask].copy()
    data["Revenue"] = data["Units_Sold"] * data["Unit_Price"]
    data["COGS"] = data["Units_Sold"] * data["Unit_Cost"]
    data["Gross_Profit"] = data["Revenue"] - data["COGS"]
    data["Margin_Pct"] = data["Gross_Profit"] / data["Revenue"] * 100
    data["Inventory_Value"] = data["Inventory_Level"] * data["Unit_Cost"]
    data["Forecast_Error"] = data["Units_Sold"] - data["Demand_Forecast"]
    data["YearMonth"] = data["Date"].dt.to_period("M").astype(str)
    data["Month"] = data["Date"].dt.month
    data["DayOfWeek"] = data["Date"].dt.day_name()
    data["DOI"] = data["Inventory_Level"] / data["Units_Sold"].replace(0, np.nan)
    data["Below_ROP"] = (data["Inventory_Level"] < data["Reorder_Point"]).astype(int)
    return data

def load_tables():
    result = {}
    for name in ["sku_summary","monthly_trends","warehouse_summary",
                 "supplier_summary","region_summary","kpi_snapshot",
                 "abcxyz_matrix","reorder_recommendations"]:
        path = os.path.join(TABLES_DIR, f"{name}.csv")
        if os.path.exists(path):
            result[name] = pd.read_csv(path)
    return result

def load_chart(filename):
    path = os.path.join(CHARTS_DIR, filename)
    return Image.open(path) if os.path.exists(path) else None

df = load_data()
tables = load_tables()

with st.sidebar:
    st.image("https://img.icons8.com/color/96/warehouse.png", width=60)
    st.title("📦 Supply Chain\nAnalytics")
    st.markdown("---")
    st.subheader("🔍 Filters")

    all_skus = sorted(df["SKU_ID"].unique())
    all_whs = sorted(df["Warehouse_ID"].unique())
    all_sups = sorted(df["Supplier_ID"].unique())
    all_regs = sorted(df["Region"].unique())

    sel_skus = st.multiselect("SKU(s)", all_skus, default=all_skus, key="f_sku")
    sel_whs = st.multiselect("Warehouse(s)", all_whs, default=all_whs, key="f_wh")
    sel_sups = st.multiselect("Supplier(s)", all_sups, default=all_sups, key="f_sup")
    sel_regs = st.multiselect("Region(s)", all_regs, default=all_regs, key="f_reg")

    date_min = df["Date"].min().date()
    date_max = df["Date"].max().date()
    sel_dates = st.date_input("Date Range", value=(date_min, date_max),
                              min_value=date_min, max_value=date_max)
    if isinstance(sel_dates, (list, tuple)) and len(sel_dates) == 2:
        d0, d1 = pd.Timestamp(sel_dates[0]), pd.Timestamp(sel_dates[1])
    else:
        d0, d1 = pd.Timestamp(date_min), pd.Timestamp(date_max)

    st.markdown("---")
    st.caption("© 2024 Supply Chain Analytics")

dff = df[
    df["SKU_ID"].isin(sel_skus) &
    df["Warehouse_ID"].isin(sel_whs) &
    df["Supplier_ID"].isin(sel_sups) &
    df["Region"].isin(sel_regs) &
    (df["Date"] >= d0) & (df["Date"] <= d1)
].copy()

if dff.empty:
    st.warning("No data matches the current filters. Please adjust the sidebar.")
    st.stop()

st.markdown("# 📦 Supply Chain & Inventory Analytics Dashboard")
st.markdown(
    f"**Dataset:** {len(df):,} daily records across "
    f"{df['SKU_ID'].nunique()} SKUs · {df['Warehouse_ID'].nunique()} Warehouses · "
    f"{df['Supplier_ID'].nunique()} Suppliers · {df['Region'].nunique()} Regions | "
    f"Period: **{df['Date'].min().date()} → {df['Date'].max().date()}**"
)
st.markdown(f"_Showing **{len(dff):,}** filtered rows_")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 KPIs & Overview","📈 Demand & Trends","🏷 Product Performance",
    "📦 Inventory & Risk","🚚 Supplier Analysis","🔖 ABC / XYZ",
    "💡 Insights & Actions",
])

with tab1:
    st.markdown('<div class="section-title">Key Performance Indicators</div>', unsafe_allow_html=True)
    total_rev = dff["Revenue"].sum(); total_units = int(dff["Units_Sold"].sum())
    avg_margin = dff["Margin_Pct"].mean(); inv_val = dff["Inventory_Value"].sum()
    avg_lt = dff["Supplier_Lead_Time_Days"].mean()
    sku_s = tables.get("sku_summary", pd.DataFrame())
    if not sku_s.empty and "Inventory_Turnover" in sku_s.columns:
        avg_turn = sku_s["Inventory_Turnover"].mean(); avg_doi = sku_s["Avg_DOI"].mean()
    else:
        avg_turn = avg_doi = float("nan")

    col1,col2,col3,col4 = st.columns(4)
    with col1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Revenue</div><div class="kpi-value">${total_rev/1e6:.2f}M</div><div class="kpi-sub">Filtered period</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Units Sold</div><div class="kpi-value">{total_units:,}</div><div class="kpi-sub">Total units</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Gross Margin</div><div class="kpi-value">{avg_margin:.1f}%</div><div class="kpi-sub">Avg across all SKUs</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Inventory Value</div><div class="kpi-value">${inv_val/1e6:.1f}M</div><div class="kpi-sub">At cost</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col5,col6,col7,col8 = st.columns(4)
    with col6: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Avg Lead Time</div><div class="kpi-value">{avg_lt:.1f} days</div><div class="kpi-sub">Across all suppliers</div></div>', unsafe_allow_html=True)
    with col7:
        val = f"{avg_turn:.2f}×" if not np.isnan(avg_turn) else "N/A"
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Inv. Turnover</div><div class="kpi-value">{val}</div><div class="kpi-sub">COGS / avg inventory value</div></div>', unsafe_allow_html=True)
    with col8:
        val = f"{avg_doi:.0f} days" if not np.isnan(avg_doi) else "N/A"
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Days of Inventory</div><div class="kpi-value">{val}</div><div class="kpi-sub">Avg across SKUs</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.subheader("Dataset at a Glance")
    col_a,col_b = st.columns(2)
    with col_a:
        st.metric("Unique SKUs", dff["SKU_ID"].nunique()); st.metric("Unique Warehouses", dff["Warehouse_ID"].nunique())
    with col_b:
        st.metric("Unique Suppliers", dff["Supplier_ID"].nunique()); st.metric("Unique Regions", dff["Region"].nunique())
    img = load_chart("01_monthly_revenue_units_trend.png")
    if img: st.image(img, use_container_width=True)

with tab2:
    st.markdown('<div class="section-title">Demand & Sales Trends</div>', unsafe_allow_html=True)
    monthly_f = dff.groupby("YearMonth").agg(
        Revenue=("Revenue","sum"), Units_Sold=("Units_Sold","sum"),
        Avg_Inventory=("Inventory_Level","mean")).reset_index()
    fig, ax1 = plt.subplots(figsize=(12,4)); ax2 = ax1.twinx()
    ax1.bar(monthly_f["YearMonth"], monthly_f["Revenue"]/1e6, color="#3b82f6", alpha=.65, label="Revenue (M$)")
    ax2.plot(monthly_f["YearMonth"], monthly_f["Units_Sold"]/1e3, color="#f59e0b", linewidth=2.2, marker="o", markersize=4, label="Units (K)")
    ax1.set_ylabel("Revenue (M $)"); ax2.set_ylabel("Units Sold (K)"); plt.xticks(rotation=45, ha="right")
    lines1,lab1=ax1.get_legend_handles_labels(); lines2,lab2=ax2.get_legend_handles_labels()
    ax1.legend(lines1+lines2,lab1+lab2,loc="upper left"); ax1.set_title("Monthly Revenue & Units Sold (filtered)",fontweight="bold")
    fig.tight_layout(); st.pyplot(fig); plt.close()
    st.markdown("#### Average Units Sold by Day of Week")
    dow_order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    dow=dff.groupby("DayOfWeek")["Units_Sold"].mean().reindex(dow_order)
    fig2,ax2_=plt.subplots(figsize=(9,3)); ax2_.bar(dow.index,dow.values,color="#3b82f6"); ax2_.set_ylabel("Avg Units / day"); ax2_.set_title("Day-of-Week Demand Pattern",fontweight="bold"); fig2.tight_layout(); st.pyplot(fig2); plt.close()
    st.markdown("#### Promotion Impact")
    img=load_chart("09_promotion_impact.png")
    if img: st.image(img,use_container_width=True)
    st.markdown("#### Monthly Data Table")
    st.dataframe(monthly_f.rename(columns={"YearMonth":"Month","Revenue":"Revenue ($)","Units_Sold":"Units Sold","Avg_Inventory":"Avg Inventory Level"}).style.format({"Revenue ($)":"${:,.0f}","Units Sold":"{:,.0f}","Avg Inventory Level":"{:.0f}"}),use_container_width=True)

with tab3:
    st.markdown('<div class="section-title">Product / SKU Performance</div>', unsafe_allow_html=True)
    img=load_chart("02_top15_sku_revenue.png")
    if img: st.image(img,use_container_width=True)
    st.markdown("#### SKU Performance Table")
    sku_s=tables.get("sku_summary",pd.DataFrame())
    if not sku_s.empty:
        display_cols=[c for c in ["SKU_ID","Total_Revenue","Total_Units_Sold","Gross_Profit","Margin_Pct","Inventory_Turnover","Avg_DOI","ABC_Class","XYZ_Class"] if c in sku_s.columns]
        show_sku=sku_s[display_cols].copy(); fmt={}
        if "Total_Revenue" in show_sku.columns: fmt["Total_Revenue"]="${:,.0f}"
        if "Gross_Profit" in show_sku.columns: fmt["Gross_Profit"]="${:,.0f}"
        if "Margin_Pct" in show_sku.columns: fmt["Margin_Pct"]="{:.1f}%"
        if "Inventory_Turnover" in show_sku.columns: fmt["Inventory_Turnover"]="{:.2f}×"
        if "Avg_DOI" in show_sku.columns: fmt["Avg_DOI"]="{:.0f}d"
        st.dataframe(show_sku.style.format(fmt),use_container_width=True)
    st.markdown("#### Gross Margin Distribution")
    sku_margin=dff.groupby("SKU_ID")["Margin_Pct"].mean().sort_values(ascending=False)
    fig3,ax3=plt.subplots(figsize=(12,4)); ax3.bar(sku_margin.index,sku_margin.values,color="#10b981"); plt.xticks(rotation=45,ha="right",fontsize=8); ax3.set_ylabel("Gross Margin (%)"); ax3.set_title("Average Gross Margin by SKU (filtered)",fontweight="bold"); fig3.tight_layout(); st.pyplot(fig3); plt.close()

with tab4:
    st.markdown('<div class="section-title">Inventory Levels & Risk</div>', unsafe_allow_html=True)
    for filename in ["05_inventory_turnover.png","06_reorder_point_risk.png","10_inventory_risk.png"]:
        img=load_chart(filename)
        if img: st.image(img,use_container_width=True)
    st.markdown("#### SKUs Currently Below Reorder Point")
    below_rop=dff[dff["Below_ROP"]==1].groupby("SKU_ID").agg(
        Days_Below_ROP=("Below_ROP","sum"), Avg_Inventory=("Inventory_Level","mean"),
        Reorder_Point=("Reorder_Point","first"), Supplier=("Supplier_ID","first"),
        Avg_Lead_Time=("Supplier_Lead_Time_Days","mean")).sort_values("Days_Below_ROP",ascending=False).reset_index()
    st.dataframe(below_rop.style.format({"Avg_Inventory":"{:.0f}","Reorder_Point":"{:.0f}","Avg_Lead_Time":"{:.1f}d"}),use_container_width=True)
    st.markdown("#### Reorder Recommendations")
    reorder=tables.get("reorder_recommendations",pd.DataFrame())
    if not reorder.empty: st.dataframe(reorder.style.format({"Avg_Lead_Time":"{:.1f}d","Avg_Inventory":"{:.0f}","Reorder_Point":"{:.0f}"}),use_container_width=True)

with tab5:
    st.markdown('<div class="section-title">Supplier & Lead-Time Analysis</div>', unsafe_allow_html=True)
    for filename in ["07_supplier_lead_time.png","08_revenue_region_warehouse.png"]:
        img=load_chart(filename)
        if img: st.image(img,use_container_width=True)
    col_s1,col_s2=st.columns(2)
    with col_s1:
        st.markdown("#### Supplier Summary"); sup_s=tables.get("supplier_summary",pd.DataFrame())
        if not sup_s.empty: st.dataframe(sup_s.style.format({"Avg_Lead_Time":"{:.1f}d","Total_Revenue":"${:,.0f}"}),use_container_width=True)
    with col_s2:
        st.markdown("#### Warehouse Summary"); wh_s=tables.get("warehouse_summary",pd.DataFrame())
        if not wh_s.empty: st.dataframe(wh_s.style.format({"Total_Revenue":"${:,.0f}","Avg_Inventory":"{:.0f}","Avg_Lead_Time":"{:.1f}d"}),use_container_width=True)
    st.markdown("#### Region Summary"); reg_s=tables.get("region_summary",pd.DataFrame())
    if not reg_s.empty: st.dataframe(reg_s.style.format({"Total_Revenue":"${:,.0f}"}),use_container_width=True)

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
    col_abc,col_xyz=st.columns(2)
    with col_abc:
        img=load_chart("03_abc_classification.png")
        if img: st.image(img,use_container_width=True)
    with col_xyz:
        img=load_chart("04_xyz_classification.png")
        if img: st.image(img,use_container_width=True)
    st.markdown("#### ABC × XYZ Matrix — SKU Detail")
    axyz=tables.get("abcxyz_matrix",pd.DataFrame())
    if not axyz.empty:
        if "ABC_Class" in axyz.columns and "XYZ_Class" in axyz.columns:
            pivot=axyz.pivot_table(index="ABC_Class",columns="XYZ_Class",values="SKU_ID",aggfunc="count",fill_value=0)
            st.markdown("**SKU count per ABC × XYZ cell:**"); st.dataframe(pivot,use_container_width=False)
        st.markdown("**Full SKU detail:**"); fmt2={}
        if "Total_Revenue" in axyz.columns: fmt2["Total_Revenue"]="${:,.0f}"
        if "Inventory_Turnover" in axyz.columns: fmt2["Inventory_Turnover"]="{:.2f}×"
        if "Avg_DOI" in axyz.columns: fmt2["Avg_DOI"]="{:.0f}d"
        if "CoV" in axyz.columns: fmt2["CoV"]="{:.1f}%"
        st.dataframe(axyz.style.format(fmt2),use_container_width=True)

with tab7:
    st.markdown('<div class="section-title">Business Insights & Replenishment Actions</div>', unsafe_allow_html=True)
    sku_s=tables.get("sku_summary",pd.DataFrame())
    top_rev=sku_s.nlargest(1,"Total_Revenue")["SKU_ID"].values[0] if not sku_s.empty else "N/A"
    a_skus=sku_s[sku_s["ABC_Class"]=="A"]["SKU_ID"].tolist() if not sku_s.empty else []
    z_skus=sku_s[sku_s["XYZ_Class"]=="Z"]["SKU_ID"].tolist() if not sku_s.empty else []
    high_lt=tables.get("supplier_summary",pd.DataFrame())
    top_lt_sup=high_lt.nlargest(1,"Avg_Lead_Time")["Supplier_ID"].values[0] if not high_lt.empty else "N/A"
    bot_lt_sup=high_lt.nsmallest(1,"Avg_Lead_Time")["Supplier_ID"].values[0] if not high_lt.empty else "N/A"
    below_rop_cnt=int(dff.groupby("SKU_ID")["Below_ROP"].max().sum())
    promo_uplift_avg=0.0
    if "Promotion_Flag" in dff.columns:
        promo_avg=dff.groupby("Promotion_Flag")["Units_Sold"].mean()
        if 0 in promo_avg.index and 1 in promo_avg.index and promo_avg[0] > 0:
            promo_uplift_avg=(promo_avg[1]-promo_avg[0])/promo_avg[0]*100
    insights=[
        ("📈","Demand Trend","Sales patterns vary across the year, with higher and lower revenue periods visible in the dataset. Replenishment planning should account for periods of elevated demand identified in the analysis."),
        ("🏆","Top Revenue SKU",f"**{top_rev}** is the highest-revenue SKU. Ensure it has the highest service-level priority and a dedicated safety-stock buffer."),
        ("🔑","Class-A SKUs",f"**{len(a_skus)} SKUs** (Class A) generate 70% of total revenue: {', '.join(a_skus[:5])}{'…' if len(a_skus)>5 else ''}. These should be reviewed weekly and monitored closely to maintain product availability."),
        ("⚠️","Erratic Demand (Class Z)",f"**{len(z_skus)} SKUs** have highly erratic demand (XYZ Class Z, CoV > 50%). Consider increasing safety stock buffers or switching to a min-max replenishment policy."),
        ("🚨","Below Reorder Point",f"**{below_rop_cnt} SKUs** have spent at least one day below their reorder point in the filtered window — see the Inventory & Risk tab for the full list and recommended actions."),
        ("🚚","Lead-Time Variance",f"Supplier **{top_lt_sup}** has the longest average lead time. Supplier **{bot_lt_sup}** is the fastest. Consider dual-sourcing critical Class A SKUs with long lead-time suppliers."),
        ("🎁","Promotion Effectiveness",f"Promotional days drive an average **{promo_uplift_avg:+.1f}%** change in units sold. Review inventory levels ahead of promotions to maintain product availability during higher-demand periods."),
        ("📦","Inventory Turnover","SKUs with turnover < 2× per year are over-stocked. Review ordering quantities and consider promotional clearance to reduce carrying costs."),
    ]
    for icon,title,body in insights:
        st.markdown(f'<div class="insight-box"><strong>{icon} {title}:</strong> {body}</div>',unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
    st.markdown("#### 🔧 Replenishment Recommendations")
    actions=[
        ("Immediate","Place replenishment orders for all SKUs currently below their reorder point. Prioritise Class A SKUs first."),
        ("Short-term","Increase safety stock for Class Z (erratic demand) SKUs by 20–30% to buffer against forecast error."),
        ("Short-term","Pre-build inventory for Class A / promotional SKUs ahead of Q3 peak season."),
        ("Medium-term","Negotiate lead-time reductions with the highest-lead-time supplier to bring it in line with the fleet average."),
        ("Medium-term","Implement weekly demand review cycles for Class A+Z SKUs (high-revenue + erratic demand)."),
        ("Long-term","Consider VMI (Vendor Managed Inventory) arrangements with reliable, low-lead-time suppliers for Class C SKUs to reduce internal admin overhead."),
    ]
    for horizon,action in actions:
        box_class="warn-box" if horizon=="Immediate" else "insight-box"
        st.markdown(f'<div class="{box_class}"><strong>[{horizon}]</strong> {action}</div>',unsafe_allow_html=True)
