"""
data_fetcher.py
---------------
Fetches historical OHLCV data for Gold (XAU/USD) via yfinance.

Why yfinance?
  - No API key required
  - Free and widely used in finance projects
  - Returns pandas DataFrames directly, compatible with pandas-ta

Design decision: We use the ticker "GC=F" (Gold Futures) as a proxy for
spot gold (XAU/USD). It is the most liquid and commonly referenced instrument
for macro/positional gold analysis.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOLD_TICKER = "GC=F"          # Gold Futures (CME)
GOLD_SPOT_FALLBACK = "GLD"    # SPDR Gold ETF — used if futures unavailable


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_gold_data(period_years: int = 3, interval: str = "1wk") -> pd.DataFrame:
    """
    Download historical gold price data.

    Parameters
    ----------
    period_years : int
        How many years of history to fetch. Default 3 years gives enough
        history for macro indicators like EMA-200 to be meaningful.
    interval : str
        yfinance interval string.
        - "1wk"  → Weekly candles  (recommended for macro/positional)
        - "1d"   → Daily candles
        - "1mo"  → Monthly candles

    Returns
    -------
    pd.DataFrame
        OHLCV DataFrame with columns: Open, High, Low, Close, Volume
        Index is DatetimeIndex.

    Raises
    ------
    RuntimeError
        If data could not be fetched from any source.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=period_years * 365)

    print(f"[DataFetcher] Fetching {GOLD_TICKER} | {interval} | {start_date.date()} → {end_date.date()}")

    df = yf.download(
        tickers=GOLD_TICKER,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval=interval,
        auto_adjust=True,   # Adjusts for splits/dividends automatically
        progress=False,
    )

    if df is None or df.empty:
        print(f"[DataFetcher] WARNING: {GOLD_TICKER} returned no data. Trying fallback {GOLD_SPOT_FALLBACK}...")
        df = yf.download(
            tickers=GOLD_SPOT_FALLBACK,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

    if df is None or df.empty:
        raise RuntimeError("Could not fetch gold data from yfinance. Check internet connection.")

    # Flatten multi-level columns if present (yfinance sometimes returns them)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Keep only standard OHLCV columns
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(subset=["Close"], inplace=True)

    print(f"[DataFetcher] Fetched {len(df)} candles. Latest close: {df['Close'].iloc[-1]:.2f} USD")
    return df


def get_current_price() -> float:
    """
    Fetch the most recent available closing price for gold.

    Returns
    -------
    float
        Latest close price in USD.
    """
    ticker = yf.Ticker(GOLD_TICKER)
    hist = ticker.history(period="5d")
    if hist.empty:
        raise RuntimeError("Could not fetch current price.")
    return float(hist["Close"].iloc[-1])
