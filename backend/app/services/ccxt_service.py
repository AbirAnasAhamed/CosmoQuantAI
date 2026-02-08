import ccxt.async_support as ccxt
import json
import logging
from typing import List, Dict, Any
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

class CcxtService:
    """
    Service to handle dynamic asset and exchange discovery using CCXT.
    Implements caching using Redis to avoid rate limits.
    """
    
    # List of popular exchanges to prioritize or filter
    POPULAR_EXCHANGES = [
        'binance', 'kraken', 'coinbase', 'kucoin', 'bybit', 'okx', 'bitstamp', 
        'gateio', 'htx', 'mexc', 'bitget', 'gemini'
    ]

    def __init__(self):
        pass

    async def get_exchanges(self) -> List[Dict[str, str]]:
        """
        Returns a list of supported exchanges.
        Cached for 24 hours.
        """
        cache_key = "market_discovery:exchanges"
        
        # Try to get from cache
        redis = redis_manager.get_redis()
        if redis:
            cached_data = await redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

        # If not in cache, generate list
        # ccxt.exchanges is a simple list of strings. 
        # We will map them to a more useful structure and filter/sort.
        
        exchanges_list = []
        for exchange_id in ccxt.exchanges:
            if exchange_id in self.POPULAR_EXCHANGES:
                exchanges_list.append({
                    "id": exchange_id,
                    "name": exchange_id.title(),
                    "popular": True
                })
        
        # Sort: Popular first, then alphabetical
        exchanges_list.sort(key=lambda x: x['id'])
        
        # Cache the result
        if redis:
            await redis.setex(cache_key, 86400, json.dumps(exchanges_list)) # 24 hours
            
        return exchanges_list

    async def get_pairs(self, exchange_id: str) -> List[str]:
        """
        Returns a list of active pairs/symbols for a given exchange.
        Cached for 1 hour.
        """
        exchange_id = exchange_id.lower()
        cache_key = f"market_discovery:pairs:{exchange_id}"
        
        # Try to get from cache
        redis = redis_manager.get_redis()
        if redis:
            cached_data = await redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

        # Check if exchange is valid
        if exchange_id not in ccxt.exchanges:
            raise ValueError(f"Exchange '{exchange_id}' not found in CCXT.")

        api = None
        try:
            # Instantiate exchange class dynamically
            exchange_class = getattr(ccxt, exchange_id)
            api = exchange_class({'enableRateLimit': True})
            
            # Load markets
            markets = await api.load_markets()
            
            # Filter pairs (active only, spot/swap preferred if distinguishable, but generally all active symbols)
            pairs = []
            for symbol, market in markets.items():
                if market.get('active', True):
                    pairs.append(symbol)
            
            pairs.sort()
            
            # Cache the result
            if redis:
                await redis.setex(cache_key, 3600, json.dumps(pairs)) # 1 hour
            
            return pairs
            
        except Exception as e:
            logger.error(f"Error fetching pairs for {exchange_id}: {e}")
            raise e
        finally:
            if api:
                await api.close()

ccxt_service = CcxtService()
