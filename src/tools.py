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

def company_dashboard(df, ticker: str = None, **kwargs):
    """
    Generate a full metrics dashboard for a given company ticker.
    Runs all scoring functions and EV/EBIT calculation, returning
    a structured dict for rendering as an HTML dashboard.
    """
    if ticker is None:
        return {"text": "Please provide a ticker symbol.", "artifact_paths": []}

    ticker = ticker.upper()

    company_df = df[df[TICKER].str.upper() == ticker]
    if company_df.empty:
        return {"text": f"No data found for ticker: {ticker}", "artifact_paths": []}

    results = {}

    # --- Valuation ---
    ev_result = _ev_ebit_df(df)
    company_ev = ev_result[ev_result[TICKER].str.upper() == ticker]
    if not company_ev.empty:
        row = company_ev.iloc[0]
        results["ev_ebit"]    = round(float(row["EV_EBIT"]), 2)
        results["market_cap"] = round(float(row[MKTCAP]), 0)
        results["ebit"]       = round(float(row[EBIT]), 0)
        results["company"]    = row[COMPANY]

    # --- Quality scores ---
    def _get_score_by_position(score_fn, col_index):
        try:
            out = score_fn(df)
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            for line in text.splitlines():
                parts = line.split()
                if not parts or parts[0].upper() != ticker:
                    continue
                numeric_tokens = []
                for tok in parts:
                    try:
                        float(tok)
                        numeric_tokens.append(float(tok))
                    except ValueError:
                        continue
                if numeric_tokens:
                    idx = col_index if col_index >= 0 else len(numeric_tokens) + col_index
                    if 0 <= idx < len(numeric_tokens):
                        return round(numeric_tokens[idx], 4)
            return None
        except Exception as e:
            print(f"  [_get_score warning] {e}")
            return None

    results["franchise_power"]    = _get_score_by_position(scoring.score_franchise_power,    3)
    def _get_fs_percentile():
        try:
            out = scoring.score_financial_strength(df)
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            scores = {}
            for line in text.splitlines():
                parts = line.split()
                if not parts:
                    continue
                t = parts[0].upper()
                nums = []
                for tok in parts:
                    try:
                        nums.append(float(tok))
                    except ValueError:
                        continue
                if nums:
                    scores[t] = nums[0]
            if ticker not in scores:
                return None
            all_vals = [v for v in scores.values() if v is not None]
            ticker_val = scores[ticker]
            pct = sum(1 for v in all_vals if v <= ticker_val) / len(all_vals)
            return round(pct, 4)
        except Exception as e:
            print(f"  [_get_fs_percentile warning] {e}")
            return None

    results["financial_strength"] = _get_fs_percentile()
    results["accruals"]           = _get_score_by_position(scoring.score_accruals,           -1)
    results["beneish"]            = _get_score_by_position(scoring.score_beneish,            -1)
    results["distress"]           = _get_score_by_position(scoring.score_distress,           -1)

    fp = results["franchise_power"]
    fs = results["financial_strength"]
    if fp is not None and fs is not None:
        results["quality"] = round(0.5 * fp + 0.5 * fs, 4)
    else:
        results["quality"] = None

    # --- Analyst blurb ---
    blurb_result = write_company_blurbs(company_df)
    results["blurb"] = blurb_result.get("text", "")

    # --- Rank within peer universe ---
    ev_sorted = _ev_ebit_df(df).sort_values("EV_EBIT").reset_index(drop=True)
    ev_sorted.index += 1
    rank_match = ev_sorted[ev_sorted[TICKER].str.upper() == ticker]
    results["ev_rank"]    = int(rank_match.index[0]) if not rank_match.empty else None
    results["peer_count"] = len(ev_sorted)

    # --- HTML output ---
    import pathlib
    out_dir = pathlib.Path("tool_outputs")
    out_dir.mkdir(exist_ok=True)

    score_keys = ["franchise_power", "financial_strength", "quality", "accruals", "beneish", "distress"]
    invert_keys = {"beneish", "distress", "accruals"}
    score_rows = ""
    for k in score_keys:
        v = results.get(k)
        if v is not None:
            pct = (1 - float(v)) * 100 if k in invert_keys else float(v) * 100
            score_rows += f"<div class='s'><b>{k}</b>: {v}<div class='bar'><div class='fill' style='width:{pct:.0f}%'></div></div></div>"

    html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<style>
body {{ font-family: monospace; background: #0d0f14; color: #e8eaf0; padding: 40px; }}
.s {{ margin: 8px 0; }}
.bar {{ background: #333; height: 8px; border-radius: 4px; margin-top: 4px; }}
.fill {{ height: 8px; border-radius: 4px; background: #4ade80; }}
</style></head><body>
<h1 style='color:#c8a96e'>{results.get('company', 'N/A')} ({ticker})</h1>
<p>EV/EBIT: {results.get('ev_ebit', 'N/A')}x | Mkt Cap: ${results.get('market_cap', 0):,.0f}M | EBIT: ${results.get('ebit', 0):,.0f}M</p>
<hr style='border-color:#333'>
{score_rows}
<hr style='border-color:#333'>
<p style='color:#aaa'>{results.get('blurb', '')}</p>
</body></html>"""

    (out_dir / f"{ticker}_dashboard.html").write_text(html)
    print(f"Dashboard saved: tool_outputs/{ticker}_dashboard.html")

    lines = [
        f"=== Dashboard: {results.get('company', ticker)} ({ticker}) ===",
        f"EV/EBIT:           {results.get('ev_ebit', 'N/A')}x",
        f"Market Cap:        ${results.get('market_cap', 0):,.0f}M",
        f"EBIT:              ${results.get('ebit', 0):,.0f}M",
        f"EV rank:           #{results.get('ev_rank', 'N/A')} of {results.get('peer_count', 'N/A')}",
        "",
        f"Franchise Power:   {results.get('franchise_power', 'N/A')}",
        f"Fin. Strength:     {results.get('financial_strength', 'N/A')}",
        f"Quality:           {results.get('quality', 'N/A')}",
        f"Accruals:          {results.get('accruals', 'N/A')}",
        f"Beneish (PMAN):    {results.get('beneish', 'N/A')}",
        f"Distress (PFD):    {results.get('distress', 'N/A')}",
        "",
        "Blurb:",
        results.get("blurb", ""),
    ]

    return {"text": "\n".join(lines), "data": results, "artifact_paths": []}

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


def top_recommendations(df, top_n: int = 5, **kwargs):
    """
    Master Quantitative Value pipeline per Gray & Carlisle with step-by-step audit trail.
      0. Full universe: positive EBIT, positive EV, mktcap >= $1B
      1. Eliminate top 5% by COMBOACCRUAL (highest accruals)
      2. Eliminate top 5% by PMAN (highest fraud probability)
      3. Eliminate top 5% by PFD (highest distress probability)
      4. Rank survivors by EBIT/EV cheapness (P_PRICE)
      5. Rank survivors by QUALITY = 0.5 * P_FP + 0.5 * P_FS_norm (P_QUALITY)
      6. FINAL_SCORE = average(P_PRICE, P_QUALITY)
      7. Return top N stocks
    """
    lines = []

    def _log(msg):
        lines.append(msg)

    # --- Step 0: Base universe ---
    ev_df = _ev_ebit_df(df).copy()
    ev_df = ev_df[
        (ev_df["EV_EBIT"] >= 1.0) &
        (ev_df[EBIT] > 0) &
        (ev_df["EV"] > 0) &
        (ev_df[MKTCAP] >= 1000)
    ]
    ev_df["EBIT_EV"] = 1 / ev_df["EV_EBIT"]

    _log("=" * 60)
    _log("QUANTITATIVE VALUE SCREENING — STEP-BY-STEP")
    _log("=" * 60)
    _log(f"\nStep 0 — Full universe (positive EBIT, EV > 0, mktcap >= $1B): {len(ev_df)} stocks")
    _log("  " + ", ".join(sorted(ev_df[TICKER].tolist())))

    # Merge all quality screens via compute_quality_score
    quality_full = scoring.compute_quality_score(df)[
        [TICKER, "COMBOACCRUAL", "PMAN", "PFD", "P_FP", "P_FS"]
    ]
    merged = ev_df.merge(quality_full, on=TICKER, how="inner")

    # --- Step 1: Eliminate top 5% by COMBOACCRUAL ---
    thresh_ac = merged["COMBOACCRUAL"].quantile(0.95)
    removed = merged[merged["COMBOACCRUAL"] > thresh_ac][TICKER].tolist()
    merged = merged[merged["COMBOACCRUAL"] <= thresh_ac]
    _log(f"\nStep 1 — Eliminate top 5% COMBOACCRUAL (threshold={thresh_ac:.4f}): {len(merged)} stocks remain")
    if removed:
        _log(f"  Removed: {', '.join(removed)}")

    # --- Step 2: Eliminate top 5% by PMAN (Beneish fraud probability) ---
    thresh_pman = merged["PMAN"].quantile(0.95)
    removed = merged[merged["PMAN"] > thresh_pman][TICKER].tolist()
    merged = merged[merged["PMAN"] <= thresh_pman]
    _log(f"\nStep 2 — Eliminate top 5% PMAN (threshold={thresh_pman:.4f}): {len(merged)} stocks remain")
    if removed:
        _log(f"  Removed: {', '.join(removed)}")

    # --- Step 3: Eliminate top 5% by PFD (financial distress probability) ---
    thresh_pfd = merged["PFD"].quantile(0.95)
    removed = merged[merged["PFD"] > thresh_pfd][TICKER].tolist()
    merged = merged[merged["PFD"] <= thresh_pfd]
    _log(f"\nStep 3 — Eliminate top 5% PFD (threshold={thresh_pfd:.4f}): {len(merged)} stocks remain")
    if removed:
        _log(f"  Removed: {', '.join(removed)}")

    # --- Step 4: Rank on EBIT/EV cheapness ---
    merged["P_PRICE"] = merged["EBIT_EV"].rank(pct=True)
    _log(f"\nStep 4 — Ranked {len(merged)} survivors by EBIT/EV cheapness (P_PRICE)")

    # --- Step 5: Rank on QUALITY ---
    merged["P_FS_norm"] = merged["P_FS"] / 10.0
    merged["P_QUALITY"] = (0.5 * merged["P_FP"] + 0.5 * merged["P_FS_norm"]).rank(pct=True)
    _log(f"\nStep 5 — Ranked {len(merged)} survivors by QUALITY (P_QUALITY)")

    # --- Step 6: FINAL = average(P_PRICE, P_QUALITY) ---
    merged["FINAL_SCORE"] = (merged["P_PRICE"] + merged["P_QUALITY"]) / 2
    _log(f"\nStep 6 — FINAL_SCORE = average(P_PRICE, P_QUALITY)")

    # --- Step 7: Top N ---
    merged = merged.sort_values("FINAL_SCORE", ascending=False).head(top_n).reset_index(drop=True)
    merged.index += 1
    merged.index.name = "Rank"

    result = merged[[
        TICKER, COMPANY,
        "EV_EBIT", "P_PRICE",
        "P_FP", "P_FS", "P_QUALITY",
        "COMBOACCRUAL", "PMAN", "PFD",
        "FINAL_SCORE",
    ]].rename(columns={
        TICKER:         "Ticker",
        COMPANY:        "Company",
        "EV_EBIT":      "EV/EBIT",
        "P_PRICE":      "Cheapness_%ile",
        "P_FP":         "FranchisePower_%ile",
        "P_FS":         "FinStrength_raw",
        "P_QUALITY":    "Quality_%ile",
        "COMBOACCRUAL": "Accrual_score",
        "PMAN":         "Fraud_prob",
        "PFD":          "Distress_prob",
        "FINAL_SCORE":  "Final_Score",
    })

    _log(f"\nStep 7 — Top {top_n} stocks (buy list):")
    _log(result.to_string())
    _log("\n" + "=" * 60)

    return {"text": "\n".join(lines), "artifact_paths": []}


def rank_quantitative_value(df, top_n: int = 5, **kwargs):
    """Delegates to top_recommendations — the master QV pipeline."""
    return top_recommendations(df, top_n=top_n, **kwargs)
 

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
    "company_dashboard": company_dashboard,
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
    "rank_quantitative_value": rank_quantitative_value,
    "top_recommendations": top_recommendations,
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
    "company_dashboard": "Renders a full metrics dashboard for a single company by ticker. Runs EV/EBIT, all quality/scoring functions, and generates an analyst blurb. Use when user asks to 'show a dashboard', 'summarize a company', or 'profile [TICKER]'.",
    "rank_quantitative_value": "Final Quantitative Value screen: combines EBIT/EV cheapness percentile with QUALITY score (franchise power + financial strength) to rank and return the top 5 stocks per the Gray & Carlisle methodology.",
    "top_recommendations": "Full Quantitative Value pipeline: screens out manipulators, frauds, and distressed firms (top 5 percent each), then ranks survivors by combined cheapness (EBIT/EV) and quality (franchise power + financial strength) to return the top 5 stock recommendations per Gray & Carlisle."
}





