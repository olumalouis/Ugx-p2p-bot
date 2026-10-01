from flask import Flask
import threading, requests, time, telebot, os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PORT = int(os.environ.get("PORT", 8000))

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/')
def home():
    return "Bot is Live!"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "✅ UGX P2P Bot is Active!\nScanning: Airtel + MTN\nAlerts when GAP >= 80 UGX")

def get_offers(trade, pay_types):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {"asset":"USDT","fiat":"UGX","tradeType":trade,"page":1,"rows":5,"payTypes":pay_types}
    try:
        r = requests.post(url, json=payload, timeout=10).json()
        return r['data']
    except:
        return []

def format_signal():
    buy_offers = get_offers("BUY", ["AirtelMoney", "MTNMobileMoney"])
    sell_offers = get_offers("SELL", ["AirtelMoney", "MTNMobileMoney"])

    if not buy_offers or not sell_offers:
        return None

    buy_sorted = sorted(buy_offers, key=lambda x: float(x['adv']['price']))
    sell_sorted = sorted(sell_offers, key=lambda x: float(x['adv']['price']), reverse=True)

    best_buy = buy_sorted[0]
    best_sell = sell_sorted[0]

    buy_price = float(best_buy['adv']['price'])
    sell_price = float(best_sell['adv']['price'])
    gap = sell_price - buy_price

    if gap < 80:
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

        return (f"Offer updated: {trade_type} USDT | {pay_name}\n"
                f"Price: {price} UGX per USDT\n"
                f"Available: {surplus} USDT\n"
                f"Limits: {min_lim} - {max_lim} UGX\n"
                f"Merchant: {nick}\n"
                f"Stats: {month_orders} monthly orders | {finish_rate:.1f}% completion\n"
                f"Merchant Link: {merchant_link}\n"
                f"Direct Trade: {trade_link}\n\n")

    msg = f"🔥 Binance P2P — USDT/UGX - GAP {gap:.2f} UGX 🔥\n\n"
    msg += f"Buy USDT | Airtel + MTN\n\n"
    for offer in buy_sorted[:2]:
        msg += format_one(offer, "Buy")

    msg += f"Sell USDT | Airtel + MTN\n\n"
    for offer in sell_sorted[:3]:
        msg += format_one(offer, "Sell")

    msg += f"💰 Profit on 100 USDT: ~{gap*100:,.0f} UGX\n"
    msg += f"P2P Market: https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
    return msg

def scanner():
    while True:
        try:
            signal = format_signal()
            if signal:
                bot.send_message(CHAT_ID, signal, disable_web_page_preview=True)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)

def run_bot():
    bot.infinity_polling()

threading.Thread(target=scanner, daemon=True).start()
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
