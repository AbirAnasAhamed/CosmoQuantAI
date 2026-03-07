import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Any, List, Optional
import ccxt.async_support as ccxt
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

class OrderBlockDetector:
    """
    Analyzes market depth (bids/asks) to detect dense concentrations of orders ("Smart Money" blocks).
    """
    def __init__(self, volume_threshold_multiplier: float = 3.0):
        # We look for price levels where volume is X times the average volume in the book
        self.volume_threshold_multiplier = volume_threshold_multiplier

    def detect_blocks(self, orderbook: Dict[str, Any], block_type: str = "bids") -> List[Dict[str, float]]:
        """
        Scans a side of the order book for order blocks.
        block_type: 'bids' (support) or 'asks' (resistance)
        Returns a list of detected blocks: [{"price": P, "volume": V}]
        """
        levels = orderbook.get(block_type, [])
        if not levels:
            return []

        # levels format from CCXT is usually [[price, volume], ...]
        # Calculate average volume
        total_volume = sum(level[1] for level in levels)
        avg_volume = total_volume / len(levels) if levels else 0

        # Threshold for considering a level an "Order Block"
        threshold = avg_volume * self.volume_threshold_multiplier

        detected_blocks = []
        for price, volume in levels:
            if volume >= threshold:
                detected_blocks.append({
                    "price": float(price),
                    "volume": float(volume),
                    "type": block_type
                })

        return detected_blocks

class OrderBlockExecutionEngine:
    """
    Handles trading execution securely. Segregates Real (CCXT) and Paper trading.
    """
    def __init__(self, config: Dict[str, Any]):
        self.is_paper_trading = config.get("is_paper_trading", True)
        self.exchange_id = config.get("exchange", "binance").lower()
        self.pair = config.get("pair")
        self.api_key = config.get("apiKey")
        self.api_secret = config.get("apiSecret")
        
        # Paper trading state
        self.paper_balance_quote = config.get("paper_balance_initial", 10000.0)
        self.paper_balance_base = 0.0
        self.active_position = None # Simplification: only 1 active position for the bot

    async def execute_trade(self, side: str, amount: float, price: float) -> Optional[Dict[str, Any]]:
        """
        Executes a trade, routing to either Paper or Real logic.
        """
        if self.is_paper_trading:
            return await self._execute_paper(side, amount, price)
        else:
            return await self._execute_real(side, amount, price)

    async def _execute_paper(self, side: str, amount: float, price: float) -> Optional[Dict[str, Any]]:
        trade_id = f"paper_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()
        
        cost = amount * price
        
        if side == "buy":
            if self.paper_balance_quote >= cost:
                self.paper_balance_quote -= cost
                self.paper_balance_base += amount
                self.active_position = {"side": "long", "entry_price": price, "amount": amount}
                logger.debug(f"[PAPER] Bought {amount} {self.pair} at {price}. Cost: {cost}")
            else:
                logger.warning(f"[PAPER] Insufficient balance for BUY. Need {cost}, have {self.paper_balance_quote}")
                return None
        elif side == "sell":
             if self.paper_balance_base >= amount:
                 self.paper_balance_base -= amount
                 self.paper_balance_quote += cost
                 self.active_position = None
                 logger.debug(f"[PAPER] Sold {amount} {self.pair} at {price}. Value: {cost}")
             else:
                 logger.warning(f"[PAPER] Insufficient base balance for SELL. Need {amount}, have {self.paper_balance_base}")
                 return None
                 
        return {
            "id": trade_id,
            "side": side,
            "amount": amount,
            "price": price,
            "timestamp": timestamp,
            "status": "closed"
        }

    async def _execute_real(self, side: str, amount: float, price: float) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.api_secret:
            logger.error("[REAL] Missing API credentials.")
            return None
            
        exchange_class = getattr(ccxt, self.exchange_id)
        exchange = exchange_class({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True}
        })
        
        try:
            # We use market order for immediate execution upon block detection for simplicity here
            # In production, Limit orders near the block might be preferred.
            logger.info(f"[REAL] Executing {side} order on {self.exchange_id} for {amount} {self.pair}")
            order = await exchange.create_market_order(self.pair, side, amount)
            return order
        except Exception as e:
            logger.error(f"[REAL] Order execution failed: {e}")
            return None
        finally:
            await exchange.close()

class OrderBlockBotTask:
    """
    The main asynchronous bot worker that ties Detection and Execution together.
    """
    def __init__(self, bot_id: int, config: Dict[str, Any]):
        self.bot_id = bot_id
        self.config = config
        self.pair = config.get("pair")
        self.exchange_id = config.get("exchange", "binance").lower()
        self.trade_amount = config.get("trade_amount", 0.01) # Base currency amount
        
        self.detector = OrderBlockDetector(volume_threshold_multiplier=config.get("threshold_multiplier", 3.0))
        self.engine = OrderBlockExecutionEngine(config)
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        # We will use CCXT just to fetch public orderbook data rapidly for detection
        self._public_exchange = getattr(ccxt, self.exchange_id)({'enableRateLimit': True})

    async def start(self):
        self.running = True
        logger.info(f"Order Block Bot {self.bot_id} started for {self.pair}")
        await self._log(f"Bot started. Searching for order blocks on {self.pair}...")
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
        await self._public_exchange.close()
        logger.info(f"Order Block Bot {self.bot_id} stopped.")
        await self._log("Bot stopped.")

    async def _log(self, message: str, level: str = "info", data: dict = None):
        """
        Broadcast logs to Redis so they stream to the frontend via WS.
        """
        redis = redis_manager.get_redis()
        if not redis: return
        
        log_payload = {
            "channel": f"logs_{self.bot_id}",
            "data": {
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "data": data
            }
        }
        await redis.publish("bot_logs", json.dumps(log_payload))

    async def _run_loop(self):
        try:
            while self.running:
                # 1. Fetch live order book
                try:
                    orderbook = await self._public_exchange.fetch_order_book(self.pair, limit=50)
                except Exception as e:
                    await self._log(f"Error fetching order book: {e}", "error")
                    await asyncio.sleep(2)
                    continue

                # 2. Detect Smart Money Blocks
                support_blocks = self.detector.detect_blocks(orderbook, "bids")
                resistance_blocks = self.detector.detect_blocks(orderbook, "asks")

                all_blocks = support_blocks + resistance_blocks
                if all_blocks:
                    # Notify frontend visually
                    await self._log(f"Detected {len(all_blocks)} order block(s)", "info", {"blocks": all_blocks})

                # 3. Strategy Logic (Extremely basic for demonstration)
                # If we detect major support (big bid wall) near the current spread, go Long.
                # If we detect major resistance (big ask wall) near the spread, go Short/Sell.
                
                # Fetch current price briefly
                ticker = await self._public_exchange.fetch_ticker(self.pair)
                current_price = ticker.get('last')
                
                if current_price and not self.engine.active_position:
                    # Look for a support block close to current price (e.g. within 0.5%)
                    for b in support_blocks:
                        if (current_price - b['price']) / b['price'] < 0.005:
                            await self._log(f"Price approaching massive support wall at {b['price']}. Executing BUY.", "warn")
                            trade_res = await self.engine.execute_trade("buy", self.trade_amount, current_price)
                            if trade_res:
                                await self._log(f"BUY executed at {current_price}", "success", {"trade": trade_res})
                            break
                            
                elif current_price and self.engine.active_position:
                     entry = self.engine.active_position['entry_price']
                     # Exit logic: if we are near a resistance block, or simply taking 1% profit
                     for b in resistance_blocks:
                         if (b['price'] - current_price) / current_price < 0.005:
                             await self._log(f"Price approaching resistance block at {b['price']}. Executing SELL.", "warn")
                             trade_res = await self.engine.execute_trade("sell", self.trade_amount, current_price)
                             if trade_res:
                                 await self._log(f"SELL executed at {current_price}", "success", {"trade": trade_res})
                             break
                     
                     # Simple TP/SL
                     if (current_price - entry) / entry >= 0.01: # 1% TP
                         trade_res = await self.engine.execute_trade("sell", self.trade_amount, current_price)
                         await self._log(f"Take profit executed at {current_price}", "success", {"trade": trade_res})
                     elif (entry - current_price) / entry >= 0.01: # 1% SL
                         trade_res = await self.engine.execute_trade("sell", self.trade_amount, current_price)
                         await self._log(f"Stop loss executed at {current_price}", "error", {"trade": trade_res})

                # Poll interval
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Bot Task crashed: {e}")
            await self._log(f"Bot crashed: {e}", "error")
