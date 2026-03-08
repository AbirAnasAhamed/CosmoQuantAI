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
        self.sell_order_type = config.get("sell_order_type", "market")
        
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
                
                amount = self.config.get("amount_per_trade", 10.0) / entry_price if entry_price > 0 else 0
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
        exchange_params = {
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        }
        
        # Live Mode-e API select kora
        if not self.is_paper_trading and api_key_record:
            exchange_params.update({
                'apiKey': decrypt_key(api_key_record.api_key),
                'secret': decrypt_key(api_key_record.secret_key)
            })
            
            # Optional Passphrase for KuCoin/OKX/MEXC
            if hasattr(api_key_record, 'passphrase') and api_key_record.passphrase:
                try:
                    exchange_params['password'] = decrypt_key(api_key_record.passphrase)
                except Exception:
                     # Fallback if not encrypted or error
                    exchange_params['password'] = api_key_record.passphrase
            
        self.exchange = exchange_class(exchange_params)
        
        # Initialize execution engine with the correct exchange instance
        self.engine = OrderBlockExecutionEngine(self.config, exchange=self.exchange)
        
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
                            await self.execute_snipe(price, "buy", mid_price)
                            break
                else:
                    # Trailing Stop-Loss Engine
                    await self.manage_risk(mid_price)

                self._publish_status(mid_price)
                await asyncio.sleep(0.05) # 50ms latency for L2 scan
            except Exception as e:
                logger.error(f"Hunter Loop Error: {e}")
                await asyncio.sleep(1)

    async def execute_snipe(self, wall_price: float, side: str, current_mid_price: float):
        entry_price = wall_price + 0.00001
        
        # Calculate base asset amount from quote currency amount
        quote_amount = self.config.get("amount_per_trade", 10.0)
        base_amount = float(f"{quote_amount / entry_price:.6f}")
        
        res = await self.engine.execute_trade(side, base_amount, entry_price)
        if res:
            # Safely extract average fill price. Fallback to requested entry_price if not provided or 0
            avg_price = res.get('average')
            fill_price = res.get('price')
            actual_entry = avg_price if avg_price and avg_price > 0 else (fill_price if fill_price and fill_price > 0 else entry_price)
            actual_entry = float(actual_entry)
            
            # Sanity Check to prevent instant SL logic if CCXT returns an outdated or widely inaccurate fill price
            slippage_pct = abs(actual_entry - current_mid_price) / current_mid_price
            if slippage_pct > 0.02: # If the executed price differs from the mid price by more than 2%
                logger.warning(f"Suspicious fill price from CCXT: {actual_entry}. Overriding with mid_price: {current_mid_price}")
                actual_entry = current_mid_price
            
            self.active_pos = {
                "entry": actual_entry,
                "amount": base_amount,
                "sl": actual_entry * (1 - (self.initial_risk_pct / 100)),
                "tp": actual_entry + self.target_spread,
                "limit_order_id": None
            }
            self.highest_price = actual_entry
            
            # Place Limit Order immediately if configured
            if self.sell_order_type == 'limit':
                limit_res = await self.engine.execute_trade("sell", base_amount, self.active_pos['tp'], order_type="limit")
                if limit_res and 'id' in limit_res:
                    self.active_pos['limit_order_id'] = limit_res['id']
                    logger.info(f"Placed Limit TP Order {limit_res['id']} at {self.active_pos['tp']}")
            
            logger.info(f"Entered Trade at {actual_entry}. SL: {self.active_pos['sl']}")
            await self._send_telegram(f"⚡ WallHunter Bot {side.upper()} order filled!\nPair: {self.symbol}\nExpected Entry: {entry_price:.6f}\nActual Fill: {actual_entry:.6f}\nTarget TP: {self.active_pos['tp']:.6f}\nTrailing SL: {self.active_pos['sl']:.6f}\nTrade Amount: ${quote_amount}")

    async def manage_risk(self, current_price: float):
        if not self.active_pos: return

        if current_price > self.highest_price:
            self.highest_price = current_price
            # Update Trailing SL
            new_sl = self.highest_price * (1 - (self.tsl_pct / 100))
            self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)

        if current_price <= self.active_pos['sl']:
            logger.info(f"⚠️ Triggering SL: Current Price ({current_price:.6f}) <= SL ({self.active_pos['sl']:.6f})")
            sell_amount = self.active_pos.get('amount') or (self.config.get("amount_per_trade", 10.0) / self.active_pos['entry'])
            
            # Cancel open limit order if TSL hits
            if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
                await self.engine.cancel_order(self.active_pos['limit_order_id'])
                logger.info("Cancelled Limit TP Order due to Stop Loss hit")
                
            await self.engine.execute_trade("sell", sell_amount, current_price)
            # Calculate PnL
            pnl_val = (current_price - self.active_pos['entry']) * sell_amount
            await self._send_telegram(f"🛑 WallHunter EXIT - Stopped Out!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Stop Loss / TSL Hit")
            
        elif current_price >= self.active_pos['tp']:
            logger.info(f"✅ Triggering TP: Current Price ({current_price:.6f}) >= TP ({self.active_pos['tp']:.6f})")
            sell_amount = self.active_pos.get('amount') or (self.config.get("amount_per_trade", 10.0) / self.active_pos['entry'])
            
            if self.sell_order_type == 'market':
                await self.engine.execute_trade("sell", sell_amount, current_price)
            else:
                logger.info(f"Target Profit {self.active_pos['tp']} reached. Assuming Limit Order {self.active_pos.get('limit_order_id')} is filled.")
            
            # Calculate PnL
            pnl_val = (current_price - self.active_pos['entry']) * sell_amount
            await self._send_telegram(f"🎯 WallHunter EXIT - Take Profit Hit!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Take Profit Hit")

    async def stop(self):
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"Bot {self.bot_id} (WallHunter) stopped.")
        await self._send_telegram(f"🔴 WallHunter Bot [ID: {self.bot_id}] Stopped.")
