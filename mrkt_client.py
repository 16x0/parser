import logging
from typing import Any, Dict, List, Optional
from curl_cffi import requests
from config import config

logger = logging.getLogger("mrkt_client")

class MRKTClient:
    """Клиент для MRKT API с поддержкой браузерного TLS и cookies (curl_cffi)."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or config.MRKT_AUTH_TOKEN
        self.base_url = config.API_BASE_URL.rstrip('/')
        self.session: Optional[requests.AsyncSession] = None

    async def __aenter__(self):
        self.session = requests.AsyncSession(impersonate="chrome120")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://cdn.tgmrkt.io",
            "referer": "https://cdn.tgmrkt.io/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "content-type": "application/json",
        }
        if self.token:
            headers["authorization"] = self.token
        return headers

    def _get_cookies(self) -> Dict[str, str]:
        if self.token:
            return {"access_token": self.token}
        return {}

    async def get_listings(
        self,
        collection_names: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None,
        ordering: Optional[str] = "Price",
        low_to_high: bool = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        number: Optional[int] = None,
        count: int = 20,
        cursor: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "collectionNames": collection_names or [],
            "modelNames": model_names or [],
            "backdropNames": [],
            "symbolNames": [],
            "ordering": ordering,
            "lowToHigh": low_to_high,
            "maxPrice": max_price,
            "minPrice": min_price,
            "mintable": None,
            "number": number,
            "count": count,
            "cursor": cursor,
            "query": None,
            "promotedFirst": False,
        }

        url = f"{self.base_url}/gifts/saling"
        try:
            resp = await self.session.post(
                url,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                json=payload,
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (401, 403):
                logger.error(f"Ошибка авторизации MRKT ({resp.status_code}): обновите токен!")
            else:
                logger.warning(f"MRKT API вернул {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.error(f"Исключение при запросе к MRKT: {e}")

        return {"gifts": [], "cursor": None}

    async def get_fresh_listings(self, count: int = 20) -> List[Dict[str, Any]]:
        # ordering="None" в MRKT API означает сортировку по новизне (ListedAt)
        res = await self.get_listings(ordering="None", low_to_high=False, count=count)
        return res.get("gifts", [])

    async def get_collection_floor(self, collection_name: str) -> Optional[float]:
        res = await self.get_listings(collection_names=[collection_name], ordering="Price", low_to_high=True, count=1)
        gifts = res.get("gifts", [])
        if gifts:
            first = gifts[0]
            raw = first.get("salePrice") or first.get("price") or first.get("amount")
            if raw is not None:
                try:
                    val = float(raw)
                    return val / 1_000_000_000.0 if val > 1_000_000 else val
                except (ValueError, TypeError):
                    pass
        return None
