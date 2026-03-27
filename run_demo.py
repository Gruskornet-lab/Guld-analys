"""
run_demo.py
-----------
Runs the full analysis pipeline using local CSV data.
Used when yfinance is unavailable (offline / restricted network).

In production, replace load_from_csv() with fetch_gold_data() from
data_fetcher.py to use live data.

This file demonstrates that the full indicator computation + Claude AI
analysis pipeline works end-to-end.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from src.indicators import compute_indicators
from src.ai_analyst import run_analysis, save_report


def load_from_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.strip() for c in df.columns]
    return df


def main():
    print("=" * 60)
    print("  Gold Technical Analysis — AI-Powered Report Generator")
    print("  (Demo mode — using local CSV data)")
    print("=" * 60)
    print()

    csv_path = "data/gold_weekly_demo.csv"

    print("[Step 1/3] Loading gold data from CSV...")
    df = load_from_csv(csv_path)
    print(f"           OK — {len(df)} weekly candles loaded\n")

    print("[Step 2/3] Computing technical indicators...")
    indicators = compute_indicators(df)
    print(f"           OK — Bias: {indicators.overall_bias.upper()} "
          f"(Bull: {indicators.bull_signals} / Bear: {indicators.bear_signals})\n")

    print("  Indicator snapshot:")
    print(f"    Price:       {indicators.current_price:.2f} USD  ({indicators.weekly_change_pct:+.2f}%)")
    print(f"    EMA-20/50/200: {indicators.ema_20:.0f} / {indicators.ema_50:.0f} / {indicators.ema_200:.0f}")
    print(f"    EMA trend:   {indicators.ema_trend}")
    print(f"    RSI-14:      {indicators.rsi_14:.1f}  ({indicators.rsi_signal})")
    print(f"    MACD cross:  {indicators.macd_cross}  |  Histogram: {indicators.macd_histogram:.2f}")
    print(f"    BB position: {indicators.bb_position}  |  Width: {indicators.bb_width_pct:.1f}%")
    print(f"    ATR:         {indicators.atr_14:.2f}  ({indicators.atr_pct:.2f}% of price)")
    print(f"    52w High/Low: {indicators.high_52w:.0f} / {indicators.low_52w:.0f}")
    print(f"    Fibonacci:   61.8%={indicators.fib_618:.0f}  38.2%={indicators.fib_382:.0f}  23.6%={indicators.fib_236:.0f}")
    print()

    print("[Step 3/3] Generating AI analysis report via Claude API...")
    report = run_analysis(indicators, interval_label="weekly")
    print()

    print("=" * 60)
    print(report)
    print("=" * 60)

    save_report(report, output_dir="reports")


if __name__ == "__main__":
    main()
