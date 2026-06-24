# Claude Start Here

Read `AGENTS.md`, `CODEX.md`, `DEVELOPMENT_MEMORY.md`, and `README.md` before editing.

## Purpose

Billionaires SDK is a small Python wrapper around the Bridge API. It lets Python strategies send validated BUY/SELL signals with retries, idempotency, status checks, typed responses, async helpers, and basket orders.

## Current Branding

- Name: Billionaires SDK
- Package: `billionaires-sdk`
- Import: `billionaires_sdk`
- Env vars: `BILLIONAIRES_BASE_URL`, `BILLIONAIRES_API_KEY`
- Supported platforms: Billionaires Terminal and AlgoAdmin white-label deployments

Do not reintroduce legacy names.

## Checks

```bash
python -m unittest discover -s tests
python -m compileall .
```

Tests must not place live orders.
