"""
performance_tracker.py
----------------------
Beräknar prisstatistik för guld över olika tidsperioder.
Används av både vecko- och månadsrapporten.

Statistik som beräknas:
  - YTD (year-to-date):        1 jan → idag
  - Senaste 3 månader:         90 dagar tillbaka
  - Aktuell månad:             1:a i månaden → idag
  - Senaste veckan:            föregående måndag → fredag

Alla värden returneras som procentförändring och absolut USD-förändring.
"""

import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class GoldPerformance:
    """Håller beräknad prisstatistik för alla tidsperioder."""

    # YTD
    ytd_start_price:   float = 0.0
    ytd_end_price:     float = 0.0
    ytd_pct:           float = 0.0
    ytd_usd:           float = 0.0
    ytd_label:         str   = ""

    # 3 månader
    q3m_start_price:   float = 0.0
    q3m_end_price:     float = 0.0
    q3m_pct:           float = 0.0
    q3m_usd:           float = 0.0
    q3m_label:         str   = ""

    # Aktuell månad
    month_start_price: float = 0.0
    month_end_price:   float = 0.0
    month_pct:         float = 0.0
    month_usd:         float = 0.0
    month_label:       str   = ""

    # Senaste veckan
    week_start_price:  float = 0.0
    week_end_price:    float = 0.0
    week_pct:          float = 0.0
    week_usd:          float = 0.0
    week_label:        str   = ""


def _find_closest_price(df: pd.DataFrame, target_date: datetime) -> float:
    """
    Hittar stängningspriset närmast ett givet datum.
    Går bakåt i tid om exakt datum saknas (t.ex. helger).
    """
    target = pd.Timestamp(target_date.date())
    available = df.index[df.index <= target]
    if available.empty:
        return float(df['Close'].iloc[0])
    return float(df.loc[available[-1], 'Close'])


def compute_performance(df: pd.DataFrame) -> GoldPerformance:
    """
    Beräknar prisstatistik för alla tidsperioder från OHLCV-data.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV-data med DatetimeIndex. Behöver minst 1 år av daglig eller
        veckodata för att YTD ska vara meningsfullt.

    Returns
    -------
    GoldPerformance
        Dataclass med alla beräknade värden.
    """
    perf        = GoldPerformance()
    today       = datetime.today()
    current_price = float(df['Close'].iloc[-1])

    # -----------------------------------------------------------------------
    # YTD — 1 januari i år → idag
    # -----------------------------------------------------------------------
    ytd_start_date  = datetime(today.year, 1, 1)
    ytd_start_price = _find_closest_price(df, ytd_start_date)

    perf.ytd_start_price = ytd_start_price
    perf.ytd_end_price   = current_price
    perf.ytd_pct         = ((current_price - ytd_start_price) / ytd_start_price) * 100
    perf.ytd_usd         = current_price - ytd_start_price
    perf.ytd_label       = f"YTD ({today.year})"

    # -----------------------------------------------------------------------
    # Senaste 3 månader
    # -----------------------------------------------------------------------
    q3m_start_date  = today - timedelta(days=90)
    q3m_start_price = _find_closest_price(df, q3m_start_date)

    perf.q3m_start_price = q3m_start_price
    perf.q3m_end_price   = current_price
    perf.q3m_pct         = ((current_price - q3m_start_price) / q3m_start_price) * 100
    perf.q3m_usd         = current_price - q3m_start_price
    perf.q3m_label       = f"3 månader ({q3m_start_date.strftime('%b %Y')} → nu)"

    # -----------------------------------------------------------------------
    # Aktuell månad — 1:a → idag
    # -----------------------------------------------------------------------
    month_start_date  = datetime(today.year, today.month, 1)
    month_start_price = _find_closest_price(df, month_start_date)

    perf.month_start_price = month_start_price
    perf.month_end_price   = current_price
    perf.month_pct         = ((current_price - month_start_price) / month_start_price) * 100
    perf.month_usd         = current_price - month_start_price
    perf.month_label       = today.strftime("%B %Y")

    # -----------------------------------------------------------------------
    # Senaste veckan — föregående måndag → fredag (eller senaste stängning)
    # -----------------------------------------------------------------------
    days_since_monday = today.weekday()          # måndag=0
    last_monday = today - timedelta(days=days_since_monday)
    last_friday = last_monday + timedelta(days=4)
    if last_friday > today:
        last_friday = today

    week_start_price = _find_closest_price(df, last_monday)
    week_end_price   = _find_closest_price(df, last_friday)

    perf.week_start_price = week_start_price
    perf.week_end_price   = week_end_price
    perf.week_pct         = ((week_end_price - week_start_price) / week_start_price) * 100
    perf.week_usd         = week_end_price - week_start_price
    perf.week_label       = (
        f"Vecka {last_monday.isocalendar().week} "
        f"({last_monday.strftime('%d %b')} – {last_friday.strftime('%d %b')})"
    )

    return perf


def format_stats_block(perf: GoldPerformance) -> str:
    """
    Formaterar statistiken som ett snyggt textblock för rapporten.

    Exempel på output:
      📊 PRISSTATISTIK
      ─────────────────────────────────────────
      YTD (2026):               +8.42%  (+228 USD)
      3 månader (jan 2026 → nu):+4.11%  (+107 USD)
      Mars 2026:                +1.23%  (+33 USD)
      Vecka 13 (30 mar – 4 apr):+0.21%  (+6 USD)
    """
    def fmt(pct: float, usd: float) -> str:
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.2f}%  ({sign}{usd:.0f} USD)"

    lines = [
        "📊 PRISSTATISTIK",
        "─" * 45,
        f"{'YTD:':<30} {fmt(perf.ytd_pct, perf.ytd_usd)}",
        f"{'Senaste 3 månader:':<30} {fmt(perf.q3m_pct, perf.q3m_usd)}",
        f"{perf.month_label + ':':<30} {fmt(perf.month_pct, perf.month_usd)}",
        f"{perf.week_label + ':':<30} {fmt(perf.week_pct, perf.week_usd)}",
    ]
    return "\n".join(lines)
