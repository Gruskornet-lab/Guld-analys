"""
backtest.py
-----------
Kör historisk simulering av EMA-200 + RSI-timing strategin på 3 års data.

Strategiregler (samma som strategy.py):
  KÖP:  Pris > EMA-200 OCH RSI < 50 OCH priset stiger (RSI vänder upp)
  SÄLJ: Pris < EMA-200 ELLER RSI > 75
  HÅLL: Annars

Jämför mot buy & hold för att ge ett ärligt resultat.

Viktigt förbehåll:
  Backtester visar hur strategin HAR presterat — inte hur den KOMMER prestera.
  Alla resultat är exklusive skatt, courtage och spread.
"""

import pandas as pd
from datetime import datetime
from src.indicators import compute_indicators

STARTING_CAPITAL = 10_000.0
POSITION_SIZE    = 0.95


def _evaluate_signal(ind) -> str:
    """Samma logik som strategy.py men utan import-cirkel."""
    price    = ind.current_price
    ema_200  = ind.ema_200
    rsi      = ind.rsi_14

    closes   = ind.close_series_20w
    price_recovering = (closes[-1] > closes[-2]) if len(closes) >= 2 else True

    ema_50 = ind.ema_50
    if rsi > 75:
        return "SELL"
    if price < ema_50:
        return "SELL"
    if price > ema_50 and rsi < 55 and price_recovering:
        return "BUY"
    return "HOLD"


def run_backtest(df: pd.DataFrame) -> dict:
    """
    Kör backtesten på historisk OHLCV-data.

    Parameters
    ----------
    df : pd.DataFrame
        Veckovis OHLCV-data.

    Returns
    -------
    dict
        Komplett backtest-resultat.
    """
    print("[Backtest] Kör EMA-200 + RSI-timing simulering...")

    cash          = STARTING_CAPITAL
    ounces        = 0.0
    avg_buy_price = 0.0
    trades        = []
    portfolio_values = []
    peak_value    = STARTING_CAPITAL
    max_drawdown  = 0.0
    winning = 0
    losing  = 0

    MIN_ROWS = 30

    for i in range(MIN_ROWS, len(df)):
        slice_df      = df.iloc[:i+1].copy()
        current_price = float(slice_df['Close'].iloc[-1])
        date          = slice_df.index[-1]

        try:
            ind    = compute_indicators(slice_df)
            signal = _evaluate_signal(ind)
        except Exception:
            signal = "HOLD"

        action = "HOLD"
        pnl    = 0.0

        if signal == "BUY" and ounces == 0 and cash > 0:
            invest        = cash * POSITION_SIZE
            ounces        = invest / current_price
            avg_buy_price = current_price
            cash         -= invest
            action        = "BUY"

        elif signal == "SELL" and ounces > 0:
            sell_value    = ounces * current_price
            pnl           = sell_value - (ounces * avg_buy_price)
            cash         += sell_value
            if pnl >= 0: winning += 1
            else:        losing  += 1
            ounces        = 0.0
            avg_buy_price = 0.0
            action        = "SELL"

        total_value = cash + (ounces * current_price)
        if total_value > peak_value:
            peak_value = total_value
        dd = ((peak_value - total_value) / peak_value) * 100
        if dd > max_drawdown:
            max_drawdown = dd

        portfolio_values.append({
            "date":  date.strftime("%Y-%m-%d"),
            "value": round(total_value, 2),
            "price": round(current_price, 2),
        })

        if action != "HOLD":
            trades.append({
                "date":   date.strftime("%Y-%m-%d"),
                "action": action,
                "signal": signal,
                "price":  round(current_price, 2),
                "pnl":    round(pnl, 2),
            })

    final_price = float(df['Close'].iloc[-1])
    final_value = cash + (ounces * final_price)

    # Buy and hold jämförelse
    first_price     = float(df['Close'].iloc[MIN_ROWS])
    bah_ounces      = (STARTING_CAPITAL * POSITION_SIZE) / first_price
    bah_final       = (STARTING_CAPITAL * (1 - POSITION_SIZE)) + (bah_ounces * final_price)
    bah_return      = ((bah_final - STARTING_CAPITAL) / STARTING_CAPITAL) * 100

    total_return    = ((final_value - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    closed_trades   = winning + losing
    win_rate        = (winning / max(closed_trades, 1)) * 100

    print(
        f"[Backtest] Klar. {len(trades)} trades | "
        f"Avkastning: {total_return:+.2f}% | "
        f"Win rate: {win_rate:.0f}% | "
        f"Max drawdown: -{max_drawdown:.1f}%"
    )

    return {
        "strategy_name":          "EMA-50v + RSI-timing (ettårig trend)",
        "starting_capital":       STARTING_CAPITAL,
        "final_value":            round(final_value, 2),
        "total_return_pct":       round(total_return, 2),
        "total_pnl":              round(final_value - STARTING_CAPITAL, 2),
        "max_drawdown_pct":       round(max_drawdown, 2),
        "total_trades":           len(trades),
        "winning_trades":         winning,
        "losing_trades":          losing,
        "win_rate_pct":           round(win_rate, 2),
        "buy_and_hold_return_pct": round(bah_return, 2),
        "buy_and_hold_final":     round(bah_final, 2),
        "trades":                 trades,
        "portfolio_values":       portfolio_values,
        "period_start":           df.index[MIN_ROWS].strftime("%Y-%m-%d"),
        "period_end":             df.index[-1].strftime("%Y-%m-%d"),
    }


def format_backtest_block(result: dict) -> str:
    """Formaterar backtest-resultatet som ett textblock för rapporten."""
    strat_better = result['total_return_pct'] > result['buy_and_hold_return_pct']
    comparison   = "✅ Bättre än buy & hold" if strat_better else "❌ Sämre än buy & hold"
    w = result['winning_trades']
    l = result['losing_trades']

    lines = [
        f"📈 BACKTEST — {result['strategy_name']}",
        f"Period: {result['period_start']} → {result['period_end']}",
        "─" * 45,
        f"{'Startvärde:':<30} {result['starting_capital']:>10,.2f} USD",
        f"{'Slutvärde:':<30} {result['final_value']:>10,.2f} USD",
        f"{'Total avkastning:':<30} {result['total_return_pct']:>+9.2f}%",
        f"{'Max drawdown:':<30} {-result['max_drawdown_pct']:>9.2f}%",
        f"{'Antal trades:':<30} {result['total_trades']:>10}",
        "Win rate:".ljust(30) + f" {result['win_rate_pct']:>9.1f}%  ({w}W / {l}L)",
        "─" * 45,
        f"{'Buy & hold avkastning:':<30} {result['buy_and_hold_return_pct']:>+9.2f}%",
        f"Strategin vs buy & hold: {comparison}",
        "",
        "⚠️  Exkl. skatt, courtage och spread.",
        "    Historiska resultat garanterar inte framtida avkastning.",
    ]

    if result['trades']:
        lines.append("")
        lines.append("Senaste 5 trades:")
        for t in result['trades'][-5:]:
            icon = "🟢" if t['action'] == "BUY" else "🔴"
            pnl  = f"P&L: {t['pnl']:+.2f} USD" if t['action'] == "SELL" else "position öppnad"
            lines.append(f"  {icon} {t['date']}  {t['action']:<5}  @ {t['price']:.2f}  {pnl}")

    return "\n".join(lines)
