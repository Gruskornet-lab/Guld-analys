# Installationsguide — Automatiska Telegram-notiser

Den här guiden tar dig igenom hela uppsättningen steg för steg.
Beräknad tid: 20–30 minuter.

---

## Steg 1: Skapa ett GitHub-konto (om du inte har ett)

1. Gå till https://github.com och klicka "Sign up"
2. Välj det gratis alternativet — det räcker mer än väl

---

## Steg 2: Ladda upp projektet till GitHub

1. Logga in på GitHub
2. Klicka på "+" uppe till höger → "New repository"
3. Namn: `gold-analysis` (eller vad du vill)
4. Välj **Private** (så att dina API-nycklar inte syns publikt)
5. Klicka "Create repository"

Ladda sedan upp filerna. Enklaste sättet är via GitHub Desktop:
- Ladda ner GitHub Desktop: https://desktop.github.com
- Välj "Add existing repository" och peka på din gold-analysis-mapp
- Commita och pusha alla filer

---

## Steg 3: Skapa en Telegram-bot (tar 2 minuter)

### 3a. Skapa boten
1. Öppna Telegram-appen på telefonen
2. Sök efter **@BotFather** och starta en chatt
3. Skriv: `/newbot`
4. BotFather frågar efter ett namn — skriv t.ex. `Gold Analysis Bot`
5. BotFather frågar efter ett användarnamn — skriv t.ex. `goldanalysis_mittnamn_bot`
   (måste sluta på `bot` och vara unikt)
6. Du får tillbaka en token som ser ut så här:
   `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`
   **Spara denna — det är din TELEGRAM_BOT_TOKEN**

### 3b. Hitta ditt Chat-ID
1. Starta en chatt med din nya bot (klicka på länken BotFather ger dig)
2. Skicka ett valfritt meddelande, t.ex. "hej"
3. Öppna den här länken i webbläsaren (byt ut TOKEN mot din riktiga token):
   `https://api.telegram.org/botTOKEN/getUpdates`
4. I svaret, hitta `"chat":{"id":` — numret efter är ditt **TELEGRAM_CHAT_ID**
   Det ser ut som: `123456789`

---

## Steg 4: Lägg till API-nycklar som GitHub Secrets

Secrets lagras krypterat i GitHub — de syns aldrig i koden eller loggarna.

1. Gå till ditt GitHub-repo
2. Klicka på **Settings** (inställningar) → **Secrets and variables** → **Actions**
3. Klicka **"New repository secret"** och lägg till dessa tre:

| Namn                 | Värde                              |
|----------------------|------------------------------------|
| `ANTHROPIC_API_KEY`  | Din Anthropic API-nyckel (sk-ant-...) |
| `TELEGRAM_BOT_TOKEN` | Token från BotFather               |
| `TELEGRAM_CHAT_ID`   | Ditt Telegram-användar-ID          |

Hämta din Anthropic API-nyckel på: https://console.anthropic.com

---

## Steg 5: Testa att allt fungerar

1. Gå till ditt GitHub-repo
2. Klicka på fliken **"Actions"**
3. Klicka på workflowen "Weekly Gold Analysis" i listan till vänster
4. Klicka på **"Run workflow"** → **"Run workflow"** (grön knapp)
5. Vänta 1–2 minuter
6. Kolla din Telegram — rapporten ska dyka upp som ett meddelande!

Om något går fel: klicka på körningen i Actions-fliken för att se felloggen.

---

## Automatisk körning

När allt fungerar kör GitHub Actions automatiskt varje **måndag kl 07:30**
(vintertid, CET). Du behöver inte göra något — rapporten kommer till Telegram
av sig själv.

---

## Vanliga problem

**"Telegram-meddelandet kommer inte"**
→ Kontrollera att du skickade ett meddelande till boten i steg 3b
→ Verifiera att TELEGRAM_CHAT_ID är ett nummer, inte ett användarnamn

**"API-nyckelfel"**
→ Kontrollera att ANTHROPIC_API_KEY börjar med `sk-ant-`
→ Verifiera att du har krediter på https://console.anthropic.com

**"yfinance-fel"**
→ GitHub Actions har full internettillgång, detta ska fungera automatiskt
