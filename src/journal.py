"""
journal.py
----------
Sparar och läser veckobeslut i en lokal JSON-fil (data/journal.json).

Varför JSON och inte en databas?
  - Ingen databas att installera eller konfigurera
  - Filen kan committas till GitHub — historiken följer med automatiskt
  - Läsbar med valfri textredigerare om något går fel
  - Tillräckligt för det volymen av data vi hanterar (52 poster/år)

Datastruktur per veckopost:
  {
    "week":        13,
    "year":        2026,
    "date":        "2026-03-31",
    "bias":        "BULLISH",          <- Veckans beslut från rapporten
    "price_open":  2702.82,            <- Priset när rapporten skrevs
    "price_close": null,               <- Fylls i nästa vecka
    "pct_change":  null,               <- Beräknas när price_close är känt
    "outcome":     null                <- "CORRECT" / "INCORRECT" / "NEUTRAL"
  }
"""

import json
import os
from datetime import datetime
from typing import Optional

JOURNAL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'journal.json')


def _load() -> list:
    """Laddar journalen från disk. Returnerar tom lista om filen inte finns."""
    path = os.path.abspath(JOURNAL_PATH)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save(entries: list) -> None:
    """Sparar journalen till disk."""
    path = os.path.abspath(JOURNAL_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Publik API
# ---------------------------------------------------------------------------

def save_weekly_decision(bias: str, price_open: float) -> None:
    """
    Sparar veckans beslut (BULLISH/BEARISH/NEUTRAL) och öppningspriset.
    Anropas i slutet av varje veckoanalys.

    Parameters
    ----------
    bias : str
        Veckobeslut — "BULLISH", "BEARISH" eller "NEUTRAL"
    price_open : float
        Guldpriset när rapporten genererades (veckoöppning).
    """
    today    = datetime.today()
    week_num = today.isocalendar().week
    year     = today.year

    entries = _load()

    # Uppdatera befintlig post om samma vecka redan finns
    for entry in entries:
        if entry['week'] == week_num and entry['year'] == year:
            entry['bias']       = bias.upper()
            entry['price_open'] = price_open
            _save(entries)
            print(f"[Journal] Uppdaterade vecka {week_num}/{year}: {bias} @ {price_open:.2f}")
            return

    # Annars lägg till ny post
    entries.append({
        "week":        week_num,
        "year":        year,
        "date":        today.strftime("%Y-%m-%d"),
        "bias":        bias.upper(),
        "price_open":  price_open,
        "price_close": None,
        "pct_change":  None,
        "outcome":     None
    })
    _save(entries)
    print(f"[Journal] Sparade vecka {week_num}/{year}: {bias} @ {price_open:.2f}")


def close_previous_week(price_close: float) -> None:
    """
    Stänger föregående veckas post med stängningspriset och beräknar utfall.
    Anropas i början av varje ny veckoanalys (innan rapporten genereras).

    Utfallslogik:
      BULLISH + pris upp   → CORRECT
      BULLISH + pris ner   → INCORRECT
      BEARISH + pris ner   → CORRECT
      BEARISH + pris upp   → INCORRECT
      NEUTRAL              → NEUTRAL

    Parameters
    ----------
    price_close : float
        Stängningspriset för föregående vecka (= nuvarande öppning).
    """
    today     = datetime.today()
    week_num  = today.isocalendar().week
    year      = today.year
    prev_week = week_num - 1 if week_num > 1 else 52
    prev_year = year if week_num > 1 else year - 1

    entries = _load()

    for entry in entries:
        if entry['week'] == prev_week and entry['year'] == prev_year:
            if entry['price_open'] and entry['price_close'] is None:
                pct = ((price_close - entry['price_open']) / entry['price_open']) * 100
                entry['price_close'] = price_close
                entry['pct_change']  = round(pct, 2)

                bias = entry['bias']
                if bias == 'NEUTRAL':
                    entry['outcome'] = 'NEUTRAL'
                elif bias == 'BULLISH' and pct > 0:
                    entry['outcome'] = 'CORRECT'
                elif bias == 'BEARISH' and pct < 0:
                    entry['outcome'] = 'CORRECT'
                else:
                    entry['outcome'] = 'INCORRECT'

                _save(entries)
                print(
                    f"[Journal] Stängde vecka {prev_week}/{prev_year}: "
                    f"{pct:+.2f}% → {entry['outcome']}"
                )
                return

    print(f"[Journal] Ingen öppen post hittades för vecka {prev_week}/{prev_year}.")


def get_entries_for_month(year: int, month: int) -> list:
    """
    Returnerar alla journalposter för en given månad.
    Används av monthly_analyst.py för att bygga månadsrapporten.
    """
    entries = _load()
    result  = []
    for entry in entries:
        entry_date = datetime.strptime(entry['date'], "%Y-%m-%d")
        if entry_date.year == year and entry_date.month == month:
            result.append(entry)
    return sorted(result, key=lambda x: x['week'])


def get_all_entries_for_year(year: int) -> list:
    """Returnerar alla poster för ett givet år."""
    return [e for e in _load() if e['year'] == year]


def extract_bias_from_report(report_text: str) -> str:
    """
    Extraherar veckobeslut (BULLISH/BEARISH/NEUTRAL) från rapporttexten.
    Letar efter raden: **Veckovärdering: BULLISH**

    Returnerar "NEUTRAL" om inget hittades.
    """
    import re
    match = re.search(r'Veckovärdering:\s*(BULLISH|BEARISH|NEUTRAL)', report_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "NEUTRAL"
