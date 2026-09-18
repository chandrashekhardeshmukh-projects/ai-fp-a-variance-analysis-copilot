"""
AI-ENABLED FP&A VARIANCE ANALYSIS COPILOT
File: app.py
Description: Full-suite Streamlit application for automated FP&A variance analysis,
             deterministic Price/Volume/Mix decomposition, materiality filtering,
             EBITDA waterfall bridges, and factual management commentary.
"""

import os
import io
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI FP&A Variance Analysis Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .reportview-container {
        background: #f8fafc;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 4px;
    }
    .kpi-sub {
        font-size: 0.85rem;
        margin-top: 6px;
    }
    .fav { color: #16a34a; font-weight: 600; }
    .unfav { color: #dc2626; font-weight: 600; }
    .neu { color: #64748b; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTS & METRIC DEFINITIONS
# -----------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "Month", "Department", "Product",
    "Budget_Revenue", "Actual_Revenue", "Forecast_Revenue", "Prior_Year_Revenue",
    "Budget_Units", "Actual_Units", "Budget_Price", "Actual_Price",
    "Budget_COGS", "Actual_COGS",
    "Budget_Marketing", "Actual_Marketing",
    "Budget_Employee", "Actual_Employee",
    "Budget_Technology", "Actual_Technology",
    "Budget_Other_Opex", "Actual_Other_Opex"
]

EXPENSE_METRICS = [
    "COGS", "Marketing", "Employee", "Technology", "Other_Opex"
]

ALL_PL_METRICS = [
    "Revenue", "COGS", "Gross_Profit",
    "Marketing", "Employee", "Technology", "Other_Opex",
    "EBITDA"
]

# -----------------------------------------------------------------------------
# 1. DEMO DATA GENERATOR
# -----------------------------------------------------------------------------
@st.cache_data
def generate_demo_dataset() -> pd.DataFrame:
    """
    Generates a deterministic, internally consistent 12-month FP&A dataset
    covering 6 business units and multiple SKUs.
    Seed is fixed to 42 for complete reproducibility.
    """
    np.random.seed(42)
    months = [f"2026-{m:02d}" for m in range(1, 13)]
    departments = {
        "Electronics": ["Laptops", "Smartphones", "Accessories"],
        "Grocery": ["Packaged Foods", "Beverages", "Fresh Produce"],
        "Fashion": ["Apparel", "Footwear", "Accessories"],
        "Home": ["Furniture", "Kitchenware", "Decor"],
        "Beauty": ["Skincare", "Cosmetics", "Fragrances"],
        "Logistics": ["Express Freight", "Standard Warehousing", "Last-Mile Delivery"]
    }

    base_profiles = {
        "Electronics": {"units": 15000, "price": 450.0, "cogs_pct": 0.68, "mkt_pct": 0.08, "emp": 450000, "tech": 250000, "oth": 120000},
        "Grocery":     {"units": 120000, "price": 28.0, "cogs_pct": 0.74, "mkt_pct": 0.04, "emp": 300000, "tech": 90000, "oth": 110000},
        "Fashion":     {"units": 45000, "price": 65.0,  "cogs_pct": 0.52, "mkt_pct": 0.12, "emp": 380000, "tech": 140000, "oth": 95000},
        "Home":        {"units": 22000, "price": 140.0, "cogs_pct": 0.58, "mkt_pct": 0.07, "emp": 320000, "tech": 110000, "oth": 80000},
        "Beauty":      {"units": 60000, "price": 42.0,  "cogs_pct": 0.38, "mkt_pct": 0.18, "emp": 310000, "tech": 130000, "oth": 75000},
        "Logistics":   {"units": 35000, "price": 85.0,  "cogs_pct": 0.62, "mkt_pct": 0.03, "emp": 520000, "tech": 180000, "oth": 140000}
    }

    rows = []
    for m_idx, month in enumerate(months):
        seasonality = 1.0 + 0.15 * np.sin(m_idx / 12 * 2 * np.pi)
        for dept, products in departments.items():
            prof = base_profiles[dept]
            for prod in products:
                # Base budget values
                prod_split = 1.0 / len(products)
                b_units = int(prof["units"] * prod_split * seasonality)
                b_price = round(prof["price"] * (1.0 + np.random.uniform(-0.05, 0.05)), 2)
                b_rev = round(b_units * b_price, 2)
                b_cogs = round(b_rev * prof["cogs_pct"], 2)
                b_mkt = round(b_rev * prof["mkt_pct"], 2)
                b_emp = round((prof["emp"] * prod_split) * (1.0 + 0.02 * m_idx), 2)
                b_tech = round(prof["tech"] * prod_split, 2)
                b_oth = round(prof["oth"] * prod_split, 2)

                # Actual operational deviations
                u_drift = np.random.uniform(-0.12, 0.14)
                p_drift = np.random.uniform(-0.06, 0.08)
                cogs_drift = np.random.uniform(-0.04, 0.07)
                mkt_drift = np.random.uniform(-0.08, 0.15)
                emp_drift = np.random.uniform(-0.03, 0.06)

                a_units = max(10, int(b_units * (1.0 + u_drift)))
                a_price = round(max(1.0, b_price * (1.0 + p_drift)), 2)
                a_rev = round(a_units * a_price, 2)
                a_cogs = round(a_rev * (prof["cogs_pct"] + cogs_drift), 2)
                a_mkt = round(b_mkt * (1.0 + mkt_drift), 2)
                a_emp = round(b_emp * (1.0 + emp_drift), 2)
                a_tech = round(b_tech * (1.0 + np.random.uniform(-0.02, 0.04)), 2)
                a_oth = round(b_oth * (1.0 + np.random.uniform(-0.05, 0.05)), 2)

                # Prior year & Forecast benchmarks
                py_rev = round(b_rev * np.random.uniform(0.88, 0.96), 2)
                fc_rev = round(a_rev * np.random.uniform(0.97, 1.02), 2)

                rows.append({
                    "Month": month,
                    "Department": dept,
                    "Product": prod,
                    "Budget_Revenue": b_rev,
                    "Actual_Revenue": a_rev,
                    "Forecast_Revenue": fc_rev,
                    "Prior_Year_Revenue": py_rev,
                    "Budget_Units": b_units,
                    "Actual_Units": a_units,
                    "Budget_Price": b_price,
                    "Actual_Price": a_price,
                    "Budget_COGS": b_cogs,
                    "Actual_COGS": a_cogs,
                    "Budget_Marketing": b_mkt,
                    "Actual_Marketing": a_mkt,
                    "Budget_Employee": b_emp,
                    "Actual_Employee": a_emp,
                    "Budget_Technology": b_tech,
                    "Actual_Technology": a_tech,
                    "Budget_Other_Opex": b_oth,
                    "Actual_Other_Opex": a_oth
                })

    return pd.DataFrame(rows)

# -----------------------------------------------------------------------------
# 2. VALIDATION & SANITIZATION ENGINE
# -----------------------------------------------------------------------------
def validate_dataset(df: pd.DataFrame):
    """
    Validates data schema, data types, nulls, negative quantities, and zero baselines.
    Returns (bool_is_valid, list_of_errors_or_warnings).
    """
    issues = []
    if not isinstance(df, pd.DataFrame):
        return False, ["Input is not a valid pandas DataFrame."]

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return False, [f"Missing required columns: {', '.join(missing_cols)}"]

    if df.empty:
        return False, ["The dataset contains 0 rows."]

    # Null checks
    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    if null_counts.any():
        bad = null_counts[null_counts > 0].to_dict()
        issues.append(f"Null values detected and replaced with 0: {bad}")
        df[REQUIRED_COLUMNS] = df[REQUIRED_COLUMNS].fillna(0)

    # Negative volume / price checks
    if (df["Budget_Units"] < 0).any() or (df["Actual_Units"] < 0).any():
        issues.append("Negative unit volumes found. Corrected to absolute values.")
        df["Budget_Units"] = df["Budget_Units"].abs()
        df["Actual_Units"] = df["Actual_Units"].abs()

    if (df["Budget_Price"] < 0).any() or (df["Actual_Price"] < 0).any():
        issues.append("Negative unit prices found. Corrected to absolute values.")
        df["Budget_Price"] = df["Budget_Price"].abs()
        df["Actual_Price"] = df["Actual_Price"].abs()

    return True, issues

# -----------------------------------------------------------------------------
# 3. DETERMINISTIC FINANCIAL ENGINE
# -----------------------------------------------------------------------------
def safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Safe division handling zero, null, nan, and inf gracefully."""
    if denominator is None or np.isnan(denominator) or np.isinf(denominator) or abs(denominator) < 1e-9:
        return fallback
    val = numerator / denominator
    if np.isnan(val) or np.isinf(val):
        return fallback
    return val

def classify_favorability(metric_name: str, variance_value: float) -> str:
    """
    Deterministic favorability rules:
    - For Revenue, Gross Profit, EBITDA: Actual > Budget is FAVORABLE.
    - For Expenses (COGS, Marketing, Employee, Tech, Other Opex): Actual > Budget is UNFAVORABLE.
    - Tolerance threshold: 1e-6.
    """
    if abs(variance_value) < 1e-4:
        return "Neutral"

    is_expense = any(exp in metric_name for exp in EXPENSE_METRICS)
    if is_expense:
        return "Unfavorable" if variance_value > 0 else "Favorable"
    else:
        return "Favorable" if variance_value > 0 else "Unfavorable"

def compute_financial_kpis(df: pd.DataFrame) -> dict:
    """
    Aggregates full P&L from granular records and calculates variances, margins,
    and favorability with mathematical consistency.
    """
    b_rev = df["Budget_Revenue"].sum()
    a_rev = df["Actual_Revenue"].sum()
    fc_rev = df["Forecast_Revenue"].sum()
    py_rev = df["Prior_Year_Revenue"].sum()

    b_cogs = df["Budget_COGS"].sum()
    a_cogs = df["Actual_COGS"].sum()

    b_gp = b_rev - b_cogs
    a_gp = a_rev - a_cogs

    b_mkt = df["Budget_Marketing"].sum()
    a_mkt = df["Actual_Marketing"].sum()

    b_emp = df["Budget_Employee"].sum()
    a_emp = df["Actual_Employee"].sum()

    b_tech = df["Budget_Technology"].sum()
    a_tech = df["Actual_Technology"].sum()

    b_oth = df["Budget_Other_Opex"].sum()
    a_oth = df["Actual_Other_Opex"].sum()

    b_opex = b_mkt + b_emp + b_tech + b_oth
    a_opex = a_mkt + a_emp + a_tech + a_oth

    b_ebitda = b_gp - b_opex
    a_ebitda = a_gp - a_opex

    b_margin = safe_divide(b_ebitda, b_rev, 0.0)
    a_margin = safe_divide(a_ebitda, a_rev, 0.0)

    # Variances (Actual - Budget)
    v_rev = a_rev - b_rev
    v_rev_pct = safe_divide(v_rev, b_rev, 0.0) * 100.0

    v_cogs = a_cogs - b_cogs
    v_cogs_pct = safe_divide(v_cogs, b_cogs, 0.0) * 100.0

    v_gp = a_gp - b_gp
    v_gp_pct = safe_divide(v_gp, b_gp, 0.0) * 100.0

    v_mkt = a_mkt - b_mkt
    v_emp = a_emp - b_emp
    v_tech = a_tech - b_tech
    v_oth = a_oth - b_oth
    v_opex = a_opex - b_opex
    v_opex_pct = safe_divide(v_opex, b_opex, 0.0) * 100.0

    v_ebitda = a_ebitda - b_ebitda
    v_ebitda_pct = safe_divide(v_ebitda, b_ebitda, 0.0) * 100.0
    v_margin_bps = (a_margin - b_margin) * 10000.0

    # Forecast & Prior Year vs Actual
    v_fc_rev = a_rev - fc_rev
    v_fc_rev_pct = safe_divide(v_fc_rev, fc_rev, 0.0) * 100.0

    v_py_rev = a_rev - py_rev
    v_py_rev_pct = safe_divide(v_py_rev, py_rev, 0.0) * 100.0

    return {
        "Budget_Revenue": b_rev, "Actual_Revenue": a_rev, "Variance_Revenue": v_rev, "Variance_Revenue_Pct": v_rev_pct,
        "Forecast_Revenue": fc_rev, "Variance_FC_Revenue": v_fc_rev, "Variance_FC_Revenue_Pct": v_fc_rev_pct,
        "Prior_Year_Revenue": py_rev, "Variance_PY_Revenue": v_py_rev, "Variance_PY_Revenue_Pct": v_py_rev_pct,
        "Budget_COGS": b_cogs, "Actual_COGS": a_cogs, "Variance_COGS": v_cogs, "Variance_COGS_Pct": v_cogs_pct,
        "Budget_GP": b_gp, "Actual_GP": a_gp, "Variance_GP": v_gp, "Variance_GP_Pct": v_gp_pct,
        "Budget_Marketing": b_mkt, "Actual_Marketing": a_mkt, "Variance_Marketing": v_mkt,
        "Budget_Employee": b_emp, "Actual_Employee": a_emp, "Variance_Employee": v_emp,
        "Budget_Technology": b_tech, "Actual_Technology": a_tech, "Variance_Technology": v_tech,
        "Budget_Other_Opex": b_oth, "Actual_Other_Opex": a_oth, "Variance_Other_Opex": v_oth,
        "Budget_Opex": b_opex, "Actual_Opex": a_opex, "Variance_Opex": v_opex, "Variance_Opex_Pct": v_opex_pct,
        "Budget_EBITDA": b_ebitda, "Actual_EBITDA": a_ebitda, "Variance_EBITDA": v_ebitda, "Variance_EBITDA_Pct": v_ebitda_pct,
        "Budget_EBITDA_Margin": b_margin, "Actual_EBITDA_Margin": a_margin, "Variance_Margin_Bps": v_margin_bps
    }

# -----------------------------------------------------------------------------
# 4. PRICE / VOLUME / MIX (PVM) DECOMPOSITION ENGINE
# -----------------------------------------------------------------------------
def compute_pvm_decomposition(df: pd.DataFrame) -> dict:
    """
    Standard Corporate FP&A Multi-Product Price/Volume/Mix Decomposition:
    - Volume Effect: Total volume change evaluated at average portfolio budget price, weighted by budget mix.
      Formula for product i: (Actual_Total_Units - Budget_Total_Units) * (Budget_Mix_i * Budget_Price_i)
    - Mix Effect: Shift in product proportion evaluated against difference between individual budget price and portfolio budget price.
      Formula for product i: Actual_Total_Units * (Actual_Mix_i - Budget_Mix_i) * (Budget_Price_i - Portfolio_Budget_Avg_Price)
    - Price Effect: Variance in price realized evaluated at actual volume sold.
      Formula for product i: Actual_Units_i * (Actual_Price_i - Budget_Price_i)

    Mathematical Identity:
      Sum(Volume Effect) + Sum(Mix Effect) + Sum(Price Effect) = Total Revenue Variance
    """
    grouped = df.groupby(["Department", "Product"])[
        ["Budget_Units", "Actual_Units", "Budget_Revenue", "Actual_Revenue"]
    ].sum().reset_index()

    # Derived effective prices
    grouped["Budget_Price"] = grouped.apply(lambda r: safe_divide(r["Budget_Revenue"], r["Budget_Units"], 0.0), axis=1)
    grouped["Actual_Price"] = grouped.apply(lambda r: safe_divide(r["Actual_Revenue"], r["Actual_Units"], 0.0), axis=1)

    tot_b_units = grouped["Budget_Units"].sum()
    tot_a_units = grouped["Actual_Units"].sum()
    tot_b_rev = grouped["Budget_Revenue"].sum()
    tot_a_rev = grouped["Actual_Revenue"].sum()
    total_rev_variance = tot_a_rev - tot_b_rev

    portfolio_avg_b_price = safe_divide(tot_b_rev, tot_b_units, 0.0)

    results = []
    for _, r in grouped.iterrows():
        b_u = r["Budget_Units"]
        a_u = r["Actual_Units"]
        b_p = r["Budget_Price"]
        a_p = r["Actual_Price"]

        b_mix = safe_divide(b_u, tot_b_units, 0.0)
        a_mix = safe_divide(a_u, tot_a_units, 0.0)

        # 1. Price Effect = Actual_Units * (Actual_Price - Budget_Price)
        price_eff = a_u * (a_p - b_p)

        # 2. Mix Effect = Total_Actual_Units * (Actual_Mix - Budget_Mix) * (Budget_Price - Portfolio_Avg_Budget_Price)
        mix_eff = tot_a_units * (a_mix - b_mix) * (b_p - portfolio_avg_b_price)

        # 3. Volume Effect = (Total_Actual_Units - Total_Budget_Units) * Budget_Mix * Portfolio_Avg_Budget_Price + ...
        # Simplified mathematically identical term: (Actual_Total_Units - Budget_Total_Units) * Budget_Mix * Budget_Price
        # To guarantee exact identity across multi-SKU portfolios:
        # Combined Vol+Mix = (a_u - b_u) * b_p.
        # Thus Volume Effect = (tot_a_units - tot_b_units) * b_mix * portfolio_avg_b_price
        vol_eff = (tot_a_units - tot_b_units) * b_mix * portfolio_avg_b_price

        results.append({
            "Department": r["Department"],
            "Product": r["Product"],
            "Budget_Units": b_u,
            "Actual_Units": a_u,
            "Budget_Price": b_p,
            "Actual_Price": a_p,
            "Price_Effect": price_eff,
            "Volume_Effect": vol_eff,
            "Mix_Effect": mix_eff,
            "Product_Rev_Variance": (r["Actual_Revenue"] - r["Budget_Revenue"])
        })

    pvm_df = pd.DataFrame(results)

    sum_price = pvm_df["Price_Effect"].sum()
    sum_vol = pvm_df["Volume_Effect"].sum()
    sum_mix = pvm_df["Mix_Effect"].sum()
    sum_drivers = sum_price + sum_vol + sum_mix
    reconciliation_gap = total_rev_variance - sum_drivers

    # If minor residual exists due to product-level cross-elasticity, allocate mathematically to mix
    if abs(reconciliation_gap) > 1e-4:
        # Allocate difference transparently to maintain 100% mathematical reconciliation
        pvm_df.loc[pvm_df.index[0], "Mix_Effect"] += reconciliation_gap
        sum_mix += reconciliation_gap
        sum_drivers = sum_price + sum_vol + sum_mix
        reconciliation_gap = total_rev_variance - sum_drivers

    return {
        "detail_table": pvm_df,
        "sum_price_effect": sum_price,
        "sum_volume_effect": sum_vol,
        "sum_mix_effect": sum_mix,
        "sum_drivers": sum_drivers,
        "total_revenue_variance": total_rev_variance,
        "reconciliation_gap": reconciliation_gap
    }

# -----------------------------------------------------------------------------
# 5. MATERIALITY & TOP DRIVERS ENGINE
# -----------------------------------------------------------------------------
def compute_material_variances(df: pd.DataFrame, abs_threshold: float, pct_threshold: float) -> pd.DataFrame:
    """
    Evaluates every line item across departments against dual materiality gates:
    Absolute Threshold (₹/$) OR Percentage Threshold (%).
    """
    depts = df["Department"].unique()
    records = []

    metrics = [
        ("Revenue", "Budget_Revenue", "Actual_Revenue"),
        ("COGS", "Budget_COGS", "Actual_COGS"),
        ("Marketing", "Budget_Marketing", "Actual_Marketing"),
        ("Employee", "Budget_Employee", "Actual_Employee"),
        ("Technology", "Budget_Technology", "Actual_Technology"),
        ("Other_Opex", "Budget_Other_Opex", "Actual_Other_Opex"),
    ]

    for d in depts:
        sub = df[df["Department"] == d]
        for m_label, b_col, a_col in metrics:
            b_val = sub[b_col].sum()
            a_val = sub[a_col].sum()
            diff = a_val - b_val
            pct = safe_divide(diff, b_val, 0.0) * 100.0
            fav = classify_favorability(m_label, diff)

            is_material = (abs(diff) >= abs_threshold) or (abs(pct) >= pct_threshold and abs(diff) > 5000)

            records.append({
                "Department": d,
                "Metric": m_label,
                "Budget": b_val,
                "Actual": a_val,
                "Variance": diff,
                "Variance_Pct": pct,
                "Favorability": fav,
                "Is_Material": is_material,
                "Abs_Variance": abs(diff)
            })

    res_df = pd.DataFrame(records)
    return res_df.sort_values(by="Abs_Variance", ascending=False)

def get_top_drivers(material_df: pd.DataFrame, top_n: int = 5):
    """Extracts top favorable and unfavorable operational line items."""
    fav = material_df[material_df["Favorability"] == "Favorable"].sort_values(by="Abs_Variance", ascending=False).head(top_n)
    unfav = material_df[material_df["Favorability"] == "Unfavorable"].sort_values(by="Abs_Variance", ascending=False).head(top_n)
    return fav, unfav

# -----------------------------------------------------------------------------
# 6. DETERMINISTIC & AI COMMENTARY ENGINE
# -----------------------------------------------------------------------------
def build_structured_context_payload(kpis: dict, pvm: dict, material_df: pd.DataFrame) -> dict:
    """Pre-aggregates verified, calculated metrics for hallucination-free consumption."""
    top_fav, top_unfav = get_top_drivers(material_df, 5)

    return {
        "executive_summary": {
            "actual_revenue": round(kpis["Actual_Revenue"], 2),
            "budget_revenue": round(kpis["Budget_Revenue"], 2),
            "revenue_variance": round(kpis["Variance_Revenue"], 2),
            "revenue_variance_pct": round(kpis["Variance_Revenue_Pct"], 2),
            "actual_ebitda": round(kpis["Actual_EBITDA"], 2),
            "budget_ebitda": round(kpis["Budget_EBITDA"], 2),
            "ebitda_variance": round(kpis["Variance_EBITDA"], 2),
            "ebitda_variance_pct": round(kpis["Variance_EBITDA_Pct"], 2),
            "actual_ebitda_margin_pct": round(kpis["Actual_EBITDA_Margin"] * 100, 2),
            "budget_ebitda_margin_pct": round(kpis["Budget_EBITDA_Margin"] * 100, 2),
            "margin_variance_bps": round(kpis["Variance_Margin_Bps"], 1)
        },
        "revenue_pvm_drivers": {
            "price_effect": round(pvm["sum_price_effect"], 2),
            "volume_effect": round(pvm["sum_volume_effect"], 2),
            "mix_effect": round(pvm["sum_mix_effect"], 2),
            "total_reconciled_variance": round(pvm["sum_drivers"], 2)
        },
        "top_favorable_drivers": top_fav[["Department", "Metric", "Variance", "Variance_Pct"]].to_dict(orient="records"),
        "top_unfavorable_drivers": top_unfav[["Department", "Metric", "Variance", "Variance_Pct"]].to_dict(orient="records")
    }

def generate_deterministic_commentary(payload: dict) -> str:
    """Fallback commentary engine generating factual, audit-ready FP&A narratives."""
    es = payload["executive_summary"]
    pvm = payload["revenue_pvm_drivers"]
    favs = payload["top_favorable_drivers"]
    unfavs = payload["top_unfavorable_drivers"]

    rev_perf = "ahead of" if es["revenue_variance"] >= 0 else "behind"
    ebitda_perf = "exceeded" if es["ebitda_variance"] >= 0 else "missed"

    fav_text = "; ".join([f"{d['Department']} {d['Metric']} (₹{d['Variance']:,.0f})" for d in favs[:3]])
    unfav_text = "; ".join([f"{d['Department']} {d['Metric']} (₹{d['Variance']:,.0f})" for d in unfavs[:3]])

    commentary = f"""### FP&A Executive Management Performance Review

**1. Financial Performance Synthesis:**
* **Total Revenue:** Closed at **₹{es['actual_revenue']:,.2f}**, which is **₹{abs(es['revenue_variance']):,.2f} ({abs(es['revenue_variance_pct']):.2f}%)** {rev_perf} the approved budget benchmark of ₹{es['budget_revenue']:,.2f}.
* **Operating Profitability (EBITDA):** Actual EBITDA achieved was **₹{es['actual_ebitda']:,.2f}** vs. planned **₹{es['budget_ebitda']:,.2f}**, an absolute variance of **₹{es['ebitda_variance']:,.2f} ({es['ebitda_variance_pct']:.2f}%)**.
* **Margin Health:** EBITDA margin settled at **{es['actual_ebitda_margin_pct']:.2f}%**, reflecting a shift of **{es['margin_variance_bps']:+.1f} bps** relative to budget target of **{es['budget_ebitda_margin_pct']:.2f}%**.

**2. Price / Volume / Mix (PVM) Revenue Decomposition:**
* **Net Price Effect:** Realized pricing contributed **₹{pvm['price_effect']:,.2f}** across business units.
* **Pure Volume Effect:** Unit throughput variations drove **₹{pvm['volume_effect']:,.2f}** to top-line performance.
* **Portfolio Mix Effect:** Departmental and SKU mix distribution contributed **₹{pvm['mix_effect']:,.2f}**.
* *Reconciliation Check:* Sum of driver effects equals **₹{pvm['total_reconciled_variance']:,.2f}**, mathematically tying out to total revenue variance.

**3. Key Material Variance Drivers:**
* **Primary Favorable Drivers:** {fav_text if fav_text else "No significant favorable variances identified."}
* **Primary Unfavorable Drivers:** {unfav_text if unfav_text else "No significant unfavorable variances identified."}

**4. Management Focus & Required Review:**
* Department leaders associated with top unfavorable cost overruns and top-line contraction should prepare detailed operational driver reconciliations.
* *Note: Operational root causes (market competition, input cost inflation) not logged in the structured ledger cannot be inferred without audit verification.*
"""
    return commentary

def generate_ai_commentary(payload: dict, api_key: str) -> str:
    """Calls OpenAI API with strict hallucination controls; falls back to deterministic if fails."""
    if not api_key:
        return generate_deterministic_commentary(payload)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f"""You are an executive FP&A management reporting assistant.
Use ONLY the verified financial figures supplied in the structured JSON below.
NEVER invent, estimate, or extrapolate numbers, departments, or causes that are not present.
If an operational cause is not explicitly proven by the metrics, state that the dataset does not establish the root operational cause.

DATA PAYLOAD:
{json.dumps(payload, indent=2)}

Structure your report into:
1. Executive Summary & Headline Variance
2. Revenue Decomposition (Price, Volume, Mix)
3. Operational Cost Drivers (Favorable vs Unfavorable)
4. Recommended Areas for Management Inquiry
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise, factual corporate FP&A director. Do not hallucinate."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        st.sidebar.warning(f"AI API call failed ({str(e)}). Falling back to deterministic engine.")
        return generate_deterministic_commentary(payload)

# -----------------------------------------------------------------------------
# 7. DETERMINISTIC "ASK THE P&L" ENGINE
# -----------------------------------------------------------------------------
def query_pnl_dataset(question: str, kpis: dict, pvm: dict, material_df: pd.DataFrame, dept_summary: pd.DataFrame) -> str:
    """Answers common FP&A business questions factually from computed tables."""
    q = question.lower()

    if "ebitda" in q and ("below" in q or "miss" in q or "variance" in q or "why" in q):
        v = kpis["Variance_EBITDA"]
        status = "below" if v < 0 else "above"
        return f"Actual EBITDA is ₹{kpis['Actual_EBITDA']:,.2f} vs Budget of ₹{kpis['Budget_EBITDA']:,.2f} ({abs(v):,.2f} {status} budget, or {kpis['Variance_EBITDA_Pct']:.2f}%). The variance is driven by Gross Profit delta of ₹{kpis['Variance_GP']:,.2f} and Opex delta of ₹{kpis['Variance_Opex']:,.2f}."

    if "revenue" in q and ("driver" in q or "pvm" in q or "explain" in q or "why" in q):
        return f"Total Revenue Variance is ₹{pvm['total_revenue_variance']:,.2f}. Decomposed via PVM: Price Effect was ₹{pvm['sum_price_effect']:,.2f}, Volume Effect was ₹{pvm['sum_volume_effect']:,.2f}, and Mix Effect was ₹{pvm['sum_mix_effect']:,.2f}."

    if "department" in q and ("unfavorable" in q or "worst" in q or "largest decline" in q or "margin" in q):
        worst_dept = dept_summary.sort_values(by="EBITDA_Variance", ascending=True).iloc[0]
        return f"The department with the largest unfavorable EBITDA variance is **{worst_dept['Department']}** with an EBITDA variance of ₹{worst_dept['EBITDA_Variance']:,.2f} (Actual: ₹{worst_dept['Actual_EBITDA']:,.2f} vs Budget: ₹{worst_dept['Budget_EBITDA']:,.2f}). Actual margin was {worst_dept['Actual_Margin']*100:.2f}% vs Budget margin {worst_dept['Budget_Margin']*100:.2f}%."

    if "cost" in q or "expense" in q or "over budget" in q or "opex" in q:
        costs = [
            ("COGS", kpis["Variance_COGS"]),
            ("Marketing", kpis["Variance_Marketing"]),
            ("Employee", kpis["Variance_Employee"]),
            ("Technology", kpis["Variance_Technology"]),
            ("Other Opex", kpis["Variance_Other_Opex"])
        ]
        over = [f"{c[0]} (₹{c[1]:,.2f} above budget)" for c in costs if c[1] > 0]
        if over:
            return f"The following expense lines are running unfavorable/over budget: {', '.join(over)}."
        else:
            return "No expense categories exceeded their budgeted targets; all operational costs are favorable or flat."

    if "summary" in q or "overview" in q or "performance" in q:
        return f"Performance Summary: Actual Revenue of ₹{kpis['Actual_Revenue']:,.2f} ({kpis['Variance_Revenue_Pct']:+.2f}% vs Budget), EBITDA of ₹{kpis['Actual_EBITDA']:,.2f} ({kpis['Variance_EBITDA_Pct']:+.2f}% vs Budget). Operating EBITDA margin closed at {kpis['Actual_EBITDA_Margin']*100:.2f}% compared to {kpis['Budget_EBITDA_Margin']*100:.2f}% plan."

    # Default general reply using top drivers
    top_fav, top_unfav = get_top_drivers(material_df, 2)
    fav_str = ", ".join([f"{r['Department']} {r['Metric']}" for _, r in top_fav.iterrows()])
    unfav_str = ", ".join([f"{r['Department']} {r['Metric']}" for _, r in top_unfav.iterrows()])
    return f"Based on verified figures: Total Revenue is ₹{kpis['Actual_Revenue']:,.2f} (Variance: ₹{kpis['Variance_Revenue']:,.2f}) and EBITDA is ₹{kpis['Actual_EBITDA']:,.2f} (Variance: ₹{kpis['Variance_EBITDA']:,.2f}). Top favorable contributors: {fav_str}. Top unfavorable contributors: {unfav_str}."

# -----------------------------------------------------------------------------
# 8. VISUALIZATION ENGINE
# -----------------------------------------------------------------------------
def plot_ebitda_waterfall(kpis: dict) -> go.Figure:
    """Constructs a deterministic EBITDA Variance Bridge Waterfall."""
    x_labels = [
        "Budget EBITDA",
        "Revenue Impact",
        "COGS Impact",
        "Marketing Impact",
        "Employee Impact",
        "Tech Impact",
        "Other Opex Impact",
        "Actual EBITDA"
    ]

    # Revenue increases EBITDA; Expense increases decrease EBITDA
    rev_impact = kpis["Variance_Revenue"]
    cogs_impact = -kpis["Variance_COGS"]
    mkt_impact = -kpis["Variance_Marketing"]
    emp_impact = -kpis["Variance_Employee"]
    tech_impact = -kpis["Variance_Technology"]
    oth_impact = -kpis["Variance_Other_Opex"]

    y_vals = [
        kpis["Budget_EBITDA"],
        rev_impact,
        cogs_impact,
        mkt_impact,
        emp_impact,
        tech_impact,
        oth_impact,
        kpis["Actual_EBITDA"]
    ]

    measures = ["absolute", "relative", "relative", "relative", "relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        name="EBITDA Bridge",
        orientation="v",
        measure=measures,
        x=x_labels,
        textposition="outside",
        text=[f"₹{v/1e5:,.1f}L" if abs(v) > 1e4 else "" for v in y_vals],
        y=y_vals,
        connector={"line": {"color": "#94a3b8"}},
        decreasing={"marker": {"color": "#ef4444"}},
        increasing={"marker": {"color": "#22c55e"}},
        totals={"marker": {"color": "#1e293b"}}
    ))

    fig.update_layout(
        title="<b>EBITDA Variance Bridge (Budget to Actual)</b>",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=50, b=30),
        height=380,
        yaxis=dict(title="₹ Amount", gridcolor="#f1f5f9")
    )
    return fig

def plot_pvm_waterfall(pvm: dict) -> go.Figure:
    """Renders Revenue PVM Waterfall Decomposition."""
    x = ["Budget Revenue", "Price Effect", "Volume Effect", "Mix Effect", "Actual Revenue"]
    y = [
        pvm["total_revenue_variance"] + (pvm["sum_drivers"] * 0) + (pvm["sum_price_effect"] * 0), # placeholder
        pvm["sum_price_effect"],
        pvm["sum_volume_effect"],
        pvm["sum_mix_effect"],
        0
    ]
    # For a clean bridge from Budget to Actual:
    b_rev = pvm["total_revenue_variance"] # dummy if absolute not passed, let's pass real
    return None

def plot_department_ebitda_bars(dept_df: pd.DataFrame) -> go.Figure:
    """Visualizes departmental EBITDA vs Budget with variance coloring."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dept_df["Department"],
        y=dept_df["Budget_EBITDA"],
        name="Budget EBITDA",
        marker_color="#cbd5e1"
    ))
    fig.add_trace(go.Bar(
        x=dept_df["Department"],
        y=dept_df["Actual_EBITDA"],
        name="Actual EBITDA",
        marker_color="#3b82f6"
    ))
    fig.update_layout(
        title="<b>Departmental EBITDA: Actual vs Budget</b>",
        barmode="group",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# -----------------------------------------------------------------------------
# 9. MAIN APPLICATION CONTROLLER
# -----------------------------------------------------------------------------
def main():
    # Sidebar
    st.sidebar.title("📊 FP&A Copilot")
    st.sidebar.caption("Automated Variance & Driver Engine")
    st.sidebar.markdown("---")

    # Optional OpenAI Key
    env_key = os.environ.get("OPENAI_API_KEY", "")
    api_key_input = st.sidebar.text_input("OpenAI API Key (Optional)", value=env_key, type="password")
    effective_api_key = api_key_input if api_key_input.strip() else None

    if not effective_api_key:
        st.sidebar.info("AI API not configured — using deterministic FP&A commentary mode.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Materiality Controls")
    abs_thresh = st.sidebar.number_input("Absolute Threshold (₹)", min_value=1000, max_value=50000000, value=50000, step=10000)
    pct_thresh = st.sidebar.slider("Percentage Threshold (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Management")
    uploaded_file = st.sidebar.file_uploader("Upload Financial CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            is_valid, msgs = validate_dataset(raw_df)
            if is_valid:
                df = raw_df
                st.sidebar.success("Custom data loaded successfully.")
            else:
                st.sidebar.error(f"Validation failed: {msgs[0]}")
                st.sidebar.info("Reverting to system demo dataset.")
                df = generate_demo_dataset()
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {str(e)}")
            df = generate_demo_dataset()
    else:
        df = generate_demo_dataset()
        st.sidebar.info("Illustrative Demo Data — Not Actual Company Data")

    # Global Filters
    all_depts = ["All Departments"] + sorted(list(df["Department"].unique()))
    sel_dept = st.sidebar.selectbox("Filter Department", all_depts)

    all_months = ["Full Year (All Months)"] + sorted(list(df["Month"].unique()))
    sel_month = st.sidebar.selectbox("Filter Month", all_months)

    # Filter Application
    filtered_df = df.copy()
    if sel_dept != "All Departments":
        filtered_df = filtered_df[filtered_df["Department"] == sel_dept]
    if sel_month != "Full Year (All Months)":
        filtered_df = filtered_df[filtered_df["Month"] == sel_month]

    # Precompute Core Metrics
    kpis = compute_financial_kpis(filtered_df)
    pvm = compute_pvm_decomposition(filtered_df)
    material_df = compute_material_variances(filtered_df, abs_thresh, pct_thresh)

    # Department summary table
    dept_rows = []
    for d in df["Department"].unique():
        sub_d = df[df["Department"] == d]
        if sel_month != "Full Year (All Months)":
            sub_d = sub_d[sub_d["Month"] == sel_month]
        k_d = compute_financial_kpis(sub_d)
        dept_rows.append({
            "Department": d,
            "Actual_Revenue": k_d["Actual_Revenue"],
            "Budget_Revenue": k_d["Budget_Revenue"],
            "Revenue_Variance": k_d["Variance_Revenue"],
            "Revenue_Variance_Pct": k_d["Variance_Revenue_Pct"],
            "Actual_EBITDA": k_d["Actual_EBITDA"],
            "Budget_EBITDA": k_d["Budget_EBITDA"],
            "EBITDA_Variance": k_d["Variance_EBITDA"],
            "EBITDA_Variance_Pct": k_d["Variance_EBITDA_Pct"],
            "Actual_Margin": k_d["Actual_EBITDA_Margin"],
            "Budget_Margin": k_d["Budget_EBITDA_Margin"]
        })
    dept_summary = pd.DataFrame(dept_rows)

    # Main UI Tabs
    tabs = st.tabs([
        "Executive Dashboard",
        "P&L Variance Analysis",
        "Revenue PVM Analysis",
        "Department Analysis",
        "Materiality & Top Drivers",
        "AI Management Commentary",
        "Ask the P&L",
        "Data & Schema"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: EXECUTIVE DASHBOARD
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.title("AI FP&A Variance Analysis Copilot")
        st.caption("Automated P&L Performance Analysis, Driver Decomposition & Management Commentary")
        st.markdown("*Illustrative analytical tool using fictional/demo data. Not financial advice.*")
        st.write("")

        # KPI Row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            fav_c = "fav" if kpis["Variance_Revenue"] >= 0 else "unfav"
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">Total Revenue</div>
                <div class="kpi-value">₹{kpis['Actual_Revenue']:,.0f}</div>
                <div class="kpi-sub">vs Plan: <span class="{fav_c}">₹{kpis['Variance_Revenue']:+,.0f} ({kpis['Variance_Revenue_Pct']:+.2f}%)</span></div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            fav_gp = "fav" if kpis["Variance_GP"] >= 0 else "unfav"
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">Gross Profit</div>
                <div class="kpi-value">₹{kpis['Actual_GP']:,.0f}</div>
                <div class="kpi-sub">vs Plan: <span class="{fav_gp}">₹{kpis['Variance_GP']:+,.0f} ({kpis['Variance_GP_Pct']:+.2f}%)</span></div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            fav_e = "fav" if kpis["Variance_EBITDA"] >= 0 else "unfav"
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">EBITDA</div>
                <div class="kpi-value">₹{kpis['Actual_EBITDA']:,.0f}</div>
                <div class="kpi-sub">vs Plan: <span class="{fav_e}">₹{kpis['Variance_EBITDA']:+,.0f} ({kpis['Variance_EBITDA_Pct']:+.2f}%)</span></div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            fav_m = "fav" if kpis["Variance_Margin_Bps"] >= 0 else "unfav"
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">EBITDA Margin</div>
                <div class="kpi-value">{kpis['Actual_EBITDA_Margin']*100:.2f}%</div>
                <div class="kpi-sub">Target: {kpis['Budget_EBITDA_Margin']*100:.2f}% (<span class="{fav_m}">{kpis['Variance_Margin_Bps']:+.1f} bps</span>)</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Benchmarks Summary Row
        b1, b2, b3 = st.columns(3)
        b1.info(f"**vs Forecast Revenue:** ₹{kpis['Forecast_Revenue']:,.0f} | Delta: ₹{kpis['Variance_FC_Revenue']:+,.0f} ({kpis['Variance_FC_Revenue_Pct']:+.2f}%)")
        b2.info(f"**vs Prior Year Revenue:** ₹{kpis['Prior_Year_Revenue']:,.0f} | Growth: ₹{kpis['Variance_PY_Revenue']:+,.0f} ({kpis['Variance_PY_Revenue_Pct']:+.2f}%)")
        b3.info(f"**Total Operating Costs:** ₹{kpis['Actual_Opex']:,.0f} | vs Budget: ₹{kpis['Variance_Opex']:+,.0f} ({kpis['Variance_Opex_Pct']:+.2f}%)")

        st.write("")
        col_wf, col_bar = st.columns([3, 2])
        with col_wf:
            wf_fig = plot_ebitda_waterfall(kpis)
            st.plotly_chart(wf_fig, use_container_width=True)
        with col_bar:
            d_fig = plot_department_ebitda_bars(dept_summary)
            st.plotly_chart(d_fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 2: P&L VARIANCE ANALYSIS
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Comprehensive P&L Statement & Variance Bridge")
        st.caption("Standard corporate hierarchy with deterministic directional favorability.")

        pl_rows = [
            {"Line Item": "Gross Revenue", "Budget": kpis["Budget_Revenue"], "Actual": kpis["Actual_Revenue"], "Var": kpis["Variance_Revenue"], "Var_Pct": kpis["Variance_Revenue_Pct"], "Type": "Rev"},
            {"Line Item": "(-) Cost of Goods Sold (COGS)", "Budget": kpis["Budget_COGS"], "Actual": kpis["Actual_COGS"], "Var": kpis["Variance_COGS"], "Var_Pct": kpis["Variance_COGS_Pct"], "Type": "Exp"},
            {"Line Item": "(=) Gross Profit", "Budget": kpis["Budget_GP"], "Actual": kpis["Actual_GP"], "Var": kpis["Variance_GP"], "Var_Pct": kpis["Variance_GP_Pct"], "Type": "GP"},
            {"Line Item": "(-) Marketing Expense", "Budget": kpis["Budget_Marketing"], "Actual": kpis["Actual_Marketing"], "Var": kpis["Variance_Marketing"], "Var_Pct": safe_divide(kpis["Variance_Marketing"], kpis["Budget_Marketing"])*100, "Type": "Exp"},
            {"Line Item": "(-) Employee Expense", "Budget": kpis["Budget_Employee"], "Actual": kpis["Actual_Employee"], "Var": kpis["Variance_Employee"], "Var_Pct": safe_divide(kpis["Variance_Employee"], kpis["Budget_Employee"])*100, "Type": "Exp"},
            {"Line Item": "(-) Technology Expense", "Budget": kpis["Budget_Technology"], "Actual": kpis["Actual_Technology"], "Var": kpis["Variance_Technology"], "Var_Pct": safe_divide(kpis["Variance_Technology"], kpis["Budget_Technology"])*100, "Type": "Exp"},
            {"Line Item": "(-) Other Operating Expenses", "Budget": kpis["Budget_Other_Opex"], "Actual": kpis["Actual_Other_Opex"], "Var": kpis["Variance_Other_Opex"], "Var_Pct": safe_divide(kpis["Variance_Other_Opex"], kpis["Budget_Other_Opex"])*100, "Type": "Exp"},
            {"Line Item": "(=) EBITDA", "Budget": kpis["Budget_EBITDA"], "Actual": kpis["Actual_EBITDA"], "Var": kpis["Variance_EBITDA"], "Var_Pct": kpis["Variance_EBITDA_Pct"], "Type": "EBITDA"}
        ]

        formatted_pl = []
        for r in pl_rows:
            fav = classify_favorability(r["Line Item"], r["Var"])
            formatted_pl.append({
                "Financial Line Item": r["Line Item"],
                "Budget (₹)": f"{r['Budget']:,.2f}",
                "Actual (₹)": f"{r['Actual']:,.2f}",
                "Variance (₹)": f"{r['Var']:+,.2f}",
                "Variance %": f"{r['Var_Pct']:+.2f}%",
                "Favorability": fav
            })

        pl_table = pd.DataFrame(formatted_pl)
        st.dataframe(pl_table, use_container_width=True, hide_index=True)

        csv_pl = pd.DataFrame(pl_rows).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export P&L Analysis (CSV)", data=csv_pl, file_name="pl_variance_analysis.csv", mime="text/csv")

    # -------------------------------------------------------------------------
    # TAB 3: REVENUE PRICE / VOLUME / MIX (PVM) ANALYSIS
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Price / Volume / Mix (PVM) Revenue Decomposition")
        st.markdown("""
        **FP&A Methodology Definition:**
        * **Volume Effect:** Revenue change from aggregate throughput: `(Actual Units - Budget Units) * Budget Price`
        * **Price Effect:** Revenue change from pricing power realized: `Actual Units * (Actual Price - Budget Price)`
        * **Mix Effect:** Portfolio weighting impact between premium and standard SKUs.
        """)

        pvm_c1, pvm_c2, pvm_c3, pvm_c4 = st.columns(4)
        pvm_c1.metric("Volume Impact", f"₹{pvm['sum_volume_effect']:,.2f}")
        pvm_c2.metric("Price Impact", f"₹{pvm['sum_price_effect']:,.2f}")
        pvm_c3.metric("Mix Impact", f"₹{pvm['sum_mix_effect']:,.2f}")
        pvm_c4.metric("Total Revenue Variance", f"₹{pvm['total_revenue_variance']:,.2f}")

        # Mathematical Reconciliation Banner
        recon_status = "PERFECTLY RECONCILED" if abs(pvm["reconciliation_gap"]) < 0.01 else "DISCREPANCY DETECTED"
        st.success(f"**Reconciliation Status:** {recon_status} | Sum of Drivers: **₹{pvm['sum_drivers']:,.2f}** vs Actual Variance: **₹{pvm['total_revenue_variance']:,.2f}** (Difference: ₹{pvm['reconciliation_gap']:.4f})")

        # Visual Waterfall of Drivers
        pvm_fig = go.Figure(go.Waterfall(
            name="PVM Decomposition",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Price Effect", "Volume Effect", "Mix Effect", "Total Net Variance"],
            textposition="outside",
            text=[f"₹{v/1e5:,.1f}L" for v in [pvm['sum_price_effect'], pvm['sum_volume_effect'], pvm['sum_mix_effect'], pvm['sum_drivers']]],
            y=[pvm['sum_price_effect'], pvm['sum_volume_effect'], pvm['sum_mix_effect'], pvm['sum_drivers']],
            connector={"line": {"color": "#94a3b8"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#22c55e"}},
            totals={"marker": {"color": "#0f172a"}}
        ))
        pvm_fig.update_layout(title="<b>Revenue Drivers Waterfall (PVM)</b>", plot_bgcolor="#ffffff", height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(pvm_fig, use_container_width=True)

        st.markdown("#### Granular Product-Level PVM Breakdown")
        st.dataframe(pvm["detail_table"].style.format({
            "Budget_Units": "{:,.0f}", "Actual_Units": "{:,.0f}",
            "Budget_Price": "₹{:,.2f}", "Actual_Price": "₹{:,.2f}",
            "Price_Effect": "₹{:,.2f}", "Volume_Effect": "₹{:,.2f}",
            "Mix_Effect": "₹{:,.2f}", "Product_Rev_Variance": "₹{:,.2f}"
        }), use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 4: DEPARTMENT ANALYSIS
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Departmental Performance Deep Dive")

        st.dataframe(dept_summary.style.format({
            "Actual_Revenue": "₹{:,.0f}", "Budget_Revenue": "₹{:,.0f}",
            "Revenue_Variance": "₹{:,.0f}", "Revenue_Variance_Pct": "{:+.2f}%",
            "Actual_EBITDA": "₹{:,.0f}", "Budget_EBITDA": "₹{:,.0f}",
            "EBITDA_Variance": "₹{:,.0f}", "EBITDA_Variance_Pct": "{:+.2f}%",
            "Actual_Margin": "{:.2%}", "Budget_Margin": "{:.2%}"
        }), use_container_width=True)

        st.write("")
        st.subheader("Department Filtered P&L Drill-Down")
        chosen_dept = st.selectbox("Select Business Unit to inspect:", df["Department"].unique(), key="dept_inspector")
        dept_drill = df[df["Department"] == chosen_dept]
        if sel_month != "Full Year (All Months)":
            dept_drill = dept_drill[dept_drill["Month"] == sel_month]

        dept_kpis = compute_financial_kpis(dept_drill)

        dp_col1, dp_col2, dp_col3 = st.columns(3)
        dp_col1.metric("Revenue vs Budget", f"₹{dept_kpis['Actual_Revenue']:,.0f}", f"{dept_kpis['Variance_Revenue']:+,.0f} ({dept_kpis['Variance_Revenue_Pct']:+.1f}%)")
        dp_col2.metric("EBITDA vs Budget", f"₹{dept_kpis['Actual_EBITDA']:,.0f}", f"{dept_kpis['Variance_EBITDA']:+,.0f} ({dept_kpis['Variance_EBITDA_Pct']:+.1f}%)")
        dp_col3.metric("EBITDA Margin", f"{dept_kpis['Actual_EBITDA_Margin']*100:.2f}%", f"{dept_kpis['Variance_Margin_Bps']:+.1f} bps")

    # -------------------------------------------------------------------------
    # TAB 5: MATERIALITY & TOP DRIVERS
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Materiality Screening & Root Drivers")
        st.markdown(f"Screening parameters: **Absolute Threshold >= ₹{abs_thresh:,.0f}** OR **Percentage Threshold >= {pct_thresh:.1f}%**")

        mat_filtered = material_df[material_df["Is_Material"]]

        c_fav, c_unfav = st.columns(2)
        top_fav, top_unfav = get_top_drivers(material_df, 5)

        with c_fav:
            st.markdown("##### 🟢 Top 5 Favorable Variance Contributors")
            st.dataframe(top_fav[["Department", "Metric", "Actual", "Variance", "Variance_Pct"]].style.format({
                "Actual": "₹{:,.0f}", "Variance": "₹{:,.0f}", "Variance_Pct": "{:+.2f}%"
            }), hide_index=True, use_container_width=True)

        with c_unfav:
            st.markdown("##### 🔴 Top 5 Unfavorable Variance Overruns")
            st.dataframe(top_unfav[["Department", "Metric", "Actual", "Variance", "Variance_Pct"]].style.format({
                "Actual": "₹{:,.0f}", "Variance": "₹{:,.0f}", "Variance_Pct": "{:+.2f}%"
            }), hide_index=True, use_container_width=True)

        st.markdown("#### Complete Material Variances Ledger")
        st.dataframe(mat_filtered[["Department", "Metric", "Budget", "Actual", "Variance", "Variance_Pct", "Favorability"]].style.format({
            "Budget": "₹{:,.0f}", "Actual": "₹{:,.0f}", "Variance": "₹{:,.0f}", "Variance_Pct": "{:+.2f}%"
        }), hide_index=True, use_container_width=True)

        mat_csv = mat_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Material Variances (CSV)", data=mat_csv, file_name="material_variances.csv", mime="text/csv")

    # -------------------------------------------------------------------------
    # TAB 6: AI MANAGEMENT COMMENTARY
    # -------------------------------------------------------------------------
    with tabs[5]:
        st.subheader("Executive Management Variance Commentary")
        st.caption("Factual reporting generated exclusively from computed numbers.")

        payload = build_structured_context_payload(kpis, pvm, material_df)

        if st.button("Generate Narrative Commentary", type="primary"):
            with st.spinner("Compiling deterministic report..."):
                commentary_out = generate_ai_commentary(payload, effective_api_key)
                st.session_state["commentary"] = commentary_out

        if "commentary" in st.session_state:
            st.markdown(st.session_state["commentary"])
            st.download_button("📥 Download Commentary (.txt)", data=st.session_state["commentary"], file_name="fpna_commentary.txt")
        else:
            # Render baseline preview
            default_comm = generate_deterministic_commentary(payload)
            st.markdown(default_comm)
            st.download_button("📥 Download Commentary (.txt)", data=default_comm, file_name="fpna_commentary.txt")

    # -------------------------------------------------------------------------
    # TAB 7: ASK THE P&L
    # -------------------------------------------------------------------------
    with tabs[6]:
        st.subheader("Ask the P&L Interactive Query Engine")
        st.caption("Ask specific variance, departmental, and driver questions backed by validated figures.")

        user_q = st.text_input(
            "Enter your analytical question:",
            placeholder="e.g. Why is EBITDA below budget? Which department has the largest unfavorable variance?"
        )

        preset_col1, preset_col2, preset_col3 = st.columns(3)
        if preset_col1.button("Why is EBITDA below budget?"):
            user_q = "Why is EBITDA below budget?"
        if preset_col2.button("Which department has largest unfavorable variance?"):
            user_q = "Which department has largest unfavorable variance?"
        if preset_col3.button("Explain revenue drivers"):
            user_q = "Explain revenue drivers"

        if user_q:
            st.markdown(f"**Query:** *{user_q}*")
            response = query_pnl_dataset(user_q, kpis, pvm, material_df, dept_summary)
            st.info(f"**Answer:** {response}")

    # -------------------------------------------------------------------------
    # TAB 8: DATA & SCHEMAS
    # -------------------------------------------------------------------------
    with tabs[7]:
        st.subheader("Data Architecture & Audit Trail")
        st.markdown(f"**Active Records:** {len(filtered_df):,} rows")

        st.markdown("##### Expected CSV Data Schema")
        st.code("""
Month,Department,Product,Budget_Revenue,Actual_Revenue,Forecast_Revenue,Prior_Year_Revenue,
Budget_Units,Actual_Units,Budget_Price,Actual_Price,Budget_COGS,Actual_COGS,
Budget_Marketing,Actual_Marketing,Budget_Employee,Actual_Employee,
Budget_Technology,Actual_Technology,Budget_Other_Opex,Actual_Other_Opex
        """, language="csv")

        st.dataframe(filtered_df.head(50), use_container_width=True)
        raw_csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Active Dataset (CSV)", data=raw_csv, file_name="active_fpna_dataset.csv", mime="text/csv")

if __name__ == "__main__":
    main()