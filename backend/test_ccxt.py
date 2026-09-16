import asyncio
import ccxt.async_support as ccxt

async def test():
    ex = ccxt.binance({'options': {'defaultType': 'swap'}})
    await ex.load_markets()
    print("BTC/USDT in markets:", 'BTC/USDT' in ex.markets)
    print("BTC/USDT:USDT in markets:", 'BTC/USDT:USDT' in ex.markets)
    print("Funding rate for BTC/USDT:USDT:", await ex.fetch_funding_rate('BTC/USDT:USDT'))
    await ex.close()

asyncio.run(test())
