from flask import Flask
from threading import Thread
import os
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
Thread(target=run_web, daemon=True).start()import os, time, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

app = Flask(__name__)
@app.route('/')
def home(): return "UGX Bot Live 24/7"

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning UGX P2P now...")
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    def get_price(t):
        try:
            r=requests.post(url, json={"asset":"USDT","fiat":"UGX","tradeType":t,"page":1,"rows":1}, timeout=10).json()
            return float(r['data'][0]['adv']['price'])
        except: return None
    buy=get_price("BUY"); sell=get_price("SELL")
    if buy and sell:
        gap=abs(sell-buy); profit=gap*20
        status="✅ GOOD" if gap>=100 and profit>=4000 else "❌ NO PROFIT"
        await update.message.reply_text(f"{status}\nBUY: {buy} UGX\nSELL: {sell} UGX\nGap: {gap:.0f} UGX\nProfit on $20: {profit:.0f} UGX")
    else:
        await update.message.reply_text("Error fetching prices")

def run_flask():
    app.run(host="0.0.0.0", port=10000)

def run_bot():
    if not TOKEN:
        print("No TOKEN"); return
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("scan", scan_command))
    bot_app.add_handler(CommandHandler("start", scan_command))
    print("Bot polling...")
    bot_app.run_polling()

threading.Thread(target=run_flask, daemon=True).start()
run_bot()
