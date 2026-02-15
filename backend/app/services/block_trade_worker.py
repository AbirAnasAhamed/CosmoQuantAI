
import asyncio
import json
import logging
from app.services.block_trade_monitor import block_trade_monitor
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

class BlockTradeWorker:
    def __init__(self):
        self.running = False
        self.known_trade_ids = set() # Simple deduplication using a set (in-memory)
        # In production, use Redis SET with expiration for robust deduplication across restarts

    async def start(self):
        logger.info("🚀 Block Trade Worker Started")
        self.running = True
        
        # Ensure Redis is initialized
        if not redis_manager.redis:
             await redis_manager.init_redis()

        while self.running:
            try:
                # 1. Get Config
                config = block_trade_monitor.get_config()
                # For now, we cycle through active exchanges for a few major pairs.
                # Ideally, this list comes from a "Market Discovery" service or config.
                target_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] 
                
                for symbol in target_symbols:
                    if not self.running: break
                    
                    # 2. Fetch Trades
                    trades_map = await block_trade_monitor.fetch_recent_trades(symbol, limit=50)
                    
                    for exchange_id, trades in trades_map.items():
                        new_trades = []
                        for trade in trades:
                            # Create a unique ID for deduplication
                            # Some exchanges provide ID, some don't. Fallback to timestamp+price+amount
                            trade_id = trade.get('id')
                            if not trade_id:
                                trade_id = f"{exchange_id}_{symbol}_{trade['timestamp']}_{trade['price']}_{trade['amount']}"
                            
                            if trade_id not in self.known_trade_ids:
                                self.known_trade_ids.add(trade_id)
                                new_trades.append(trade)
                                
                                # Keep set size manageable
                                if len(self.known_trade_ids) > 10000:
                                    self.known_trade_ids = set(list(self.known_trade_ids)[-5000:])
                        
                        # 3. Publish New Block Trades
                        if new_trades:
                            logger.info(f"💎 Detected {len(new_trades)} block trades on {exchange_id} for {symbol}")
                            
                            payload = {
                                "type": "block_trade",
                                "data": new_trades
                            }
                            
                            await redis_manager.redis.publish("block_trade_stream", json.dumps(payload))
                
                await asyncio.sleep(5)  # Poll interval

            except Exception as e:
                logger.error(f"Block Trade Worker Error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self.running = False
        logger.info("🛑 Block Trade Worker Stopped")

block_trade_worker = BlockTradeWorker()
