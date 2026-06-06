"""
==============================================
  FOREX SIGNAL BOT — Powered by EMA + RSI + MACD
  Sends real BUY/SELL signals to your Telegram
==============================================
"""

import os
import asyncio
import logging
from datetime import datetime
import yfinance as yf
import pandas as pd
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── CONFIG (set these in Railway environment variables) ───────────────────────
TOKEN     = os.getenv("TELEGRAM_TOKEN")   # Your bot token from @BotFather
CHAT_ID   = os.getenv("CHAT_ID")         # Your Telegram chat/channel ID
INTERVAL  = int(os.getenv("INTERVAL", "15"))   # Scan every X minutes (default 15)

# ── FOREX PAIRS ───────────────────────────────────────────────────────────────
PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCHF": "USDCHF=X",
    "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
}

# Track last signal per pair to avoid duplicates
last_signals = {}


# ── INDICATOR CALCULATIONS ────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series):
    e12    = ema(series, 12)
    e26    = ema(series, 26)
    line   = e12 - e26
    signal = ema(line, 9)
    hist   = line - signal
    return line, signal, hist

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ── SIGNAL DETECTION ──────────────────────────────────────────────────────────

def analyse(pair_name: str, ticker: str) -> dict | None:
    try:
        df = yf.download(ticker, period="5d", interval="15m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 40:
            log.warning(f"{pair_name}: not enough data")
            return None

        close = df["Close"].squeeze()

        ema9  = ema(close, 9)
        ema21 = ema(close, 21)
        rsi14 = rsi(close, 14)
        _, _, hist = macd(close)
        atr14 = atr(df, 14)

        # Last two candles for crossover detection
        p_e9, p_e21 = ema9.iloc[-2], ema21.iloc[-2]
        c_e9, c_e21 = ema9.iloc[-1], ema21.iloc[-1]

        price     = float(close.iloc[-1])
        cur_rsi   = float(rsi14.iloc[-1])
        cur_hist  = float(hist.iloc[-1])
        cur_atr   = float(atr14.iloc[-1])

        cross_up   = (p_e9 <= p_e21) and (c_e9 > c_e21)
        cross_down = (p_e9 >= p_e21) and (c_e9 < c_e21)

        # Signal rules
        if cross_up and cur_rsi < 70 and cur_hist > 0:
            direction = "BUY"
        elif cross_down and cur_rsi > 30 and cur_hist < 0:
            direction = "SELL"
        else:
            return None

        # Avoid repeating the same signal
        if last_signals.get(pair_name) == direction:
            return None
        last_signals[pair_name] = direction

        # SL / TP using ATR (1.5× ATR for SL, 1.5× and 3× for TP)
        mult = 1.5
        if direction == "BUY":
            sl  = round(price - cur_atr * mult, 5)
            tp1 = round(price + cur_atr * mult, 5)
            tp2 = round(price + cur_atr * mult * 2, 5)
        else:
            sl  = round(price + cur_atr * mult, 5)
            tp1 = round(price - cur_atr * mult, 5)
            tp2 = round(price - cur_atr * mult * 2, 5)

        # Signal strength score (0–3)
        score = sum([
            True,                                                          # crossover always counts
            (direction == "BUY" and cur_rsi < 55) or
            (direction == "SELL" and cur_rsi > 45),                        # clean RSI
            (direction == "BUY" and cur_hist > 0) or
            (direction == "SELL" and cur_hist < 0),                        # MACD confirms
        ])
        strength = ["⚡ Weak", "💪 Moderate", "🔥 Strong", "🚀 Very Strong"][score]

        return {
            "pair":      pair_name,
            "direction": direction,
            "price":     round(price, 5),
            "sl":        sl,
            "tp1":       tp1,
            "tp2":       tp2,
            "rsi":       round(cur_rsi, 1),
            "hist":      round(cur_hist, 5),
            "strength":  strength,
            "time":      datetime.utcnow().strftime("%H:%M UTC"),
        }

    except Exception as e:
        log.error(f"{pair_name} error: {e}")
        return None


# ── MESSAGE FORMATTING ────────────────────────────────────────────────────────

def format_signal(s: dict) -> str:
    if s["direction"] == "BUY":
        header = "🟢 *BUY SIGNAL* 📈"
        action = "Look for LONG entry"
    else:
        header = "🔴 *SELL SIGNAL* 📉"
        action = "Look for SHORT entry"

    return (
        f"{header}\n"
        f"{'━' * 28}\n"
        f"💱 *Pair:*       `{s['pair']}`\n"
        f"💰 *Entry:*      `{s['price']}`\n"
        f"🛑 *Stop Loss:*  `{s['sl']}`\n"
        f"🎯 *TP1:*        `{s['tp1']}`\n"
        f"🎯 *TP2:*        `{s['tp2']}`\n"
        f"{'━' * 28}\n"
        f"📊 *RSI:*        {s['rsi']}\n"
        f"📉 *MACD Hist:*  {s['hist']}\n"
        f"💡 *Strength:*   {s['strength']}\n"
        f"⏰ *Time:*       {s['time']}\n"
        f"{'━' * 28}\n"
        f"🔔 _{action} on MT5_\n"
        f"⚠️ _Use 1–2% risk per trade. Not financial advice._"
    )


# ── SCANNER LOOP ──────────────────────────────────────────────────────────────

async def scan_and_alert(bot: Bot):
    log.info("🔍 Scanning all pairs...")
    found = 0
    for pair_name, ticker in PAIRS.items():
        result = analyse(pair_name, ticker)
        if result:
            msg = format_signal(result)
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN
            )
            log.info(f"✅ Signal sent: {pair_name} {result['direction']}")
            found += 1
            await asyncio.sleep(1)  # small delay between messages

    if found == 0:
        log.info("No new signals this scan.")


async def run_scanner(app: Application):
    """Runs the scanner loop every INTERVAL minutes."""
    await asyncio.sleep(5)  # small startup delay
    bot = app.bot
    await bot.send_message(
        chat_id=CHAT_ID,
        text=(
            "⚡ *Forex Signal Bot is LIVE!*\n"
            f"Scanning: {', '.join(PAIRS.keys())}\n"
            f"Interval: every {INTERVAL} minutes\n"
            "Strategy: EMA9/21 Crossover + RSI + MACD\n\n"
            "Use /status to check · /pairs to list pairs · /stop to pause"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    while True:
        await scan_and_alert(bot)
        await asyncio.sleep(INTERVAL * 60)


# ── TELEGRAM COMMANDS ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Forex Signal Bot*\n\n"
        "Commands:\n"
        "/status — bot health check\n"
        "/pairs — list active pairs\n"
        "/scan — force an instant scan\n\n"
        "Signals fire automatically every scan interval.",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"✅ Bot is running\n"
        f"⏱ Scan interval: {INTERVAL} min\n"
        f"💱 Pairs: {len(PAIRS)}\n"
        f"📡 Last signals: {last_signals or 'None yet'}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_pairs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pairs_list = "\n".join(f"• {p}" for p in PAIRS.keys())
    await update.message.reply_text(
        f"📊 *Active Pairs:*\n{pairs_list}",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Running instant scan...")
    await scan_and_alert(ctx.bot)
    await update.message.reply_text("✅ Scan complete.")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN or not CHAT_ID:
        raise ValueError("❌ Set TELEGRAM_TOKEN and CHAT_ID in environment variables!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pairs",  cmd_pairs))
    app.add_handler(CommandHandler("scan",   cmd_scan))

    # Start scanner as background task
    app.post_init = lambda a: asyncio.ensure_future(run_scanner(a))

    log.info("🚀 Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
