import os

from billionaires_sdk import BridgeClient


def on_signal(symbol: str, side: str) -> None:
    bridge = BridgeClient.from_env()
    bridge.ensure_ready(require_paper=True)
    order = bridge.buy if side.upper() == "BUY" else bridge.sell
    result = order(
        symbol=symbol,
        exchange="NFO",
        quantity=50,
        product="MIS",
        pricetype="MARKET",
        group=os.environ.get("BILLIONAIRES_GROUP", "Scalping"),
    )
    print(result.success, result.success_count, result.failed_count)


if __name__ == "__main__":
    on_signal("NIFTY24JUN23500CE", "BUY")
