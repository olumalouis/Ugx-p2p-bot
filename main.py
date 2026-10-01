from flask import Flask
from threading import Thread
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Web server for Render FREE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "UGX P2P Bot is Live 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- Telegram Bot ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🇺🇬 Welcome to UGX P2P Scanner Bot!\n\nUse /scan to find best USDT/UGX prices on Binance P2P")

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Binance P2P for UGX...")
    
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": "USDT",
        "fiat": "UGX",
        "tradeType": "BUY",
        "page": 1,
        "rows": 5,
        "payTypes": [],
        "publisherType": None
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        ads = data.get('data', [])
        
        if not ads:
            await update.message.reply_text("No offers found now.")
            return
            
        msg = "💰 *Top UGX P2P Offers (BUY USDT):*\n\n"
        for i, ad in enumerate(ads[:5], 1):
            adv = ad['adv']
            price = adv['price']
            nick = ad['advertiser']['nickName']
            msg += f"{i}. {price} UGX - {nick}\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error scanning: {e}")

# Start bot
if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN missing!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("scan", scan_command))
        print("Bot started...")
        application.run_polling()
