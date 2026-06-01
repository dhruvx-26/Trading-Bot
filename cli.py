from __future__ import annotations

import argparse
import os
import sys

from bot.client import BinanceClient
from bot.logging_config import setup_logging, get_logger
from bot.orders import build_order_request, place_order


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Binance API key (default: BINANCE_API_KEY env var)",
    )
    parser.add_argument(
        "--api-secret",
        default=None,
        metavar="SECRET",
        help="Binance API secret (default: BINANCE_API_SECRET env var)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level (default: INFO; file always gets DEBUG)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ping", help="Ping the Binance Futures Testnet")

    place_parser = subparsers.add_parser("place", help="Place a futures order")
    place_parser.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    place_parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    place_parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT"],
        type=str.upper,
        help="Order type: MARKET or LIMIT",
    )
    place_parser.add_argument(
        "--qty",
        required=True,
        metavar="QUANTITY",
        help="Order quantity, e.g. 0.001",
    )
    place_parser.add_argument(
        "--price",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders)",
    )

    return parser


def _resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Return (api_key, api_secret) from args or environment."""
    api_key = args.api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET", "")
    return api_key, api_secret


def cmd_ping(client: BinanceClient) -> int:
    """Run the ping command. Returns exit code."""
    ok = client.ping()
    if ok:
        print("✅  Binance Futures Testnet is reachable.")
        return 0
    else:
        print("❌  Could not reach Binance Futures Testnet.")
        return 1


def cmd_place(client: BinanceClient, args: argparse.Namespace, logger) -> int:
    """Run the place-order command. Returns exit code."""
    try:
        order_req = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.qty,
            price=args.price,
        )
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        print(f"\n❌  Validation error: {exc}\n")
        return 2

    print("\n" + "─" * 50)
    print("  ORDER REQUEST")
    print("─" * 50)
    print(f"  Symbol    : {order_req.symbol}")
    print(f"  Side      : {order_req.side}")
    print(f"  Type      : {order_req.order_type}")
    print(f"  Quantity  : {order_req.quantity}")
    print(f"  Price     : {order_req.price if order_req.price else 'MARKET'}")
    print("─" * 50 + "\n")

    result = place_order(client, order_req)

    print("─" * 50)
    print("  ORDER RESULT")
    print("─" * 50)
    print(result.pretty())
    print("─" * 50 + "\n")

    return 0 if result.success else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = get_logger("cli")

    logger.debug("CLI invoked with args: %s", vars(args))

    try:
        api_key, api_secret = _resolve_credentials(args)
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        print(f"\n❌  Configuration error: {exc}\n")
        sys.exit(1)

    if args.command == "ping":
        exit_code = cmd_ping(client)
    elif args.command == "place":
        exit_code = cmd_place(client, args, logger)
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
