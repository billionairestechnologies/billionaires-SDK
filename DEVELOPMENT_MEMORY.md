# Billionaires SDK Development Memory

Last updated: 2026-06-24

## Current State

- Repo: `github.com/billionairestechnologies/billionaires-SDK`
- Branch: `main`
- Current pushed commit: `d73e8a4 chore: rebrand package as Billionaires SDK`
- Package name: `billionaires-sdk`
- Import name: `billionaires_sdk`
- Version: `1.0.0`

## What The SDK Does

The SDK wraps the Bridge API:

```text
GET  /api/signals/status
POST /api/signals/order
```

It provides:

- API-key headers
- JSON request handling
- retries and backoff
- automatic idempotency keys
- Paper/Live preflight checks
- typed `BridgeResponse` and `BridgeStatus`
- BUY, SELL, generic order, basket, and async helpers
- `deployment_id` support for Algo deployments; serialized to API field `deploymentId`
- local validation for quantity, side, order type, price, trigger price, base URL, and retry settings

## Client Setup

Install from GitHub:

```bash
pip install git+https://github.com/billionairestechnologies/billionaires-SDK.git
```

Use:

```python
from billionaires_sdk import BridgeClient

bridge = BridgeClient.from_env()
bridge.ensure_ready(require_paper=True)

bridge.buy(
    symbol="NIFTY24JUN23500CE",
    exchange="NFO",
    quantity=50,
    deployment_id="active-deployment-id",
)
```

Env vars:

```text
BILLIONAIRES_BASE_URL=https://your-domain.com
BILLIONAIRES_API_KEY=bt_live_your_key
```

## Compatibility

- Billionaires Terminal supports this SDK.
- AlgoAdmin white-label deployments also support this SDK.
- The SDK should remain generic and client-friendly.

## Validation Already Run

```powershell
py -3 -m unittest discover -s tests
py -3 -m compileall .
pip install git+https://github.com/billionairestechnologies/billionaires-SDK.git
```

All passed on 2026-06-24. No live broker order was placed.

## Remaining Work

- Publish package as `billionaires-sdk` if public package install is desired.
- Add release tags.
- Add a real Paper Trade E2E guide once a test tenant/API key is available.
- Keep examples minimal and safe.
