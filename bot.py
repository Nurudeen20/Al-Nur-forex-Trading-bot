import os
import asyncio
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVAL = int(os.getenv("INTERVAL", "15"))

PAIRS = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "AUDUSD": ("AUD", "USD"),
    "USDCHF": ("USD", "CHF"),
}

price_history = {pair: [] for pair in PAIRS}
last_signals = {}

def get_price(from_cur, to_cur):
    try:
        url = f"https://api.frankfurter.app/latest?from={from_cur}&to={to_cur}"
        r = requests.get(url, timeout=10)
        data = r.json()
        return data["rates"][to_cur]
    except:
        return None

def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    e = prices[0]
    for p in prices:
        e = p * k + e * (1 - k)
    return e

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(len(prices) - period, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyse(pair_name, from_cur, to_cur):
    price = get_price(from_cur, to_cur)
    if not price:
        return None
    history = price_history[pair_name]
    history.append(price)
    if len(history) > 50:
        history.pop(0)
    if len(history) < 25:
        return None
    e9 = ema(history, 9)
    e21 = ema(history, 21)
    r = rsi(history)
    if not e9 or not e21:
        return None
    prev = history[:-1]
    pe9 = ema(prev, 9)
    pe21 = ema(prev, 21)
    if not pe9 or not pe21:
        return None
    cross_up = pe9 <= pe21 and e9 > e21
    cross_down = pe9 >= pe21 and e9 < e21
    if cross_up and r < 70:
        direction = "BUY"
    elif cross_down and r > 30:
        direction = "SELL"
    else:
        return None
    if last_signals.get(pair_name) == direction:
        return None
    last_signals[pair_name] = direction
    sl_pips = price * 0.002
    tp_pips = price * 0.003
    if direction == "BUY":
        sl = round(price - sl_pips, 5)
        tp1 = round(price + tp_pips, 5)
        tp2 = round(price + tp_pips * 2, 5)
    else:
        sl = round(price + sl_pips, 5)
        tp1 = round(price - tp_pips, 5)
        tp2 = round(price - tp_pips * 2, 5)
    score = sum([
        True,
        (direction == "BUY" and r < 55) or (direction == "SELL" and r > 45),
    ])
    strength = ["💪 Moderate", "🔥 Strong", "🚀 Very Strong"][min(score, 2)]
    return {
        "pair": pair_name,
        "direction": direction,
        "price": round(price, 5),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rsi": round(r, 1),
        "strength": strength,
        "time": datetime.utcnow().strftime("%H:%M UTC"),
    }

def format_signal(s):
    header = "🟢 *BUY SIGNAL* 📈" if s["direction"] == "BUY" else "🔴 *SELL SIGNAL* 📉"
    action = "Look for LONG entry" if s["direction"] == "BUY" else "Look for SHORT entry"
    return (
        f"{header}\n"
        f"{'━' * 28}\n"
        f"💱 *Pair:*      `{s['pair']}`\n"
        f"💰 *Entry:*     `{s['price']}`\n"
        f"🛑 *Stop Loss:* `{s['sl']}`\n"
        f"🎯 *TP1:*       `{s['tp1']}`\n"
        f"🎯 *TP2:*       `{s['tp2']}`\n"
        f"{'━' * 28}\n"
        f"📊 *RSI:*       {s['rsi']}\n"
        f"💡 *Strength:*  {s['strength']}\n"
        f"⏰ *Time:*      {s['time']}\n"
        f"{'━' * 28}\n"
        f"🔔 _{action} on MT5_\n"
        f"⚠️ _Use 1-2% risk per trade. Not financial advice._"
    )

async def scan_and_alert(bot):
    log.info("Scanning pairs...")
    for pair_name, (from_cur, to_cur) in PAIRS.items():
        result = analyse(pair_name, from_cur, to_cur)
        if result:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=format_signal(result),
                parse_mode=ParseMode.MARKDOWN
            )
            log.info(f"Signal sent: {pair_name} {result['direction']}")
        await asyncio.sleep(1)

async def run_scanner(app):
    await asyncio.sleep(5)
    await app.bot.send_message(
        chat_id=CHAT_ID,
        text=(
            "⚡ *Al-Nur Forex Signal Bot is LIVE!*\n"
            f"Scanning: {', '.join(PAIRS.keys())}\n"
            f"Interval: every {INTERVAL} minutes\n"
            "Strategy: EMA 9/21 + RSI Filter\n\n"
            "Commands: /status · /pairs · /scan"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    while True:
        await scan_and_alert(app.bot)
        await asyncio.sleep(INTERVAL * 60)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Al-Nur Forex Signal Bot*\n\n"
        "/status — check bot status\n"
        "/pairs — list active pairs\n"
        "/scan — force instant scan",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"✅ Bot is running\n"
        f"⏱ Interval: {INTERVAL} min\n"
        f"💱 Pairs: {len(PAIRS)}\n"
        f"📡 Last signals: {last_signals or 'None yet'}"
    )

async def cmd_pairs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pairs_list = "\n".join(f"• {p}" for p in PAIRS.keys())
    await update.message.reply_text(
        f"📊 *Active Pairs:*\n{pairs_list}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning now...")
    await scan_and_alert(ctx.bot)
    await update.message.reply_text("✅ Scan complete!")

async def post_init(application):
    asyncio.ensure_future(run_scanner(application))

def main():
    if not TOKEN or not CHAT_ID:
        raise ValueError("Set TELEGRAM_TOKEN and CHAT_ID!")
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("pairs", cmd_pairs))
    application.add_handler(CommandHandler("scan", cmd_scan))
    log.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
