# EV/EBIT — Cheapness Screen

## What It Measures
EV/EBIT (Enterprise Value divided by Earnings Before Interest and Taxes) measures how cheap a stock is relative to its operating earnings. A lower ratio means the company is cheaper — you are paying less for each dollar of operating profit.

## Formula
```
EV = Market Cap + Long-Term Debt + Current Debt - Cash and Short-Term Investments
PRICE = EBIT / EV   (i.e. EV/EBIT inverted for ranking: lower = cheaper)
```

In this system, companies are ranked from lowest to highest EV/EBIT. The lowest-ranked companies are considered the cheapest.

## Inputs from Compustat
- `mkvalt` — Market Value (Market Cap)
- `dltt` — Long-Term Debt
- `dlc` — Debt in Current Liabilities
- `che` — Cash and Short-Term Investments
- `ebit` — Earnings Before Interest and Taxes

## Filters Applied
- EV/EBIT must be >= 1.0 (excludes distorted or negative ratios)
- EBIT must be positive (company must be operationally profitable)
- EV must be positive
- Market Cap must be >= $1,000M (large/mid-cap only)

## Interpretation
- **1x–5x**: Extremely cheap; may indicate distress, value trap, or genuine opportunity
- **5x–15x**: Cheap to fairly valued
- **15x–25x**: Average range for large-cap stocks
- **25x+**: Expensive; market expects high future growth

## Important Caveats
- EV/EBIT is not meaningful for financial companies (banks, insurance) because their balance sheets are structured differently — debt is a input to their business model, not just financing
- A very low EV/EBIT can signal financial distress rather than cheapness — always cross-reference with the Financial Distress (PFD) score
- This is one component of the overall QUALITY score; cheapness alone is not sufficient for investment decisions
