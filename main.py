import os, asyncio, aiohttp
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
LINK = "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
MIN_GAP = 70

async def get_offers(t):
    payload = {"asset":"USDT","fiat":"UGX","page":1,"rows":10,"tradeType":t,"payTypes":[]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                d=await r.json()
                out=[]
                for x in d.get("data",[])[:10]:
                    adv=x.get("adv",{})
                    user=x.get("advertiser",{})
                    price=float(adv.get("price",0))
                    pay=" ".join([m.get("tradeMethodName","") for m in adv.get("tradeMethods",[])])
                    if any(k in pay.lower() for k in ["mtn","airtel","airtime"]):
                        out.append({
                            "price":price,
                            "name":user.get("nickName",""),
                            "userNo":user.get("userNo",""),
                            "min":adv.get("minSingleTransAmount","?"),
                            "max":adv.get("maxSingleTransAmount","?"),
                            "available":adv.get("tradableQuantity","?"),
                            "pay":pay,
                            "rating": user.get("monthFinishRate", 0) * 100 if isinstance(user.get("monthFinishRate"), float) else user.get("monthFinishRate","?"),
                            "orders": user.get("monthOrderCount","?"),
                            "completion": user.get("positiveRate","?")
                        })
                return out
    except Exception as e:
        print(e)
        return []

async def start_cmd(u,c):
    await u.message.reply_text("Bot alive ✅\n/price - GAP + 2 links + rating\n/status - bot check")

async def status_cmd(u,c):
    buys=await get_offers("BUY")
    sells=await get_offers("SELL")
    await u.message.reply_text(f"✅ Bot Online\nBUY: {len(buys)} offers\nSELL: {len(sells)} offers\nAlert: {MIN_GAP} UGX")

async def price_cmd(u,c):
    await u.message.reply_text("Scanning...")
    buys=await get_offers("BUY")
    sells=await get_offers("SELL")
    if not buys or not sells:
        await u.message.reply_text("No offers")
        return
    b=min(buys, key=lambda x:x["price"])
    s=max(sells, key=lambda x:x["price"])
    gap=s["price"]-b["price"]
    b_link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={b['userNo']}"
    s_link = f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={s['userNo']}"
    
    # Fix rating display
    def fmt_rate(r):
        try:
            if r=="?" or r==None: return "?"
            f=float(r)
            if f<=1: f=f*100
            return f"{f:.1f}%"
        except: return str(r)

    msg=(f"💰 GAP: {gap:.2f} UGX (Profit $100={gap*100:.0f})\n\n"
         f"🟢 BUY: {b['price']} UGX\n"
         f"Seller: {b['name']}\n"
         f"⭐ Rating: {fmt_rate(b['rating'])} ({b['orders']} orders)\n"
         f"Available: {b['available']} USDT\n"
         f"Limit: {b['min']}-{b['max']} UGX\n"
         f"Pay: {b['pay']}\n"
         f"👉 Trade: {b_link}\n\n"
         f"🔴 SELL: {s['price']} UGX\n"
         f"Buyer: {s['name']}\n"
         f"⭐ Rating: {fmt_rate(s['rating'])} ({s['orders']} orders)\n"
         f"Available: {s['available']} USDT\n"
         f"Limit: {s['min']}-{s['max']} UGX\n"
         f"Pay: {s['pay']}\n"
         f"👉 Trade: {s_link}\n\n"
         f"All: {LINK}")
    await u.message.reply_text(msg)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Started with rating")
    while True:
        await asyncio.sleep(3600)

if __name__=="__main__":
    asyncio.run(main())
