# Franchise Power (FP) — Long-Run Quality Screen

## What It Measures
Franchise Power measures a company's ability to sustain high returns over a long period. It uses 8-year geometric averages of return metrics to identify companies with durable competitive advantages — i.e. genuine "franchise" businesses rather than one-off earners.

## Formula
```
8yr ROA  = 8-year geometric mean of (Net Income / Total Assets)
8yr ROC  = 8-year geometric mean of (Net Income / Invested Capital)
8yr FCF  = 8-year geometric mean of (Operating Cash Flow / Total Assets)

P_8yr_ROA = percentile rank of 8yr ROA
P_8yr_ROC = percentile rank of 8yr ROC
P_CFOA    = percentile rank of 8yr FCF/Assets
MM        = 1 if Sales > median Sales (market share proxy), else 0

FP_avg = average(P_8yr_ROA, P_8yr_ROC, P_CFOA, MM)
P_FP   = percentile rank of FP_avg
```

## Invested Capital Definition
```
Invested Capital = Stockholders Equity + Long-Term Debt + Current Debt - Cash
```
This captures the full capital base of the business (both equity and debt funded), which is more complete than equity alone.

## Why Geometric Mean?
The geometric mean accounts for compounding and is more appropriate for multi-year return calculations than the arithmetic mean. It penalizes volatility — a company with steady 10% returns ranks higher than one with alternating 0% and 20% returns.

## Inputs from Compustat
- `ni` — Net Income
- `at` — Total Assets
- `oancf` — Operating Cash Flow
- `seq` — Stockholders Equity
- `dltt` — Long-Term Debt
- `dlc` — Current Debt
- `che` — Cash
- `sale` — Sales (for market share proxy MM)

## Interpretation of P_FP
P_FP is a percentile score from 0 to 1:
- **P_FP > 0.8**: Top quintile — strong durable franchise
- **P_FP 0.6–0.8**: Above average quality
- **P_FP 0.4–0.6**: Average
- **P_FP < 0.4**: Weak long-run returns

## Important Caveats
- Requires at least 8 years of data per company — companies with fewer years are excluded
- The geometric mean calculation shifts negative values to handle loss-making years, but companies with consistently negative ROA will still score poorly
- P_FP contributes 50% of the final QUALITY score (combined with P_FS)
- MM (market share proxy) is a simple above/below median revenue flag — it is a rough approximation of market position
