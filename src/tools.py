# tools registry for ai data analysis agent

import os
import pandas as pd
from openai import OpenAI

import src.scoring as scoring

import src.checks as checks
import src.io_utils as io_utils
import src.modeling as modeling
import src.plotting as plotting
import src.profiling as profiling
import src.summaries as summaries

# src/tools.py
"""
def calc_ratio():
    #calculate the EV/EBITDA ratio

def rank_ratio():
    #rank the companies with the lowest EV/EBITDA ratio

def write():
    #write a 2 sentence blurb about each company
"""

# column names
TICKER  = "(tic) Ticker Symbol"
COMPANY = "(conm) Company Name"
DATE    = "(datadate) Data Date"
MKTCAP  = "(mkvalt) Market Value - Total - Fiscal"
DEBT_LT = "(dltt) Long-Term Debt - Total"
DEBT_CL = "(dlc) Debt in Current Liabilities - Total"
CASH    = "(che) Cash and Short-Term Investments"
EBIT    = "(ebit) Earnings Before Interest and Taxes"
REVENUE = "(sale) Sales/Turnover (Net)"
NI      = "(ni) Net Income (Loss)"
 
 
def _latest(df):
    """Get the most recent fiscal year row for each company."""
    df = df.copy()
    df[DATE] = pd.to_datetime(df[DATE], dayfirst=True, errors="coerce")
    return df.sort_values(DATE).groupby(TICKER, as_index=False).last()
 
 
def _ev_ebit_df(df):
    """Return a dataframe with EV and EV/EBIT calculated for each company."""
    latest = _latest(df)
    for col in [MKTCAP, DEBT_LT, DEBT_CL, CASH, EBIT]:
        latest[col] = pd.to_numeric(latest[col], errors="coerce")
    latest["EV"]= latest[MKTCAP] + latest[DEBT_LT].fillna(0) + latest[DEBT_CL].fillna(0) - latest[CASH].fillna(0)
    latest["EV_EBIT"] = latest["EV"] / latest[EBIT]
    return latest[[TICKER, COMPANY, MKTCAP, EBIT, "EV", "EV_EBIT"]].dropna(subset=["EV_EBIT"])
 
 
def calculate_ev_ebit(df, **kwargs):
    """Calculate EV/EBIT for each company using its most recent fiscal year."""
    result = _ev_ebit_df(df).rename(columns={TICKER: "Ticker", COMPANY: "Company", MKTCAP: "Market_Cap", EBIT: "EBIT"})
    return {"text": result.to_string(index=False), "artifact_paths": []}
 
 
def rank_stocks(df, **kwargs):
    """Rank companies from cheapest to most expensive by EV/EBIT (lower = better)."""
    financial_keywords = ["BANK", "FINANCIAL", "INSURANCE", "BANCORP", "SAVINGS", "REIT", "TRUST", "MORTGAGE", "LENDING", "CREDIT", "CAPITAL"]
    pattern = "|".join(financial_keywords)
    
    result = _ev_ebit_df(df)
    result = result[
        (result["EV_EBIT"] >= 1.0) &
        (result[EBIT] > 0) &
        (result["EV"] > 0) &
        (result[MKTCAP] >= 1000)
    ].sort_values("EV_EBIT").reset_index(drop=True)
    result = result.head(10)
    result.index += 1
    result.index.name = "Rank"
    result = result.rename(columns={TICKER: "Ticker", COMPANY: "Company", MKTCAP: "Market_Cap", EBIT: "EBIT"})
    result["EV_EBIT"] = result["EV_EBIT"].map(lambda x: f"{x:.2f}x")
    return {"text": result.to_string(), "artifact_paths": []}

def write_company_blurbs(df, **kwargs):
    """Write a 2-sentence analyst blurb for each company using the OpenAI API."""
    client = OpenAI()
    latest = _latest(df)
    for col in [MKTCAP, DEBT_LT, DEBT_CL, CASH, EBIT, REVENUE, NI]:
        latest[col] = pd.to_numeric(latest[col], errors="coerce")
    latest["EV_EBIT"] = (latest[MKTCAP] + latest[DEBT_LT].fillna(0) + latest[DEBT_CL].fillna(0) - latest[CASH].fillna(0)) / latest[EBIT]
 
    blurbs = []
    for _, row in latest.iterrows():
        prompt = (
            f"Write exactly 2 sentences about {row[COMPANY]} ({row[TICKER]}). "
            f"Revenue: ${row[REVENUE]:,.0f}M, EBIT: ${row[EBIT]:,.0f}M, "
            f"Net Income: ${row[NI]:,.0f}M, EV/EBIT: {row['EV_EBIT']:.1f}x. "
            f"Sentence 1: describe profitability. Sentence 2: comment on EV/EBIT valuation (15-25x is generally average for large-cap stocks)."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.4,
        )
        blurbs.append(f"[{row[TICKER]}] {row[COMPANY]}\n{response.choices[0].message.content.strip()}\n")
 
    return {"text": "\n".join(blurbs), "artifact_paths": []}
 

TOOLS = {
    # summaries
    "calculate_ev_ebit": calculate_ev_ebit, 
    "rank_stocks": rank_stocks, 
    "write_company_blurbs": write_company_blurbs,
    "summarize_numeric": summaries.summarize_numeric,
    "summarize_categorical": summaries.summarize_categorical,
    "missingness_table": summaries.missingness_table,
    "pearson_correlation": summaries.pearson_correlation,
    # profiling
    "basic_profile": profiling.basic_profile,
    "split_columns": profiling.split_columns,
    # modeling
    "multiple_linear_regression": modeling.multiple_linear_regression,
    # plotting
    "plot_missingness": plotting.plot_missingness,
    "plot_corr_heatmap": plotting.plot_corr_heatmap,
    "plot_histograms": plotting.plot_histograms,
    "plot_bar_charts": plotting.plot_bar_charts,
    "plot_cat_num_boxplot": plotting.plot_cat_num_boxplot,
    # checks
    "assert_json_safe": checks.assert_json_safe,
    "target_check": checks.target_check,
    # io
    "ensure_dirs": io_utils.ensure_dirs,
    "read_data": io_utils.read_data,
    #added
    "score_franchise_power": scoring.score_franchise_power,
    "score_financial_strength": scoring.score_financial_strength,
    "score_accruals": scoring.score_accruals,
    "score_beneish": scoring.score_beneish,
    "score_distress": scoring.score_distress,
    "score_quality": scoring.score_quality,
}

TOOL_DESCRIPTIONS = {
    "rank_stocks": "Calculates Enterprise Value (EV = Market Cap + Debt - Cash) divided by EBIT, then ranks companies from lowest to highest EV/EBIT ratio.",
    "write_company_blurbs": "Write a 2-sentence analyst blurb for each company based on financial data including revenue, EBIT, net income, and EV/EBIT valuation.",
    "plot_bar_charts": "Bar chart of category counts for categorical columns.",
    "plot_cat_num_boxplot": "Boxplot of a numeric variable grouped by a categorical variable.",
    "calculate_ev_ebit": "Calculate EV and EV/EBIT ratio for each company using their most recent fiscal year data.",
    "score_financial_strength": "Piotroski-style 10-point financial strength score (P_FS). Use for any request mentioning 'financial strength', 'FS score', or 'Piotroski'.",
    "score_franchise_power": "Computes 8-year geometric average ROA, ROC, and FCF/assets, ranked as franchise power (P_FP). Use for any request mentioning 'franchise power', 'FP score', 'ROA', or 'ROC'.",
    "score_accruals": "Computes balance-sheet accruals and net operating accruals (COMBOACCRUAL). Use for any request mentioning 'accruals', 'accrual screen', 'STA', or 'SNOA'.",
    "score_beneish": "Beneish M-Score fraud probability (PMAN). Use for any request mentioning 'Beneish', 'M-score', 'fraud screen', or 'earnings manipulation'.",
    "score_distress": "Financial distress probability (PFD) from Campbell et al. Use for any request mentioning 'financial distress', 'PFD', 'bankruptcy', or 'distress score'.",
    "score_quality": "Final quality score combining franchise power and financial strength: QUALITY = 0.5 x P_FP + 0.5 x P_FS. Use for any request mentioning 'quality score', 'final score', or 'QUALITY'.",
}



