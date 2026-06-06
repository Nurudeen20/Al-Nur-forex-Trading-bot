# ⚡ Forex Signal Bot

Sends real BUY/SELL signals to your Telegram using:
- EMA 9/21 Crossover
- RSI (14) Filter
- MACD Confirmation
- ATR-based Stop Loss & Take Profit

Pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD, NZDUSD

---

## 🚀 SETUP GUIDE (Step by Step)

---

### STEP 1 — Create Your Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Give it a name e.g. `My Forex Signals`
4. Give it a username e.g. `myforexsignals_bot`
5. BotFather gives you a **TOKEN** — copy and save it
   Example: `7123456789:AAFxxxxxxxxxxxxxxxxxxxxx`

---

### STEP 2 — Get Your Chat ID

1. Search for **@userinfobot** on Telegram
2. Send `/start`
3. It replies with your **Chat ID** — copy it
   Example: `123456789`

   > OR create a Telegram channel, add your bot as admin,
   > and use the channel's Chat ID (starts with -100...)

---

### STEP 3 — Push Code to GitHub

1. Create a free account at https://github.com
2. Create a **New Repository** (call it `forex-signal-bot`)
3. Upload these files:
   - bot.py
   - requirements.txt
   - Procfile
4. Commit and push

---

### STEP 4 — Deploy on Railway

1. Go to https://railway.app and sign up (free)
2. Click **New Project → Deploy from GitHub repo**
3. Select your `forex-signal-bot` repo
4. Go to **Variables** tab and add these:

   | Key | Value |
   |-----|-------|
   | `TELEGRAM_TOKEN` | your token from BotFather |
   | `CHAT_ID` | your chat ID from Step 2 |
   | `INTERVAL` | `15` (scan every 15 mins) |

5. Railway auto-detects the Procfile and starts the bot
6. Check **Logs** tab — you should see `🚀 Bot starting...`

---

### STEP 5 — Test It

Open your Telegram bot and send:
- `/start` — welcome message
- `/status` — confirms bot is alive
- `/scan` — forces an instant scan right now
- `/pairs` — lists all active pairs

---

## 📲 Signal Format

When a signal fires, you'll get this in Telegram:

```
🟢 BUY SIGNAL 📈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💱 Pair:       EURUSD
💰 Entry:      1.08423
🛑 Stop Loss:  1.08201
🎯 TP1:        1.08645
🎯 TP2:        1.08867
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RSI:        52.3
📉 MACD Hist:  0.00021
💡 Strength:   🔥 Strong
⏰ Time:       14:32 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Look for LONG entry on MT5
⚠️ Use 1–2% risk per trade.
```

---

## ⚠️ Risk Management Rules

- Never risk more than **1–2% of your account** per trade
- Always use the **Stop Loss** provided
- TP1 = safe exit, TP2 = let it run
- Signals are strongest during **London (8AM–12PM UTC)** and **New York (1PM–5PM UTC)** sessions
- Avoid trading during **major news events** (NFP, FOMC etc.)

---

## 🛠 Customisation

Edit `bot.py` to change:
- `PAIRS` — add/remove forex pairs
- `INTERVAL` — how often to scan (in Railway Variables)
- `mult` — ATR multiplier for SL/TP (default 1.5)

---

## ❗ Disclaimer

This bot is for educational purposes. Forex trading involves
significant risk. Past signals do not guarantee future results.
Always practice on a **demo account** before going live.
