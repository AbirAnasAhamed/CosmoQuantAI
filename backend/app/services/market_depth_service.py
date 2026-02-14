import ccxt.async_support as ccxt
import json
import logging
import math
from typing import Dict, List, Any, Optional
from app.core.config import settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

class MarketDepthService:
    """
    Service to fetch and aggregate order book data (Market Depth) for visualization.
    Implements caching using Redis to prevent rate limiting.
    """

    def __init__(self):
        pass

    async def fetch_order_book_heatmap(
        self, 
        symbol: str, 
        exchange_id: str = 'binance', 
        depth: int = 100, 
        bucket_size: float = 50.0
    ) -> Dict[str, Any]:
        """
        Fetches the order book and aggregates it into price buckets.
        
        Args:
            symbol (str): Trading pair, e.g., 'BTC/USDT'.
            exchange_id (str): Exchange name, e.g., 'binance'.
            depth (int): Number of order book levels to fetch.
            bucket_size (float): Price range for grouping orders.

        Returns:
            Dict[str, Any]: {
                "current_price": float,
                "bids": [{"price": float, "volume": float}, ...],
                "asks": [{"price": float, "volume": float}, ...],
                "symbol": str,
                "exchange": str
            }
        """
        # normalize inputs
        symbol = symbol.upper()
        exchange_id = exchange_id.lower()
        
        # 1. Check Cache
        cache_key = f"market_depth:{exchange_id}:{symbol}:{bucket_size}"
        redis = redis_manager.get_redis()
        
        if redis:
            cached_data = await redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

        # 2. Fetch Live Data
        exchange_class = getattr(ccxt, exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Exchange '{exchange_id}' not supported.")

        exchange = exchange_class({'enableRateLimit': True})
        
        try:
            # Load markets to verify symbol support (optional but good for validation)
            # await exchange.load_markets() 
            # Skipping load_markets for speed if we assume symbol is correct or handling error later
            
            # Fetch Order Book
            order_book = await exchange.fetch_order_book(symbol, limit=depth)
            
            # Fetch Ticker for current price (or use mid price from order book)
            ticker = await exchange.fetch_ticker(symbol)
            current_price = ticker.get('last', 0.0)

            # 3. Aggregate Data
            aggregated_bids = self._aggregate_orders(order_book['bids'], bucket_size, is_bid=True)
            aggregated_asks = self._aggregate_orders(order_book['asks'], bucket_size, is_bid=False)
            
            result = {
                "symbol": symbol,
                "exchange": exchange_id,
                "current_price": current_price,
                "bids": aggregated_bids,
                "asks": aggregated_asks
            }

            # 4. Cache Result (5 seconds TTL)
            if redis:
                await redis.setex(cache_key, 5, json.dumps(result))

            return result

        except Exception as e:
            logger.error(f"Error fetching market depth for {symbol} on {exchange_id}: {e}")
            raise e
        finally:
            await exchange.close()

    def _aggregate_orders(self, orders: List[List[float]], bucket_size: float, is_bid: bool) -> List[Dict[str, float]]:
        """
        Groups orders into price buckets.
        
        Args:
            orders: List of [price, amount]
            bucket_size: Size of each price bucket
            is_bid: True if aggregating bids (round down), False for asks (round up)
            
        Returns:
            List of dictionaries with 'price' (bucket) and 'volume' (sum).
        """
        buckets = {}
        
        for price, amount in orders:
            if bucket_size > 0:
                if is_bid:
                    # For bids, we want to group e.g. 99.9 -> 95 (if bucket is 5)
                    # Floor division
                    bucket_price = math.floor(price / bucket_size) * bucket_size
                else:
                    # For asks, we want to group e.g. 100.1 -> 105
                    # Ceiling division
                    bucket_price = math.ceil(price / bucket_size) * bucket_size
            else:
                bucket_price = price
                
            # Avoid float precision issues for keys
            bucket_price = round(bucket_price, 2)
            
            if bucket_price not in buckets:
                buckets[bucket_price] = 0.0
            buckets[bucket_price] += amount

        # Convert to list and sort
        sorted_buckets = [
            {"price": price, "volume": volume} 
            for price, volume in buckets.items()
        ]
        
        # Sort bids descending (highest price first), asks ascending (lowest price first)
        sorted_buckets.sort(key=lambda x: x['price'], reverse=is_bid)
        
        return sorted_buckets

market_depth_service = MarketDepthService()
