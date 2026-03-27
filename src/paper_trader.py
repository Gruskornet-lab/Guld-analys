"""
paper_trader.py
---------------
Simulerar köp och sälj av guld baserat på veckosignaler.
Ingen riktig handel sker — allt är simulerat med fejkade pengar.

Strategi: Enkel
  - BULLISH  → Köp guld (lång position) med 95% av kassan
  - BEARISH  → Sälj allt guld, gå till kassa
  - NEUTRAL  → Behåll nuvarande position

Portföljdata sparas i data/portfolio.json och uppdateras varje vecka.

Begrepp:
  Position    = hur mycket guld vi äger just nu (i troy ounces)
  Kassa       = hur mycket USD vi har som inte är investerat
  P&L         = Profit and Loss — vinst eller förlust
  Drawdown    = hur mycket portföljen sjunkit från sitt högsta värde
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'portfolio.json')
STARTING_CAPITAL = 10_000.0   # USD
POSITION_SIZE    = 0.95        # Investera 95% av kassan vid köp (5% buffert)


@dataclass
class Trade:
    """Representerar en enskild affär."""
    week:        int
    year:        int
    date:        str
    action:      str    # "BUY" / "SELL" / "HOLD"
    signal:      str    # "BULLISH" / "BEARISH" / "NEUTRAL"
    price:       float  # Guldpris vid affären
    ounces:      float  # Antal troy ounces
    value:       float  # Totalt värde i USD
    cash_after:  float  # Kassa efter affären
    pnl:         float  # Vinst/förlust på denna affär (0 vid köp)
    pnl_pct:     float  # Vinst/förlust i procent


@dataclass
class Portfolio:
    """Håller portföljens nuvarande tillstånd."""
    cash:             float = STARTING_CAPITAL
    ounces:           float = 0.0
    avg_buy_price:    float = 0.0
    total_pnl:        float = 0.0
    peak_value:       float = STARTING_CAPITAL
    max_drawdown_pct: float = 0.0
    total_trades:     int   = 0
    winning_trades:   int   = 0
    losing_trades:    int   = 0
    trades:           list  = None

    def __post_init__(self):
        if self.trades is None:
            self.trades = []

    def current_value(self, current_price: float) -> float:
        """Beräknar totalt portföljvärde: kassa + guld till marknadspris."""
        return self.cash + (self.ounces * current_price)

    def update_drawdown(self, current_price: float):
        """Uppdaterar max drawdown om portföljen nått nytt bottenläge."""
        value = self.current_value(current_price)
        if value > self.peak_value:
            self.peak_value = value
        drawdown = ((self.peak_value - value) / self.peak_value) * 100
        if drawdown > self.max_drawdown_pct:
            self.max_drawdown_pct = drawdown


def _load_portfolio() -> Portfolio:
    """Laddar portföljen från disk. Skapar ny om filen inte finns."""
    path = os.path.abspath(PORTFOLIO_PATH)
    if not os.path.exists(path):
        return Portfolio()
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    p = Portfolio(
        cash=data['cash'],
        ounces=data['ounces'],
        avg_buy_price=data['avg_buy_price'],
        total_pnl=data['total_pnl'],
        peak_value=data['peak_value'],
        max_drawdown_pct=data['max_drawdown_pct'],
        total_trades=data['total_trades'],
        winning_trades=data['winning_trades'],
        losing_trades=data['losing_trades'],
        trades=data['trades'],
    )
    return p


def _save_portfolio(p: Portfolio):
    """Sparar portföljen till disk."""
    path = os.path.abspath(PORTFOLIO_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        'cash':             p.cash,
        'ounces':           p.ounces,
        'avg_buy_price':    p.avg_buy_price,
        'total_pnl':        p.total_pnl,
        'peak_value':       p.peak_value,
        'max_drawdown_pct': p.max_drawdown_pct,
        'total_trades':     p.total_trades,
        'winning_trades':   p.winning_trades,
        'losing_trades':    p.losing_trades,
        'trades':           p.trades,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Huvud-handelsfunktion
# ---------------------------------------------------------------------------

def execute_weekly_trade(signal: str, current_price: float) -> dict:
    """
    Utför veckans simulerade handel baserat på strategisignal och pris.

    Parameters
    ----------
    signal : str
        "BUY", "SELL" eller "HOLD" — från strategy.py
        (accepterar även "BULLISH"/"BEARISH" för bakåtkompatibilitet)
    current_price : float
        Nuvarande guldpris i USD per troy ounce

    Returns
    -------
    dict
        Sammanfattning av vad som hände denna vecka
    """
    today   = datetime.today()
    p       = _load_portfolio()
    signal  = signal.upper()
    # Bakåtkompatibilitet: översätt gamla bias-signaler
    if signal == "BULLISH": signal = "BUY"
    if signal == "BEARISH": signal = "SELL"
    if signal == "NEUTRAL": signal = "HOLD"

    week_num = today.isocalendar().week
    year     = today.year
    action   = "HOLD"
    pnl      = 0.0
    pnl_pct  = 0.0
    ounces_traded = 0.0

    # -------------------------------------------------------------------
    # BULLISH → Köp guld om vi inte redan har en lång position
    # -------------------------------------------------------------------
    if signal == "BUY" and p.ounces == 0 and p.cash > 0:
        invest_amount  = p.cash * POSITION_SIZE
        ounces_bought  = invest_amount / current_price
        p.ounces       = ounces_bought
        p.avg_buy_price = current_price
        p.cash         -= invest_amount
        p.total_trades += 1
        ounces_traded   = ounces_bought
        action          = "BUY"
        print(f"[PaperTrader] KÖP {ounces_bought:.4f} oz @ {current_price:.2f} USD")

    # -------------------------------------------------------------------
    # BEARISH → Sälj allt guld om vi har en position
    # -------------------------------------------------------------------
    elif signal == "SELL" and p.ounces > 0:
        sell_value     = p.ounces * current_price
        pnl            = sell_value - (p.ounces * p.avg_buy_price)
        pnl_pct        = (pnl / (p.ounces * p.avg_buy_price)) * 100
        p.cash        += sell_value
        p.total_pnl   += pnl
        p.total_trades += 1
        ounces_traded   = p.ounces

        if pnl >= 0:
            p.winning_trades += 1
        else:
            p.losing_trades  += 1

        action   = "SELL"
        print(f"[PaperTrader] SÄLJ {p.ounces:.4f} oz @ {current_price:.2f} USD | P&L: {pnl:+.2f} USD ({pnl_pct:+.2f}%)")
        p.ounces        = 0.0
        p.avg_buy_price = 0.0

    else:
        print(f"[PaperTrader] HÅLL — Signal: {signal}, Position: {p.ounces:.4f} oz")

    # Uppdatera drawdown
    p.update_drawdown(current_price)

    # Spara trade i historik
    trade = {
        "week":       week_num,
        "year":       year,
        "date":       today.strftime("%Y-%m-%d"),
        "action":     action,
        "signal":     signal,
        "price":      current_price,
        "ounces":     ounces_traded,
        "value":      ounces_traded * current_price,
        "cash_after": p.cash,
        "pnl":        round(pnl, 2),
        "pnl_pct":    round(pnl_pct, 2),
    }
    p.trades.append(trade)
    _save_portfolio(p)

    total_value = p.current_value(current_price)
    total_return_pct = ((total_value - STARTING_CAPITAL) / STARTING_CAPITAL) * 100

    return {
        "action":         action,
        "signal":         signal,
        "price":          current_price,
        "ounces":         p.ounces,
        "cash":           p.cash,
        "total_value":    total_value,
        "total_return":   total_return_pct,
        "total_pnl":      p.total_pnl,
        "max_drawdown":   p.max_drawdown_pct,
        "win_rate":       (p.winning_trades / max(p.winning_trades + p.losing_trades, 1)) * 100,
    }


def format_portfolio_block(current_price: float) -> str:
    """
    Formaterar en portföljöversikt för rapporten.

    Exempel:
      💼 PAPER TRADING PORTFÖLJ
      ─────────────────────────────────────────────
      Startvärde:      10 000.00 USD
      Nuvarande värde: 11 234.56 USD  (+12.35%)
      Kassa:            1 234.56 USD
      Guld:             4.2341 oz  (@ 2 702.82 USD)
      Total P&L:       +1 234.56 USD
      Win rate:         67%
      Max drawdown:     -4.21%
    """
    p            = _load_portfolio()
    total_value  = p.current_value(current_price)
    total_return = ((total_value - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    closed       = p.winning_trades + p.losing_trades
    win_rate     = (p.winning_trades / max(closed, 1)) * 100

    sign = "+" if total_return >= 0 else ""

    lines = [
        "💼 PAPER TRADING PORTFÖLJ",
        "─" * 45,
        f"{'Startvärde:':<25} {STARTING_CAPITAL:>10,.2f} USD",
        f"{'Nuvarande värde:':<25} {total_value:>10,.2f} USD  ({sign}{total_return:.2f}%)",
        f"{'Kassa:':<25} {p.cash:>10,.2f} USD",
        f"{'Guld:':<25} {p.ounces:>10.4f} oz  (@ {current_price:.2f} USD/oz)",
        f"{'Total P&L:':<25} {p.total_pnl:>+10,.2f} USD",
        f"{'Win rate:':<25} {win_rate:>9.0f}%  ({p.winning_trades}W / {p.losing_trades}L)",
        f"{'Max drawdown:':<25} {-p.max_drawdown_pct:>9.2f}%",
    ]
    return "\n".join(lines)
