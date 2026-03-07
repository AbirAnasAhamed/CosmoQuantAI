import asyncio
import logging
import time
from typing import Dict, Any, Optional
import ccxt.async_support as ccxt
from app.strategies.order_block_bot import OrderBlockExecutionEngine

logger = logging.getLogger(__name__)

class WallHunterBot:
    def __init__(self, bot_id: int, config: Dict[str, Any]):
        self.bot_id = bot_id
        self.config = config
        self.exchange_id = config.get("exchange", "binance").lower()
        self.symbol = config.get("symbol", "DOGE/USDT")
        self.is_paper_trading = config.get("is_paper_trading", True)
        
        # Strategy Parameters
        self.vol_threshold = config.get("volume_threshold", 500000)
        self.target_spread = config.get("spread", 0.0002)
        self.initial_risk_pct = config.get("risk_pct", 0.5)
        self.trailing_sl_pct = config.get("trailing_sl_pct", 0.2)
        
        # Execution Engine
        self.engine = OrderBlockExecutionEngine(config)
        self.active_pos = None
        self.highest_price = 0.0
        self.running = False

    async def start(self):
        self.running = True
        exchange_class = getattr(ccxt, self.exchange_id)
        self.exchange = exchange_class({'enableRateLimit': True})
        asyncio.create_task(self._run_loop())

    async def _run_loop(self):
        while self.running:
            try:
                # 1. Fetch L2 Order Book
                orderbook = await self.exchange.fetch_order_book(self.symbol, limit=20)
                bids = orderbook['bids']
                asks = orderbook['asks']
                current_price = (bids[0][0] + asks[0][0]) / 2

                if not self.active_pos:
                    # 2. Search for Strong Buy Wall
                    for price, vol in bids:
                        if vol >= self.vol_threshold:
                            await self.enter_trade(price, "buy")
                            break
                else:
                    # 3. Monitor Active Trade & Trailing SL
                    await self.monitor_exit(current_price)

                await asyncio.sleep(0.1) # High-frequency polling
            except Exception as e:
                logger.error(f"WallHunter Error: {e}")
                await asyncio.sleep(1)

    async def enter_trade(self, wall_price: float, side: str):
        entry_price = wall_price + 0.00001
        amount = self.config.get("trade_amount", 100)
        
        res = await self.engine.execute_trade(side, amount, entry_price)
        if res:
            self.active_pos = {
                "entry": entry_price,
                "stop_loss": entry_price * (1 - (self.initial_risk_pct / 100)),
                "tp_target": entry_price + self.target_spread
            }
            self.highest_price = entry_price
            logger.info(f"Entered Trade at {entry_price}. SL: {self.active_pos['stop_loss']}")

    async def monitor_exit(self, price: float):
        # Update Highest Price for Trailing SL
        if price > self.highest_price:
            self.highest_price = price
            new_sl = self.highest_price * (1 - (self.trailing_sl_pct / 100))
            self.active_pos["stop_loss"] = max(self.active_pos["stop_loss"], new_sl)

        # Check Exit Conditions
        if price <= self.active_pos["stop_loss"]:
            await self.engine.execute_trade("sell", self.config["trade_amount"], price)
            self.active_pos = None
            logger.info("Exit: Stop Loss Hit")
        elif price >= self.active_pos["tp_target"]:
            await self.engine.execute_trade("sell", self.config["trade_amount"], price)
            self.active_pos = None
            logger.info("Exit: Take Profit Hit")
