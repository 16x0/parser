from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from config import config

@dataclass
class LotAnalysis:
    lot_id: str
    collection_name: str
    number: Optional[int]
    buy_price: float
    floor_price: float
    net_sell_price: float
    net_profit: float
    roi_percent: float
    is_lucky_number: bool = False
    attributes: List[str] = field(default_factory=list)
    preview_url: Optional[str] = None
    deep_link: str = ""

def is_lucky_number(num: Optional[int]) -> bool:
    """Проверка номера на красивый/редкий (low mint, одинаковые цифры, зеркалки)."""
    if num is None:
        return False
    # Low mint (< 100)
    if 1 <= num <= 100:
        return True
    
    s = str(num)
    # Одинаковые цифры (111, 777, 999, 7777)
    if len(s) > 1 and len(set(s)) == 1:
        return True
    
    # Круглые числа (200, 500, 1000, 5000)
    if num % 100 == 0:
        return True
    
    # Зеркальные / палиндромы (1221, 1331)
    if len(s) >= 3 and s == s[::-1]:
        return True

    return False

def analyze_lot(
    lot: Dict[str, Any],
    cached_floor_price: Optional[float] = None,
    min_spread_percent: float = config.MIN_SPREAD_PERCENT,
    fee_percent: float = config.MARKET_FEE_PERCENT,
) -> Optional[LotAnalysis]:
    """
    Анализ лота на выгодность спреда.
    Возвращает объект LotAnalysis, если лот удовлетворяет критериям, иначе None.
    """
    lot_id = str(lot.get("id") or lot.get("_id") or "")
    collection = lot.get("collectionName") or lot.get("collection") or lot.get("title") or "Telegram Gift"
    number = lot.get("number")
    
    # Извлечение цены покупки (в nanoTONs)
    raw_price = lot.get("salePrice") or lot.get("price") or lot.get("amount")
    if raw_price is None:
        return None
    
    try:
        val = float(raw_price)
        buy_price = val / 1_000_000_000.0 if val > 1_000_000 else val
    except (ValueError, TypeError):
        return None

    if buy_price <= 0:
        return None

    # Определение актуального Floor Price:
    # 1. Приоритет: флор по конкретной связке Модель + Фон
    # 2. Флор по всей коллекции из объекта лота
    # 3. Кэшированный флор из воркера
    embedded_model_floor = lot.get("floorPriceNanoTONsByBackdropModel")
    embedded_col_floor = lot.get("floorPriceNanoTONsByCollection")
    
    floor_price: Optional[float] = None
    if embedded_model_floor and embedded_model_floor > 0:
        floor_price = float(embedded_model_floor) / 1_000_000_000.0
    elif embedded_col_floor and embedded_col_floor > 0:
        floor_price = float(embedded_col_floor) / 1_000_000_000.0
    elif cached_floor_price and cached_floor_price > 0:
        floor_price = cached_floor_price

    if not floor_price or floor_price <= 0:
        return None

    # Расчет чистой цены продажи после вычета комиссии маркетплейса
    net_sell_price = floor_price * (1.0 - (fee_percent / 100.0))
    net_profit = net_sell_price - buy_price
    roi_percent = (net_profit / buy_price) * 100.0

    attributes: List[str] = []
    
    model = lot.get("modelName")
    if model:
        rarity_m = lot.get("modelRarityPerMille")
        rarity_str = f" ({rarity_m/10}%)" if rarity_m else ""
        attributes.append(f"Модель: {model}{rarity_str}")
        
    backdrop = lot.get("backdropName")
    if backdrop:
        rarity_b = lot.get("backdropRarityPerMille")
        rarity_str = f" ({rarity_b/10}%)" if rarity_b else ""
        attributes.append(f"Фон: {backdrop}{rarity_str}")

    lucky = is_lucky_number(number)
    if lucky:
        attributes.append(f"Красивый номер #{number}")

    # Условия триггера:
    # 1. Спред превышает минимальный порог
    # 2. Либо редкий красивый номер по цене флора или дешевле
    is_profitable = roi_percent >= min_spread_percent
    is_rare_at_floor = lucky and (buy_price <= floor_price * 1.05)

    if is_profitable or is_rare_at_floor:
        deep_link = f"https://t.me/mrkt/app?startapp=gift_{lot_id}" if lot_id else "https://t.me/mrkt"
        
        # Получаем URL изображения подарка
        thumb_key = lot.get("modelStickerThumbnailKey")
        preview_url = f"https://cdn.tgmrkt.io/{thumb_key}" if thumb_key else lot.get("imageUrl")

        return LotAnalysis(
            lot_id=lot_id,
            collection_name=collection,
            number=number,
            buy_price=round(buy_price, 3),
            floor_price=round(floor_price, 3),
            net_sell_price=round(net_sell_price, 3),
            net_profit=round(net_profit, 3),
            roi_percent=round(roi_percent, 1),
            is_lucky_number=lucky,
            attributes=attributes,
            preview_url=preview_url,
            deep_link=deep_link
        )

    return None
