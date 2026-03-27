"""
strategy.py
-----------
EMA-50 (veckovis) + RSI-timing strategi för guld.

Varför EMA-50 på veckobasis istället för EMA-200?
  EMA-200 på daglig data = ca 200 handelsdagar = 40 veckor
  EMA-50 på veckobasis   = 50 veckor = ca ett år
  De mäter ungefär SAMMA sak — den ettåriga trenden.

  Med 3 år av veckodata är EMA-200 (veckovis) = 200 veckor = 4 år,
  vilket kräver mer data än vi har. EMA-50 veckovis är rätt nivå
  för vår tidshorizont och stämmer överens med den backtestade
  12-månaders MA-strategin från QuantifiedStrategies.com.

Strategi-regler:
  KÖP  när ALLA dessa stämmer:
    1. Pris > EMA-50 (veckovis)     → ettårig trend är bullish
    2. RSI-14 < 55                  → priset har dragit tillbaka
    3. Priset steg förra veckan     → rörelse bekräftar vändning

  SÄLJ när NÅGOT av dessa stämmer:
    1. Pris < EMA-50 (veckovis)     → ettårig trend bruten
    2. RSI-14 > 75                  → kraftigt överköpt

  HÅLL annars
"""

from dataclasses import dataclass


@dataclass
class StrategySignal:
    action:    str    # "BUY", "SELL", "HOLD"
    reason:    str
    trend_ok:  bool
    rsi_entry: bool
    rsi_exit:  bool
    price:     float
    ema_50:    float
    rsi:       float


def evaluate_strategy(ind) -> StrategySignal:
    """
    Utvärderar EMA-50 (veckovis) + RSI-timing strategin.
    Använder EMA-50 som proxy för den ettåriga trenden.
    """
    price   = ind.current_price
    ema_50  = ind.ema_50    # EMA-50 veckovis ≈ 12-månaders trend
    rsi     = ind.rsi_14

    closes          = ind.close_series_20w
    price_recovering = (closes[-1] > closes[-2]) if len(closes) >= 2 else True

    trend_ok  = price > ema_50
    rsi_entry = rsi < 55 and price_recovering
    rsi_exit  = rsi > 75

    if rsi_exit:
        action = "SELL"
        reason = f"RSI {rsi:.1f} > 75 — kraftigt överköpt. Ta hem vinsten."

    elif not trend_ok:
        action = "SELL"
        reason = (
            f"Pris {price:.0f} < EMA-50 {ema_50:.0f} — "
            f"ettårig trend bruten. Gå till kassa."
        )

    elif trend_ok and rsi_entry:
        action = "BUY"
        reason = (
            f"Pris {price:.0f} > EMA-50 {ema_50:.0f} (trend bullish) + "
            f"RSI {rsi:.1f} < 55 med prisåterhämtning — entry."
        )

    else:
        action = "HOLD"
        reason = (
            f"Trend {'bullish' if trend_ok else 'bearish'} "
            f"(EMA-50: {ema_50:.0f}), RSI {rsi:.1f}. "
            f"{'Håll position eller väntar på bättre entry.' if trend_ok else 'Väntar på trend.'}"
        )

    return StrategySignal(
        action=action, reason=reason,
        trend_ok=trend_ok, rsi_entry=rsi_entry, rsi_exit=rsi_exit,
        price=price, ema_50=ema_50, rsi=rsi,
    )


def format_strategy_block(signal: StrategySignal) -> str:
    icons      = {"BUY": "🟢 KÖP", "SELL": "🔴 SÄLJ", "HOLD": "⚪ HÅLL"}
    action_str = icons.get(signal.action, signal.action)

    trend_str = (
        f"✅ Bullish (pris {signal.price:.0f} > EMA-50v {signal.ema_50:.0f})"
        if signal.trend_ok else
        f"❌ Bearish (pris {signal.price:.0f} < EMA-50v {signal.ema_50:.0f})"
    )
    rsi_entry_str = (
        f"✅ RSI {signal.rsi:.1f} < 55 + prisåterhämtning"
        if signal.rsi_entry else
        f"— RSI {signal.rsi:.1f} (väntar på < 55)"
    )
    rsi_exit_str = (
        f"⚠️  AKTIVERAD — RSI {signal.rsi:.1f} > 75"
        if signal.rsi_exit else
        f"— Ej aktiverad (RSI {signal.rsi:.1f} < 75)"
    )

    lines = [
        "🎯 STRATEGISIGNAL — EMA-50 (VECKOVIS) + RSI TIMING",
        "─" * 45,
        f"{'Signal:':<22} {action_str}",
        f"{'Trend (EMA-50v):':<22} {trend_str}",
        f"{'RSI-entry (<55):':<22} {rsi_entry_str}",
        f"{'RSI-exit (>75):':<22} {rsi_exit_str}",
        "─" * 45,
        f"Motivering: {signal.reason}",
    ]
    return "\n".join(lines)
