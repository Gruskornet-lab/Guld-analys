# Gold Technical Analysis — AI-Powered Report Generator

## Project Overview

An automated technical analysis system for Gold (XAU/USD) that:

1. **Fetches** 3 years of historical weekly price data (no API key required)
2. **Computes** institutional-grade technical indicators across trend, momentum, and volatility
3. **Generates** a professional analysis report using Claude AI (Anthropic API)
4. **Saves** each report with a timestamp for record-keeping

This project demonstrates the use of AI to automate a real-world financial analysis workflow. It is part of a broader AI automation project portfolio.

---

## Architecture

```
gold-analysis/
├── main.py                 # Entry point — orchestrates all steps
├── src/
│   ├── data_fetcher.py     # yfinance data download (Gold Futures GC=F)
│   ├── indicators.py       # Technical indicator computation (pandas-ta)
│   └── ai_analyst.py       # Claude API prompt engineering + report generation
├── reports/                # Auto-generated analysis reports (timestamped .txt)
└── README.md               # This file
```

---

## Technical Indicators Used

| Category    | Indicator              | Why                                                |
|-------------|------------------------|----------------------------------------------------|
| Trend       | EMA 20 / 50 / 200      | Institutional trend benchmarks                     |
| Trend       | EMA cross detection    | Identifies regime changes                          |
| Momentum    | RSI-14                 | Overbought/oversold + divergence analysis           |
| Momentum    | MACD (12/26/9)         | Trend momentum shifts and crossovers               |
| Volatility  | Bollinger Bands (20,2) | Squeeze/expansion cycles, mean reversion zones     |
| Volatility  | ATR-14                 | Normalised volatility for risk sizing              |
| Structure   | 52-week high/low       | Macro support/resistance                           |
| Structure   | Fibonacci 23.6/38.2/61.8% | Retracement levels for entry/exit zones        |

---

## Setup

### Prerequisites

- Python 3.10+
- An Anthropic API key (free tier available at [console.anthropic.com](https://console.anthropic.com))

### Install dependencies

```bash
pip install yfinance pandas pandas-ta anthropic
```

### Set your API key

```bash
# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### Run

```bash
python main.py
```

---

## Example Output

```
============================================================
  Gold Technical Analysis — AI-Powered Report Generator
============================================================

[Step 1/3] Fetching historical gold data...
           OK — 156 weekly candles loaded

[Step 2/3] Computing technical indicators...
           OK — Bias: BULLISH (Bull: 5 / Bear: 3)

  Indicator snapshot:
    Price:       3042.50 USD  (+1.23%)
    EMA trend:   bull
    RSI-14:      61.4  (neutral)
    MACD cross:  none
    BB position: upper_half
    ATR:         47.82  (1.57% of price)

[Step 3/3] Generating AI analysis report via Claude API...

# Gold (XAU/USD) — Technical Analysis Report
...
============================================================
```

---

## Design Decisions

**Why yfinance?**
No API key required, free, and widely used in open-source finance projects. Uses Gold Futures (GC=F) as the most liquid and commonly referenced instrument.

**Why weekly timeframe for macro analysis?**
Weekly candles filter out intraday noise and are the standard timeframe for institutional macro/positional strategies. EMA-200 on weekly = ~4 years of trend context.

**Why Claude for the analysis layer?**
Rather than hardcoding interpretation rules, Claude can reason about the combination of signals contextually — the same way a human analyst would. It also makes the report readable, not just a list of numbers.

**Why structured prompt engineering?**
By separating data computation (Python/pandas-ta) from interpretation (Claude), the system is modular. The indicator logic can be upgraded independently of the AI layer.

---

## Limitations

- **Not real-time**: Data from yfinance has a 15-minute to 24-hour delay depending on the source.
- **Not investment advice**: Technical analysis identifies patterns in historical data. It does not predict the future.
- **Weekly signals are slow**: This system is designed for positional/macro analysis (days to weeks), not intraday trading.

---

## Possible Extensions

- [ ] Add fundamental macro context (DXY, US10Y yields, CPI) from FRED API
- [ ] Build a Flask/FastAPI web interface
- [ ] Add email delivery of weekly reports
- [ ] Extend to other assets (Silver, Bitcoin, S&P 500)
- [ ] Add backtesting module to evaluate signal accuracy

---

## Author Note

This project was built as part of an AI automation learning portfolio. It demonstrates:
- Python modular architecture
- External API integration (yfinance + Anthropic)
- Financial data processing with pandas
- Prompt engineering for structured analytical output
