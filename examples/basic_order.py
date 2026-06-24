import os

from billionaires_sdk import BridgeAPIError, BridgeClient, BridgeConfigError


bridge = BridgeClient(
    base_url=os.environ["BILLIONAIRES_BASE_URL"],
    api_key=os.environ["BILLIONAIRES_API_KEY"],
)

try:
    bridge.ensure_ready(require_paper=True)
    result = bridge.buy(
        symbol="NIFTY24JUN23500CE",
        exchange="NFO",
        quantity=50,
        product="MIS",
        pricetype="MARKET",
        deployment_id="paste-active-deployment-id",
        group="Scalping",
    )
    print(result.success, result.success_count, result.failed_count)
    result.raise_for_failures()
except BridgeConfigError as exc:
    print(f"Config error: {exc}")
except BridgeAPIError as exc:
    print(f"API error: {exc}")
