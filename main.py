from flask import Flask
import threading, requests, time, telebot, os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/')
def home():
    return "Bot is Live!"

def get_price(trade):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {"asset":"USDT","fiat":"UGX","tradeType":trade,"page":1,"rows":1,"payTypes":["AirtelMoney"]}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return float(r['data'][0]['adv']['price'])
    except:
        return None

def scanner():
    while True:
        buy = get_price("BUY")
        sell = get_price("SELL")
        if buy and sell:
            gap = sell - buy
            if gap >= 80:
                try:
                    bot.send_message(CHAT_ID, f"🚨 GAP {gap:.0f} UGX\nBUY:{buy:.0f} SELL:{sell:.0f}")
                except: pass
        time.sleep(30)

threading.Thread(target=scanner, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
