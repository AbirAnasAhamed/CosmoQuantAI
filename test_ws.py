import asyncio
import websockets

async def test():
    uri = "ws://localhost:8000/api/v1/market-depth/ws/binance/BTC/USDT"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected!")
            await ws.close()
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test())
