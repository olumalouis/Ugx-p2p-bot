import os
import asyncio
import aiohttp
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MIN_GAP = float(os.getenv("MIN_GAP", "70"))

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
ALLOWED_PAYMENTS = ["airtel", "mtn", "airtime", "m-pesa", "mobile money"]

status_data = {
    "last_gap": 0,
    "total_scans": 0,
    "last_error": "None",
    "best_buy": 0,
    "best_sell": 0
}

async def fetch_offers(trade_type):
    payload = {
        "asset": "USDT",
        "fiat": "UGX",
        "merchantCheck": False,
        "page": 1,
        "rows": 20,
        "tradeType": trade_type,
        "payTypes": []
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(BINANCE_P2P_URL, json=payload, timeout=15) as resp:
                data = await resp.json()
                offers = []
                for item in data.get("data", []):
                    adv = item.get("adv", {})
                    advertiser = item.get("advertiser", {})
                    price = float(adv.get("price", 0))
                    pay_methods = [p.get("tradeMethodName","").lower() for p in adv.get("tradeMethods", [])]
                    pay_str = " ".join(pay_methods)
                    if any(a in pay_str for a in ALLOWED_PAYMENTS):
                        offers.append({
                            "price": price,
                            "name": advertiser.get("nickName",""),
                            "pay": ", ".join([p.get("tradeMethodName","") for p in adv.get("tradeMethods", [])]),
                            "limit": f"{adv.get('minSingleTransAmount')} - {adv.get('maxSingleTransAmount')}",
                        })
                return offers
    except Exception as e:
        status_data["last_error"] = str(e)[:200]
        return []

async def check_gap(app):
    while True:
        try:
            buy_offers = await fetch_offers("BUY")
            sell_offers = await fetch_offers("SELL")
            if buy_offers and sell_offers:
                best_buy = sorted(buy_offers, key=lambda x: x["price"])[0]
                best_sell = sorted(sell_offers, key=lambda x: x["price"], reverse=True)[0]
                gap = best_sell["price"] - best_buy["price"]
                status_data["last_gap"] = round(gap, 2)
                status_data["best_buy"] = best_buy["price"]
                status_data["best_sell"] = best_sell["price"]
                status_data["total_scans"] += 1
                status_data["last_error"] = "None"
                if gap >= MIN_GAP:
                    profit20 = gap * 20
                    profit100 = gap * 100
                    msg = f"""🚀 *UGX P2P ARBITRAGE ALERT* 🚀

*GAP: {gap:.2f} UGX*

*BUY CHEAP:*
👤 {best_buy['name']}
💰 {best_buy['price']} UGX
🏦 {best_buy['pay']}

*SELL HIGH:*
👤 {best_sell['name']}
💰 {best_sell['price']} UGX
🏦 {best_sell['pay']}

*PROFIT:*
$20 => {profit20:,.0f} UGX
$100 => {profit100:,.0f} UGX

[Open Binance P2P](https://p2p.binance.com/en/trade/BUY/USDT?fiat=UGX)
"""
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
            await asyncio.sleep(120)
        except Exception as e:
            status_data["last_error"] = str(e)[:200]
            await asyncio.sleep(30)

async def status_cmd(update, context):
    msg = f"✅ *Running*\n\n*GAP:* {status_data['last_gap']} UGX\n*BUY:* {status_data['best_buy']}\n*SELL:* {status_data['best_sell']}\n*Min:* {MIN_GAP}\n*Scans:* {status_data['total_scans']}\n*Error:* {status_data['last_error']}\n*Filters:* Airtel + MTN + Airtime"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def price_cmd(update, context):
    await update.message.reply_text("⏳ Scanning...")
    buy_offers = await fetch_offers("BUY")
    sell_offers = await fetch_offers("SELL")
    if not buy_offers or not sell_offers:
        await update.message.reply_text(f"No offers. Error: {status_data['last_error']}")
        return
    buy_sorted = sorted(buy_offers, key=lambda x: x["price"])[:3]
    sell_sorted = sorted(sell_offers, key=lambda x: x["price"], reverse=True)[:3]
    gap = sell_sorted[0]["price"] - buy_sorted[0]["price"]
    text = f"*Current (Airtel+MTN+Airtime):*\n\n*BUY CHEAP:*\n"
    for o in buy_sorted:
        text += f"- {o['price']} | {o['name']} | {o['pay']}\n"
    text += f"\n*SELL HIGH:*\n"
    for o in sell_sorted:
        text += f"- {o['price']} | {o['name']} | {o['pay']}\n"
    text += f"\n*GAP: {gap:.2f} UGX* | $100 = {gap*100:,.0f} UGX"
    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.job_queue.run_once(lambda ctx: asyncio.create_task(check_gap(app)), when=1)
    print(f"Bot started MIN_GAP={MIN_GAP}")
    app.run_polling()

if __name__ == "__main__":
    main()
