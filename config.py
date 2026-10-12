import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Авторизационный токен MRKT (полученный из WebApp Network или через auth эндпоинт)
    MRKT_AUTH_TOKEN: str = os.getenv("MRKT_AUTH_TOKEN", "")
    
    # ID чата по умолчанию
    DEFAULT_CHAT_ID: int = int(os.getenv("DEFAULT_CHAT_ID", "0")) if os.getenv("DEFAULT_CHAT_ID") else 0
    
    # Базовый URL API маркетплейса
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.tgmrkt.io/api/v1")
    
    # Параметры снайпинга и аналитики
    MIN_SPREAD_PERCENT: float = float(os.getenv("MIN_SPREAD_PERCENT", "20.0"))
    MARKET_FEE_PERCENT: float = float(os.getenv("MARKET_FEE_PERCENT", "5.0"))
    POLL_INTERVAL_SECONDS: float = float(os.getenv("POLL_INTERVAL_SECONDS", "1.5"))
    FLOOR_REFRESH_INTERVAL: float = float(os.getenv("FLOOR_REFRESH_INTERVAL", "45.0"))
    
    # Целевые коллекции для приоритетного мониторинга (пустой список = все коллекции)
    TARGET_COLLECTIONS: List[str] = [
        item.strip() for item in os.getenv("TARGET_COLLECTIONS", "").split(",") if item.strip()
    ]
    
    # URL для Telegram WebApp (локальный или захощенный)
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "http://127.0.0.1:8000")
    
    # Сервер FastApi для WebApp
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

config = Config()
