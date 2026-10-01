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
    # SCAN BOTH PAYMENT METHODS
    buy_offers = get_offers("BUY", ["AirtelMoney", "MTNMobileMoney"])
    sell_offers = get_offers("SELL", ["AirtelMoney", "MTNMobileMoney"])

    if not buy_offers or not sell_offers:
        return None

    # Find best prices
    buy_offers_sorted = sorted(buy_offers, key=lambda x: float(x['adv']['price']))
    sell_offers_sorted = sorted(sell_offers, key=lambda x: float(x['adv']['price']), reverse=True)

    best_buy = buy_offers_sorted[0]
    best_sell = sell_offers_sorted[0]

    buy_price = float(best_buy['adv']['price'])
    sell_price = float(best_sell['adv']['price'])
    gap = sell_price - buy_price

    if gap < 80:
        return None

    def format_one(adv_data, trade_type):
        a = adv_data['adv']
        u = adv_data['advertiser']
        pay = ", ".join(a['tradeMethods'][0]['tradeMethodName'] if 'tradeMethods' in a else ["Mobile Money"])
        # Detect pay type
        pay_name = a['tradeMethods'][0]['tradeMethodName'] if a.get('tradeMethods') else "Mobile Money"
        return (f"Offer updated: {trade_type} USDT | {pay_name}\n"
                f"{a['price']} UGX per USDT\n"
                f"Available: {a['surplusAmount']} USDT\n"
                f"Limits: {a['minSingleTransAmount']}–{a['maxSingleTransAmount']} UGX\n"
                f"Merchant: {u['nickName']} | {u['monthOrderCount']} monthly orders | {u['monthFinishRate']*100:.1f}% completion\n"
                f"Binance P2P: https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX\n\n")

    msg = f"Binance P2P — USDT/UGX - GAP {gap:.2f} UGX\n\n"
    msg += f"Buy USDT | Airtel + MTN\n\n"
    for offer in buy_offers_sorted[:2]:
        msg += format_one(offer, "Buy")

    msg += f"Sell USDT | Airtel + MTN\n\n"
    for offer in sell_offers_sorted[:3]:
        msg += format_one(offer, "Sell")

    msg += f"💰 Profit on 100 USDT: ~{gap*100:,.0f} UGX"
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
