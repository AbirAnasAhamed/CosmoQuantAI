import asyncio
import logging
import time
from typing import Dict, Any, Optional
import ccxt.async_support as ccxt
import json
from app.utils import get_redis_client
from app.strategies.order_block_bot import OrderBlockExecutionEngine
from app.services.notification import NotificationService
from app.db.session import SessionLocal

try:
    from app.core.security import decrypt_key
except ImportError:
    # Forward compatibility if it doesn't exist
    def decrypt_key(key):
        return key

logger = logging.getLogger(__name__)

class WallHunterBot:
    def __init__(self, bot_id: int, config: Dict[str, Any], db_session=None, owner_id: int = None):
        self.bot_id = bot_id
        self.owner_id = owner_id
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
        self.redis = get_redis_client()

    async def _send_telegram(self, msg: str):
        if not self.owner_id:
            return
        try:
            db = SessionLocal()
            await NotificationService.send_message(db, self.owner_id, msg)
            db.close()
        except Exception as e:
            logger.error(f"Failed to send Telegram in WallHunterBot: {e}")

    def _publish_status(self, current_price: float):
        try:
            pnl_val = 0.0
            pnl_pct = 0.0
            entry_price = 0.0
            sl_price = 0.0
            tp_price = 0.0
            position = False

            if self.active_pos:
                position = True
                entry_price = self.active_pos.get('entry', 0)
                sl_price = self.active_pos.get('sl', 0)
                tp_price = self.active_pos.get('tp', 0)
                
                amount = self.config.get("trade_amount", 100) / entry_price if entry_price > 0 else 0
                pnl_val = (current_price - entry_price) * amount
                if entry_price > 0:
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100

            status_payload = {
                "id": self.bot_id,
                "status": "active" if self.running else "inactive",
                "pnl": float(f"{pnl_val:.2f}"),
                "pnl_percent": float(f"{pnl_pct:.2f}"),
                "price": float(f"{current_price:.6f}"),
                "position": position,
                "entry_price": float(f"{entry_price:.6f}"),
                "sl_price": float(f"{sl_price:.6f}"),
                "tp_price": float(f"{tp_price:.6f}"),
                "target_spread": self.target_spread,
                "vol_threshold": self.vol_threshold
            }
            self.redis.publish(f"bot_status:{self.bot_id}", json.dumps(status_payload))
        except Exception as e:
            pass

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
        
        mode = "Live Trading" if not self.is_paper_trading else "Paper Trading"
        await self._send_telegram(f"🟢 WallHunter Bot [ID: {self.bot_id}] Started!\nPair: {self.symbol}\nMode: {mode}\nVolume Threshold: {self.vol_threshold}")

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

                self._publish_status(mid_price)
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
            await self._send_telegram(f"⚡ WallHunter Bot {side.upper()} order filled on Volume Wall!\nPair: {self.symbol}\nEntry Price: {entry_price:.6f}\nTarget TP: {self.active_pos['tp']:.6f}\nTrailing SL: {self.active_pos['sl']:.6f}\nTrade Amount: ${amount}")

    async def manage_risk(self, current_price: float):
        if not self.active_pos: return

        if current_price > self.highest_price:
            self.highest_price = current_price
            # Update Trailing SL
            new_sl = self.highest_price * (1 - (self.tsl_pct / 100))
            self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)

        if current_price <= self.active_pos['sl']:
            await self.engine.execute_trade("sell", self.config.get('trade_amount', 100), current_price)
            # Calculate PnL
            amount = self.config.get("trade_amount", 100) / self.active_pos['entry'] if self.active_pos['entry'] > 0 else 0
            pnl_val = (current_price - self.active_pos['entry']) * amount
            await self._send_telegram(f"🛑 WallHunter EXIT - Stopped Out!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Stop Loss / TSL Hit")
            
        elif current_price >= self.active_pos['tp']:
            await self.engine.execute_trade("sell", self.config.get('trade_amount', 100), current_price)
            # Calculate PnL
            amount = self.config.get("trade_amount", 100) / self.active_pos['entry'] if self.active_pos['entry'] > 0 else 0
            pnl_val = (current_price - self.active_pos['entry']) * amount
            await self._send_telegram(f"🎯 WallHunter EXIT - Take Profit Hit!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Take Profit Hit")

    async def stop(self):
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"Bot {self.bot_id} (WallHunter) stopped.")
        await self._send_telegram(f"🔴 WallHunter Bot [ID: {self.bot_id}] Stopped.")
