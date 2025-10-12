import aiohttp
from .config import settings

class ApiClient:
    """
    Обёртка для DRF-запросов. Автоматически добавляет X-Api-Key.
    В случае ошибки печатает тело ответа, чтобы понимать причину (403/400/...).
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.api_base_url).rstrip("/")
        self.api_key = api_key or settings.api_key
        self._session: aiohttp.ClientSession | None = None

    async def _get_sess(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            headers = {"Content-Type": "application/json"}
            # ВАЖНО: X-Api-Key должен быть непустым
            if not self.api_key:
                if settings.debug_bots:
                    print("[ApiClient] WARNING: api_key пустой — запросы будут получать 403")
            else:
                headers["X-Api-Key"] = self.api_key

            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def _handle(self, resp: aiohttp.ClientResponse):
        text = await resp.text()
        if 200 <= resp.status < 300:
            # Пытаемся распарсить JSON
            try:
                return await resp.json()
            except Exception:
                return text
        # Ошибка — бросаем с телом, чтобы в боте видеть причину
        raise aiohttp.ClientResponseError(
            resp.request_info, resp.history, status=resp.status, message=text or resp.reason
        )

    async def get(self, path: str, params: dict | None = None):
        s = await self._get_sess()
        async with s.get(self.base_url + path, params=params) as r:
            return await self._handle(r)

    async def post(self, path: str, json: dict | None = None):
        s = await self._get_sess()
        async with s.post(self.base_url + path, json=json) as r:
            return await self._handle(r)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
