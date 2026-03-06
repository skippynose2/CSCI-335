"""ROIC.ai API client. Handles authentication and rate limiting."""

import logging
import time

import httpx

from stockscrape.config import ROIC_API_KEY, ROIC_BASE_URL

logger = logging.getLogger(__name__)


class RoicClient:
    """Synchronous client for the ROIC.ai REST API."""

    def __init__(self, api_key: str = ROIC_API_KEY, base_url: str = ROIC_BASE_URL):
        if not api_key:
            raise RuntimeError("ROIC_API_KEY is not set. Add it to your .env file.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=60.0)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        params = params or {}
        params["apikey"] = self._api_key
        url = f"{self._base_url}{path}"
        resp = self._client.get(url, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            logger.warning("Rate limited, sleeping %ds", retry_after)
            time.sleep(retry_after)
            resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Earnings Calls ──────────────────────────────────────────────────────

    def list_earnings_calls(self, ticker: str, limit: int = 500) -> list[dict]:
        return self._get(f"/v2/company/earnings-calls/list/{ticker}", {"limit": limit})

    def get_transcript(self, ticker: str, year: int, quarter: int) -> dict:
        return self._get(
            f"/v2/company/earnings-calls/transcript/{ticker}",
            {"year": year, "quarter": quarter},
        )

    # ── Stock Prices ────────────────────────────────────────────────────────

    def get_stock_prices(
        self, ticker: str, date_start: str = "2015-01-01", limit: int = 100000
    ) -> list[dict]:
        return self._get(
            f"/v2/stock-prices/{ticker}",
            {"date_start": date_start, "limit": limit, "order": "asc"},
        )

    # ── Fundamentals ────────────────────────────────────────────────────────

    def get_income_statement(self, ticker: str, period: str = "quarterly", limit: int = 250) -> list[dict]:
        return self._get(
            f"/v2/fundamental/income-statement/{ticker}",
            {"period": period, "limit": limit},
        )

    def get_balance_sheet(self, ticker: str, period: str = "quarterly", limit: int = 250) -> list[dict]:
        return self._get(
            f"/v2/fundamental/balance-sheet/{ticker}",
            {"period": period, "limit": limit},
        )

    def get_cash_flow(self, ticker: str, period: str = "quarterly", limit: int = 250) -> list[dict]:
        return self._get(
            f"/v2/fundamental/cash-flow/{ticker}",
            {"period": period, "limit": limit},
        )
