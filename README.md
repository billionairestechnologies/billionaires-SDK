# Billionaires / ProAlgoTrade Bridge Python SDK

Use this SDK to send BUY/SELL signals from a Python strategy to the ProAlgoTrade Bridge API.

The SDK wraps:

```text
POST /api/signals/order
GET  /api/signals/status
```

It handles API-key headers, JSON encoding, retries, idempotency keys, timeout handling, response parsing, paper/live preflight checks, async wrappers, basket orders, and common validation.

## Install

Install directly from GitHub:

```bash
pip install git+https://github.com/billionairestechnologies/billionaires-SDK.git
```

For local development after cloning this repository:

```bash
git clone https://github.com/billionairestechnologies/billionaires-SDK.git
cd billionaires-SDK
pip install -e .
```

After package publishing:

```bash
pip install proalgotrade-bridge
```

## Environment

```text
PROALGOTRADE_BASE_URL=https://your-domain.com
PROALGOTRADE_API_KEY=bt_live_your_key
```

## Quick Start

```python
from proalgotrade import BridgeClient

bridge = BridgeClient.from_env()

bridge.ensure_ready(require_paper=True)

result = bridge.buy(
    symbol="NIFTY24JUN23500CE",
    exchange="NFO",
    quantity=50,
    product="MIS",
    pricetype="MARKET",
    group="Scalping",
)

print(result.success, result.success_count, result.failed_count)
```

## Status / Compatibility

```python
status = bridge.status()
print(status.api_version, status.paper, status.active_client_count)
```

Before live execution:

```python
bridge.ensure_ready(require_live=True)
```

For paper testing:

```python
bridge.ensure_ready(require_paper=True)
```

## Retries and Idempotency

Retries are enabled by default:

```python
bridge = BridgeClient.from_env(max_retries=2, retry_backoff=0.5)
```

Every order automatically includes a unique `idempotencyKey`. If a network retry repeats the same order, the platform returns the cached result instead of placing a duplicate order.

Use your own key when your strategy already has an order ID:

```python
bridge.buy(
    symbol="RELIANCE",
    exchange="NSE",
    quantity=1,
    idempotency_key="strategy-20260624-0001",
)
```

## Response Object

```python
result = bridge.sell(symbol="RELIANCE", exchange="NSE", quantity=1)

print(result.success)
print(result.dry_run)
print(result.target_count)
print(result.successful_results)
print(result.failed_results)

result.raise_for_failures()
```

Use `result.to_dict()` if you need the raw API response.

## Limit and Stop Orders

```python
bridge.buy(
    symbol="RELIANCE",
    exchange="NSE",
    quantity=1,
    product="MIS",
    pricetype="LIMIT",
    price=2450.50,
)
```

```python
bridge.sell(
    symbol="RELIANCE",
    exchange="NSE",
    quantity=1,
    product="MIS",
    pricetype="SL-M",
    trigger_price=2440.00,
)
```

## Group and Account Targeting

```python
bridge.buy(
    symbol="NIFTY24JUN23500CE",
    exchange="NFO",
    quantity=50,
    group="Scalping",
)
```

```python
bridge.order(
    action="BUY",
    symbol="NIFTY24JUN23500CE",
    exchange="NFO",
    quantity=50,
    groups=["Scalping", "HNI"],
)
```

```python
bridge.order(
    action="BUY",
    symbol="RELIANCE",
    exchange="NSE",
    quantity=1,
    account_ids=["ACCOUNT_UUID_1", "ACCOUNT_UUID_2"],
)
```

If no group or account is provided, the platform targets all active client accounts for that API key owner.

## Basket Orders

```python
responses = bridge.basket(
    [
        {"action": "BUY", "symbol": "RELIANCE", "exchange": "NSE", "quantity": 1},
        {"action": "SELL", "symbol": "TCS", "exchange": "NSE", "quantity": 1},
    ],
    require_paper=True,
)

for response in responses:
    print(response.success, response.order)
```

## Async Usage

```python
import asyncio
from proalgotrade import BridgeClient


async def main():
    bridge = BridgeClient.from_env()
    await bridge.async_ensure_ready(require_paper=True)
    result = await bridge.async_buy(
        symbol="NIFTY24JUN23500CE",
        exchange="NFO",
        quantity=50,
        group="Scalping",
    )
    print(result.success)


asyncio.run(main())
```

## Error Handling

```python
from proalgotrade import BridgeAPIError, BridgeConfigError

try:
    bridge.buy(symbol="RELIANCE", exchange="NSE", quantity=1)
except BridgeConfigError as exc:
    print("Local config error:", exc)
except BridgeAPIError as exc:
    print("Bridge API error:", exc.status_code, exc.response)
```

Use Paper Trade mode in the dashboard before live execution.

## Client Safety Checklist

Before live use:

1. Create a Bridge API key from the platform.
2. Turn Paper Trade ON.
3. Run `bridge.ensure_ready(require_paper=True)`.
4. Send one BUY and one SELL test signal.
5. Check platform execution logs.
6. Turn Paper Trade OFF only after payloads and logs are verified.
7. Use `bridge.ensure_ready(require_live=True)` before production startup.

## Support

For setup help, contact Billionaires Technologies support or your account manager.
