# Agent Handoff

Read this before making changes. This file is for Codex, Claude, and any future AI/code agent.

## What This Repo Is

- Product: Billionaires SDK
- Repo: `github.com/billionairestechnologies/billionaires-SDK`
- Purpose: Python client for Billionaires Terminal Bridge API and supported AlgoAdmin white-label deployments
- Package name: `billionaires-sdk`
- Import name: `billionaires_sdk`
- Current pushed state: `d73e8a4 chore: rebrand package as Billionaires SDK`

## First Files To Read

1. `AGENTS.md`
2. `CODEX.md`
3. `CLAUDE.md`
4. `DEVELOPMENT_MEMORY.md`
5. `README.md`
6. `billionaires_sdk/client.py`
7. `tests/test_client.py`

## API Contract

The SDK wraps:

```text
GET  /api/signals/status
POST /api/signals/order
```

Auth uses:

```text
x-bt-api-key: <key>
```

The SDK default env vars are:

```text
BILLIONAIRES_BASE_URL
BILLIONAIRES_API_KEY
```

Algo deployment targeting:

```python
bridge.buy(..., deployment_id="active-deployment-id")
```

The SDK serializes `deployment_id` as Bridge API field `deploymentId`.

## Safety

- Do not reintroduce legacy package/import/env names.
- Do not place live broker orders in tests.
- Use Paper Trade mode for real platform E2E checks.
- Keep examples simple and client-friendly.

## Checks

```powershell
py -3 -m unittest discover -s tests
py -3 -m compileall .
```

Clean generated `__pycache__`, `build`, and `*.egg-info` folders before committing.
