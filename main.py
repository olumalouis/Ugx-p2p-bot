import os, asyncio, aiohttp
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
LINK = "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=UGX"
MIN_GAP_AUTO = 75
MIN_GAP_MANUAL = 40

async def get_offers(t):
    payload = {"asset":"USDT","fiat":"UGX","page":1,"rows":15,"tradeType":t,"payTypes":[]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(URL, json=payload, timeout=10) as r:
                d=await r.json()
                out=[]
                for x in d.get("data",[])[:15]:
                    adv=x.get("adv",{})
                    user=x.get("advertiser",{})
                    price=float(adv.get("price",0))
                    pay=" ".join([m.get("tradeMethodName","") for m in adv.get("tradeMethods",[])])
                    if any(k in pay.lower() for k in ["mtn","airtel","airtime","mobile money"]):
                        out.append({
                            "price":price,
                            "name":user.get("nickName",""),
                            "userNo":user.get("userNo",""),
                            "min":adv.get("minSingleTransAmount","?"),
                            "max":adv.get("maxSingleTransAmount","?"),
                            "available":adv.get("tradableQuantity","?"),
                            "pay":pay,
                            "rating": user.get("monthFinishRate","?"),
                            "orders": user.get("monthOrderCount","?")
                        })
                return out
    except: return []

def fmt_rate(r):
    try:
        if r=="?" or r==None: return "?"
        f=float(r)
        if f<=1: f=f*100
        return f"{f:.1f}%"
    except: return str(r)

def build_pairs(buys, sells):
    pairs=[]
    for b in buys:
        for s in sells:
            if b["userNo"]!=s["userNo"]:
                gap=s["price"]-b["price"]
                if gap>0:
                    pairs.append((gap,b,s))
    pairs.sort(key=lambda x: x[0], reverse=True)
    return pairs

async def start_cmd(u,c):
    await u.message.reply_text("Bot alive ✅\n/price - Top 3 pairs (40+ GAP)\n/status - check")

async def status_cmd(u,c):
    buys=await get_offers("BUY")
    sells=await get_offers("SELL")
    pairs=build_pairs(buys, sells)
    best = pairs[0][0] if pairs else 0
    await u.message.reply_text(f"✅ Bot Online\nBUY: {len(buys)} SELL: {len(sells)}\nBest GAP now: {best:.2f} UGX\nAuto alert: >= {MIN_GAP_AUTO} UGX\nManual: >= {MIN_GAP_MANUAL} UGX (Top 3)")

async def price_cmd(u,c):
    await u.message.reply_text("Scanning MTN/Airtel...")
    buys=await get_offers("BUY")
    sells=await get_offers("SELL")
    pairs=build_pairs(buys, sells)
    filtered=[p for p in pairs if p[0]>=MIN_GAP_MANUAL][:3]
    if not filtered:
        await u.message.reply_text(f"No pair with GAP >= {MIN_GAP_MANUAL} UGX now.\nBest GAP: {pairs[0][0]:.2f} UGX" if pairs else "No offers")
        return
    msg=f"💰 TOP {len(filtered)} PAIRS (GAP >= {MIN_GAP_MANUAL})\n\n"
    for i,(gap,b,s) in enumerate(filtered,1):
        b_link=f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={b['userNo']}"
        s_link=f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={s['userNo']}"
        msg+=(
            f"--- PAIR {i}: GAP {gap:.2f} UGX | $100={gap*100:.0f} UGX ---\n"
            f"🟢 BUY {b['price']} @ {b['name']} ⭐{fmt_rate(b['rating'])} ({b['orders']})\n"
            f" Avail: {b['available']} USDT | Lim: {b['min']}-{b['max']}\n"
            f" 👉 {b_link}\n"
            f"🔴 SELL {s['price']} @ {s['name']} ⭐{fmt_rate(s['rating'])} ({s['orders']})\n"
            f" Avail: {s['available']} USDT | Lim: {s['min']}-{s['max']}\n"
            f" 👉 {s_link}\n\n"
        )
    msg+=f"All: {LINK}"
    await u.message.reply_text(msg)

async def auto_loop(app):
    last_gap=0
    while True:
        try:
            buys=await get_offers("BUY")
            sells=await get_offers("SELL")
            pairs=build_pairs(buys, sells)
            top=[p for p in pairs if p[0]>=MIN_GAP_AUTO][:2]
            if top and top[0][0]!=last_gap and CHAT_ID:
                last_gap=top[0][0]
                msg=f"🚀 HIGH GAP ALERT! >= {MIN_GAP_AUTO} UGX\n\n"
                for gap,b,s in top:
                    b_link=f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={b['userNo']}"
                    s_link=f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={s['userNo']}"
                    msg+=(
                        f"💰 GAP {gap:.2f} | $100={gap*100:.0f} UGX\n"
                        f"BUY {b['price']} {b['name']} ⭐{fmt_rate(b['rating'])} -> {b_link}\n"
                        f"SELL {s['price']} {s['name']} ⭐{fmt_rate(s['rating'])} -> {s_link}\n\n"
                    )
                await app.bot.send_message(chat_id=CHAT_ID, text=msg)
        except Exception as e:
            print(e)
        await asyncio.sleep(120)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    asyncio.create_task(auto_loop(app))
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Bot started A=Top3 B=Auto")
    while True: await asyncio.sleep(3600)

if __name__=="__main__":
    asyncio.run(main())
