# Financial Strength (FS) — Piotroski F-Score

## What It Measures
The Financial Strength score is based on the Piotroski F-Score, a 10-point scoring system that assesses a company's financial health across three dimensions: profitability, leverage/liquidity, and operating efficiency. Each condition scores 1 if met, 0 if not.

## Formula
```
P_FS = sum of all binary FS scores (0 to 10)
```
Higher is better. A score of 8–10 indicates strong financial health.

## The 10 Binary Signals

### Profitability (3 signals)
| Signal | Condition | Meaning |
|--------|-----------|---------|
| FS_ROA | ROA > 0 | Company is profitable |
| FS_FCFTA | FCFTA > 0 | Positive operating cash flow |
| FS_ACCRUAL | (FCFTA - ROA) < 0 | Cash earnings exceed accrual earnings |

### Leverage, Liquidity & Funding (3 signals)
| Signal | Condition | Meaning |
|--------|-----------|---------|
| FS_LEVER | Change in leverage < 0 | Debt burden decreased |
| FS_LIQUID | Change in current ratio > 0 | Liquidity improved |
| FS_NEQISS | Change in shares < 0 | No equity dilution |

### Operating Efficiency (4 signals)
| Signal | Condition | Meaning |
|--------|-----------|---------|
| FS_AROA | ROA improved YoY | Profitability trending up |
| FS_AFCFTA | FCF/Assets improved YoY | Cash generation trending up |
| FS_ATURN | Asset turnover improved YoY | Using assets more efficiently |
| FS_AMARGIN | Gross margin improved YoY | Pricing power or cost control improving |

## Key Intermediate Variables
```
ROA     = Net Income / Total Assets
FCFTA   = Operating Cash Flow / Total Assets
LEVER   = change in (Total Debt / Total Assets)
LIQUID  = change in (Current Assets / Current Liabilities)
NEQISS  = change in Common Shares Outstanding
ATURN   = Sales / Total Assets (change YoY)
AMARGIN = (Sales - COGS) / Sales (change YoY)
```

## Inputs from Compustat
- `ni` — Net Income
- `at` — Total Assets
- `oancf` — Operating Cash Flow
- `dltt` + `dlc` — Total Debt
- `act` — Current Assets
- `lct` — Current Liabilities
- `csho` — Common Shares Outstanding
- `sale` — Sales
- `cogs` — Cost of Goods Sold

## Interpretation
- **0–2**: Very weak financial health
- **3–5**: Average
- **6–7**: Good
- **8–10**: Strong — historically associated with outperformance

## Important Caveats
- Requires at least 2 years of data (needs year-over-year changes)
- P_FS is normalized to 0–1 before being combined into the final QUALITY score
- Works best for non-financial companies; banks and insurers have different balance sheet structures
