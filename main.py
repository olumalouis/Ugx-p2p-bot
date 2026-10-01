import os, asyncio, aiohttp
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
LINK = "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
MIN_GAP = 70

async def get_offers(trade_type):
    payload = {"asset":"USDT","fiat":"UGX","page":1,"rows":10,"tradeType":trade_type,"payTypes":[]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                data = await r.json()
                res=[]
                for item in data.get("data",[])[:10]:
                    adv=item.get("adv",{})
                    price=float(adv.get("price",0))
                    methods=" ".join([m.get("tradeMethodName","") for m in adv.get("tradeMethods",[])])
                    if any(x in methods.lower() for x in ["mtn","airtel","airtime","mobile"]):
                        res.append({
                            "price":price,
                            "name":item.get("advertiser",{}).get("nickName",""),
                            "min":adv.get("minSingleTransAmount","?"),
                            "max":adv.get("maxSingleTransAmount","?"),
                            "pay":methods
                        })
                return res
    except:
        return []

async def start_cmd(update, context):
    await update.message.reply_text("Bot alive ✅\nSend /price to check GAP with link + limit")

async def price_cmd(update, context):
    await update.message.reply_text("Scanning MTN/Airtel...")
    buys = await get_offers("BUY")
    sells = await get_offers("SELL")
    if not buys or not sells:
        await update.message.reply_text("No offers found now")
        return
    b=min(buys, key=lambda x:x["price"])
    s=max(sells, key=lambda x:x["price"])
    gap=s["price"]-b["price"]
    msg=(f"💰 GAP: {gap:.2f} UGX\n"
         f"Profit $100 = {gap*100:.0f} UGX\n\n"
         f"🟢 BUY: {b['price']} UGX\n"
         f"Seller: {b['name']}\n"
         f"Limit: {b['min']} - {b['max']} UGX\n"
         f"Pay: {b['pay']}\n\n"
         f"🔴 SELL: {s['price']} UGX\n"
         f"Buyer: {s['name']}\n"
         f"Limit: {s['min']} - {s['max']} UGX\n"
         f"Pay: {s['pay']}\n\n"
         f"🔗 {LINK}")
    await update.message.reply_text(msg)

async def auto_loop(app):
    while True:
        try:
            buys=await get_offers("BUY")
            sells=await get_offers("SELL")
            if buys and sells:
                b=min(buys, key=lambda x:x["price"])
                s=max(sells, key=lambda x:x["price"])
                gap=s["price"]-b["price"]
                if gap>=MIN_GAP and CHAT_ID:
                    await app.bot.send_message(chat_id=CHAT_ID, text=f"🚀 GAP {gap:.2f} UGX!\nBUY {b['price']} / SELL {s['price']}\nProfit $100={gap*100:.0f}\n{LINK}")
        except Exception as e:
            print(e)
        await asyncio.sleep(120)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    asyncio.create_task(auto_loop(app))
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Bot started OK")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
