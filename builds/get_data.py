"""
get_data.py
===========
Pulls annual fundamental data for active US companies listed on major
exchanges (NYSE, NASDAQ, NYSE American/AMEX) from WRDS using
Compustat North America (comp.funda).

Exchange filter uses Compustat exchg codes:
  11 = NYSE
  14 = NYSE American (formerly AMEX)
  15 = Midwest Stock Exchange
  16 = Pacific Stock Exchange
  17 = Philadelphia Stock Exchange
  19 = Toronto Stock Exchange  (excluded — US only)
  11 = NYSE MKT
  12 = NYSE Arca
  14 = AMEX
  15 = BSE
  16 = CBOE
  17 = CHX
  19 = TSX
  11 = NYSE
  14 = AMEX
  15 = MSE
  16 = PSE
  17 = PHLX

  Codes used:
    11  NYSE
    12  NYSE Arca
    13  NYSE MKT (American)
    14  AMEX / NYSE American
    15  Midwest SE
    16  Pacific SE
    17  Philadelphia SE
    19  Toronto SE          <- excluded (Canada)
  Plus:
    32  NASDAQ (all tiers: Global Select, Global Market, Capital Market)

No market cap filter is applied — exchange listing is the only screen.
Expected output: ~8,000–12,000 rows (roughly 600–900 unique companies
over 15 years once Compustat standard filters are applied).

Results saved to:  msci_world_fundamentals.csv

Column names match the target dataset format exactly.

Requirements:
  pip install wrds pandas
"""

import sys
import pandas as pd
import wrds

# ------------------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------------------
START_DATE = "2010-01-01"
END_DATE   = "2025-12-31"

OUTPUT_FILE = "msci_world_fundamentals.csv"

# Compustat exchg codes for major US exchanges
# 11=NYSE, 12=NYSE Arca, 13=NYSE MKT, 14=AMEX/NYSE American, 32=NASDAQ
# Also including 15 (Midwest SE), 16 (Pacific SE), 17 (Philadelphia SE)
MAJOR_EXCHANGES = (11, 12, 13, 14, 15, 16, 17, 32)

# Compustat standard filters
DATAFMT = "STD"
INDFMT  = "INDL"
CONSOL  = "C"

# Exact column names from the target CSV (in order)
COLUMN_RENAME = {
    "costat":   "(costat) Active/Inactive Status Marker",
    "curcd":    "(curcd) ISO Currency Code",
    "datafmt":  "(datafmt) Data Format",
    "indfmt":   "(indfmt) Industry Format",
    "consol":   "(consol) Level of Consolidation - Company Annual Descriptor",
    "tic":      "(tic) Ticker Symbol",
    "datadate": "(datadate) Data Date",
    "gvkey":    "(gvkey) Global Company Key",
    "conm":     "(conm) Company Name",
    "cusip":    "(cusip) CUSIP",
    "exchg":    "(exchg) Stock Exchange Code",
    "fyr":      "(fyr) Fiscal Year-end Month",
    "fic":      "(fic) Current ISO Country Code - Incorporation",
    "act":      "(act) Current Assets - Total",
    "at":       "(at) Assets - Total",
    "che":      "(che) Cash and Short-Term Investments",
    "dlc":      "(dlc) Debt in Current Liabilities - Total",
    "dltt":     "(dltt) Long-Term Debt - Total",
    "lct":      "(lct) Current Liabilities - Total",
    "lt":       "(lt) Liabilities - Total",
    "ppegt":    "(ppegt) Property, Plant and Equipment - Total (Gross)",
    "re":       "(re) Retained Earnings",
    "rect":     "(rect) Receivables - Total",
    "seq":      "(seq) Stockholders Equity - Parent",
    "txp":      "(txp) Income Taxes Payable",
    "cogs":     "(cogs) Cost of Goods Sold",
    "dp":       "(dp) Depreciation and Amortization",
    "ebit":     "(ebit) Earnings Before Interest and Taxes",
    "gp":       "(gp) Gross Profit (Loss)",
    "ni":       "(ni) Net Income (Loss)",
    "oiadp":    "(oiadp) Operating Income After Depreciation",
    "sale":     "(sale) Sales/Turnover (Net)",
    "txt":      "(txt) Income Taxes - Total",
    "xsga":     "(xsga) Selling, General and Administrative Expense",
    "capx":     "(capx) Capital Expenditures",
    "fincf":    "(fincf) Financing Activities - Net Cash Flow",
    "oancf":    "(oancf) Operating Activities - Net Cash Flow",
    "csho":     "(csho) Common Shares Outstanding",
    "mkvalt":   "(mkvalt) Market Value - Total - Fiscal",
    "prcc_f":   "(prcc_f) Price Close - Annual - Fiscal",
}

SELECT_COLS = ", ".join(f"a.{c}" for c in COLUMN_RENAME)

# ------------------------------------------------------------------------------
# CONNECT
# ------------------------------------------------------------------------------

print("Connecting to WRDS...")
try:
    db = wrds.Connection()
except Exception as e:
    sys.exit(f"Could not connect to WRDS: {e}")
print("Connected.\n")

# ------------------------------------------------------------------------------
# QUERY
# ------------------------------------------------------------------------------

exchange_sql = ", ".join(str(e) for e in MAJOR_EXCHANGES)

print(f"Querying Compustat North America — active US companies on major exchanges...")
print(f"  Exchanges (exchg codes): {exchange_sql}")
print(f"  Period: {START_DATE} to {END_DATE}\n")

query = f"""
    SELECT {SELECT_COLS}
    FROM   comp.funda AS a
    WHERE  a.datafmt  = '{DATAFMT}'
      AND  a.indfmt   = '{INDFMT}'
      AND  a.consol   = '{CONSOL}'
      AND  a.costat   = 'A'
      AND  a.fic      = 'USA'
      AND  a.exchg    IN ({exchange_sql})
      AND  a.datadate BETWEEN '{START_DATE}' AND '{END_DATE}'
    ORDER BY a.gvkey, a.datadate
"""

df = db.raw_sql(query, date_cols=["datadate"])
print(f"  -> {len(df):,} rows, {df['gvkey'].nunique():,} unique companies\n")

if df.empty:
    db.close()
    sys.exit("No data returned. Check WRDS permissions or exchange codes.")

# ------------------------------------------------------------------------------
# CLEAN
# ------------------------------------------------------------------------------

print("Cleaning data...")

df.columns = [c.lower() for c in df.columns]

before = len(df)
df = df.drop_duplicates(subset=["gvkey", "datadate"])
dropped = before - len(df)
if dropped:
    print(f"  Dropped {dropped:,} duplicate rows")

df = df.sort_values(["gvkey", "datadate"]).reset_index(drop=True)

# ------------------------------------------------------------------------------
# FILTER 1: Keep only companies that are CURRENTLY actively listed
# comp.company.costat is the authoritative current status — 'A' means the
# company is still active today. This is more reliable than funda.costat
# which can lag behind corporate events.
# ------------------------------------------------------------------------------

print("Checking current active listing status via comp.company...")
active_query = """
    SELECT gvkey
    FROM   comp.company
    WHERE  costat = 'A'
"""
active_gvkeys = db.raw_sql(active_query)["gvkey"]
before = len(df)
df = df[df["gvkey"].isin(active_gvkeys)]
print(f"  Removed {before - len(df):,} rows for companies no longer actively listed")
print(f"  Remaining: {df['gvkey'].nunique():,} companies\n")

# ------------------------------------------------------------------------------
# FILTER 2: Keep only companies with >= 8 years of financial data
# ------------------------------------------------------------------------------

MIN_YEARS = 8

print(f"Filtering to companies with >= {MIN_YEARS} annual observations...")
year_counts = df.groupby("gvkey")["datadate"].count()
qualifying_gvkeys = year_counts[year_counts >= MIN_YEARS].index
before_rows = len(df)
before_cos = df["gvkey"].nunique()
df = df[df["gvkey"].isin(qualifying_gvkeys)]
print(f"  Removed {before_cos - df['gvkey'].nunique():,} companies with fewer than {MIN_YEARS} years of data")
print(f"  Removed {before_rows - len(df):,} rows")
print(f"  Remaining: {df['gvkey'].nunique():,} companies\n")

# ------------------------------------------------------------------------------
# FINAL SORT & DATE FORMAT
# ------------------------------------------------------------------------------

df = df.sort_values(["gvkey", "datadate"]).reset_index(drop=True)

# Format date to match target CSV format (DD/MM/YY)
df["datadate"] = pd.to_datetime(df["datadate"]).dt.strftime("%d/%m/%y")

print(f"  Final dataset: {len(df):,} rows x {len(df.columns)} columns")
print(f"  Companies: {df['gvkey'].nunique():,}")
print(f"  Countries: {', '.join(sorted(df['fic'].dropna().unique()))}\n")

# ------------------------------------------------------------------------------
# RENAME COLUMNS to exact target names
# ------------------------------------------------------------------------------

df = df.rename(columns=COLUMN_RENAME)
df = df[list(COLUMN_RENAME.values())]  # enforce exact column order

# ------------------------------------------------------------------------------
# SAVE
# ------------------------------------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved to: {OUTPUT_FILE}")

db.close()
print("Done.")