"""
monthly_analyst.py
------------------
Genererar månadsrapporten den första måndagen i varje månad.

Vad månadsrapporten innehåller:
  1. Titel med månad och år
  2. Statistikblock (YTD, 3 månader, föregående månad, föregående vecka)
  3. Utvärdering av varje vecka under föregående månad:
     - Vad beslutades (BULLISH/BEARISH/NEUTRAL)
     - Vad hände i verkligheten (pris upp/ner, %)
     - Utfall (CORRECT / INCORRECT / NEUTRAL)
  4. Träffsäkerhetsstatistik för månaden
  5. Kortanalys av varför det gick som det gick (Claude tolkar)
  6. Disclaimer

Körlogik:
  - Körs automatiskt om det är den 1:a–7:e i månaden OCH måndag
  - Kan också köras manuellt: python main.py --monthly
"""

import anthropic
import os
from datetime import datetime, timedelta
from src.journal import get_entries_for_month
from src.performance_tracker import GoldPerformance, format_stats_block


MODEL      = "claude-sonnet-4-5"
MAX_TOKENS = 2500


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------

def _build_weekly_review_table(entries: list) -> str:
    """
    Bygger en textrepresentation av veckoutvärderingen.

    Exempel:
      Vecka 1  | 2026-01-06 | BULLISH   | +1.23% | CORRECT
      Vecka 2  | 2026-01-13 | BEARISH   | +0.45% | INCORRECT
    """
    if not entries:
        return "Inga veckoposter hittade för denna månad."

    lines = [
        f"{'Vecka':<10} {'Datum':<14} {'Beslut':<12} {'Utfall %':<12} {'Resultat':<12}",
        "─" * 62,
    ]
    for e in entries:
        week     = f"Vecka {e['week']}"
        date     = e.get('date', 'N/A')
        bias     = e.get('bias', 'N/A')
        pct      = f"{e['pct_change']:+.2f}%" if e.get('pct_change') is not None else "Pågående"
        outcome  = e.get('outcome') or "Ej stängd"

        # Emoji för snabb visuell läsning
        icon = {"CORRECT": "✅", "INCORRECT": "❌", "NEUTRAL": "⚪"}.get(outcome, "⏳")
        lines.append(f"{week:<10} {date:<14} {bias:<12} {pct:<12} {icon} {outcome}")

    return "\n".join(lines)


def _accuracy_summary(entries: list) -> str:
    """Beräknar träffsäkerhet för månaden."""
    closed   = [e for e in entries if e.get('outcome') in ('CORRECT', 'INCORRECT')]
    correct  = sum(1 for e in closed if e['outcome'] == 'CORRECT')
    total    = len(closed)

    if total == 0:
        return "Inga stängda veckor att utvärdera ännu."

    pct = (correct / total) * 100
    return (
        f"Träffsäkerhet: {correct}/{total} beslut korrekta ({pct:.0f}%)\n"
        f"Bästa vecka:   {max((e for e in closed), key=lambda x: x.get('pct_change', 0) or 0, default={}).get('week', 'N/A')}\n"
        f"Sämsta vecka:  {min((e for e in closed), key=lambda x: x.get('pct_change', 0) or 0, default={}).get('week', 'N/A')}"
    )


def _build_monthly_prompt(
    prev_year:     int,
    prev_month:    int,
    entries:       list,
    weekly_table:  str,
    accuracy:      str,
    stats_block:   str,
) -> str:
    """Bygger prompten för månadsrapporten."""

    month_name = datetime(prev_year, prev_month, 1).strftime("%B %Y")
    today      = datetime.today()
    report_week = today.isocalendar().week

    # Bygg detaljerad kontext per vecka för Claude
    week_details = []
    for e in entries:
        detail = (
            f"Vecka {e['week']} ({e.get('date','?')}): "
            f"Beslut={e.get('bias','?')}, "
            f"Pris öppning={e.get('price_open','?')} USD, "
            f"Pris stängning={e.get('price_close','?')} USD, "
            f"Förändring={e.get('pct_change','?')}%, "
            f"Utfall={e.get('outcome','?')}"
        )
        week_details.append(detail)

    week_context = "\n".join(week_details) if week_details else "Inga poster."

    return f"""Du är en senior analytiker inom ädelmetaller och granskar föregående månads handelsbeslut.
Skriv rapporten på svenska. Var professionell, specifik och ärlig — om besluten var felaktiga, förklara varför.

---

MÅNADSRAPPORT FÖR: {month_name}
RAPPORT GENERERAD: {today.strftime('%Y-%m-%d')} (Vecka {report_week})

---

VECKOBESLUT OCH UTFALL UNDER {month_name.upper()}:
{week_context}

---

KRÄV DETTA EXAKTA FORMAT:

# Månadsrapport Guld (XAU/USD) — {month_name}
*Genererad: {today.strftime('%Y-%m-%d')} | Vecka {report_week}*

---

{stats_block}

---

## 📅 Veckoutvärdering — {month_name}

{weekly_table}

---

## 🔍 Analys av månaden
[Skriv 3–5 meningar som förklarar varför besluten gick som de gick.
Vad stämde i analysen? Vad missades? Vilka faktorer (nyheter, makro, tekniska) var avgörande?
Var ärlig och specifik — detta är ett lärdomsdokument.]

## 📈 Träffsäkerhet
{accuracy}

## 💡 Lärdomar inför nästa månad
[2–3 konkreta punkter om vad som kan förbättras i analysprocessen baserat på denna månads utfall.]

---

## ⚠️ Disclaimer
Denna rapport är en efterhandsutvärdering av tekniska analysbeslut.
Den utgör inte investeringsrådgivning. Historiska resultat garanterar inte framtida avkastning.

---

Skriv hela rapporten nu på svenska, exakt enligt formatet ovan."""


# ---------------------------------------------------------------------------
# Huvud-funktion
# ---------------------------------------------------------------------------

def run_monthly_analysis(
    perf:       GoldPerformance,
    prev_year:  int  = None,
    prev_month: int  = None,
) -> str:
    """
    Genererar månadsrapporten för föregående månad.

    Parameters
    ----------
    perf : GoldPerformance
        Prisstatistik från performance_tracker.py
    prev_year : int, optional
        Vilket år månadsrapporten gäller. Standard = förra månaden.
    prev_month : int, optional
        Vilken månad rapporten gäller. Standard = förra månaden.

    Returns
    -------
    str
        Fullständig månadsrapport på svenska.
    """
    today = datetime.today()

    # Default: föregående månad
    if prev_month is None or prev_year is None:
        first_this_month = today.replace(day=1)
        last_month       = first_this_month - timedelta(days=1)
        prev_year        = last_month.year
        prev_month       = last_month.month

    entries      = get_entries_for_month(prev_year, prev_month)
    weekly_table = _build_weekly_review_table(entries)
    accuracy     = _accuracy_summary(entries)
    stats_block  = format_stats_block(perf)

    prompt = _build_monthly_prompt(
        prev_year, prev_month, entries, weekly_table, accuracy, stats_block
    )

    client = anthropic.Anthropic()
    print(f"[MonthlyAnalyst] Genererar månadsrapport för {prev_year}-{prev_month:02d}...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )

    report_text = message.content[0].text
    print(
        f"[MonthlyAnalyst] Klar. "
        f"Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out"
    )
    return report_text


def is_first_monday_of_month() -> bool:
    """
    Returnerar True om idag är den första måndagen i månaden.
    Används av main.py för att avgöra om månadsrapport ska köras.
    """
    today = datetime.today()
    if today.weekday() != 0:      # Inte måndag
        return False
    return today.day <= 7         # Första 7 dagarna = första möjliga måndag


def save_monthly_report(report_text: str, year: int, month: int, output_dir: str = "reports") -> str:
    """Sparar månadsrapporten som en namngiven fil."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"gold_monthly_{year}_{month:02d}.txt"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"[MonthlyAnalyst] Rapport sparad: {filepath}")
    return filepath
