"""
ai_analyst.py
-------------
Skickar indikatordata + helgnyheter + prisstatistik till Claude API
och returnerar en strukturerad veckoanalysrapport.

Rapportstruktur:
  1. Titel — datum + veckonummer
  2. Prisstatistik — YTD / 3 månader / månad / vecka
  3. Veckans beslut — 2–3 meningar + BULLISH/BEARISH/NEUTRAL
  4. Helgnyheter — artiklar fre–sön med bias och länk
  5. Trendanalys, Momentum, Volatilitet, Nyckelpriser
  6. Teknisk sammanfattning
  7. Disclaimer
"""

import anthropic
import os
import re
import json
from datetime import datetime, timedelta
from src.indicators import GoldIndicators
from src.performance_tracker import GoldPerformance, format_stats_block

MODEL      = "claude-sonnet-4-5"
MAX_TOKENS = 3000


# ---------------------------------------------------------------------------
# Nyhetshämtning
# ---------------------------------------------------------------------------

def fetch_weekend_news(client: anthropic.Anthropic) -> str:
    """
    Söker efter guld-relaterade nyheter från helgen (fredag–söndag)
    via Claudes inbyggda web_search-verktyg.
    """
    today             = datetime.today()
    days_since_friday = (today.weekday() - 4) % 7
    last_friday       = today - timedelta(days=days_since_friday)
    date_range        = f"{last_friday.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"

    print(f"[AIAnalyst] Söker helgnyheter ({date_range})...")

    news_prompt = f"""Search for the most important gold (XAU/USD) market news from {date_range}.

Focus on: Fed/ECB decisions, US inflation data, DXY movements, geopolitical events, major economic releases, gold ETF flows.

Return ONLY a JSON array:
[
  {{
    "headline": "Article headline",
    "summary": "One sentence: what happened and why it matters for gold",
    "bias": "BULLISH" or "BEARISH" or "NEUTRAL",
    "url": "Full article URL"
  }}
]

Return ONLY the JSON array. If no relevant news, return: []"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": news_prompt}]
        )

        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text += block.text

        json_match = re.search(r'\[.*?\]', raw_text, re.DOTALL)
        if not json_match:
            return "_Inga helgnyheter hittades._"

        articles = json.loads(json_match.group())
        if not articles:
            return "_Inga relevanta helgnyheter hittades för guld (fre–sön)._"

        lines = []
        for a in articles:
            icon = "🟢" if a.get("bias") == "BULLISH" else ("🔴" if a.get("bias") == "BEARISH" else "⚪")
            lines.append(
                f"**{a.get('headline','N/A')}**\n"
                f"{a.get('summary','')}\n"
                f"Signal: {icon} {a.get('bias','NEUTRAL')} | "
                f"Läs mer: {a.get('url','N/A')}"
            )

        print(f"[AIAnalyst] Hittade {len(articles)} helgnyheter.")
        return "\n\n".join(lines)

    except Exception as e:
        print(f"[AIAnalyst] Nyhetssökning misslyckades: {e}")
        return "_Nyhetssökning ej tillgänglig._"


# ---------------------------------------------------------------------------
# Prompt-byggare
# ---------------------------------------------------------------------------

def _build_prompt(
    ind:             GoldIndicators,
    interval_label:  str,
    news_section:    str,
    stats_block:     str,
    strategy_signal  = None,
) -> str:
    today     = datetime.today()
    week_num  = today.isocalendar().week
    date_str  = today.strftime("%Y-%m-%d")

    fib_context   = (
        f"  - Fibonacci 61.8%: {ind.fib_618:.2f} USD\n"
        f"  - Fibonacci 38.2%: {ind.fib_382:.2f} USD\n"
        f"  - Fibonacci 23.6%: {ind.fib_236:.2f} USD\n"
    )
    recent_closes = ", ".join([str(p) for p in ind.close_series_20w])

    return f"""Du är en senior kvantitativ analytiker inom ädelmetaller med handelsperspektivet hos en Goldman Sachs- och JPMorgan-trader.
Skriv rapporten på svenska. Var specifik, datadriven och professionell.
Detta är analytisk tolkning — inte investeringsrådgivning.

---
INSTRUMENT: Gold (XAU/USD) — {interval_label.upper()}
DATUM: {date_str} | Vecka {week_num}
---

TEKNISKA INDIKATORER:
Pris: {ind.current_price:.2f} USD ({ind.weekly_change_pct:+.2f}%)
EMA-20/50/200: {ind.ema_20:.0f} / {ind.ema_50:.0f} / {ind.ema_200:.0f}
EMA-trend: {ind.ema_trend} | vs EMA-200: {ind.price_vs_ema200_pct:+.2f}% | Kors: {ind.ema_20_50_cross}
RSI-14: {ind.rsi_14:.1f} ({ind.rsi_signal})
MACD: line={ind.macd_line:.2f} sig={ind.macd_signal:.2f} hist={ind.macd_histogram:.2f} kors={ind.macd_cross}
BB: övre={ind.bb_upper:.0f} mitt={ind.bb_middle:.0f} nedre={ind.bb_lower:.0f} pos={ind.bb_position} bredd={ind.bb_width_pct:.1f}%
ATR: {ind.atr_14:.2f} ({ind.atr_pct:.2f}%)
52v high/low: {ind.high_52w:.0f} / {ind.low_52w:.0f}
{fib_context}
Signal-score: Bull={ind.bull_signals} Bear={ind.bear_signals} → {ind.overall_bias}
Senaste 20 stängningar: {recent_closes}

---
STRATEGISIGNAL (EMA-200 + RSI-timing):
{f"{strategy_signal.action}: {strategy_signal.reason}" if strategy_signal else "Ej tillgänglig"}

HELGNYHETER (fre–sön):
{news_section}

---
KRÄV DETTA EXAKTA FORMAT (skriv på svenska):

# Gold (XAU/USD) — Vecka {week_num}, {date_str}

---

{stats_block}

---

## 📌 Veckans beslut
[2–3 meningar: kombinera tekniska indikatorer + helgnyheter till en sammanhängande bild.
Tänk som en senior trader — vad är den viktigaste informationen just nu?]
**Veckovärdering: BULLISH** (eller BEARISH eller NEUTRAL — välj ett)

---

## 📰 Helgnyheter (fre–sön)
[För varje artikel, exakt detta format:]

**[Rubrik]**
[En mening om vad som hände och varför det är relevant för guld.]
Signal: 🟢/🔴/⚪ BULLISH/BEARISH/NEUTRAL
Läs mer: [URL]

---

## 📊 Trendanalys
[Tolka EMA-strukturen. Trendriktning och prisläge relativt nyckel-EMA:er.]

## 📈 Momentumanalys
[RSI och MACD — bekräftar eller divergerar momentumet från trenden?]

## 〰️ Volatilitet & Bollingerband
[Squeeze eller expansion? Vad indikerar det om kommande rörelse?]

## 🎯 Nyckelpriser att bevaka
[Stöd/motstånd, Fibonacci-nivåer — med förklaring varför de är viktiga.]

## 📋 Teknisk sammanfattning
[3–5 meningar som syntetiserar allt. Specificera triggers för fortsättning/vändning.]

---

## ⚠️ Disclaimer
Denna rapport är teknisk analys av prisindikatorer och nyhetssammanfattningar.
Den utgör inte investeringsrådgivning. Genomför alltid din egen analys.

---

Skriv hela rapporten nu på svenska."""


# ---------------------------------------------------------------------------
# Huvud-analysfunktion
# ---------------------------------------------------------------------------

def run_analysis(
    ind:             GoldIndicators,
    perf:            GoldPerformance,
    strategy_signal  = None,
    interval_label:  str = "weekly",
) -> str:
    """
    Kör hela veckopipelinen:
      1. Hämtar helgnyheter
      2. Formaterar statistikblock
      3. Bygger prompt och skickar till Claude

    Parameters
    ----------
    ind : GoldIndicators
        Tekniska indikatorer från indicators.py
    perf : GoldPerformance
        Prisstatistik från performance_tracker.py
    interval_label : str
        Tidshorisont-etikett.

    Returns
    -------
    str
        Fullständig veckorapport på svenska.
    """
    client       = anthropic.Anthropic()
    news_section = fetch_weekend_news(client)
    stats_block  = format_stats_block(perf)
    prompt       = _build_prompt(ind, interval_label, news_section, stats_block, strategy_signal)

    print(f"[AIAnalyst] Genererar veckorapport ({MODEL})...")
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )

    report_text = message.content[0].text
    print(f"[AIAnalyst] Klar. Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out")
    return report_text


def extract_bias_from_report(report_text: str) -> str:
    """Extraherar BULLISH/BEARISH/NEUTRAL från rapporttexten."""
    match = re.search(r'Veckovärdering:\s*\*{0,2}(BULLISH|BEARISH|NEUTRAL)\*{0,2}', report_text, re.IGNORECASE)
    return match.group(1).upper() if match else "NEUTRAL"


# ---------------------------------------------------------------------------
# Rapportsparare
# ---------------------------------------------------------------------------

def save_report(report_text: str, output_dir: str = "reports") -> str:
    """Sparar rapporten med veckonummer i filnamnet."""
    os.makedirs(output_dir, exist_ok=True)
    today    = datetime.now()
    week_num = today.isocalendar().week
    ts       = today.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"gold_v{week_num}_{ts}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"[AIAnalyst] Rapport sparad: {filepath}")
    return filepath
