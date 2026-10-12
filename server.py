import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from config import config

app = FastAPI(title="MRKT Radar TMA API")

# Разрешаем CORS для запросов из браузера и Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ссылка на экземпляр сканера в памяти
scanner_instance = None

webapp_dir = os.path.join(os.path.dirname(__file__), "webapp")

class SettingsRequest(BaseModel):
    minSpread: float

@app.get("/")
async def serve_index():
    """Отдача HTML-файла Telegram Web App."""
    index_file = os.path.join(webapp_dir, "index.html")
    return FileResponse(index_file)

@app.get("/api/lots")
async def get_lots():
    """Получение свежих реальных лотов и найденных спредов."""
    if not scanner_instance:
        return {"hot": [], "recent": []}
    return {
        "hot": scanner_instance.hot_lots,
        "recent": scanner_instance.recent_lots
    }

@app.get("/api/gaps")
async def get_gaps():
    """Получение реальных разрывов цен (Floor Gaps) между 1-м и 2-м лотом."""
    if not scanner_instance:
        return []
    return scanner_instance.gaps

@app.get("/api/status")
async def get_status():
    """Получение статуса сканера и текущих Floor Prices."""
    if not scanner_instance:
        return {"status": "starting", "floors": {}, "subscribers": 0}
    return {
        "status": "online" if scanner_instance.is_running else "offline",
        "subscribers": len(scanner_instance.subscribers),
        "floors": scanner_instance.floor_cache,
        "minSpread": config.MIN_SPREAD_PERCENT
    }

@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    """Обновление порога минимального спреда."""
    config.MIN_SPREAD_PERCENT = req.minSpread
    return {"success": True, "minSpread": config.MIN_SPREAD_PERCENT}
