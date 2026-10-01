from flask import Flask
import threading, requests, time, telebot, os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PORT = int(os.environ.get("PORT", 8000))

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

last_check_time = "Never"
last_gap = 0
last_error = "None"
scan_count = 0

@app.route('/')
def home():
    return f"Bot is Live! Last check: {last_check_time} | Gap: {last_gap}"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "✅ UGX P2P Bot is Active!\nMode: PAIR MODE - 1 Buy + 1 Sell\nCommands:\n/start\n/price\n/status")

@bot.message_handler(commands=['price'])
def price_cmd(message):
    bot.reply_to(message, "⏳ Checking market...")
    try:
        signal = format_signal(check_only=True)
        if signal:
            bot.send_message(message.chat.id, signal, disable_web_page_preview=True)
        else:
            bot.reply_to(message, "❌ No data from Binance, try again")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['status'])
def status_cmd(message):
    status_msg = f"🤖 BOT HEALTH\nMode: PAIR MODE\nLast check: {last_check_time}\nLast GAP: {last_gap:.2f} UGX\nTotal scans: {scan_count}\nLast error: {last_error}\nStatus: Running ✅"
    bot.reply_to(message, status_msg)

def get_offers(trade, pay_types):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {"asset":"USDT","fiat":"UGX","tradeType":trade,"page":1,"rows":10,"payTypes":pay_types}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r['data']
    except:
        return []

def format_signal(check_only=False):
    global last_check_time, last_gap, last_error, scan_count
    try:
        buy_offers = get_offers("BUY", ["AirtelMoney", "MTNMobileMoney"])
        sell_offers = get_offers("SELL", ["AirtelMoney", "MTNMobileMoney"])
        scan_count += 1
        last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not buy_offers or not sell_offers:
            last_error = "Binance returned empty"
            return None

        buy_sorted = sorted(buy_offers, key=lambda x: float(x['adv']['price']))
        sell_sorted = sorted(sell_offers, key=lambda x: float(x['adv']['price']), reverse=True)

        best_buy = buy_sorted[0]
        best_sell = sell_sorted[0]
        gap = float(best_sell['adv']['price']) - float(best_buy['adv']['price'])
        last_gap = gap
        last_error = "None"

        if gap < 80 and not check_only:
            return None

        def get_info(data):
            adv = data['adv']
            user = data['advertiser']
            return {
                "price": adv['price'],
                "min": adv['minSingleTransAmount'],
                "max": adv['maxSingleTransAmount'],
                "avail": adv['surplusAmount'],
                "nick": user['nickName'],
                "orders": user['monthOrderCount'],
                "rate": int(float(user['monthFinishRate'])*100),
                "link": f"https://p2p.binance.com/en/adDetail?adId={adv['advNo']}"
            }

        pairs = []
        for i in range(min(2, len(buy_sorted), len(sell_sorted))):
            b = get_info(buy_sorted[i])
            s = get_info(sell_sorted[i])
            g = float(s['price']) - float(b['price'])
            pairs.append((b,s,g))

        msg = f"🔥 GAP {gap:.0f} UGX | {len(pairs)} PAIRS FOUND 🔥\n\n"

        for idx, (b,s,g) in enumerate(pairs, 1):
            msg += f"--- PAIR {idx} | GAP {g:.0f} UGX ---\n"
            msg += f"BUY @ {b['price']} | {b['nick']} ({b['orders']} orders {b['rate']}%)\n"
            msg += f"Limit {b['min']}-{b['max']} | Avail {b['avail']}\n"
            msg += f"{b['link']}\n\n"
            msg += f"SELL @ {s['price
