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
    bot.reply_to(message, "✅ UGX P2P Bot is Active!\nMode: ANY AMOUNT - Blank filter\nScanning: Airtel + MTN every 2 min\nCommands:\n/start - Check bot\n/price - Current price now\n/status - Bot health")

@bot.message_handler(commands=['price'])
def price_cmd(message):
    bot.reply_to(message, "⏳ Checking market (ANY AMOUNT mode)...")
    try:
        buy_offers = get_offers("BUY", ["AirtelMoney", "MTNMobileMoney"])
        sell_offers = get_offers("SELL", ["AirtelMoney", "MTNMobileMoney"])
        if buy_offers and sell_offers:
            buy_price = float(sorted(buy_offers, key=lambda x: float(x['adv']['price']))[0]['adv']['price'])
            sell_price = float(sorted(sell_offers, key=lambda x: float(x['adv']['price']), reverse=True)[0]['adv']['price'])
            gap = sell_price - buy_price
            signal = format_signal(check_only=True)
            if signal:
                bot.send_message(message.chat.id, signal, disable_web_page_preview=True)
            else:
                bot.send_message(message.chat.id, "❌ No signal formatted")
        else:
            bot.reply_to(message, "❌ Could not fetch Binance now")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['status'])
def status_cmd(message):
    status_msg = f"🤖 BOT HEALTH\n\nMode: BLANK (Any Amount)\nLast check: {last_check_time}\nLast GAP: {last_gap:.2f} UGX\nTotal scans: {scan_count}\nLast error: {last_error}\nStatus: Running ✅"
    bot.reply_to(message, status_msg)

def get_offers(trade, pay_types):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    # BLANK MODE: no amount = show all merchants
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

        buy_price = float(best_buy['adv']['price'])
        sell_price = float(best_sell['adv']['price'])
        gap = sell_price - buy_price
        last_gap = gap
        last_error = "None"

        if gap < 80 and not check_only:
            return None

        def format_one(data, trade_type):
            adv = data['adv']
            user = data['advertiser']
            price = adv['price']
            surplus = adv['surplusAmount']
            min_lim = adv['minSingleTransAmount']
            max_lim = adv['maxSingleTransAmount']
            pay_name = adv['tradeMethods'][0]['tradeMethodName'] if adv.get('tradeMethods') else "Mobile Money"
            nick = user['nickName']
            month_orders = user['monthOrderCount']
            finish_rate = user['monthFinishRate']*100
            user_no = user['userNo']
            adv_no = adv['advNo']
            merchant_link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={user_no}"
            trade_link = f"https://p2p.binance.com/en/adDetail?adId={adv_no}"
            return (f"{trade_type} {price} UGX | {pay_name}\n"
                    f"👤 {nick} | {month_orders} orders {finish_rate:.0f}%\n"
                    f"💰 Limit: {min_lim} - {max_lim} UGX | Avail: {surplus} USDT\n"
                    f"🔗 Trade: {trade_link}\n\n")

        msg = f"🔥 GAP {gap:.2f} UGX | ANY AMOUNT MODE 🔥\n\nBUY OFFERS (cheapest first):\n"
        for offer in buy_sorted[:2]:
            msg += format_one(offer, "Buy @")
        msg += f"SELL OFFERS (highest first):\n"
        for offer in sell_sorted[:3]:
            msg += format_one(offer, "Sell @")
        msg += f"💡 You can trade ANY amount you have.\nCheck if your balance fits inside Limit above.\n💰 If you trade $20 profit ~{gap*20:,.0f} UGX | $100 profit ~{gap*100:,.0f} UGX\n"
        msg += f"P2P: https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
        return msg
    except Exception as e:
        last_error = str(e)
        print(f"Error: {e}")
        return None

def scanner():
    while True:
        try:
            signal = format_signal()
            if signal:
                bot.send_message(CHAT_ID, signal, disable_web_page_preview=True)
        except Exception as e:
            print(f"Error scanner: {e}")
        time.sleep(120)

def run_bot():
    bot.infinity_polling()

threading.Thread(target=scanner, daemon=True).start()
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
