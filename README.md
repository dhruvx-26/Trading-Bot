# Trading Bot — Binance Futures Testnet

A clean, well-structured Python CLI for placing **Market** and **Limit** orders on the
[Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com).

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, retries, HTTP)
│   ├── orders.py          # Order placement logic + structured result objects
│   ├── validators.py      # Input validation (raises ValueError on bad input)
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log    # Auto-created; sample logs included
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Register on Binance Futures Testnet

1. Visit <https://testnet.binancefuture.com> and create an account.
2. Navigate to **API Management** and generate a key pair.
3. Save your **API Key** and **Secret** — you'll need them below.

### 2. Clone / download the project

```bash
git clone https://github.com/your-username/trading_bot.git
cd trading_bot
```

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set credentials

**Option A — Environment variables (recommended)**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

Add these to `~/.bashrc` / `~/.zshrc` to persist them.

**Option B — CLI flags**

Pass `--api-key` and `--api-secret` directly on every command (see examples below).

---

## How to Run

### Ping the testnet

```bash
python cli.py ping
```

Expected output:
```
✅  Binance Futures Testnet is reachable.
```

---

### Place a Market BUY order

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --qty 0.001
```

Sample output:
```
──────────────────────────────────────────────────
  ORDER REQUEST
──────────────────────────────────────────────────
  Symbol    : BTCUSDT
  Side      : BUY
  Type      : MARKET
  Quantity  : 0.001
  Price     : MARKET
──────────────────────────────────────────────────

──────────────────────────────────────────────────
  ORDER RESULT
──────────────────────────────────────────────────
✅  Order placed successfully
   Order ID   : 4751823901
   Symbol     : BTCUSDT
   Side       : BUY
   Type       : MARKET
   Status     : FILLED
   Orig Qty   : 0.001
   Exec Qty   : 0.001
   Avg Price  : 67345.20
──────────────────────────────────────────────────
```

---

### Place a Limit SELL order

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --qty 0.001 \
  --price 70000
```

Sample output:
```
──────────────────────────────────────────────────
  ORDER REQUEST
──────────────────────────────────────────────────
  Symbol    : BTCUSDT
  Side      : SELL
  Type      : LIMIT
  Quantity  : 0.001
  Price     : 70000
──────────────────────────────────────────────────

──────────────────────────────────────────────────
  ORDER RESULT
──────────────────────────────────────────────────
✅  Order placed successfully
   Order ID   : 4751824087
   Symbol     : BTCUSDT
   Side       : SELL
   Type       : LIMIT
   Status     : NEW
   Orig Qty   : 0.001
   Exec Qty   : 0
   Limit Price: 70000
──────────────────────────────────────────────────
```

Status `NEW` means the order is resting on the book waiting to be filled.

---

### Enable DEBUG output

```bash
python cli.py --log-level DEBUG place --symbol ETHUSDT --side BUY --type MARKET --qty 0.01
```

DEBUG mode prints raw request params and response bodies to the console
(and always writes them to the log file regardless of console level).

---

### Pass credentials inline

```bash
python cli.py \
  --api-key abc123 \
  --api-secret xyz789 \
  place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## CLI Reference

```
usage: trading_bot [-h] [--api-key KEY] [--api-secret SECRET]
                   [--log-level {DEBUG,INFO,WARNING,ERROR}]
                   {ping,place} ...

Subcommands:
  ping              Ping the Binance Futures Testnet
  place             Place a futures order
    --symbol        Trading pair, e.g. BTCUSDT         (required)
    --side          BUY or SELL                        (required)
    --type          MARKET or LIMIT                    (required)
    --qty           Order quantity, e.g. 0.001         (required)
    --price         Limit price (required for LIMIT)
```

---

## Logging

Logs are written to `logs/trading_bot.log` (auto-created).

- **File**: always captures DEBUG and above; rotates at 5 MB, keeps 3 backups.
- **Console**: defaults to INFO; use `--log-level DEBUG` to see raw API traffic.

Log format:
```
2025-06-01 10:12:05 | INFO     | bot.client:143 | Order placed | orderId=4751823901 ...
```

Sample logs for a MARKET order and a LIMIT order are pre-included in `logs/trading_bot.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API credentials | Exits immediately with a clear message |
| Invalid symbol / side / type | Validation error printed; no API call made |
| Negative / zero quantity | Validation error |
| LIMIT order with no price | Validation error |
| Binance API error (e.g. -1121 Invalid symbol) | Error code + message displayed |
| Network timeout / connection failure | Friendly error message + logged |
| HTTP 5xx from Binance | Auto-retried up to 3 times with backoff |

---

## Assumptions

1. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`.
   To use mainnet, change `TESTNET_BASE_URL` in `bot/client.py`.
2. **USDT-M perpetual futures** — the `/fapi/v1/order` endpoint is used.
3. **Time-in-force** defaults to `GTC` (Good Till Cancelled) for LIMIT orders.
4. **Decimal precision** — quantities and prices are handled as Python `Decimal` objects
   to avoid floating-point rounding issues; they're serialised to strings for the API.
5. **No leverage / margin management** — use the Binance UI or extend `client.py` as needed.
6. **Python 3.9+** required (uses `|` union type hints internally).

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client with session management |
| `urllib3` | Retry / backoff strategy |

No third-party Binance SDK is used — all signing and requests are implemented from scratch
for full transparency and testability.
