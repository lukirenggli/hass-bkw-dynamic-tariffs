"""Public BKW client: one GET, no credentials and no query parameters."""
import json
from datetime import datetime, timezone
import aiohttp
from .const import API_URL, REQUEST_TIMEOUT
from .price import InvalidTariffs, TariffData, parse_tariffs

class BkwApiError(Exception):
    """Unreachable API, HTTP error or invalid tariff data."""

class BkwApi:
    def __init__(self,session:aiohttp.ClientSession) -> None:
        self.session = session
    async def async_fetch(self) -> TariffData:
        try:
            async with self.session.get(API_URL,headers={"Accept":"application/json"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),allow_redirects=False) as response:
                if response.status != 200:
                    raise BkwApiError(f"BKW API returned HTTP {response.status}")
                payload = await response.json()
            return parse_tariffs(payload,datetime.now(timezone.utc))
        except (aiohttp.ClientError,TimeoutError,json.JSONDecodeError,InvalidTariffs) as err:
            raise BkwApiError(str(err)) from err
