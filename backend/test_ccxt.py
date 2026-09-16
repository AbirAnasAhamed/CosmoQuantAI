import asyncio
import ccxt.async_support as ccxt

async def test():
    ex = ccxt.binance({'options': {'defaultType': 'swap'}})
    await ex.load_markets()
    print("XAUT/USDT in markets:", 'XAUT/USDT' in ex.markets)
    print("XAUT/USDT:USDT in markets:", 'XAUT/USDT:USDT' in ex.markets)
    await ex.close()

asyncio.run(test())
