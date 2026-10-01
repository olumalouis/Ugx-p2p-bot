import os, asyncio, aiohttp
from telegram import Bot
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MIN_GAP = 70.0
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
LINK = "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
FILTER = ["airtel", "mtn", "airtime", "mobile"]

last = {"gap":0, "buy":0, "sell":0, "scans":0}

async def get_offers(t):
    try:
        payload = {"asset":"USDT","fiat":"UGX","merchantCheck":False,"page":1,"rows":10,"tradeType":t,"payTypes":[]}
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                j = await r.json()
                out=[]
                for x in j.get("data",[])[:10]:
                    adv=x.get("adv",{})
                    price=float(adv.get("price",0))
                    min_a=adv.get("minSingleTransAmount","?")
                    max_a=adv.get("maxSingleTransAmount","?")
                    methods=" ".join([m.get("tradeMethodName","").lower() for m in adv.get("tradeMethods",[])])
                    if any(f in methods for f in FILTER):
                        out.append({"price":price,"name":x.get("advertiser",{}).get("nickName",""),"min":min_a,"max":max_a,"pay":methods})
                return out
    except:
        return []

async def price_cmd(update, context):
    await update.message.reply_text("Scanning Airtel/MTN...")
    buys = await get_offers("BUY")
    sells = await get_offers("SELL")
    if not buys or not sells:
        await update.message.reply_text("No data")
        return
    b = min(buys, key=lambda x:x["price"])
    s = max(sells, key=lambda x:x["price"])
    gap = s["price"] - b["price"]
    last["gap"]=gap
    await update.message.reply_text(
        f"💰 GAP: {gap:.2f} UGX\n\n"
        f"BUY: {b['price']} UGX\nSeller: {b['name']}\nLimit: {b['min']} - {b['max']} UGX\nPay: {b['pay']}\n\n"
        f"SELL: {s['price']} UGX\nBuyer: {s['name']}\nLimit: {s['min']} - {s['max']} UGX\nPay: {s['pay']}\n\n"
        f"Profit $100 = {gap*100:.0f} UGX\n\n"
        f"🔗 {LINK}"
    )

async def status_cmd(update, context):
    await update.message.reply_text(f"Bot OK\nGap: {last['gap']}\nScans: {last['scans']}")

async def loop_check(bot):
    while True:
        try:
            buys = await get_offers("BUY")
            sells = await get_offers("SELL")
            if buys and sells:
                b = min(buys, key=lambda x:x["price"])
                s = max(sells, key=lambda x:x["price"])
                gap = s["price"] - b["price"]
                last["scans"]+=1
                last["gap"]=gap
                if gap >= MIN_GAP:
                    await bot.send_message(chat_id=CHAT_ID, text=
                        f"🚀 GAP {gap:.2f} UGX FOUND!\n\n"
                        f"BUY @ {b['price']} ({b['name']})\nLimit {b['min']}-{b['max']}\n\n"
                        f"SELL @ {s['price']} ({s['name']})\nLimit {s['min']}-{s['max']}\n\n"
                        f"Profit $100 = {gap*100:.0f} UGX\n\n🔗 {LINK}"
                    )
        except Exception as e:
            print(e)
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
