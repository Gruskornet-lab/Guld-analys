"""
indicators.py
-------------
Computes technical indicators relevant for macro/positional gold analysis.

Why these indicators?
---------------------
Gold (XAU/USD) as a macro asset responds to:
  - Long-term trend: EMA 20/50/200 (institutional benchmark levels)
  - Momentum: RSI-14 (overbought/oversold), MACD (trend momentum shifts)
  - Volatility: Bollinger Bands (squeeze/expansion cycles), ATR (risk sizing)
  - Structural levels: 52-week high/low, Fibonacci retracements

All calculations use pandas-ta, which is widely used in quantitative finance
and produces reproducible results consistent with TradingView/Bloomberg.
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data container for computed indicators
# ---------------------------------------------------------------------------

@dataclass
class GoldIndicators:
    """
    Holds all computed indicator values for the most recent candle,
    plus enough historical context for trend determination.
    """
    # --- Price snapshot ---
    current_price: float = 0.0
    prev_close: float = 0.0
    weekly_change_pct: float = 0.0

    # --- Trend ---
    ema_20: float = 0.0
    ema_50: float = 0.0
    ema_200: float = 0.0
    price_vs_ema200_pct: float = 0.0     # How far price is above/below EMA-200 (%)
    ema_20_50_cross: str = "none"        # "bullish", "bearish", or "none"
    ema_trend: str = "neutral"           # "strong_bull", "bull", "neutral", "bear", "strong_bear"

    # --- Momentum ---
    rsi_14: float = 0.0
    rsi_signal: str = "neutral"          # "overbought", "neutral", "oversold"
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_cross: str = "none"             # "bullish", "bearish", or "none"

    # --- Volatility ---
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width_pct: float = 0.0            # Band width as % of middle (squeeze indicator)
    bb_position: str = "middle"          # "above_upper", "upper_half", "middle", "lower_half", "below_lower"
    atr_14: float = 0.0
    atr_pct: float = 0.0                 # ATR as % of price (normalised volatility)

    # --- Structural levels ---
    high_52w: float = 0.0
    low_52w: float = 0.0
    fib_618: float = 0.0                 # 61.8% Fibonacci retracement
    fib_382: float = 0.0                 # 38.2% Fibonacci retracement
    fib_236: float = 0.0                 # 23.6% Fibonacci retracement

    # --- Summary signal ---
    bull_signals: int = 0
    bear_signals: int = 0
    overall_bias: str = "neutral"        # "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"

    # --- Raw series for Claude context ---
    close_series_20w: list = field(default_factory=list)   # Last 20 weekly closes


# ---------------------------------------------------------------------------
# Main computation function
# ---------------------------------------------------------------------------

def compute_indicators(df: pd.DataFrame) -> GoldIndicators:
    """
    Compute all technical indicators from OHLCV data.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV DataFrame from data_fetcher. Minimum 200 rows recommended
        for EMA-200 to be reliable.

    Returns
    -------
    GoldIndicators
        Dataclass with all indicator values for the most recent candle.
    """
    if len(df) < 30:
        raise ValueError(f"Need at least 30 candles, got {len(df)}")

    ind = GoldIndicators()

    # -----------------------------------------------------------------------
    # Price snapshot
    # -----------------------------------------------------------------------
    ind.current_price = float(df["Close"].iloc[-1])
    ind.prev_close    = float(df["Close"].iloc[-2])
    ind.weekly_change_pct = ((ind.current_price - ind.prev_close) / ind.prev_close) * 100

    # -----------------------------------------------------------------------
    # Trend — Exponential Moving Averages
    # -----------------------------------------------------------------------
    df["EMA_20"]  = ta.ema(df["Close"], length=20)
    df["EMA_50"]  = ta.ema(df["Close"], length=50)
    df["EMA_200"] = ta.ema(df["Close"], length=200)

    def safe_float(series, fallback=0.0):
        val = series.iloc[-1]
        return float(val) if val is not None and str(val) != "nan" else fallback

    ind.ema_20  = safe_float(df["EMA_20"],  ind.current_price)
    ind.ema_50  = safe_float(df["EMA_50"],  ind.current_price)
    ind.ema_200 = safe_float(df["EMA_200"], ind.current_price)

    ind.price_vs_ema200_pct = ((ind.current_price - ind.ema_200) / ind.ema_200) * 100

    # EMA cross detection (compare last two candles)
    ema20_prev = float(df["EMA_20"].iloc[-2])
    ema50_prev = float(df["EMA_50"].iloc[-2])
    if ema20_prev <= ema50_prev and ind.ema_20 > ind.ema_50:
        ind.ema_20_50_cross = "bullish"
    elif ema20_prev >= ema50_prev and ind.ema_20 < ind.ema_50:
        ind.ema_20_50_cross = "bearish"

    # EMA alignment — determines overall trend regime
    if ind.current_price > ind.ema_20 > ind.ema_50 > ind.ema_200:
        ind.ema_trend = "strong_bull"
    elif ind.current_price > ind.ema_50 and ind.ema_20 > ind.ema_200:
        ind.ema_trend = "bull"
    elif ind.current_price < ind.ema_20 < ind.ema_50 < ind.ema_200:
        ind.ema_trend = "strong_bear"
    elif ind.current_price < ind.ema_50 and ind.ema_20 < ind.ema_200:
        ind.ema_trend = "bear"
    else:
        ind.ema_trend = "neutral"

    # -----------------------------------------------------------------------
    # Momentum — RSI
    # -----------------------------------------------------------------------
    rsi_series = ta.rsi(df["Close"], length=14)
    ind.rsi_14 = float(rsi_series.iloc[-1])

    if ind.rsi_14 >= 70:
        ind.rsi_signal = "overbought"
    elif ind.rsi_14 <= 30:
        ind.rsi_signal = "oversold"
    else:
        ind.rsi_signal = "neutral"

    # -----------------------------------------------------------------------
    # Momentum — MACD (12, 26, 9) — standard settings
    # -----------------------------------------------------------------------
    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        ind.macd_line      = float(macd_df["MACD_12_26_9"].iloc[-1])
        ind.macd_signal    = float(macd_df["MACDs_12_26_9"].iloc[-1])
        ind.macd_histogram = float(macd_df["MACDh_12_26_9"].iloc[-1])

        macd_prev = float(macd_df["MACD_12_26_9"].iloc[-2])
        sig_prev  = float(macd_df["MACDs_12_26_9"].iloc[-2])
        if macd_prev <= sig_prev and ind.macd_line > ind.macd_signal:
            ind.macd_cross = "bullish"
        elif macd_prev >= sig_prev and ind.macd_line < ind.macd_signal:
            ind.macd_cross = "bearish"

    # -----------------------------------------------------------------------
    # Volatility — Bollinger Bands (20, 2)
    # -----------------------------------------------------------------------
    bb_df = ta.bbands(df["Close"], length=20, std=2)
    if bb_df is not None and not bb_df.empty:
        bb_upper_col  = [c for c in bb_df.columns if c.startswith("BBU")][0]
        bb_middle_col = [c for c in bb_df.columns if c.startswith("BBM")][0]
        bb_lower_col  = [c for c in bb_df.columns if c.startswith("BBL")][0]
        ind.bb_upper  = float(bb_df[bb_upper_col].iloc[-1])
        ind.bb_middle = float(bb_df[bb_middle_col].iloc[-1])
        ind.bb_lower  = float(bb_df[bb_lower_col].iloc[-1])
        ind.bb_width_pct = ((ind.bb_upper - ind.bb_lower) / ind.bb_middle) * 100

        if ind.current_price > ind.bb_upper:
            ind.bb_position = "above_upper"
        elif ind.current_price > ind.bb_middle + (ind.bb_upper - ind.bb_middle) * 0.5:
            ind.bb_position = "upper_half"
        elif ind.current_price < ind.bb_lower:
            ind.bb_position = "below_lower"
        elif ind.current_price < ind.bb_middle - (ind.bb_middle - ind.bb_lower) * 0.5:
            ind.bb_position = "lower_half"
        else:
            ind.bb_position = "middle"

    # -----------------------------------------------------------------------
    # Volatility — ATR (Average True Range)
    # -----------------------------------------------------------------------
    atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    ind.atr_14  = float(atr_series.iloc[-1])
    ind.atr_pct = (ind.atr_14 / ind.current_price) * 100

    # -----------------------------------------------------------------------
    # Structural levels — 52-week high/low + Fibonacci
    # -----------------------------------------------------------------------
    # Use last 52 candles (weeks) for yearly levels
    lookback = min(52, len(df))
    recent = df["Close"].iloc[-lookback:]
    ind.high_52w = float(recent.max())
    ind.low_52w  = float(recent.min())

    price_range = ind.high_52w - ind.low_52w
    ind.fib_618 = ind.low_52w + price_range * 0.618
    ind.fib_382 = ind.low_52w + price_range * 0.382
    ind.fib_236 = ind.low_52w + price_range * 0.236

    # -----------------------------------------------------------------------
    # Historical close series for Claude context (last 20 weeks)
    # -----------------------------------------------------------------------
    ind.close_series_20w = [round(float(v), 2) for v in df["Close"].iloc[-20:].tolist()]

    # -----------------------------------------------------------------------
    # Signal scoring — simple bull/bear count
    # -----------------------------------------------------------------------
    bull, bear = 0, 0

    if ind.ema_trend in ("strong_bull", "bull"):       bull += 2 if ind.ema_trend == "strong_bull" else 1
    if ind.ema_trend in ("strong_bear", "bear"):       bear += 2 if ind.ema_trend == "strong_bear" else 1
    if ind.rsi_signal == "oversold":                   bull += 1
    if ind.rsi_signal == "overbought":                 bear += 1
    if ind.macd_line > ind.macd_signal:                bull += 1
    if ind.macd_line < ind.macd_signal:                bear += 1
    if ind.macd_cross == "bullish":                    bull += 1
    if ind.macd_cross == "bearish":                    bear += 1
    if ind.bb_position in ("above_upper",):            bear += 1   # Extended
    if ind.bb_position in ("below_lower",):            bull += 1   # Oversold extension
    if ind.price_vs_ema200_pct > 0:                    bull += 1
    if ind.price_vs_ema200_pct < 0:                    bear += 1

    ind.bull_signals = bull
    ind.bear_signals = bear

    net = bull - bear
    if   net >= 4:  ind.overall_bias = "strong_bullish"
    elif net >= 2:  ind.overall_bias = "bullish"
    elif net <= -4: ind.overall_bias = "strong_bearish"
    elif net <= -2: ind.overall_bias = "bearish"
    else:           ind.overall_bias = "neutral"

    return ind
