"""
High-level order placement logic.

This module sits between the CLI and the raw BinanceClient,
providing a clean interface with structured result objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import requests

from bot.client import BinanceClient
from bot.logging_config import get_logger
from bot.validators import validate_all

logger = get_logger(__name__)


@dataclass
class OrderRequest:
    """Validated, ready-to-send order parameters."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None

    def summary(self) -> str:
        price_str = str(self.price) if self.price else "MARKET"
        return (
            f"{self.side} {self.order_type} | "
            f"Symbol: {self.symbol} | "
            f"Qty: {self.quantity} | "
            f"Price: {price_str}"
        )


@dataclass
class OrderResult:
    """Structured representation of a Binance order response."""

    success: bool
    order_id: int | None = None
    symbol: str | None = None
    side: str | None = None
    order_type: str | None = None
    status: str | None = None
    executed_qty: str | None = None
    avg_price: str | None = None
    price: str | None = None
    orig_qty: str | None = None
    raw: dict = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def from_response(cls, data: dict) -> "OrderResult":
        return cls(
            success=True,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            executed_qty=data.get("executedQty"),
            avg_price=data.get("avgPrice"),
            price=data.get("price"),
            orig_qty=data.get("origQty"),
            raw=data,
        )

    @classmethod
    def from_error(cls, error: str) -> "OrderResult":
        return cls(success=False, error=error)

    def pretty(self) -> str:
        """Human-readable multi-line summary."""
        if not self.success:
            return f"❌  Order FAILED: {self.error}"

        lines = [
            "✅  Order placed successfully",
            f"   Order ID   : {self.order_id}",
            f"   Symbol     : {self.symbol}",
            f"   Side       : {self.side}",
            f"   Type       : {self.order_type}",
            f"   Status     : {self.status}",
            f"   Orig Qty   : {self.orig_qty}",
            f"   Exec Qty   : {self.executed_qty}",
        ]
        if self.avg_price and self.avg_price != "0":
            lines.append(f"   Avg Price  : {self.avg_price}")
        if self.price and self.price != "0":
            lines.append(f"   Limit Price: {self.price}")
        return "\n".join(lines)


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
) -> OrderRequest:
    """
    Validate inputs and return a clean OrderRequest.

    Raises:
        ValueError: If any parameter is invalid.
    """
    validated = validate_all(symbol, side, order_type, quantity, price)
    req = OrderRequest(
        symbol=validated["symbol"],
        side=validated["side"],
        order_type=validated["order_type"],
        quantity=validated["quantity"],
        price=validated["price"],
    )
    logger.info("Order request built: %s", req.summary())
    return req


def place_order(client: BinanceClient, order_req: OrderRequest) -> OrderResult:
    """
    Submit an OrderRequest via the BinanceClient.

    Returns:
        OrderResult — always succeeds or wraps errors rather than raising.
    """
    logger.info("Submitting order: %s", order_req.summary())

    try:
        raw = client.place_order(
            symbol=order_req.symbol,
            side=order_req.side,
            order_type=order_req.order_type,
            quantity=order_req.quantity,
            price=order_req.price,
        )
        result = OrderResult.from_response(raw)
        logger.info(
            "Order accepted | id=%s status=%s execQty=%s avgPrice=%s",
            result.order_id,
            result.status,
            result.executed_qty,
            result.avg_price,
        )
        return result

    except requests.HTTPError as exc:
        msg = f"HTTP error from Binance: {exc}"
        logger.error(msg)
        # Try to extract Binance error details
        if exc.response is not None:
            try:
                body = exc.response.json()
                msg = f"Binance error {body.get('code')}: {body.get('msg')}"
            except Exception:
                pass
        return OrderResult.from_error(msg)

    except requests.ConnectionError as exc:
        msg = f"Network connection error: {exc}"
        logger.error(msg)
        return OrderResult.from_error(msg)

    except requests.Timeout as exc:
        msg = f"Request timed out: {exc}"
        logger.error(msg)
        return OrderResult.from_error(msg)

    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        logger.exception(msg)
        return OrderResult.from_error(msg)
