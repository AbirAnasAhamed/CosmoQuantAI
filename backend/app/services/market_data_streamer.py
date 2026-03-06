import asyncio
import json
import logging
import ccxt.pro as ccxtpro
from typing import Dict, Set

from app.core.redis import redis_manager
from app.helpers.orderbook_math import calculate_dynamic_wall_threshold

logger = logging.getLogger(__name__)

class MarketDataStreamer:
    """
    Singleton class to manage background CCXT WebSocket connections 
    and publish market depth data to Redis Pub/Sub.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MarketDataStreamer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._active_streams: Set[str] = set()
        self._exchange_instances: Dict[str, ccxtpro.Exchange] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._initialized = True

    async def start_streaming(self, exchange_id: str, symbol: str):
        """Starts streaming order book data for a given exchange and symbol if not already running."""
        stream_key = f"{exchange_id}:{symbol}"
        if stream_key in self._active_streams:
            return

        self._active_streams.add(stream_key)
        
        # Start the background task
        task = asyncio.create_task(self._stream_order_book(exchange_id, symbol, stream_key))
        self._tasks[stream_key] = task

    async def _get_exchange_instance(self, exchange_id: str) -> ccxtpro.Exchange:
        if exchange_id not in self._exchange_instances:
            exchange_class = getattr(ccxtpro, exchange_id.lower(), None)
            if not exchange_class:
                raise ValueError(f"Exchange {exchange_id} not supported")
            
            self._exchange_instances[exchange_id] = exchange_class({'enableRateLimit': True})
            
        return self._exchange_instances[exchange_id]

    async def _stream_order_book(self, exchange_id: str, symbol: str, stream_key: str):
        logger.info(f"🚀 Starting background CCXT stream for {stream_key}")
        redis = redis_manager.get_redis()
        channel = f"market_depth_stream:{exchange_id}:{symbol}"
        
        try:
            exchange = await self._get_exchange_instance(exchange_id)
        except Exception as e:
            logger.error(f"Failed to initialize exchange {exchange_id} for {symbol}: {e}")
            self._active_streams.discard(stream_key)
            return

        while stream_key in self._active_streams:
            try:
                # CCXT watch_order_book handles the WS connection gracefully behind the scenes
                orderbook = await exchange.watch_order_book(symbol.upper(), limit=50)

                bids = []
                bid_total = 0
                for bid in orderbook.get('bids', []):
                    price = float(bid[0])
                    size = float(bid[1])
                    bid_total += size
                    bids.append({"price": price, "size": size, "total": bid_total})
                    
                asks = []
                ask_total = 0
                for ask in orderbook.get('asks', []):
                    price = float(ask[0])
                    size = float(ask[1])
                    ask_total += size
                    asks.append({"price": price, "size": size, "total": ask_total})
                
                wall_threshold = calculate_dynamic_wall_threshold(bids, asks)
                
                walls = []
                for ask in asks:
                    if ask["size"] >= wall_threshold:
                        walls.append({"price": ask["price"], "type": "sell", "size": ask["size"]})
                for bid in bids:
                    if bid["size"] >= wall_threshold:
                        walls.append({"price": bid["price"], "type": "buy", "size": bid["size"]})
                        
                current_price = 0
                if asks and bids:
                    current_price = (asks[0]["price"] + bids[0]["price"]) / 2
                
                payload = {
                    "bids": bids,
                    "asks": asks,
                    "walls": walls,
                    "currentPrice": current_price
                }
                
                # Publish to Redis
                if redis:
                    await redis.publish(channel, json.dumps(payload))
                
            except Exception as e:
                logger.error(f"Error watching orderbook {symbol} on {exchange_id}: {e}")
                if "does not have market symbol" in str(e).lower() or "bad symbol" in str(e).lower():
                    logger.error(f"Invalid symbol {symbol} for exchange {exchange_id}")
                    if redis:
                        await redis.publish(channel, json.dumps({"error": f"Invalid symbol {symbol} or exchange error"}))
                    break
                    
                await asyncio.sleep(5) # Backoff before reconnecting
                
        # Cleanup
        self._active_streams.discard(stream_key)
        logger.info(f"🛑 Stopped background CCXT stream for {stream_key}")

    async def stop_all(self):
        """Stops all running streams and closes exchange instances."""
        self._active_streams.clear()
        
        # Cancel all tasks
        for task in self._tasks.values():
            task.cancel()
            
        # Close all exchange instances
        for exchange in self._exchange_instances.values():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange instance: {e}")
                
        self._exchange_instances.clear()
        self._tasks.clear()

market_data_streamer = MarketDataStreamer()
