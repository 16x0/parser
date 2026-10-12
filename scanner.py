import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from analyzer import LotAnalysis, analyze_lot
from config import config
from mrkt_client import MRKTClient

logger = logging.getLogger("scanner")

class MarketScanner:
    """Фоновый воркер для регулярного опроса листингов и детекции спредов."""

    def __init__(self, on_alert_callback: Optional[Callable[[LotAnalysis], Coroutine]] = None):
        self.on_alert = on_alert_callback
        self.is_running = False
        
        # Кэш Floor Price: {collection_name: floor_price}
        self.floor_cache: Dict[str, float] = {}
        self.last_floor_update: float = 0
        
        # Кэш просмотренных лотов для дедупликации (ID -> timestamp)
        self.seen_lots: Dict[str, float] = {}
        
        # Живые данные для WebApp (в памяти)
        self.recent_lots: List[Dict[str, Any]] = []
        self.hot_lots: List[Dict[str, Any]] = []
        self.gaps: List[Dict[str, Any]] = []
        
        # Список ID чатов подписчиков
        self.subscribers: Set[int] = set()
        if config.DEFAULT_CHAT_ID:
            self.subscribers.add(config.DEFAULT_CHAT_ID)

    def add_subscriber(self, chat_id: int):
        self.subscribers.add(chat_id)

    def remove_subscriber(self, chat_id: int):
        self.subscribers.discard(chat_id)

    def _cleanup_seen_lots(self):
        """Очистка лотов старше 1 часа, чтобы не раздувать память."""
        now = time.time()
        expired = [lid for lid, ts in self.seen_lots.items() if now - ts > 3600]
        for lid in expired:
            del self.seen_lots[lid]

    def _format_lot_for_webapp(self, lot: Dict[str, Any], analysis: Optional[LotAnalysis] = None) -> Dict[str, Any]:
        """Форматирование объекта лота для фронтенда WebApp."""
        lot_id = str(lot.get("id") or "")
        raw_price = lot.get("salePrice") or lot.get("price") or 0
        buy_price = round(raw_price / 1e9 if raw_price > 1e6 else raw_price, 2)
        
        raw_floor = (
            lot.get("floorPriceNanoTONsByBackdropModel")
            or lot.get("floorPriceNanoTONsByCollection")
            or 0
        )
        floor_price = round(raw_floor / 1e9 if raw_floor > 1e6 else raw_floor, 2)
        
        # Чистый спред с учетом 5% комиссии
        net_sell = floor_price * 0.95
        net_profit = round(net_sell - buy_price, 2)
        roi = round((net_profit / buy_price) * 100, 1) if buy_price > 0 else 0

        thumb = lot.get("modelStickerThumbnailKey")
        image_url = f"https://cdn.tgmrkt.io/{thumb}" if thumb else ""
        
        # Прямой диплинк на лот в WebApp MRKT
        deep_link = f"https://t.me/mrkt/app?startapp=gift_{lot_id}"

        return {
            "id": lot_id,
            "giftId": lot.get("giftId"),
            "title": lot.get("collectionName") or lot.get("title") or "Gift",
            "number": lot.get("number"),
            "model": lot.get("modelName"),
            "backdrop": lot.get("backdropName"),
            "symbol": lot.get("symbolName"),
            "buyPrice": buy_price,
            "floorPrice": floor_price,
            "netProfit": net_profit,
            "roi": roi,
            "image": image_url,
            "deepLink": deep_link,
            "timeAgo": "сейчас"
        }

    async def update_floors(self, client: MRKTClient):
        """Обновление минимальных цен (Floor Price) по коллекциям."""
        target_cols = config.TARGET_COLLECTIONS
        if not target_cols:
            seen_cols = [lot.get("title") for lot in self.recent_lots if lot.get("title")]
            target_cols = list(dict.fromkeys(seen_cols))[:10] or ["Lunar Snake", "Xmas Stocking", "Berry Box", "Lucky Locket", "Liberty Figure"]

        new_gaps = []
        for col in target_cols:
            res = await client.get_listings(collection_names=[col], ordering="Price", low_to_high=True, count=2)
            gifts = res.get("gifts", [])
            if gifts:
                first = gifts[0]
                p1 = (first.get("salePrice") or 0) / 1e9
                self.floor_cache[col] = round(p1, 2)
                
                # Если есть второй лот, вычисляем разрыв в стакане
                if len(gifts) > 1:
                    p2 = (gifts[1].get("salePrice") or 0) / 1e9
                    if p1 > 0 and p2 > p1:
                        gap_pct = round(((p2 - p1) / p1) * 100, 1)
                        new_gaps.append({
                            "title": col,
                            "lot1": round(p1, 2),
                            "lot2": round(p2, 2),
                            "gap": gap_pct
                        })
            await asyncio.sleep(0.2)

        self.gaps = sorted(new_gaps, key=lambda x: x["gap"], reverse=True)
        self.last_floor_update = time.time()

    async def run(self):
        self.is_running = True
        logger.info("Запуск сканера MRKT...")

        async with MRKTClient() as client:
            await self.update_floors(client)

            while self.is_running:
                try:
                    if time.time() - self.last_floor_update > config.FLOOR_REFRESH_INTERVAL:
                        await self.update_floors(client)
                        self._cleanup_seen_lots()

                    # ordering="None" запрашивает последние опубликованные лоты
                    fresh_lots = await client.get_fresh_listings(count=20)

                    new_recent_list = []
                    for lot in fresh_lots:
                        lot_id = str(lot.get("id") or "")
                        if not lot_id:
                            continue

                        collection = lot.get("collectionName")
                        floor = self.floor_cache.get(collection)

                        analysis = analyze_lot(lot, floor)
                        formatted = self._format_lot_for_webapp(lot, analysis)
                        new_recent_list.append(formatted)

                        if lot_id not in self.seen_lots:
                            self.seen_lots[lot_id] = time.time()

                            if analysis:
                                logger.info(
                                    f"🔥 НАЙДЕН СПРЕД! {analysis.collection_name} #{analysis.number}: "
                                    f"Купить {analysis.buy_price} TON | Флор {analysis.floor_price} TON | ROI +{analysis.roi_percent}%"
                                )
                                # Добавляем в горячие лоты
                                self.hot_lots.insert(0, formatted)
                                if len(self.hot_lots) > 30:
                                    self.hot_lots.pop()

                                if self.on_alert:
                                    await self.on_alert(analysis)

                    if new_recent_list:
                        self.recent_lots = new_recent_list[:30]

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Ошибка в цикле сканера: {e}", exc_info=True)

                await asyncio.sleep(config.POLL_INTERVAL_SECONDS)

        logger.info("Сканер MRKT остановлен.")

    def stop(self):
        self.is_running = False
