"""
Input validation for trading bot parameters.
All validation functions raise ValueError with a clear message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from bot.logging_config import get_logger

logger = get_logger(__name__)

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading symbol.

    Rules:
    - Non-empty string
    - Alphanumeric characters only (no spaces, special chars)
    - Uppercased automatically

    Returns:
        Uppercased symbol string.

    Raises:
        ValueError: If the symbol is invalid.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")

    symbol = symbol.strip().upper()

    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only alphanumeric characters are allowed (e.g. BTCUSDT)."
        )

    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side.

    Returns:
        Uppercased side string ('BUY' or 'SELL').

    Raises:
        ValueError: If the side is not BUY or SELL.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Returns:
        Uppercased order type string ('MARKET' or 'LIMIT').

    Raises:
        ValueError: If the type is not MARKET or LIMIT.
    """
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """
    Validate order quantity.

    Rules:
    - Must be a positive number
    - Converted to Decimal for precision

    Returns:
        Decimal quantity.

    Raises:
        ValueError: If the quantity is invalid or non-positive.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a numeric value.")

    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: str | float | None, order_type: str) -> Decimal | None:
    """
    Validate order price.

    Rules:
    - Required (and must be positive) for LIMIT orders
    - Must be None / omitted for MARKET orders (ignored if supplied, with a warning)

    Args:
        price: The price value (can be None).
        order_type: 'MARKET' or 'LIMIT' (already validated).

    Returns:
        Decimal price for LIMIT orders, None for MARKET orders.

    Raises:
        ValueError: If a LIMIT order is missing a price, or the price is non-positive.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        if price is not None:
            logger.warning(
                "Price '%s' provided for MARKET order — it will be ignored.", price
            )
        return None

    # LIMIT order — price is required
    if price is None:
        raise ValueError("Price is required for LIMIT orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a numeric value.")

    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")

    logger.debug("Price validated: %s", p)
    return p


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
) -> dict:
    """
    Run all validations and return a clean parameter dict.

    Returns:
        Dict with keys: symbol, side, order_type, quantity, price.

    Raises:
        ValueError: On any validation failure.
    """
    validated_symbol = validate_symbol(symbol)
    validated_side = validate_side(side)
    validated_type = validate_order_type(order_type)
    validated_qty = validate_quantity(quantity)
    validated_price = validate_price(price, validated_type)

    return {
        "symbol": validated_symbol,
        "side": validated_side,
        "order_type": validated_type,
        "quantity": validated_qty,
        "price": validated_price,
    }
