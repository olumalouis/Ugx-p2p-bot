import os, asyncio, aiohttp
from telegram import Bot
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MIN_GAP = 70.0
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
FILTER = ["airtel", "mtn", "airtime", "mobile"]

last_data = {"gap":0, "buy":0, "sell":0, "scans":0}

async def get_offers(type_):
    try:
        payload = {"asset":"USDT","fiat":"UGX","merchantCheck":False,"page":1,"rows":10,"tradeType":type_,"payTypes":[]}
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                j = await r.json()
                out=[]
                for i in j.get("data",[])[:10]:
                    adv=i.get("adv",{})
                    price=float(adv.get("price",0))
                    methods=" ".join([m.get("tradeMethodName","").lower() for m in adv.get("tradeMethods",[])])
                    if any(f in methods for f in FILTER):
                        out.append({"price":price,"name":i.get("advertiser",{}).get("nickName",""),"pay":methods})
                return out
    except:
        return []

async def price_cmd(update, context):
    await update.message.reply_text("Scanning...")
    buys = await get_offers("BUY")
    sells = await get_offers("SELL")
    if not buys or not sells:
        await update.message.reply_text("No data, try again")
        return
    best_buy = min(buys, key=lambda x:x["price"])
    best_sell = max(sells, key=lambda x:x["price"])
    gap = best_sell["price"] - best_buy["price"]
    last_data["gap"]=gap
    last_data["buy"]=best_buy["price"]
    last_data["sell"]=best_sell["price"]
    await update.message.reply_text(f"BUY cheapest: {best_buy['price']} ({best_buy['name']})\nSELL highest: {best_sell['price']} ({best_sell['name']})\n\nGAP: {gap:.2f} UGX\nProfit $100 = {gap*100:.0f} UGX\n\nFilter: Airtel+MTN+Airtime")

async def status_cmd(update, context):
    await update.message.reply_text(f"Bot OK\nGap: {last_data['gap']}\nBuy: {last_data['buy']}\nSell: {last_data['sell']}\nScans: {last_data['scans']}")

async def loop_check(bot):
    while True:
        try:
            buys = await get_offers("BUY")
            sells = await get_offers("SELL")
            if buys and sells:
                best_buy = min(buys, key=lambda x:x["price"])
                best_sell = max(sells, key=lambda x:x["price"])
                gap = best_sell["price"] - best_buy["price"]
                last_data["gap"]=gap
                last_data["scans"]+=1
                if gap >= MIN_GAP:
                    await bot.send_message(chat_id=CHAT_ID, text=f"🚀 GAP {gap:.2f} UGX!\nBuy {best_buy['price']} | Sell {best_sell['price']}\n$100 profit = {gap*100:.0f} UGX")
        except:
            pass
        await asyncio.sleep(120)

async def start_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    asyncio.create_task(loop_check(app.bot))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(start_app())
