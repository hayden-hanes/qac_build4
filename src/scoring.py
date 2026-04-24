# src/scoring.py
"""
Quality scoring functions based on the following screens:
  1. Accrual Screens        -> COMBOACCRUAL
  2. Beneish M-Score        -> PMAN (fraud probability)
  3. Financial Distress     -> PFD
  4. Cheapness              -> PRICE (EV/EBIT, already in tools.py)
  5. Franchise Power        -> P_FP
  6. Financial Strength     -> P_FS

Final score:
  QUALITY = 0.5 x P_FP + 0.5 x P_FS
"""

import numpy as np
import pandas as pd
from scipy.stats import norm

#columns of the CSV, made to match exactly from the origonal one we copied from WRDS

TICKER  = "(tic) Ticker Symbol"
COMPANY = "(conm) Company Name"
DATE    = "(datadate) Data Date"
MKTCAP  = "(mkvalt) Market Value - Total - Fiscal"
EBIT    = "(ebit) Earnings Before Interest and Taxes"
AT      = "(at) Assets - Total"
ACT     = "(act) Current Assets - Total"
LCT     = "(lct) Current Liabilities - Total"
DP      = "(dp) Depreciation and Amortization"
SALE    = "(sale) Sales/Turnover (Net)"
NI      = "(ni) Net Income (Loss)"
OANCF   = "(oancf) Operating Activities - Net Cash Flow"
DEBT_LT = "(dltt) Long-Term Debt - Total"
DEBT_CL = "(dlc) Debt in Current Liabilities - Total"
CASH    = "(che) Cash and Short-Term Investments"
SEQ     = "(seq) Stockholders Equity - Parent"
PPEGT   = "(ppegt) Property, Plant and Equipment - Total (Gross)"
COGS    = "(cogs) Cost of Goods Sold"
XSGA    = "(xsga) Selling, General and Administrative Expense"
RECT    = "(rect) Receivables - Total"
PRCC_F  = "(prcc_f) Price Close - Annual - Fiscal"
CSHO    = "(csho) Common Shares Outstanding"


def _prepare(df):
    """Parse dates, cast numerics, sort by company and date."""
    df = df.copy()
    df[DATE] = pd.to_datetime(df[DATE], dayfirst=True, errors="coerce")
    num_cols = [MKTCAP, EBIT, AT, ACT, LCT, DP, SALE, NI, OANCF,
                DEBT_LT, DEBT_CL, CASH, SEQ, PPEGT, COGS, XSGA,
                RECT, PRCC_F, CSHO]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values([TICKER, DATE]).reset_index(drop=True)
    return df


def _invested_capital(df):
    """Invested Capital = SEQ + Long-term Debt + Current Debt - Cash"""
    return (
        df[SEQ].fillna(0)
        + df[DEBT_LT].fillna(0)
        + df[DEBT_CL].fillna(0)
        - df[CASH].fillna(0)
    )


def _pct_rank(series):
    """Percentile rank (0-1), higher = better rank."""
    return series.rank(pct=True, na_option="keep")


def _geo_mean(values):
    """Geometric mean of a sequence, handling negatives by returning NaN."""
    values = np.array(values, dtype=float)
    if np.any(np.isnan(values)) or len(values) == 0:
        return np.nan
    if np.any(values <= 0):
        return np.nan
    return np.exp(np.mean(np.log(values)))


#accrual screens

def compute_accruals(df):
    """
    STA  = (CA(t) - CL(t) - DEP(t)) / Total Assets(t)
    SNOA = (operating assets(t) - operating liabilities(t)) / total assets(t)
         operating assets      = AT - CASH
         operating liabilities = AT - DEBT_LT - DEBT_CL - SEQ

    P_STA        = percentile(STA)   -- lower accruals = higher quality, so we invert
    P_SNOA       = percentile(SNOA)  -- same
    COMBOACCRUAL = average(P_STA, P_SNOA)
    """
    df = _prepare(df)

    df["STA"] = (
        (df[ACT].fillna(0) - df[LCT].fillna(0) - df[DP].fillna(0))
        / df[AT]
    )

    op_assets  = df[AT] - df[CASH].fillna(0)
    op_liab    = df[AT] - df[DEBT_LT].fillna(0) - df[DEBT_CL].fillna(0) - df[SEQ].fillna(0)
    df["SNOA"] = (op_assets - op_liab) / df[AT]

    # Lower accruals = better quality, so invert ranks (1 - pct_rank)
    df["P_STA"]       = 1 - _pct_rank(df["STA"])
    df["P_SNOA"]      = 1 - _pct_rank(df["SNOA"])
    df["COMBOACCRUAL"] = (df["P_STA"] + df["P_SNOA"]) / 2

    return df[[TICKER, COMPANY, DATE, "STA", "SNOA", "P_STA", "P_SNOA", "COMBOACCRUAL"]]

 
#beneish m-score

def compute_beneish(df):
    """
    Uses the full historical panel with year-over-year changes.

    Components (all require t and t-1):
      DSRI  = (Receivables(t)/Sales(t)) / (Receivables(t-1)/Sales(t-1))
      GMI   = Gross Margin(t-1) / Gross Margin(t)
      AQI   = (1 - (ACT(t) + PPEGT(t)) / AT(t)) / (1 - (ACT(t-1) + PPEGT(t-1)) / AT(t-1))
      SGI   = Sales(t) / Sales(t-1)
      DEPI  = (DEP(t-1) / (PPEGT(t-1) + DEP(t-1))) / (DEP(t) / (PPEGT(t) + DEP(t)))
      SGAI  = (XSGA(t)/Sales(t)) / (XSGA(t-1)/Sales(t-1))
      LVGI  = ((DEBT_LT(t) + DEBT_CL(t)) / AT(t)) / ((DEBT_LT(t-1) + DEBT_CL(t-1)) / AT(t-1))
      TATA  = (NI(t) - OANCF(t)) / AT(t)

    PROBM = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
            + 0.115*DEPI - 0.172*SGAI - 0.327*LVGI + 4.679*TATA
    PMAN  = CDF(PROBM)   [lower = less likely to be manipulating = better]
    """
    df = _prepare(df)
    g = df.groupby(TICKER)

    df["RECT_t1"]  = g[RECT].shift(1)
    df["SALE_t1"]  = g[SALE].shift(1)
    df["AT_t1"]    = g[AT].shift(1)
    df["ACT_t1"]   = g[ACT].shift(1)
    df["PPEGT_t1"] = g[PPEGT].shift(1)
    df["DP_t1"]    = g[DP].shift(1)
    df["XSGA_t1"]  = g[XSGA].shift(1)
    df["DEBT_t1"]  = g[DEBT_LT].shift(1) + g[DEBT_CL].shift(1)
    df["COGS_t1"]  = g[COGS].shift(1)

    df["DSRI"] = (df[RECT] / df[SALE]) / (df["RECT_t1"] / df["SALE_t1"])

    gm_t  = (df[SALE] - df[COGS]) / df[SALE]
    gm_t1 = (df["SALE_t1"] - df["COGS_t1"]) / df["SALE_t1"]
    df["GMI"] = gm_t1 / gm_t

    aq_t  = 1 - (df[ACT]       + df[PPEGT])       / df[AT]
    aq_t1 = 1 - (df["ACT_t1"]  + df["PPEGT_t1"])  / df["AT_t1"]
    df["AQI"] = aq_t / aq_t1

    df["SGI"] = df[SALE] / df["SALE_t1"]

    dep_rate_t  = df[DP]       / (df[PPEGT]       + df[DP])
    dep_rate_t1 = df["DP_t1"]  / (df["PPEGT_t1"]  + df["DP_t1"])
    df["DEPI"] = dep_rate_t1 / dep_rate_t

    df["SGAI"] = (df[XSGA] / df[SALE]) / (df["XSGA_t1"] / df["SALE_t1"])

    lev_t  = (df[DEBT_LT].fillna(0) + df[DEBT_CL].fillna(0)) / df[AT]
    lev_t1 = df["DEBT_t1"] / df["AT_t1"]
    df["LVGI"] = lev_t / lev_t1

    df["TATA"] = (df[NI] - df[OANCF]) / df[AT]

    df["PROBM"] = (
        -4.84
        + 0.920 * df["DSRI"]
        + 0.528 * df["GMI"]
        + 0.404 * df["AQI"]
        + 0.892 * df["SGI"]
        + 0.115 * df["DEPI"]
        - 0.172 * df["SGAI"]
        - 0.327 * df["LVGI"]
        + 4.679 * df["TATA"]
    )

    df["PMAN"] = df["PROBM"].apply(lambda x: norm.cdf(x) if pd.notna(x) else np.nan)

    cols = [TICKER, COMPANY, DATE,
            "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA",
            "PROBM", "PMAN"]
    return df[cols]

#pdf financial distress

def compute_distress(df):
    """
    Uses 3-year trailing averages for NIMTAAVG and EXRETAVG.

    Inputs:
      NIMTA    = NI / (Market Cap + Total Liabilities)   [net income to market+liab]
      TLMTA    = Total Liabilities / (Market Cap + Total Liabilities)
      CASHMTA  = Cash / (Market Cap + Total Liabilities)
      EXRET    = log(1 + stock return) - log(1 + market return)  [excess return]
                 approximated as: log(PRCC_F(t)/PRCC_F(t-1)) - 0  (market return = 0 approximation)
                 For a cleaner implementation, replace with actual index return data.
      SIGMA    = std dev of annual NIMTA over trailing 3 years
      RSIZE    = log(MKTCAP / total market cap)  [relative size]
                 approximated as log(MKTCAP) since total market not in dataset
      MB       = MKTCAP / SEQ  [market-to-book]
      PRICE    = log(min(PRCC_F, 15))  [log price, winsorized at $15]

    LPFD = -20.26*NIMTAAVG + 1.42*TLMTA - 7.13*CASHMTA
           + 1.41*EXRETAVG - 0.042*SIGMA - 1.42*RSIZE
           - 0.045*MB - 0.058*PRICE - 9.16
    PFD  = 1 / (1 + exp(-LPFD))    [lower = less distressed = better]
    """
    df = _prepare(df)
    g  = df.groupby(TICKER)

    total_liab = df[AT].fillna(0) - df[SEQ].fillna(0)
    mktcap_plus_liab = df[MKTCAP].fillna(0) + total_liab

    df["NIMTA"]   = df[NI] / mktcap_plus_liab.replace(0, np.nan)
    df["TLMTA"]   = total_liab / mktcap_plus_liab.replace(0, np.nan)
    df["CASHMTA"] = df[CASH].fillna(0) / mktcap_plus_liab.replace(0, np.nan)

    # Excess return: log price change YoY (market return approximated as 0)
    df["PRCC_t1"] = g[PRCC_F].shift(1)
    df["EXRET"]   = np.log(df[PRCC_F] / df["PRCC_t1"].replace(0, np.nan))

    # 3-year trailing averages
    df["NIMTAAVG"] = g["NIMTA"].transform(lambda x: x.rolling(3, min_periods=2).mean())
    df["EXRETAVG"] = g["EXRET"].transform(lambda x: x.rolling(3, min_periods=2).mean())
    df["SIGMA"]    = g["NIMTA"].transform(lambda x: x.rolling(3, min_periods=2).std())

    df["RSIZE"] = np.log(df[MKTCAP].replace(0, np.nan))
    df["MB"]    = df[MKTCAP] / df[SEQ].replace(0, np.nan)
    df["PRICE"] = np.log(df[PRCC_F].clip(upper=15).replace(0, np.nan))

    df["LPFD"] = (
        -20.26 * df["NIMTAAVG"]
        +  1.42 * df["TLMTA"]
        -  7.13 * df["CASHMTA"]
        +  1.41 * df["EXRETAVG"]
        -  0.042 * df["SIGMA"]
        -  1.42 * df["RSIZE"]
        -  0.045 * df["MB"]
        -  0.058 * df["PRICE"]
        -  9.16
    )

    df["PFD"] = 1 / (1 + np.exp(-df["LPFD"]))

    cols = [TICKER, COMPANY, DATE,
            "NIMTAAVG", "TLMTA", "CASHMTA", "EXRETAVG",
            "SIGMA", "RSIZE", "MB", "PRICE", "LPFD", "PFD"]
    return df[cols]

#franchise power

def compute_franchise_power(df):
    """
    8yr ROA  = 8-year geometric mean of (NI / AT)
    8yr ROC  = 8-year geometric mean of (NI / Invested Capital)
               Invested Capital = SEQ + DEBT_LT + DEBT_CL - CASH
    8yr FCF  = 8-year geometric mean of (OANCF / AT)

    P_8yr_ROA  = percentile(8yr ROA)
    P_8yr_ROC  = percentile(8yr ROC)
    P_CFOA     = percentile(8yr FCF / assets)
    MM         = 1 if SALE > median(SALE), else 0  [market share proxy]
    P_FP       = percentile(average(P_8yr_ROA, P_8yr_ROC, P_CFOA, MM))
    """
    df = _prepare(df)

    df["ROA"] = df[NI] / df[AT].replace(0, np.nan)
    df["ROC"] = df[NI] / _invested_capital(df).replace(0, np.nan)
    df["FCF"] = df[OANCF] / df[AT].replace(0, np.nan)

    WINDOW = 8

    def _rolling_geo_mean(series, window):
        result = []
        arr = series.values
        for i in range(len(arr)):
            start = max(0, i - window + 1)
            window_vals = arr[start: i + 1]
            # Shift to positive for geometric mean
            min_val = np.nanmin(window_vals)
            shift = abs(min_val) + 1e-6 if min_val <= 0 else 0
            shifted = window_vals + shift
            if len(shifted) < window or np.any(np.isnan(shifted)):
                result.append(np.nan)
            else:
                gm = np.exp(np.nanmean(np.log(shifted))) - shift
                result.append(gm)
        return pd.Series(result, index=series.index)

    g = df.groupby(TICKER)
    df["8yr_ROA"] = g["ROA"].transform(lambda x: _rolling_geo_mean(x, WINDOW))
    df["8yr_ROC"] = g["ROC"].transform(lambda x: _rolling_geo_mean(x, WINDOW))
    df["8yr_FCF"] = g["FCF"].transform(lambda x: _rolling_geo_mean(x, WINDOW))

    # Market share proxy: 1 if revenue above median for that year
    df["MM"] = df.groupby(DATE)[SALE].transform(
        lambda x: (x > x.median()).astype(float)
    )

    df["P_8yr_ROA"] = _pct_rank(df["8yr_ROA"])
    df["P_8yr_ROC"] = _pct_rank(df["8yr_ROC"])
    df["P_CFOA"]    = _pct_rank(df["8yr_FCF"])

    df["FP_avg"] = (df["P_8yr_ROA"] + df["P_8yr_ROC"] + df["P_CFOA"] + df["MM"]) / 4
    df["P_FP"]   = _pct_rank(df["FP_avg"])

    cols = [TICKER, COMPANY, DATE,
            "8yr_ROA", "8yr_ROC", "8yr_FCF", "MM",
            "P_8yr_ROA", "P_8yr_ROC", "P_CFOA", "P_FP"]
    return df[cols]


#finacial strength

def compute_financial_strength(df):
    """
    ROA     = NI / AT
    FCFTA   = OANCF / AT
    LEVER   = change in (total debt / AT) YoY          [decrease = good]
    LIQUID  = change in (ACT / LCT) YoY                [increase = good]
    NEQISS  = change in CSHO YoY                        [decrease = good]
    AROA    = ROA(t) - ROA(t-1)
    AFCFTA  = FCFTA(t) - FCFTA(t-1)
    ATURN   = SALE/AT(t) - SALE/AT(t-1)
    AMARGIN = (SALE - COGS)/SALE (t) - (SALE - COGS)/SALE (t-1)

    Binary scores (1 if condition met, else 0):
      FS_ROA     = 1 if ROA > 0
      FS_FCFTA   = 1 if FCFTA > 0
      FS_ACCRUAL = 1 if (FCFTA - ROA) < 0    [cash earnings > accrual earnings]
      FS_LEVER   = 1 if LEVER > 0             [leverage decreased]
      FS_LIQUID  = 1 if LIQUID > 0            [liquidity improved]
      FS_NEQISS  = 1 if NEQISS < 0            [no dilution]
      FS_AROA    = 1 if AROA > 0
      FS_AFCFTA  = 1 if AFCFTA > 0
      FS_ATURN   = 1 if ATURN > 0
      FS_AMARGIN = 1 if AMARGIN > 0

    P_FS = sum of all FS_ scores (0-10)
    """
    df = _prepare(df)
    g  = df.groupby(TICKER)

    df["ROA"]   = df[NI]    / df[AT].replace(0, np.nan)
    df["FCFTA"] = df[OANCF] / df[AT].replace(0, np.nan)
    df["TURN"]  = df[SALE]  / df[AT].replace(0, np.nan)
    df["MARGIN"]= (df[SALE] - df[COGS]) / df[SALE].replace(0, np.nan)
    df["LEV"]   = (df[DEBT_LT].fillna(0) + df[DEBT_CL].fillna(0)) / df[AT].replace(0, np.nan)
    df["LIQ"]   = df[ACT]  / df[LCT].replace(0, np.nan)

    # Year-over-year changes
    df["LEVER"]   = -(g["LEV"].diff())       # positive if leverage decreased
    df["LIQUID"]  =   g["LIQ"].diff()        # positive if liquidity improved
    df["NEQISS"]  = -(g[CSHO].diff())        # positive if shares decreased
    df["AROA"]    =   g["ROA"].diff()
    df["AFCFTA"]  =   g["FCFTA"].diff()
    df["ATURN"]   =   g["TURN"].diff()
    df["AMARGIN"] =   g["MARGIN"].diff()

    # Binary flags
    df["FS_ROA"]     = (df["ROA"]   > 0).astype(int)
    df["FS_FCFTA"]   = (df["FCFTA"] > 0).astype(int)
    df["FS_ACCRUAL"] = ((df["FCFTA"] - df["ROA"]) < 0).astype(int)
    df["FS_LEVER"]   = (df["LEVER"]   > 0).astype(int)
    df["FS_LIQUID"]  = (df["LIQUID"]  > 0).astype(int)
    df["FS_NEQISS"]  = (df["NEQISS"]  < 0).astype(int)
    df["FS_AROA"]    = (df["AROA"]    > 0).astype(int)
    df["FS_AFCFTA"]  = (df["AFCFTA"]  > 0).astype(int)
    df["FS_ATURN"]   = (df["ATURN"]   > 0).astype(int)
    df["FS_AMARGIN"] = (df["AMARGIN"] > 0).astype(int)

    fs_cols = ["FS_ROA", "FS_FCFTA", "FS_ACCRUAL", "FS_LEVER", "FS_LIQUID",
               "FS_NEQISS", "FS_AROA", "FS_AFCFTA", "FS_ATURN", "FS_AMARGIN"]
    df["P_FS"] = df[fs_cols].sum(axis=1)

    cols = [TICKER, COMPANY, DATE] + fs_cols + ["P_FS"]
    return df[cols]


#final quality score


def compute_quality_score(df):
    """
    Combines Franchise Power and Financial Strength into a final quality score.
    QUALITY = 0.5 x P_FP + 0.5 x P_FS

    Returns the latest observation per company with all component scores.
    """
    fp = compute_franchise_power(df)[[TICKER, DATE, "P_FP"]]
    fs = compute_financial_strength(df)[[TICKER, DATE, "P_FS"]]
    ac = compute_accruals(df)[[TICKER, DATE, "COMBOACCRUAL"]]
    bm = compute_beneish(df)[[TICKER, DATE, "PMAN"]]
    pd_ = compute_distress(df)[[TICKER, DATE, "PFD"]]

    # Merge all on TICKER + DATE
    merged = fp.merge(fs,  on=[TICKER, DATE], how="inner")
    merged = merged.merge(ac,  on=[TICKER, DATE], how="left")
    merged = merged.merge(bm,  on=[TICKER, DATE], how="left")
    merged = merged.merge(pd_, on=[TICKER, DATE], how="left")

    # Normalise P_FS to 0-1 (it's a raw count 0-10)
    merged["P_FS_norm"] = merged["P_FS"] / 10.0

    merged["QUALITY"] = 0.5 * merged["P_FP"] + 0.5 * merged["P_FS_norm"]

    # Keep only the latest year per company
    merged = (
        merged.sort_values(DATE)
        .groupby(TICKER, as_index=False)
        .last()
    )

    # Add company name back
    name_map = df[[TICKER, COMPANY]].drop_duplicates(subset=TICKER)
    merged = merged.merge(name_map, on=TICKER, how="left")

    merged = merged.sort_values("QUALITY", ascending=False).reset_index(drop=True)
    merged.index += 1
    merged.index.name = "Rank"

    return merged[[TICKER, COMPANY, DATE, "P_FP", "P_FS", "COMBOACCRUAL", "PMAN", "PFD", "QUALITY"]]


#tools registry entries


def score_franchise_power(df, **kwargs):
    result = compute_franchise_power(df)
    latest = result.sort_values(DATE).groupby(TICKER, as_index=False).last()
    return {"text": latest[[TICKER, COMPANY, "P_8yr_ROA", "P_8yr_ROC", "P_CFOA", "P_FP"]].to_string(index=False), "artifact_paths": []}

def score_financial_strength(df, **kwargs):
    result = compute_financial_strength(df)
    latest = result.sort_values(DATE).groupby(TICKER, as_index=False).last()
    return {"text": latest[[TICKER, COMPANY, "P_FS"]].to_string(index=False), "artifact_paths": []}

def score_accruals(df, **kwargs):
    result = compute_accruals(df)
    latest = result.sort_values(DATE).groupby(TICKER, as_index=False).last()
    return {"text": latest[[TICKER, COMPANY, "P_STA", "P_SNOA", "COMBOACCRUAL"]].to_string(index=False), "artifact_paths": []}

def score_beneish(df, **kwargs):
    result = compute_beneish(df)
    latest = result.sort_values(DATE).groupby(TICKER, as_index=False).last()
    return {"text": latest[[TICKER, COMPANY, "PROBM", "PMAN"]].to_string(index=False), "artifact_paths": []}

def score_distress(df, **kwargs):
    result = compute_distress(df)
    latest = result.sort_values(DATE).groupby(TICKER, as_index=False).last()
    return {"text": latest[[TICKER, COMPANY, "PFD"]].to_string(index=False), "artifact_paths": []}

def score_quality(df, **kwargs):
    result = compute_quality_score(df)
    return {"text": result.to_string(), "artifact_paths": []}