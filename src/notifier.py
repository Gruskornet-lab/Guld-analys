"""
notifier.py
-----------
Skickar analysrapporten som ett Telegram-meddelande via Telegram Bot API.

Stöder flera mottagare via miljövariabler:
  TELEGRAM_BOT_TOKEN   — din bots token (krävs)
  TELEGRAM_CHAT_ID     — din personliga chat-ID (krävs)
  TELEGRAM_CHAT_ID_2   — din pappas chat-ID (valfritt)
  TELEGRAM_CHAT_ID_3   — eventuell tredje mottagare (valfritt)

Lägg till fler mottagare i framtiden genom att bara lägga till
TELEGRAM_CHAT_ID_4, _5 osv. som GitHub Secrets — ingen kodändring krävs.
"""

import requests
import os

TELEGRAM_API_BASE  = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE_LENGTH = 4000


def _split_message(text: str) -> list:
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    parts = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


def _send_to_one(token: str, chat_id: str, text: str) -> bool:
    """Skickar ett meddelande till en enskild mottagare."""
    url     = TELEGRAM_API_BASE.format(token=token, method="sendMessage")
    payload = {
        "chat_id":                  chat_id,
        "text":                     text,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"[Notifier] FEL för chat_id {chat_id}: {e}")
        return False


def _get_all_recipients() -> list:
    """
    Hämtar alla konfigurerade chat-ID:n från miljövariabler.
    Letar efter TELEGRAM_CHAT_ID, TELEGRAM_CHAT_ID_2, _3 osv.
    Returnerar en lista med (etikett, chat_id)-tupler.
    """
    recipients = []

    # Primär mottagare
    primary = os.environ.get("TELEGRAM_CHAT_ID")
    if primary:
        recipients.append(("Primär", primary))

    # Extra mottagare — _2, _3, _4 ...
    i = 2
    while True:
        extra = os.environ.get(f"TELEGRAM_CHAT_ID_{i}")
        if not extra:
            break
        recipients.append((f"Mottagare {i}", extra))
        i += 1

    return recipients


def send_telegram_report(report_text: str) -> bool:
    """
    Skickar rapporten till alla konfigurerade Telegram-mottagare.

    Läser token och chat-ID:n från miljövariabler automatiskt.
    Misslyckas tyst om Telegram inte är konfigurerat.

    Returns
    -------
    bool
        True om minst en mottagare fick rapporten.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[Notifier] TELEGRAM_BOT_TOKEN saknas — ingen notis skickad.")
        return False

    recipients = _get_all_recipients()
    if not recipients:
        print("[Notifier] Inga TELEGRAM_CHAT_ID:n konfigurerade — ingen notis skickad.")
        return False

    header       = "📊 *Guldanalys — veckorapport*\n\n"
    full_message = header + report_text
    parts        = _split_message(full_message)
    total_parts  = len(parts)

    print(f"[Notifier] Skickar till {len(recipients)} mottagare ({total_parts} del/ar)...")

    any_success = False
    for label, chat_id in recipients:
        success = True
        for i, part in enumerate(parts, start=1):
            text = (f"_(Del {i}/{total_parts})_\n\n" + part) if total_parts > 1 else part
            ok   = _send_to_one(token, chat_id, text)
            if not ok:
                success = False
        status = "OK" if success else "MISSLYCKADES"
        print(f"[Notifier] {label} ({chat_id[:6]}...): {status}")
        if success:
            any_success = True

    return any_success
