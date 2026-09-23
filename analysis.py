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
matplotlib.use("Agg")          # non-interactive backend for saving files
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "data", "supply_chain_dataset.csv")
CHARTS_DIR  = os.path.join(BASE_DIR, "outputs", "charts")
TABLES_DIR  = os.path.join(BASE_DIR, "outputs", "tables")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)

# ── style ──────────────────────────────────────────────────────────────────────
PALETTE  = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444",
            "#8b5cf6", "#06b6d4", "#f97316", "#ec4899",
            "#84cc16", "#6366f1"]
BG       = "#ffffff"
GRID_CLR = "#e5e7eb"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    BG,
    "axes.edgecolor":    "#d1d5db",
    "axes.grid":         True,
    "grid.color":        GRID_CLR,
    "grid.linestyle":    "--",
    "grid.linewidth":    0.6,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    10,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.fontsize":   9,
    "font.family":       "DejaVu Sans",
})

def savefig(name: str):
    path = os.path.join(CHARTS_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  OK saved {name}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & INSPECT
# ══════════════════════════════════════════════════════════════════════════════
print("\n[1] Loading data ...")
df = pd.read_csv(DATA_PATH, parse_dates=["Date"])

print(f"    Shape            : {df.shape}")
print(f"    Columns          : {list(df.columns)}")
print(f"    Date range       : {df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"    Unique SKUs      : {df['SKU_ID'].nunique()}")
print(f"    Unique Warehouses: {df['Warehouse_ID'].nunique()}")
print(f"    Unique Suppliers : {df['Supplier_ID'].nunique()}")
print(f"    Unique Regions   : {df['Region'].nunique()}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. CLEAN
# ══════════════════════════════════════════════════════════════════════════════
print("\n[2] Cleaning data ...")

# duplicates
before = len(df)
df.drop_duplicates(inplace=True)
print(f"    Duplicates removed: {before - len(df)}")

# missing values
missing = df.isnull().sum()
print(f"    Missing values:\n{missing[missing > 0].to_string() if missing.any() else '    None'}")
df.dropna(inplace=True)

# enforce types
num_cols = ["Units_Sold", "Inventory_Level", "Supplier_Lead_Time_Days",
            "Reorder_Point", "Order_Quantity", "Unit_Cost", "Unit_Price",
            "Demand_Forecast"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["Promotion_Flag"] = df["Promotion_Flag"].astype(int)

# remove negative values that make no business sense
invalid_mask = (
    (df["Units_Sold"]         < 0) |
    (df["Inventory_Level"]    < 0) |
    (df["Unit_Cost"]          <= 0) |
    (df["Unit_Price"]         <= 0)
)
n_invalid = invalid_mask.sum()
df = df[~invalid_mask].copy()
print(f"    Invalid rows removed: {n_invalid}")
print(f"    Clean dataset shape : {df.shape}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. DERIVED METRICS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[3] Computing derived metrics ...")

df["Revenue"]          = df["Units_Sold"]      * df["Unit_Price"]
df["COGS"]             = df["Units_Sold"]      * df["Unit_Cost"]
df["Gross_Profit"]     = df["Revenue"]         - df["COGS"]
df["Margin_Pct"]       = df["Gross_Profit"]    / df["Revenue"] * 100
df["Inventory_Value"]  = df["Inventory_Level"] * df["Unit_Cost"]
df["Forecast_Error"]   = df["Units_Sold"]      - df["Demand_Forecast"]
df["Forecast_Acc_Pct"] = (
    1 - df["Forecast_Error"].abs() / df["Units_Sold"].replace(0, np.nan)
) * 100

df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
df["Month"]     = df["Date"].dt.month
df["Week"]      = df["Date"].dt.isocalendar().week.astype(int)
df["DayOfWeek"] = df["Date"].dt.day_name()

# Days of Inventory on Hand (per row)
df["DOI"] = df["Inventory_Level"] / df["Units_Sold"].replace(0, np.nan)

# below-reorder-point flag
df["Below_ROP"] = (df["Inventory_Level"] < df["Reorder_Point"]).astype(int)

# ══════════════════════════════════════════════════════════════════════════════
# 4. AGGREGATIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[4] Building summary tables ...")

# ── 4a. SKU-level summary ──────────────────────────────────────────────────
sku_summary = (
    df.groupby("SKU_ID").agg(
        Total_Units_Sold     = ("Units_Sold",      "sum"),
        Total_Revenue        = ("Revenue",         "sum"),
        Total_COGS           = ("COGS",            "sum"),
        Avg_Inventory        = ("Inventory_Level", "mean"),
        Avg_Inventory_Value  = ("Inventory_Value", "mean"),
        Below_ROP_Days       = ("Below_ROP",       "sum"),
        Avg_Lead_Time        = ("Supplier_Lead_Time_Days", "mean"),
        Promo_Days           = ("Promotion_Flag",  "sum"),
        Avg_Unit_Cost        = ("Unit_Cost",       "mean"),
        Avg_Unit_Price       = ("Unit_Price",       "mean"),
        Avg_Forecast_Acc     = ("Forecast_Acc_Pct","mean"),
        Total_Days           = ("Date",            "count"),
    ).reset_index()
)
sku_summary["Gross_Profit"]       = sku_summary["Total_Revenue"] - sku_summary["Total_COGS"]
sku_summary["Margin_Pct"]         = sku_summary["Gross_Profit"] / sku_summary["Total_Revenue"] * 100
sku_summary["Inventory_Turnover"] = sku_summary["Total_COGS"]   / sku_summary["Avg_Inventory_Value"].replace(0, np.nan)
sku_summary["Avg_DOI"]            = 365 / sku_summary["Inventory_Turnover"].replace(0, np.nan)

# ── ABC classification (by revenue contribution) ──────────────────────────
sku_summary.sort_values("Total_Revenue", ascending=False, inplace=True)
sku_summary["Cumulative_Rev_Pct"] = (
    sku_summary["Total_Revenue"].cumsum() / sku_summary["Total_Revenue"].sum() * 100
)
def abc_class(pct):
    if pct <= 70:  return "A"
    if pct <= 90:  return "B"
    return "C"
sku_summary["ABC_Class"] = sku_summary["Cumulative_Rev_Pct"].apply(abc_class)

# ── XYZ classification (demand variability) ────────────────────────────────
xyz = (
    df.groupby("SKU_ID")["Units_Sold"]
      .agg(["mean", "std"])
      .rename(columns={"mean": "Avg_Demand", "std": "Std_Demand"})
      .reset_index()
)
xyz["CoV"] = xyz["Std_Demand"] / xyz["Avg_Demand"].replace(0, np.nan) * 100

def xyz_class(cov):
    if cov <= 20:  return "X"
    if cov <= 50:  return "Y"
    return "Z"
xyz["XYZ_Class"] = xyz["CoV"].apply(xyz_class)
sku_summary = sku_summary.merge(xyz[["SKU_ID", "CoV", "XYZ_Class"]], on="SKU_ID", how="left")

sku_summary.to_csv(os.path.join(TABLES_DIR, "sku_summary.csv"), index=False)
print(f"    SKU summary saved  ({len(sku_summary)} rows)")

# ── 4b. Monthly trends ─────────────────────────────────────────────────────
monthly = (
    df.groupby("YearMonth").agg(
        Total_Units_Sold = ("Units_Sold", "sum"),
        Total_Revenue    = ("Revenue",    "sum"),
        Avg_Inventory    = ("Inventory_Level", "mean"),
        Below_ROP_Days  = ("Below_ROP",        "sum"),
        Promo_Days       = ("Promotion_Flag",  "sum"),
    ).reset_index()
)
monthly.to_csv(os.path.join(TABLES_DIR, "monthly_trends.csv"), index=False)

# ── 4c. Warehouse summary ──────────────────────────────────────────────────
wh_summary = (
    df.groupby("Warehouse_ID").agg(
        Total_Revenue   = ("Revenue",          "sum"),
        Total_Units     = ("Units_Sold",        "sum"),
        Avg_Inventory   = ("Inventory_Level",   "mean"),
        Below_ROP_Days  = ("Below_ROP",        "sum"),
        Avg_Lead_Time   = ("Supplier_Lead_Time_Days", "mean"),
    ).reset_index()
)
wh_summary.to_csv(os.path.join(TABLES_DIR, "warehouse_summary.csv"), index=False)

# ── 4d. Supplier summary ───────────────────────────────────────────────────
sup_summary = (
    df.groupby("Supplier_ID").agg(
        Avg_Lead_Time   = ("Supplier_Lead_Time_Days", "mean"),
        Total_Units     = ("Units_Sold",        "sum"),
        Total_Revenue   = ("Revenue",           "sum"),
        SKUs_Supplied   = ("SKU_ID",            "nunique"),
    ).reset_index()
)
sup_summary.to_csv(os.path.join(TABLES_DIR, "supplier_summary.csv"), index=False)

# ── 4e. Region summary ─────────────────────────────────────────────────────
region_summary = (
    df.groupby("Region").agg(
        Total_Revenue = ("Revenue",    "sum"),
        Total_Units   = ("Units_Sold", "sum"),
        Below_ROP_Days = ("Below_ROP", "sum"),
    ).reset_index()
)
region_summary.to_csv(os.path.join(TABLES_DIR, "region_summary.csv"), index=False)

# ══════════════════════════════════════════════════════════════════════════════
# 5. KPI SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
kpi = {
    "total_revenue":        round(df["Revenue"].sum(), 2),
    "total_units_sold":     int(df["Units_Sold"].sum()),
    "avg_gross_margin_pct": round(df["Margin_Pct"].mean(), 2),
    "total_inventory_value":round(df["Inventory_Value"].sum(), 2),
    "avg_inventory_turnover":round(sku_summary["Inventory_Turnover"].mean(), 2),
    "avg_doi":              round(sku_summary["Avg_DOI"].mean(), 2),
    "avg_lead_time_days":   round(df["Supplier_Lead_Time_Days"].mean(), 2),
    "sku_count":            df["SKU_ID"].nunique(),
    "warehouse_count":      df["Warehouse_ID"].nunique(),
    "supplier_count":       df["Supplier_ID"].nunique(),
}
pd.Series(kpi).to_csv(os.path.join(TABLES_DIR, "kpi_snapshot.csv"), header=["Value"])
print(f"    KPI snapshot saved")

# ══════════════════════════════════════════════════════════════════════════════
# 6. CHARTS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[5] Generating charts ...")

# helper: add value labels on bars
def autolabel(ax, fmt="{:.0f}", rotation=0, fontsize=8):
    for bar in ax.patches:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2, h * 1.01,
                fmt.format(h), ha="center", va="bottom",
                fontsize=fontsize, rotation=rotation
            )

# ── Chart 1: Monthly Revenue & Units Sold Trend ────────────────────────────
fig, ax1 = plt.subplots(figsize=(13, 5))
ax2 = ax1.twinx()
ax1.bar(monthly["YearMonth"], monthly["Total_Revenue"] / 1e6,
        color=PALETTE[0], alpha=0.7, label="Revenue (M$)")
ax2.plot(monthly["YearMonth"], monthly["Total_Units_Sold"] / 1e3,
         color=PALETTE[1], linewidth=2.5, marker="o", markersize=5,
         label="Units Sold (K)")
ax1.set_xlabel("Month")
ax1.set_ylabel("Revenue (M $)", color=PALETTE[0])
ax2.set_ylabel("Units Sold (K)", color=PALETTE[1])
plt.xticks(rotation=45, ha="right")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
ax1.set_title("Monthly Revenue & Units Sold Trend (2024)")
fig.tight_layout()
savefig("01_monthly_revenue_units_trend.png")

# ── Chart 2: Top 15 SKUs by Total Revenue ─────────────────────────────────
top15 = sku_summary.nlargest(15, "Total_Revenue")
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(top15["SKU_ID"][::-1], top15["Total_Revenue"][::-1] / 1e3,
               color=PALETTE[0])
ax.set_xlabel("Total Revenue (K $)")
ax.set_title("Top 15 SKUs by Total Revenue")
for bar, val in zip(bars, top15["Total_Revenue"][::-1]):
    ax.text(bar.get_width() * 1.005, bar.get_y() + bar.get_height() / 2,
            f"${val/1e3:.1f}K", va="center", fontsize=8)
fig.tight_layout()
savefig("02_top15_sku_revenue.png")

# ── Chart 3: ABC Classification Distribution ──────────────────────────────
abc_counts = sku_summary["ABC_Class"].value_counts().sort_index()
abc_rev    = sku_summary.groupby("ABC_Class")["Total_Revenue"].sum()

fig, axes = plt.subplots(1, 2, figsize=(11, 5))

axes[0].bar(abc_counts.index, abc_counts.values,
            color=[PALETTE[0], PALETTE[2], PALETTE[1]])
axes[0].set_title("ABC Classes — SKU Count")
axes[0].set_xlabel("ABC Class"); axes[0].set_ylabel("Number of SKUs")
for i, v in enumerate(abc_counts.values):
    axes[0].text(i, v + 0.3, str(v), ha="center", fontsize=9)

wedges, texts, autotexts = axes[1].pie(
    abc_rev.values, labels=abc_rev.index,
    autopct="%1.1f%%", startangle=90,
    colors=[PALETTE[0], PALETTE[2], PALETTE[1]]
)
axes[1].set_title("ABC Classes — Revenue Share")

fig.suptitle("ABC Inventory Classification (by Revenue Contribution)", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("03_abc_classification.png")

# ── Chart 4: XYZ Classification (Demand Variability) ──────────────────────
xyz_counts = sku_summary["XYZ_Class"].value_counts().sort_index()

fig, axes = plt.subplots(1, 2, figsize=(11, 5))
axes[0].bar(xyz_counts.index, xyz_counts.values,
            color=[PALETTE[2], PALETTE[1], PALETTE[3]])
axes[0].set_title("XYZ Classes — SKU Count")
axes[0].set_xlabel("XYZ Class"); axes[0].set_ylabel("Number of SKUs")
for i, v in enumerate(xyz_counts.values):
    axes[0].text(i, v + 0.3, str(v), ha="center", fontsize=9)

# CoV distribution
axes[1].hist(sku_summary["CoV"].dropna(), bins=20,
             color=PALETTE[4], edgecolor="white")
axes[1].axvline(20, color=PALETTE[2], linestyle="--", label="X/Y boundary (20%)")
axes[1].axvline(50, color=PALETTE[3], linestyle="--", label="Y/Z boundary (50%)")
axes[1].set_xlabel("Coefficient of Variation (%)")
axes[1].set_ylabel("Number of SKUs")
axes[1].set_title("CoV Distribution Across SKUs")
axes[1].legend()

fig.suptitle("XYZ Demand Variability Classification", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("04_xyz_classification.png")

# ── Chart 5: Inventory Turnover by SKU (top & bottom 10) ──────────────────
sku_turn = sku_summary.dropna(subset=["Inventory_Turnover"])
top10_turn  = sku_turn.nlargest(10, "Inventory_Turnover")
bot10_turn  = sku_turn.nsmallest(10, "Inventory_Turnover")

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
axes[0].barh(top10_turn["SKU_ID"][::-1],
             top10_turn["Inventory_Turnover"][::-1], color=PALETTE[2])
axes[0].set_title("Top 10 — Highest Turnover"); axes[0].set_xlabel("Inventory Turnover (×)")

axes[1].barh(bot10_turn["SKU_ID"][::-1],
             bot10_turn["Inventory_Turnover"][::-1], color=PALETTE[3])
axes[1].set_title("Bottom 10 — Lowest Turnover"); axes[1].set_xlabel("Inventory Turnover (×)")

fig.suptitle("Inventory Turnover by SKU", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("05_inventory_turnover.png")

# ── Chart 6: Reorder Point Risk Analysis ──────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

# Below-ROP rate by SKU
rop_risk = (
    df.groupby("SKU_ID")["Below_ROP"]
      .mean()
      .mul(100)
      .sort_values(ascending=False)
      .head(15)
)

axes[0].barh(
    rop_risk.index[::-1],
    rop_risk.values[::-1],
    color=PALETTE[3]
)
axes[0].set_xlabel("% of Days Below Reorder Point")
axes[0].set_title("Top 15 SKUs — Below Reorder Point")

# Below-ROP rate by warehouse
wh_rop = (
    df.groupby("Warehouse_ID")["Below_ROP"]
      .mean()
      .mul(100)
      .sort_values(ascending=False)
)

axes[1].bar(
    wh_rop.index,
    wh_rop.values,
    color=PALETTE[1]
)
axes[1].set_xlabel("Warehouse")
axes[1].set_ylabel("% of Days Below Reorder Point")
axes[1].set_title("Below-ROP Rate by Warehouse")
autolabel(axes[1], "{:.1f}")

fig.suptitle(
    "Reorder Point Risk Analysis",
    fontsize=13,
    fontweight="bold"
)
fig.tight_layout()
savefig("06_reorder_point_risk.png")

# ── Chart 7: Supplier Lead-Time Analysis ──────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

sup_lt = df.groupby("Supplier_ID")["Supplier_Lead_Time_Days"].mean().sort_values()
axes[0].barh(sup_lt.index, sup_lt.values, color=PALETTE[5])
axes[0].set_xlabel("Avg Lead Time (days)")
axes[0].set_title("Average Lead Time by Supplier")
for i, v in enumerate(sup_lt.values):
    axes[0].text(v + 0.1, i, f"{v:.1f}d", va="center", fontsize=8)

# Lead time distribution
df["Supplier_Lead_Time_Days"].plot.hist(ax=axes[1], bins=20,
                                         color=PALETTE[5], edgecolor="white")
axes[1].set_xlabel("Lead Time (days)")
axes[1].set_title("Overall Lead-Time Distribution")

fig.suptitle("Supplier Lead-Time Analysis", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("07_supplier_lead_time.png")

# ── Chart 8: Revenue by Region & Warehouse ────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

reg_rev = df.groupby("Region")["Revenue"].sum().sort_values(ascending=False)
axes[0].bar(reg_rev.index, reg_rev.values / 1e6, color=PALETTE[6])
axes[0].set_ylabel("Revenue (M $)"); axes[0].set_title("Revenue by Region")
autolabel(axes[0], "{:.1f}")

wh_rev = df.groupby("Warehouse_ID")["Revenue"].sum().sort_values(ascending=False)
axes[1].bar(wh_rev.index, wh_rev.values / 1e6, color=PALETTE[7])
axes[1].set_ylabel("Revenue (M $)"); axes[1].set_title("Revenue by Warehouse")
autolabel(axes[1], "{:.1f}")

fig.suptitle("Revenue Distribution by Region & Warehouse", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("08_revenue_region_warehouse.png")

# ── Chart 9: Promotion Impact on Sales ────────────────────────────────────
promo_impact = (
    df.groupby(["SKU_ID", "Promotion_Flag"])["Units_Sold"]
      .mean()
      .unstack(fill_value=0)
      .rename(columns={0: "No Promo", 1: "Promo"})
)
# Take only SKUs that have both conditions
promo_impact = promo_impact[(promo_impact["No Promo"] > 0) & (promo_impact["Promo"] > 0)]
promo_impact["Promo_Uplift_Pct"] = (
    (promo_impact["Promo"] - promo_impact["No Promo"]) / promo_impact["No Promo"] * 100
)
promo_uplift = promo_impact["Promo_Uplift_Pct"].sort_values(ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 6))

promo_uplift.head(15).plot.barh(ax=axes[0], color=PALETTE[2])
axes[0].axvline(0, color="black", linewidth=0.8)
axes[0].set_xlabel("Uplift (%)")
axes[0].set_title("Top 15 SKUs — Promotion Sales Uplift")

avg_promo = df.groupby("Promotion_Flag")["Units_Sold"].mean()
labels = ["No Promotion", "Promotion Active"]
axes[1].bar(labels, avg_promo.values, color=[PALETTE[0], PALETTE[2]], width=0.5)
axes[1].set_ylabel("Avg Units Sold / day")
axes[1].set_title("Avg Daily Units Sold:\nPromotion vs No Promotion")
for i, v in enumerate(avg_promo.values):
    axes[1].text(i, v + 0.2, f"{v:.1f}", ha="center", fontsize=10)

fig.suptitle("Promotion Impact Analysis", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("09_promotion_impact.png")

# ── Chart 10: Inventory Risk Matrix (DOI vs Turnover) & Below-ROP ─────────
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

# scatter: Inventory Turnover vs Avg DOI, coloured by ABC class
abc_colors = {"A": PALETTE[0], "B": PALETTE[1], "C": PALETTE[3]}
for cls, grp in sku_summary.groupby("ABC_Class"):
    axes[0].scatter(grp["Inventory_Turnover"], grp["Avg_DOI"],
                    label=f"Class {cls}", color=abc_colors[cls],
                    s=60, alpha=0.8)
axes[0].set_xlabel("Inventory Turnover (×)")
axes[0].set_ylabel("Days of Inventory on Hand")
axes[0].set_title("Inventory Risk Matrix\n(Turnover vs DOI, coloured by ABC)")
axes[0].legend()

# Below-ROP rate by SKU (top 15 at-risk)
rop_risk = (
    df.groupby("SKU_ID")["Below_ROP"]
      .mean()
      .mul(100)
      .sort_values(ascending=False)
      .head(15)
)
axes[1].barh(rop_risk.index[::-1], rop_risk.values[::-1], color=PALETTE[3])
axes[1].set_xlabel("% of Days Below Reorder Point")
axes[1].set_title("Top 15 SKUs — Days Below Reorder Point")

fig.suptitle("Inventory Risk Analysis", fontsize=13, fontweight="bold")
fig.tight_layout()
savefig("10_inventory_risk.png")

# ══════════════════════════════════════════════════════════════════════════════
# 7. INSIGHTS EXPORT
# ══════════════════════════════════════════════════════════════════════════════
print("\n[6] Saving insight tables ...")

# ABC+XYZ matrix
abcxyz = sku_summary[["SKU_ID", "Total_Revenue", "ABC_Class", "XYZ_Class",
                        "CoV", "Inventory_Turnover", "Avg_DOI", "Below_ROP_Days"]].copy()
abcxyz.to_csv(os.path.join(TABLES_DIR, "abcxyz_matrix.csv"), index=False)

# Reorder recommendations: below ROP + high lead time risk
reorder = df[df["Below_ROP"] == 1].groupby("SKU_ID").agg(
    Below_ROP_Days = ("Below_ROP",       "sum"),
    Avg_Lead_Time  = ("Supplier_Lead_Time_Days", "mean"),
    Avg_Inventory  = ("Inventory_Level",  "mean"),
    Reorder_Point  = ("Reorder_Point",    "first"),
    Supplier       = ("Supplier_ID",      "first"),
).reset_index().sort_values("Below_ROP_Days", ascending=False)
reorder.to_csv(os.path.join(TABLES_DIR, "reorder_recommendations.csv"), index=False)

print(f"    Insight tables saved")
print("\nDone  Analysis complete — all charts and tables are in outputs/")
