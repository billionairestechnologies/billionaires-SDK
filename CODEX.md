# Codex Start Here

This repository is the standalone Python SDK for the Bridge API.

## Current State

- Remote: `https://github.com/billionairestechnologies/billionaires-SDK.git`
- Branch: `main`
- Current pushed commit: `d73e8a4 chore: rebrand package as Billionaires SDK`
- Package: `billionaires-sdk`
- Import: `billionaires_sdk`

## Client Install

```bash
pip install git+https://github.com/billionairestechnologies/billionaires-SDK.git
```

After package publishing:

```bash
pip install billionaires-sdk
```

## Local Development

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests
```

On Windows, `py -3` is also acceptable.

## Platform Compatibility

- Billionaires Terminal supports this SDK.
- AlgoAdmin white-label deployments also support this SDK.
- Do not brand this SDK as any old platform name.
- Algo deployments use `deployment_id` in Python; the SDK sends it to the Bridge API as `deploymentId`.

## Required Checks

```bash
python -m unittest discover -s tests
python -m compileall .
```
