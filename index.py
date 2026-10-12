import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MRKT_TOKEN = os.getenv("MRKT_AUTH_TOKEN", "aeaac876-e184-4e01-9717-c3280dec0820")

def get_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": MRKT_TOKEN,
        "origin": "https://cdn.tgmrkt.io",
        "referer": "https://cdn.tgmrkt.io/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "content-type": "application/json",
        "cookie": f"access_token={MRKT_TOKEN}"
    }

@app.get("/api/lots")
async def get_lots():
    payload = {
        "collectionNames": [],
        "modelNames": [],
        "backdropNames": [],
        "symbolNames": [],
        "ordering": "None",
        "lowToHigh": False,
        "maxPrice": None,
        "minPrice": None,
        "mintable": None,
        "number": None,
        "count": 20,
        "cursor": "",
        "query": None,
        "promotedFirst": False
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post("https://api.tgmrkt.io/api/v1/gifts/saling", headers=get_headers(), json=payload)
            if r.status_code == 200:
                gifts = r.json().get("gifts", [])
                formatted = []
                hot = []
                for g in gifts:
                    lid = str(g.get("id") or "")
                    price = round((g.get("salePrice") or 0) / 1e9, 2)
                    floor = round((g.get("floorPriceNanoTONsByBackdropModel") or g.get("floorPriceNanoTONsByCollection") or 0) / 1e9, 2)
                    net_profit = round(floor * 0.95 - price, 2)
                    roi = round((net_profit / price) * 100, 1) if price > 0 else 0
                    thumb = g.get("modelStickerThumbnailKey")
                    
                    item = {
                        "id": lid,
                        "giftId": g.get("giftId"),
                        "title": g.get("collectionName") or "Gift",
                        "number": g.get("number"),
                        "model": g.get("modelName"),
                        "backdrop": g.get("backdropName"),
                        "buyPrice": price,
                        "floorPrice": floor,
                        "netProfit": net_profit,
                        "roi": roi,
                        "image": f"https://cdn.tgmrkt.io/{thumb}" if thumb else "",
                        "deepLink": f"https://t.me/mrkt/app?startapp=gift_{lid}"
                    }
                    formatted.append(item)
                    if roi >= 15.0 or (g.get("number") and g.get("number") <= 100):
                        hot.append(item)
                return {"hot": hot, "recent": formatted}
        except Exception as e:
            return {"error": str(e), "hot": [], "recent": []}
    return {"hot": [], "recent": []}

@app.get("/api/gaps")
async def get_gaps():
    # Запрос топ коллекций для расчета разрывов
    target_cols = ["Lunar Snake", "Xmas Stocking", "Berry Box", "Lucky Locket", "Liberty Figure"]
    gaps = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for col in target_cols:
            try:
                payload = {
                    "collectionNames": [col],
                    "ordering": "Price",
                    "lowToHigh": True,
                    "count": 2,
                    "cursor": "",
                    "modelNames": [], "backdropNames": [], "symbolNames": [],
                    "maxPrice": None, "minPrice": None, "mintable": None, "number": None,
                    "query": None, "promotedFirst": False
                }
                r = await client.post("https://api.tgmrkt.io/api/v1/gifts/saling", headers=get_headers(), json=payload)
                if r.status_code == 200:
                    gifts = r.json().get("gifts", [])
                    if len(gifts) > 1:
                        p1 = (gifts[0].get("salePrice") or 0) / 1e9
                        p2 = (gifts[1].get("salePrice") or 0) / 1e9
                        if p1 > 0 and p2 > p1:
                            gaps.append({
                                "title": col,
                                "lot1": round(p1, 2),
                                "lot2": round(p2, 2),
                                "gap": round(((p2 - p1) / p1) * 100, 1)
                            })
            except Exception:
                pass
    return sorted(gaps, key=lambda x: x["gap"], reverse=True)

@app.get("/api/status")
async def get_status():
    return {"status": "online", "minSpread": 15.0}
