"""
main.py
-------
Orkesterar hela Gold Analysis-systemet.

Pipeline varje måndag:
  1. Hämtar gulddata (veckovis + daglig)
  2. Beräknar tekniska indikatorer
  3. Beräknar prisstatistik (YTD, 3mån, månad, vecka)
  4. Utvärderar EMA-200 + RSI-timing strategin
  5. Genererar veckorapport med Claude (inkl. nyheter + statistik + signal)
  6. Utför paper trade baserat på strategisignalen
  7. Sparar beslut i journal
  8. Skickar Telegram-notis
  9. Första måndag i månaden: även månadsrapport

Manuell körning:
  python main.py              → Veckorapport + paper trade
  python main.py --monthly    → Tvinga månadsrapport
  python main.py --backtest   → Kör historisk backtest
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data_fetcher        import fetch_gold_data
from src.indicators          import compute_indicators
from src.performance_tracker import compute_performance
from src.strategy            import evaluate_strategy, format_strategy_block
from src.ai_analyst          import run_analysis, save_report
from src.journal             import save_weekly_decision, close_previous_week
from src.paper_trader        import execute_weekly_trade, format_portfolio_block
from src.backtest            import run_backtest, format_backtest_block
from src.monthly_analyst     import (
    run_monthly_analysis, save_monthly_report, is_first_monday_of_month
)
from src.notifier            import send_telegram_report


def run_weekly(df_weekly, df_daily):
    """Kör veckopipelinen."""
    print("=" * 60)
    print("  Gold Analysis — Veckorapport")
    print("=" * 60)

    # Indikatorer
    print("\n[1/6] Beräknar indikatorer...")
    indicators = compute_indicators(df_weekly)
    print(f"      OK — Pris: {indicators.current_price:.2f} USD")

    # Prisstatistik
    print("\n[2/6] Beräknar prisstatistik...")
    perf = compute_performance(df_daily)
    print(f"      OK — YTD: {perf.ytd_pct:+.2f}%")

    # Strategiutvärdering
    print("\n[3/6] Utvärderar EMA-200 + RSI-strategi...")
    signal = evaluate_strategy(indicators)
    strategy_block = format_strategy_block(signal)
    print(f"      OK — Signal: {signal.action} | {signal.reason}")

    # Stäng föregående vecka i journal
    close_previous_week(price_close=indicators.current_price)

    # Generera AI-rapport
    print("\n[4/6] Genererar AI-rapport...")
    report = run_analysis(
        indicators,
        perf,
        strategy_signal=signal,
        interval_label="weekly"
    )

    # Paper trade baserat på strategisignal (BUY/SELL/HOLD)
    print("\n[5/6] Utför paper trade...")
    execute_weekly_trade(
        signal=signal.action,
        current_price=indicators.current_price
    )
    portfolio_block = format_portfolio_block(indicators.current_price)

    # Sätt ihop fullständig rapport
    full_report = (
        report
        + "\n\n---\n\n"
        + strategy_block
        + "\n\n---\n\n"
        + portfolio_block
    )

    saved_path = save_report(full_report, output_dir="reports")
    save_weekly_decision(
        bias=signal.action,
        price_open=indicators.current_price
    )

    print("\n" + "=" * 60)
    print(full_report)
    print("=" * 60)

    # Telegram
    print("\n[6/6] Skickar Telegram-notis...")
    sent = send_telegram_report(full_report)
    print(f"      {'OK' if sent else 'INFO — Telegram ej konfigurerat'}")

    print(f"\nKlart. Sparad: {saved_path}")
    return full_report


def run_backtest_cmd(df_weekly):
    """Kör backtesten och visa resultat."""
    print("\n" + "=" * 60)
    print("  Gold Analysis — Backtest (EMA-200 + RSI-timing)")
    print("=" * 60)

    result = run_backtest(df_weekly)
    block  = format_backtest_block(result)

    print("\n" + block)

    os.makedirs("reports", exist_ok=True)
    from datetime import datetime
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"reports/backtest_{ts}.txt"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(block)
    print(f"\nBacktest sparad: {path}")
    send_telegram_report("📊 *BACKTEST — EMA-200 + RSI-timing*\n\n" + block)


def run_monthly(df_daily, force: bool = False):
    """Kör månadspipelinen."""
    if not force and not is_first_monday_of_month():
        return None

    print("\n" + "=" * 60)
    print("  Gold Analysis — Månadsrapport")
    print("=" * 60)

    perf       = compute_performance(df_daily)
    report     = run_monthly_analysis(perf)

    from datetime import datetime, timedelta
    today      = datetime.today().replace(day=1) - timedelta(days=1)
    saved_path = save_monthly_report(report, today.year, today.month)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    send_telegram_report("📅 *MÅNADSRAPPORT*\n\n" + report)
    print(f"\nMånadsrapport sparad: {saved_path}")
    return report


def main():
    force_monthly  = "--monthly"  in sys.argv
    force_backtest = "--backtest" in sys.argv

    print("\n[Data] Hämtar gulddata...")
    df_weekly = fetch_gold_data(period_years=3, interval="1wk")
    df_daily  = fetch_gold_data(period_years=2, interval="1d")
    print(f"[Data] OK — {len(df_weekly)} veckor | {len(df_daily)} dagar\n")

    if force_backtest:
        run_backtest_cmd(df_weekly)
        return

    run_weekly(df_weekly, df_daily)
    run_monthly(df_daily, force=force_monthly)


if __name__ == "__main__":
    main()
