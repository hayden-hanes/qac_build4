# Beneish M-Score — Fraud Screen

## What It Measures
The Beneish M-Score is a statistical model that identifies the probability a company is manipulating its earnings. It was developed by Professor Messod Beneish in 1999. A higher score means a higher probability of earnings manipulation.

## Formula
```
PROBM = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI - 0.327*LVGI + 4.679*TATA

PMAN = CDF(PROBM)   [cumulative normal distribution — output is a probability 0 to 1]
```

## Components (all use year-over-year changes: t vs t-1)

| Variable | Formula | What It Captures |
|----------|---------|-----------------|
| DSRI | (Receivables/Sales)t / (Receivables/Sales)t-1 | Unusual growth in receivables relative to sales |
| GMI | Gross Margin t-1 / Gross Margin t | Deteriorating gross margins |
| AQI | (1 - (CurrentAssets + PPE) / Assets)t / same t-1 | Growth in intangible/non-productive assets |
| SGI | Sales t / Sales t-1 | High sales growth (growth firms more likely to manipulate) |
| DEPI | Depreciation rate t-1 / Depreciation rate t | Slowing depreciation (may signal asset overstatement) |
| SGAI | (SGA/Sales)t / (SGA/Sales)t-1 | Rising overhead relative to sales |
| LVGI | (Total Debt/Assets)t / (Total Debt/Assets)t-1 | Increasing leverage |
| TATA | (Net Income - Operating Cash Flow) / Assets | Total accruals — gap between earnings and cash |

## Inputs from Compustat
- `rect` — Receivables
- `sale` — Sales
- `cogs` — Cost of Goods Sold
- `act` — Current Assets
- `ppegt` — Property, Plant and Equipment (Gross)
- `at` — Total Assets
- `dp` — Depreciation and Amortization
- `xsga` — Selling, General and Administrative Expense
- `dltt` + `dlc` — Total Debt
- `ni` — Net Income
- `oancf` — Operating Cash Flow

## Interpretation of PMAN
- **PMAN < 0.5**: Low probability of manipulation — safer
- **PMAN > 0.5**: Elevated probability of manipulation — caution
- **PMAN > 0.76**: Strong signal of likely manipulation (equivalent to PROBM > -1.78, Beneish's original threshold)

## Important Caveats
- The model requires at least 2 years of data per company (needs t and t-1)
- High SGI alone can trigger a high score for legitimate high-growth companies
- Should be used as a screening tool, not a definitive fraud conclusion
- Lower PMAN is better quality in this scoring system
