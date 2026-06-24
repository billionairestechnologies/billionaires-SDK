import asyncio

from billionaires_sdk import BridgeClient


async def main() -> None:
    bridge = BridgeClient.from_env()
    await bridge.async_ensure_ready(require_paper=True)
    result = await bridge.async_buy(
        symbol="NIFTY24JUN23500CE",
        exchange="NFO",
        quantity=50,
        product="MIS",
        pricetype="MARKET",
        group="Scalping",
    )
    print(result.success, result.success_count, result.failed_count)


if __name__ == "__main__":
    asyncio.run(main())
