# Financial Distress (PFD) — Campbell et al. Model

## What It Measures
PFD is the probability that a company will experience financial distress or bankruptcy. It is based on the model from Campbell, Hilscher, and Szilagyi (2008), which uses market and accounting variables to predict failure. A lower PFD means the company is financially healthier.

## Formula
```
LPFD = -20.26*NIMTAAVG + 1.42*TLMTA - 7.13*CASHMTA
       + 1.41*EXRETAVG - 0.042*SIGMA - 1.42*RSIZE
       - 0.045*MB - 0.058*PRICE - 9.16

PFD = 1 / (1 + exp(-LPFD))    [logistic transformation, output 0 to 1]
```

## Components

| Variable | Formula | What It Captures |
|----------|---------|-----------------|
| NIMTAAVG | 3-year avg of NI / (MarketCap + Total Liabilities) | Sustained profitability relative to total firm value |
| TLMTA | Total Liabilities / (MarketCap + Total Liabilities) | Leverage burden |
| CASHMTA | Cash / (MarketCap + Total Liabilities) | Liquidity cushion |
| EXRETAVG | 3-year avg of log annual price return | Recent stock performance (market signal) |
| SIGMA | Std dev of NIMTA over trailing 3 years | Earnings volatility |
| RSIZE | log(Market Cap) | Firm size — larger firms less likely to fail |
| MB | Market Cap / Stockholders Equity | Market-to-book ratio |
| PRICE | log(min(Stock Price, $15)) | Low price stocks more likely to be distressed |

## 3-Year Trailing Averages
NIMTAAVG and EXRETAVG use 3-year rolling averages from annual data. The original Campbell et al. model used quarterly data with 12-quarter averages — this implementation approximates that with annual data.

## Inputs from Compustat
- `ni` — Net Income
- `mkvalt` — Market Cap
- `at` — Total Assets
- `seq` — Stockholders Equity (used to derive total liabilities: AT - SEQ)
- `che` — Cash
- `prcc_f` — Annual Fiscal Year Close Price
- `csho` — Common Shares Outstanding

## Interpretation of PFD
- **PFD < 0.05**: Low distress risk
- **PFD 0.05–0.20**: Moderate risk — worth monitoring
- **PFD > 0.20**: Elevated distress risk
- **PFD > 0.50**: High probability of financial distress

## Important Caveats
- EXRET (excess return) in this implementation is approximated as log price change YoY — for true excess returns you would subtract a market benchmark return
- RSIZE uses log(MarketCap) as an approximation since total market cap is not in the dataset
- Lower PFD is better — companies with high PFD should be viewed with caution even if they score well on cheapness or financial strength
- PFD is a screening tool, not a definitive bankruptcy predictor
