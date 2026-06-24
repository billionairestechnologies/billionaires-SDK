from proalgotrade import BridgeClient


bridge = BridgeClient.from_env()
bridge.ensure_ready(require_paper=True)

responses = bridge.basket(
    [
        {"action": "BUY", "symbol": "RELIANCE", "exchange": "NSE", "quantity": 1},
        {"action": "SELL", "symbol": "TCS", "exchange": "NSE", "quantity": 1},
    ]
)

for response in responses:
    print(response.success, response.order)
