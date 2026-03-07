import asyncio
import logging
import time
from typing import Dict, Any, Optional
import ccxt.async_support as ccxt
from app.strategies.order_block_bot import OrderBlockExecutionEngine

try:
    from app.core.security import decrypt_key
except ImportError:
    # Forward compatibility if it doesn't exist
    def decrypt_key(key):
        return key

logger = logging.getLogger(__name__)

class WallHunterBot:
    def __init__(self, bot_id: int, config: Dict[str, Any], db_session=None):
        self.bot_id = bot_id
        self.config = config
        self.symbol = config.get("symbol", "DOGE/USDT")
        self.exchange_id = config.get("exchange", "binance").lower()
        self.is_paper_trading = config.get("is_paper_trading", True)
        
        # Strategy Params
        self.vol_threshold = config.get("volume_threshold", 500000)
        self.target_spread = config.get("spread", 0.0002)
        self.initial_risk_pct = config.get("risk_pct", 0.5)
        self.tsl_pct = config.get("trailing_sl_pct", 0.2)
        
        self.engine = OrderBlockExecutionEngine(config)
        self.active_pos = None
        self.highest_price = 0.0
        self.running = False
        self._heartbeat_task = None

    async def start(self, api_key_record=None):
        self.running = True
        # Dynamic Exchange Initialization
        exchange_class = getattr(ccxt, self.exchange_id)
        exchange_params = {'enableRateLimit': True}
        
        # Live Mode-e API select kora
        if not self.is_paper_trading and api_key_record:
            exchange_params.update({
                'apiKey': api_key_record.api_key,
                'secret': decrypt_key(api_key_record.secret_key)
            })
            
        self.exchange = exchange_class(exchange_params)
        asyncio.create_task(self._run_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Prints a friendly heartbeat to the terminal every 5 seconds"""
        while self.running:
            logger.info(f"💓 [WallHunter {self.bot_id}] active and monitoring Level 2 data on {self.symbol}...")
            await asyncio.sleep(5)

    async def _run_loop(self):
        while self.running:
            try:
                # Real-time L2 Data Fetching
                orderbook = await self.exchange.fetch_order_book(self.symbol, limit=20)
                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2

                if not self.active_pos:
                    # Scan for Walls in Bids
                    for price, vol in orderbook['bids']:
                        if vol >= self.vol_threshold:
                            await self.execute_snipe(price, "buy")
                            break
                else:
                    # Trailing Stop-Loss Engine
                    await self.manage_risk(mid_price)

                await asyncio.sleep(0.05) # 50ms latency for L2 scan
            except Exception as e:
                logger.error(f"Hunter Loop Error: {e}")
                await asyncio.sleep(1)

    async def execute_snipe(self, wall_price: float, side: str):
        entry_price = wall_price + 0.00001
        amount = self.config.get("trade_amount", 100)
        
        res = await self.engine.execute_trade(side, amount, entry_price)
        if res:
            self.active_pos = {
                "entry": entry_price,
                "sl": entry_price * (1 - (self.initial_risk_pct / 100)),
                "tp": entry_price + self.target_spread
            }
            self.highest_price = entry_price
            logger.info(f"Entered Trade at {entry_price}. SL: {self.active_pos['sl']}")

    async def manage_risk(self, current_price: float):
        if not self.active_pos: return

        if current_price > self.highest_price:
            self.highest_price = current_price
            # Update Trailing SL
            new_sl = self.highest_price * (1 - (self.tsl_pct / 100))
            self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)

        if current_price <= self.active_pos['sl']:
            await self.engine.execute_trade("sell", self.config.get('trade_amount', 100), current_price)
            self.active_pos = None
            logger.info("Exit: Stop Loss / TSL Hit")
        elif current_price >= self.active_pos['tp']:
            await self.engine.execute_trade("sell", self.config.get('trade_amount', 100), current_price)
            self.active_pos = None
            logger.info("Exit: Take Profit Hit")

    async def stop(self):
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"Bot {self.bot_id} (WallHunter) stopped.")
