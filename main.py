import os, asyncio, aiohttp
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
LINK = "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"

async def get_offers(t):
    payload = {"asset":"USDT","fiat":"UGX","page":1,"rows":10,"tradeType":t,"payTypes":[]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                j = await r.json()
                out=[]
                for x in j.get("data",[])[:10]:
                    adv=x.get("adv",{})
                    price=float(adv.get("price",0))
                    min_a=adv.get("minSingleTransAmount","?")
                    max_a=adv.get("maxSingleTransAmount","?")
                    pay=" ".join([m.get("tradeMethodName","") for m in adv.get("tradeMethods",[])])
                    if "mtn" in pay.lower() or "airtel" in pay.lower() or "airtime" in pay.lower():
                        out.append({"price":price,"name":x.get("advertiser",{}).get("nickName",""),"min":min_a,"max":max_a,"pay":pay})
                return out
    except:
        return []

async def price_cmd(update, context):
    await update.message.reply_text("Checking...")
    buys = await get_offers("BUY")
    sells = await get_offers("SELL")
    if not buys or not sells:
        await update.message.reply_text("No Airtel/MTN offers now")
        return
    b = min(buys, key=lambda x:x["price"])
    s = max(sells, key=lambda x:x["price"])
    gap = s["price"] - b["price"]
    await update.message.reply_text(f"GAP: {gap:.2f} UGX\n\nBUY: {b['price']} ({b['name']})\nLimit: {b['min']}-{b['max']}\nPay: {b['pay']}\n\nSELL: {s['price']} ({s['name']})\nLimit: {s['min']}-{s['max']}\nPay: {s['pay']}\n\nProfit $100 = {gap*100:.0f} UGX\n\n{link}".replace("{link}",LINK))

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("status", price_cmd))
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
