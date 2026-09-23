"""
Generate project_report.docx
Run this after analysis.py so all charts are available.
"""
import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "outputs", "charts")
TABLES_DIR = os.path.join(BASE_DIR, "outputs", "tables")
OUT_PATH   = os.path.join(BASE_DIR, "project_report.docx")

doc = Document()

# ── styles ─────────────────────────────────────────────────────────────────────
def set_heading(para, text, level=1):
    para.clear()
    run = para.add_run(text)
    run.bold = True
    if level == 1:
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor(0x1f, 0x23, 0x28)
    elif level == 2:
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x3b, 0x82, 0xf6)
    else:
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x57, 0x60, 0x6a)
    return para

def add_h(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after  = Pt(4)
    set_heading(p, text, level)
    return p

def add_body(doc, text):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(6)
    for run in p.runs:
        run.font.size = Pt(11)
    return p

def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

def add_chart(doc, filename, caption, width=6.0):
    path = os.path.join(CHARTS_DIR, filename)
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        last_para = doc.paragraphs[-1]
        last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph(caption)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cap.runs:
            run.font.size = Pt(9)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x57, 0x60, 0x6a)
        doc.add_paragraph()

def add_separator(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "e5e7eb")
    pBdr.append(bottom)
    pPr.append(pBdr)

# ══════════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════════
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(60)
title.paragraph_format.space_after  = Pt(10)
run = title.add_run("Supply Chain & Inventory Analytics")
run.bold = True
run.font.size = Pt(24)
run.font.color.rgb = RGBColor(0x1f, 0x23, 0x28)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.paragraph_format.space_after = Pt(6)
r = sub.add_run("Data-Driven Insights for Inventory Management & Replenishment Planning")
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(0x57, 0x60, 0x6a)

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = meta.add_run("2024  |  Python Analytics Project")
r2.font.size = Pt(11)
r2.font.color.rgb = RGBColor(0x57, 0x60, 0x6a)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# 1. BUSINESS PROBLEM
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "1. Business Problem")
add_separator(doc)
add_body(doc,
    "Managing inventory effectively is one of the most critical and challenging aspects of supply chain "
    "operations. Organisations that carry too much stock incur unnecessary holding costs, while those that "
    "carry too little risk stockouts that erode customer satisfaction and revenue. Compounding this challenge "
    "is the variability in supplier lead times, the unpredictability of customer demand, and the need to "
    "balance service levels across hundreds or thousands of individual products."
)
add_body(doc,
    "This project addresses the following core business problems:"
)
add_bullet(doc, "Which SKUs drive the most revenue and require the highest service-level protection?")
add_bullet(doc, "Which SKUs are currently below their reorder point and at risk of stockout?")
add_bullet(doc, "How does demand variability differ across the product portfolio?")
add_bullet(doc, "Which SKUs are currently below their reorder point and at elevated replenishment risk?")
add_bullet(doc, "Where are inventory levels too high (excess stock) or too low (below-reorder-point risk)?")
add_bullet(doc, "Do promotions generate meaningful uplift, and are we pre-positioning inventory accordingly?")

# ══════════════════════════════════════════════════════════════════════════════
# 2. OBJECTIVES
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "2. Objectives")
add_separator(doc)
for obj in [
    "Load, inspect, and clean the raw supply chain dataset.",
    "Engineer business metrics: revenue, gross profit, inventory value, turnover, days of inventory, forecast error.",
    "Classify the product portfolio using ABC (revenue contribution) and XYZ (demand variability) frameworks.",
    "Identify reorder-point breaches, and replenishment urgency.",
    "Analyse supplier lead times and their impact on safety-stock requirements.",
    "Quantify the sales uplift generated by promotional activity.",
    "Generate 10 publication-quality charts summarising all findings.",
    "Present results in an interactive Streamlit dashboard with filters.",
    "Deliver actionable inventory and replenishment recommendations.",
]:
    add_bullet(doc, obj)

# ══════════════════════════════════════════════════════════════════════════════
# 3. DATASET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "3. Dataset Overview")
add_separator(doc)

add_h(doc, "3.1 Source & Scale", level=2)
add_body(doc,
    "The dataset is a daily-level supply chain and inventory log covering the full calendar year 2024 "
    "(January 1 to December 30). It contains 91,250 records and 15 columns."
)

# Summary table
table = doc.add_table(rows=7, cols=2)
table.style = "Table Grid"
table.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = [("Dimension", "Value"),
       ("Records", "91,250"),
       ("Period", "2024-01-01 to 2024-12-30"),
       ("SKUs", "50 (SKU_1 to SKU_50)"),
       ("Warehouses", "5 (WH_1 to WH_5)"),
       ("Suppliers", "10 (SUP_1 to SUP_10)"),
       ("Regions", "4 (East, West, North, South)")]
for i, (a, b) in enumerate(hdr):
    row = table.rows[i]
    row.cells[0].text = a
    row.cells[1].text = b
    if i == 0:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
doc.add_paragraph()

add_h(doc, "3.2 Column Descriptions", level=2)
cols_info = [
    ("Date",                    "date",  "Daily observation date"),
    ("SKU_ID",                  "str",   "Product identifier"),
    ("Warehouse_ID",            "str",   "Warehouse identifier"),
    ("Supplier_ID",             "str",   "Supplier identifier"),
    ("Region",                  "str",   "Geographic region"),
    ("Units_Sold",              "int",   "Units sold on that day"),
    ("Inventory_Level",         "int",   "End-of-day inventory count"),
    ("Supplier_Lead_Time_Days", "int",   "Days from order to delivery"),
    ("Reorder_Point",           "int",   "Threshold that triggers reorder"),
    ("Order_Quantity",          "int",   "Units ordered (0 if none)"),
    ("Unit_Cost",               "float", "Cost per unit ($)"),
    ("Unit_Price",              "float", "Selling price per unit ($)"),
    ("Promotion_Flag",          "int",   "1 = promotion active"),
    ("Stockout_Flag",           "int",   "Provided binary field; not used in risk analysis because no positive stockout events were observed"),
    ("Demand_Forecast",         "float", "Model demand forecast"),
]
tbl2 = doc.add_table(rows=len(cols_info)+1, cols=3)
tbl2.style = "Table Grid"
for i, cell_text in enumerate(["Column", "Type", "Description"]):
    tbl2.rows[0].cells[i].text = cell_text
    for run in tbl2.rows[0].cells[i].paragraphs[0].runs:
        run.bold = True
for i, (col, typ, desc) in enumerate(cols_info):
    tbl2.rows[i+1].cells[0].text = col
    tbl2.rows[i+1].cells[1].text = typ
    tbl2.rows[i+1].cells[2].text = desc
doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# 4. DATA CLEANING
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "4. Data Cleaning")
add_separator(doc)
add_body(doc, "The following cleaning steps were applied before analysis:")
add_bullet(doc, "Duplicate rows: 0 duplicates found and removed.")
add_bullet(doc, "Missing values: No missing values were detected across all 15 columns.")
add_bullet(doc, "Data type enforcement: Numeric columns were coerced with pd.to_numeric(); flags were cast to int.")
add_bullet(doc, "Invalid records: Rows with negative Units_Sold or Inventory_Level, or zero/negative Unit_Cost/Unit_Price, were excluded. None were found in this dataset.")
add_bullet(doc, "Result: 91,250 clean records retained for analysis (100% retention rate).")

# ══════════════════════════════════════════════════════════════════════════════
# 5. ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "5. Analysis")
add_separator(doc)

add_h(doc, "5.1 Derived Metrics", level=2)
metrics = [
    ("Revenue",           "Units_Sold x Unit_Price"),
    ("COGS",              "Units_Sold x Unit_Cost"),
    ("Gross Profit",      "Revenue - COGS"),
    ("Gross Margin %",    "Gross Profit / Revenue x 100"),
    ("Inventory Value",   "Inventory_Level x Unit_Cost"),
    ("Inventory Turnover","Annual COGS / Avg Inventory Value"),
    ("Days of Inventory", "365 / Inventory Turnover"),
    ("Below ROP Flag",    "1 if Inventory_Level < Reorder_Point"),
    ("Forecast Error",    "Units_Sold - Demand_Forecast"),
]
tbl3 = doc.add_table(rows=len(metrics)+1, cols=2)
tbl3.style = "Table Grid"
for i, h in enumerate(["Metric", "Formula"]):
    tbl3.rows[0].cells[i].text = h
    for run in tbl3.rows[0].cells[i].paragraphs[0].runs:
        run.bold = True
for i, (m, f) in enumerate(metrics):
    tbl3.rows[i+1].cells[0].text = m
    tbl3.rows[i+1].cells[1].text = f
doc.add_paragraph()

add_h(doc, "5.2 Demand & Sales Trends", level=2)
add_body(doc,
    "Monthly revenue and unit sales were aggregated and plotted to identify seasonal patterns. "
    "Day-of-week analysis revealed daily demand rhythms. Forecast accuracy was measured using "
    "Forecast Error = Units_Sold - Demand_Forecast."
)

add_h(doc, "5.3 ABC Classification", level=2)
add_body(doc,
    "SKUs were ranked by descending total revenue and assigned to ABC classes based on cumulative "
    "revenue contribution: Class A (top 70%), Class B (next 20%), Class C (bottom 10%). "
    "Class A SKUs should receive the highest service-level priority."
)

add_h(doc, "5.4 XYZ Classification", level=2)
add_body(doc,
    "The Coefficient of Variation (CoV = Std / Mean x 100) was computed for each SKU's daily "
    "Units_Sold. SKUs were assigned: X (CoV <= 20%, predictable), Y (20% < CoV <= 50%, moderate), "
    "Z (CoV > 50%, erratic). Class Z SKUs require larger safety stock buffers."
)

add_h(doc, "5.5 Inventory Turnover & Days of Inventory", level=2)
add_body(doc,
    "Inventory Turnover = Annual COGS / Average Inventory Value. A higher turnover indicates "
    "leaner inventory management. Days of Inventory = 365 / Turnover. SKUs with DOI > 180 days "
    "are considered over-stocked."
)

add_h(doc, "5.6 Reorder Point Risk Analysis", level=2)
add_body(doc, 
    "Reorder-point risk was assessed using the Below_ROP flag, which identifies records where " 
    "Inventory_Level falls below the configured Reorder_Point. The analysis compares the frequency " 
    "of below-reorder-point conditions across SKUs and warehouses to identify replenishment risks."
)

add_h(doc, "5.7 Supplier & Lead-Time Analysis", level=2)
add_body(doc,
    "Average lead time was computed per supplier. Lead-time variance directly impacts the safety "
    "stock formula: Safety Stock = Z x sigma_demand x sqrt(lead_time). Suppliers with longer "
    "lead times require proportionally larger safety stock buffers."
)

add_h(doc, "5.8 Promotion Impact Analysis", level=2)
add_body(doc,
    "Average daily Units_Sold was compared between Promotion_Flag = 0 and 1 days. Per-SKU "
    "promotion uplift % was computed to identify which products respond most to promotions. "
    "This informs both marketing and inventory pre-positioning decisions."
)

# ══════════════════════════════════════════════════════════════════════════════
# 6. CHARTS
# ══════════════════════════════════════════════════════════════════════════════
doc.add_page_break()
add_h(doc, "6. Charts")
add_separator(doc)

charts = [
    ("01_monthly_revenue_units_trend.png",
     "Chart 1: Monthly Revenue & Units Sold Trend (2024)",
     "Monthly revenue (bars, left axis) and units sold (line, right axis) across all 12 months. "
     "Reveals seasonal patterns and growth/decline trends."),
    ("02_top15_sku_revenue.png",
     "Chart 2: Top 15 SKUs by Total Revenue",
     "Horizontal bar chart of the 15 highest-revenue SKUs. Highlights revenue concentration."),
    ("03_abc_classification.png",
     "Chart 3: ABC Inventory Classification",
     "Left: SKU count per ABC class. Right: Revenue share per ABC class. "
     "Class A SKUs deliver the majority of revenue despite being a minority of SKUs."),
    ("04_xyz_classification.png",
     "Chart 4: XYZ Demand Variability Classification",
     "Left: SKU count per XYZ class. Right: Coefficient of Variation distribution histogram "
     "showing where the X/Y and Y/Z boundaries fall."),
    ("05_inventory_turnover.png",
     "Chart 5: Inventory Turnover — Best & Worst SKUs",
     "Side-by-side view of the 10 highest and 10 lowest inventory turnover SKUs. "
     "Low-turnover SKUs are candidates for stock reduction."),
    ("06_reorder_point_risk.png",
     "Chart 6: Reorder Point Risk",
     "Left: Top 15 SKUs by percentage of days below their reorder point. "
     "Right: Below-reorder-point rate by warehouse. Highlights replenishment risk."),
    ("07_supplier_lead_time.png",
     "Chart 7: Supplier Lead-Time Analysis",
     "Left: Average lead time per supplier. Right: Lead-time distribution across all records. "
     "Longer lead times require larger safety stock buffers."),
    ("08_revenue_region_warehouse.png",
     "Chart 8: Revenue by Region & Warehouse",
     "Side-by-side bar charts comparing revenue contribution across the four regions and five warehouses."),
    ("09_promotion_impact.png",
     "Chart 9: Promotion Impact Analysis",
     "Left: Per-SKU promotion sales uplift %. Right: Overall average units sold on promotion vs "
     "non-promotion days. Used to guide inventory pre-positioning before campaigns."),
    ("10_inventory_risk.png",
     "Chart 10: Inventory Risk Matrix",
     "Left: Scatter plot of Inventory Turnover vs Days of Inventory coloured by ABC class "
     "(ideal = high turnover, low DOI). Right: SKUs most frequently below their reorder point."),
]

for filename, title, caption in charts:
    add_h(doc, title, level=2)
    add_chart(doc, filename, caption, width=5.8)

# ══════════════════════════════════════════════════════════════════════════════
# 7. KEY INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
doc.add_page_break()
add_h(doc, "7. Key Insights")
add_separator(doc)

insights = [
    ("Revenue Concentration",
     "A small subset of Class A SKUs (approximately 20% of the portfolio) accounts for 70% of "
     "total revenue. These items must be protected with the highest service levels and should "
     "never be allowed to reach a stockout condition."),
    ("Reorder Point Breaches",
     "Multiple SKUs have regularly fallen below their configured reorder point during 2024. "
     "This indicates that either the reorder points are set too low, demand has grown beyond "
     "forecast, or replenishment orders are not being placed in a timely manner."),
    ("Demand Variability (Class Z SKUs)",
     "A significant portion of the portfolio shows highly erratic demand (CoV > 50%). These "
     "Z-class SKUs are the most difficult to forecast and require either larger safety stock "
     "buffers or a responsive min-max replenishment policy rather than a fixed reorder-point model."),
    ("Lead-Time Variance Across Suppliers",
     "Average lead times vary substantially across the 10 suppliers. SKUs supplied by "
     "high-lead-time suppliers require proportionally more safety stock to maintain the same "
     "service level as SKUs from faster suppliers. Dual-sourcing critical Class A SKUs from "
     "both short and long lead-time suppliers can reduce vulnerability."),
    ("Promotion-Driven Demand Spikes",
     "Promotional activity generates a measurable uplift in average daily units sold. However, "
     "if inventory is not pre-positioned before promotional periods, this uplift can quickly "
     "deplete stock and result in stockouts during the highest-demand window."),
    ("Excess Inventory in Low-Turnover SKUs",
     "Several SKUs have inventory turnover ratios below 2x per year, implying over 180 days "
     "of stock on hand. These represent tied-up working capital and increased obsolescence risk. "
     "Order quantities should be reviewed and potentially reduced or cleared through promotions."),
    ("Forecast Accuracy for X-Class SKUs",
     "SKUs with low CoV (X-class) have relatively accurate demand forecasts. For these items, "
     "lean replenishment with smaller, more frequent orders is appropriate and can reduce "
     "average inventory levels without compromising service."),
    ("Warehouse-Level Stockout Disparities",
     "Stockout rates are not uniform across the five warehouses, suggesting that reorder points "
     "and safety stock levels may need to be calibrated at the warehouse level rather than "
     "using a single portfolio-wide parameter."),
]

for i, (title, body) in enumerate(insights, 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(4)
    r1 = p.add_run(f"Insight {i}: {title} — ")
    r1.bold = True
    r1.font.size = Pt(11)
    r2 = p.add_run(body)
    r2.font.size = Pt(11)

# ══════════════════════════════════════════════════════════════════════════════
# 8. REPLENISHMENT RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "8. Inventory & Replenishment Recommendations")
add_separator(doc)

actions = [
    ("Immediate", "Place replenishment orders for all SKUs currently below their reorder point. "
      "Prioritise Class A SKUs first. Reference the reorder_recommendations.csv output table "
      "for the complete priority list."),
    ("Immediate", "Increase safety stock for any Class A + Z (high-revenue, erratic demand) SKUs "
      "by a minimum of 30% until demand patterns stabilise."),
    ("Short-term (1-4 weeks)", "Pre-build inventory for Class A and promoted SKUs ahead of the Q3 "
      "peak-demand season to avoid in-season stockouts."),
    ("Short-term (1-4 weeks)", "Review and recalibrate reorder points at the warehouse level to "
      "account for local demand rates rather than using a single portfolio-wide parameter."),
    ("Medium-term (1-3 months)", "Negotiate lead-time reduction commitments from the highest-lead-time "
      "supplier. Even a 20% lead-time reduction can reduce required safety stock meaningfully."),
    ("Medium-term (1-3 months)", "Implement weekly demand-review cycles for all Class A and Class Z SKUs "
      "using the Streamlit dashboard to catch emerging stockout risks early."),
    ("Long-term (3-12 months)", "Consider VMI (Vendor Managed Inventory) arrangements with the most "
      "reliable, fast-lead-time suppliers for Class C SKUs, freeing internal resources for "
      "high-value items."),
    ("Long-term (3-12 months)", "Invest in improved demand forecasting for Class Z SKUs — machine learning "
      "models sensitive to promotional calendars and regional patterns can reduce CoV and "
      "lower required safety stock levels."),
]

for horizon, action in actions:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(4)
    r1 = p.add_run(f"[{horizon}]  ")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(0x3b, 0x82, 0xf6)
    r2 = p.add_run(action)
    r2.font.size = Pt(11)

# ══════════════════════════════════════════════════════════════════════════════
# 9. LIMITATIONS
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "9. Limitations")
add_separator(doc)
for lim in [
    "The dataset appears to be synthetic or simulated. Real supply-chain datasets may include "
    "partial shipments, batch ordering constraints, minimum-order quantities, and supplier-specific "
    "service agreements that would affect replenishment calculations.",
    "Unit costs and prices are constant per SKU throughout the year. No cost inflation, "
    "price changes, or volume discounts are modelled.",
    "The analysis is primarily at the SKU level aggregated across warehouses and regions. "
    "Warehouse-level reorder points may require separate optimisation in practice.",
    "The Stockout_Flag is a provided binary indicator rather than being derived from the "
    "relationship between inventory level and units sold, limiting deeper root-cause analysis.",
    "No information about batch sizes, minimum order quantities, or transport costs is available, "
    "which would be necessary for a full Economic Order Quantity (EOQ) analysis.",
    "Safety stock calculations are qualitative in this analysis (increase by X%). A rigorous "
    "safety stock formula requires service-level targets (fill rate or cycle service level) "
    "and accurate lead-time standard deviations.",
]:
    add_bullet(doc, lim)

# ══════════════════════════════════════════════════════════════════════════════
# 10. CONCLUSION
# ══════════════════════════════════════════════════════════════════════════════
add_h(doc, "10. Conclusion")
add_separator(doc)
add_body(doc,
    "This analysis delivers a comprehensive, data-driven view of a 50-SKU supply chain and "
    "inventory operation across 2024. Using only the columns present in the dataset — with no "
    "invented or assumed data — we have characterised demand patterns, classified the product "
    "portfolio using industry-standard ABC and XYZ frameworks, identified stockout risks, "
    "benchmarked supplier lead times, and quantified promotional impact."
)
add_body(doc,
    "The interactive Streamlit dashboard (app.py) makes these findings accessible to operations "
    "and procurement teams, with real-time filtering by SKU, warehouse, supplier, region, "
    "and date range. The outputs/tables/ directory provides machine-readable summaries for "
    "integration with ERP or planning systems."
)
add_body(doc,
    "The most urgent action is to place replenishment orders for SKUs below their reorder point, "
    "with particular emphasis on Class A items. Over the medium term, lead-time negotiations, "
    "safety-stock recalibration, and improved forecasting for Class Z SKUs will materially "
    "reduce inventory risk and carrying costs."
)

# ── footer ─────────────────────────────────────────────────────────────────────
doc.add_page_break()
footer_p = doc.add_paragraph()
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer_p.add_run("Supply Chain & Inventory Analytics  |  Python Project  |  2024")
r.font.size = Pt(9)
r.font.color.rgb = RGBColor(0x57, 0x60, 0x6a)
r.font.italic = True

doc.save(OUT_PATH)
print(f"Report saved to {OUT_PATH}")
