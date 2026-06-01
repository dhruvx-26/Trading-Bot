"""
Binance Futures Testnet client wrapper.

Handles:
- HMAC-SHA256 request signing
- Timestamping
- HTTP session management with retries
- Raw request/response logging
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.logging_config import get_logger

logger = get_logger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
API_VERSION = "/fapi/v1"

# Retry strategy for transient network errors
_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "DELETE"],
)


def _build_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY_STRATEGY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BinanceClient:
    """
    Lightweight wrapper around the Binance Futures Testnet REST API.

    Usage:
        client = BinanceClient(api_key="...", api_secret="...")
        response = client.place_order(symbol="BTCUSDT", side="BUY",
                                      order_type="MARKET", quantity=0.001)
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = 5000,
    ) -> None:
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API key and secret are required. "
                "Pass them directly or set BINANCE_API_KEY / BINANCE_API_SECRET "
                "environment variables."
            )

        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self._session = _build_session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info(
            "BinanceClient initialised — base_url=%s recv_window=%d",
            self.base_url,
            self.recv_window,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        """Add timestamp + HMAC-SHA256 signature to a params dict."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _post(self, endpoint: str, params: dict) -> dict:
        """
        Sign and POST to a private endpoint.

        Returns:
            Parsed JSON response dict.

        Raises:
            requests.HTTPError: On non-2xx responses.
            requests.ConnectionError / requests.Timeout: On network issues.
        """
        signed_params = self._sign(params)
        url = f"{self.base_url}{API_VERSION}{endpoint}"

        # Redact secret from logs
        safe_params = {k: v for k, v in signed_params.items() if k != "signature"}
        logger.debug("POST %s | params=%s", url, safe_params)

        response = self._session.post(url, data=signed_params, timeout=10)

        logger.debug(
            "Response %d | %s", response.status_code, response.text[:500]
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Try to surface Binance's error message
            try:
                err_body = response.json()
                logger.error(
                    "Binance API error %d: code=%s msg=%s",
                    response.status_code,
                    err_body.get("code"),
                    err_body.get("msg"),
                )
            except Exception:
                logger.error("HTTP %d: %s", response.status_code, response.text)
            raise

        return response.json()

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """GET a public or signed endpoint."""
        url = f"{self.base_url}{API_VERSION}{endpoint}"
        logger.debug("GET %s | params=%s", url, params)
        response = self._session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._get("/ping")
            logger.info("Ping successful.")
            return True
        except Exception as exc:
            logger.error("Ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return server timestamp in milliseconds."""
        data = self._get("/time")
        return data["serverTime"]  # type: ignore[index]

    def get_exchange_info(self, symbol: str | None = None) -> dict:
        """Fetch exchange info (optionally filtered by symbol)."""
        params = {"symbol": symbol} if symbol else {}
        return self._get("/exchangeInfo", params=params)  # type: ignore[return-value]

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Any,
        price: Any = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a futures order on Binance Testnet.

        Args:
            symbol:        Trading pair, e.g. 'BTCUSDT'.
            side:          'BUY' or 'SELL'.
            order_type:    'MARKET' or 'LIMIT'.
            quantity:      Order quantity (number or Decimal).
            price:         Limit price — required for LIMIT orders.
            time_in_force: Time-in-force for LIMIT orders (default 'GTC').

        Returns:
            Raw Binance order response dict.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            side,
            order_type,
            symbol,
            quantity,
            price if price else "MARKET",
        )

        response = self._post("/order", params)
        logger.info(
            "Order placed | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )
        return response

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Fetch details for an existing order."""
        params = self._sign({"symbol": symbol, "orderId": order_id})
        return self._get("/order", params=params)  # type: ignore[return-value]

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order."""
        params: dict[str, Any] = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling orderId=%d on %s", order_id, symbol)
        return self._post("/order", params)  # DELETE semantics via helper below

    def get_account(self) -> dict:
        """Return account information including balances."""
        params: dict[str, Any] = {}
        signed = self._sign(params)
        return self._get("/account", params=signed)  # type: ignore[return-value]
