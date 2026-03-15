import logging
import asyncio
import time
import json
import ccxt.pro as ccxt_pro
from app.utils import get_redis_client
from app.strategies.order_block_bot import OrderBlockExecutionEngine

logger = logging.getLogger(__name__)

class WallHunterFuturesStrategy:
    def __init__(self, bot_record, ccxt_service):
        self.bot_record = bot_record
        self.bot_id = bot_record.id
        self.owner_id = bot_record.owner_id
        self.exchange_service = ccxt_service
        self.config = bot_record.config or {}
        
        # ফিউচার কনফিগারেশন
        self.leverage = self.config.get('leverage', 10)
        self.margin_mode = self.config.get('margin_mode', 'cross')
        self.reduce_only = self.config.get('reduce_only', True)
        self.direction = self.config.get('position_direction', 'auto') # long, short, auto
        self.symbol = bot_record.market
        self.exchange_id = (bot_record.exchange or "binance").lower()
        self.is_paper_trading = bot_record.is_paper_trading
        
        # Strategy Params (Adapted from Spot Bot)
        self.vol_threshold = self.config.get("vol_threshold", 500000)
        self.target_spread = self.config.get("target_spread", 0.0002)
        self.initial_risk_pct = self.config.get("risk_pct", 0.5)
        self.tsl_pct = self.config.get("trailing_stop", 0.2)
        self.min_wall_lifetime = self.config.get("min_wall_lifetime", 3.0)
        self.max_wall_distance_pct = self.config.get("max_wall_distance_pct", 1.0)
        self.amount_per_trade = self.config.get("amount_per_trade", 10.0)
        
        # State
        self.running = False
        self.redis = get_redis_client()
        self.active_pos = None
        self.extreme_price = 0.0 # Will track Highest for Long, Lowest for Short
        self.tracked_walls = {} # {price: {first_seen, last_seen, vol, type}}
        
        # Tasks
        self._main_task = None
        self._heartbeat_task = None
        
        # CCXT Instances
        self.public_exchange = None
        self.private_exchange = None
        self.engine = None

    async def start(self, api_key_record=None):
        """বট স্টার্ট করার মেইন এন্ট্রি পয়েন্ট"""
        self.running = True
        logger.info(f"🚀 [FuturesHunter {self.bot_id}] Starting on {self.symbol}")
        
        try:
            # ১. এক্সচেঞ্জ ইনিশিয়ালাইজেশন
            exchange_class = getattr(ccxt_pro, self.exchange_id)
            
            # Public instance for data
            self.public_exchange = exchange_class({'enableRateLimit': True})
            
            # Private instance for trading
            exchange_params = {
                'enableRateLimit': True,
                'options': {'adjustForTimeDifference': True}
            }
            
            if not self.is_paper_trading and api_key_record:
                from app.core.security import decrypt_key
                exchange_params.update({
                    'apiKey': decrypt_key(api_key_record.api_key),
                    'secret': decrypt_key(api_key_record.secret_key)
                })
                if hasattr(api_key_record, 'passphrase') and api_key_record.passphrase:
                    exchange_params['password'] = decrypt_key(api_key_record.passphrase)
            
            self.private_exchange = exchange_class(exchange_params)
            
            # ২. ফিউচার সেটিংস সেটআপ (লেভারেজ, মার্জিন মোড)
            await self.initialize_futures_settings()
            
            # ৩. এক্সিকিউশন ইঞ্জিন
            engine_config = self.config.copy()
            engine_config['symbol'] = self.symbol
            engine_config['trading_mode'] = 'futures'
            self.engine = OrderBlockExecutionEngine(engine_config, exchange=self.private_exchange)
            
            # ৪. মেইন লুপ এবং হার্টবিট শুরু করা
            self._main_task = asyncio.create_task(self._run_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"✅ [FuturesHunter {self.bot_id}] Initialization Complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Futures Bot {self.bot_id}: {str(e)}")
            self.running = False
            raise e

    async def initialize_futures_settings(self):
        """এক্সচেঞ্জে লেভারেজ এবং মার্জিন মোড সেট করবে"""
        try:
            logger.info(f"[{self.bot_id}] Setting up Futures Market: {self.symbol}, Leverage {self.leverage}x, Mode: {self.margin_mode}")
            
            if self.is_paper_trading:
                self.private_exchange.set_sandbox_mode(True)
                
            # সেট লেভারেজ
            try:
                await self.private_exchange.set_leverage(self.leverage, self.symbol)
            except Exception as e:
                logger.warning(f"Could not set leverage (might already be set): {e}")
                
            # সেট মার্জিন মোড
            try:
                await self.private_exchange.set_margin_mode(self.margin_mode.lower(), self.symbol)
            except Exception as e:
                logger.warning(f"Could not set margin mode (might already be set): {e}")
                
        except Exception as e:
            logger.error(f"Futures Settings initialization error: {e}")

    async def _heartbeat_loop(self):
        while self.running:
            logger.info(f"💓 [FuturesHunter {self.bot_id}] monitoring {self.symbol} (Futures Mode)...")
            await asyncio.sleep(10)

    async def _run_loop(self):
        """মেইন স্ট্র্যাটেজি লুপ: L2 অর্ডারবুক ট্র্যাকিং"""
        while self.running:
            try:
                # WebSocket এর মাধ্যমে অর্ডারবুক ওয়াচ করা
                try:
                    orderbook = await self.public_exchange.watch_order_book(self.symbol, limit=20)
                except Exception as e:
                    logger.warning(f"WS Orderbook error: {e}, falling back to REST")
                    orderbook = await self.public_exchange.fetch_order_book(self.symbol, limit=20)
                
                if not orderbook['bids'] or not orderbook['asks']:
                    await asyncio.sleep(1)
                    continue

                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2
                current_time = time.time()

                if not self.active_pos:
                    current_walls = {}
                    
                    # ১. বড় ওয়াল ডিটেক্ট করা (Long এর জন্য Bids, Short এর জন্য Asks)
                    if self.direction in ['long', 'auto']:
                        for price, vol in orderbook['bids']:
                            if vol >= self.vol_threshold:
                                dist_pct = abs(price - mid_price) / mid_price * 100
                                if dist_pct <= self.max_wall_distance_pct:
                                    current_walls[price] = {'vol': vol, 'type': 'buy'}
                    
                    if self.direction in ['short', 'auto']:
                        for price, vol in orderbook['asks']:
                            if vol >= self.vol_threshold:
                                dist_pct = abs(price - mid_price) / mid_price * 100
                                if dist_pct <= self.max_wall_distance_pct:
                                    current_walls[price] = {'vol': vol, 'type': 'sell'}

                    # ২. ট্র্যাকিং এবং স্পুফিং ডিটেকশন
                    for price, info in current_walls.items():
                        if price in self.tracked_walls:
                            self.tracked_walls[price]['last_seen'] = current_time
                            
                            alive_time = current_time - self.tracked_walls[price]['first_seen']
                            if alive_time >= self.min_wall_lifetime:
                                wall_type = self.tracked_walls[price]['type']
                                logger.info(f"🟢 {wall_type.upper()} Wall Confirmed at {price} (Alive: {alive_time:.1f}s). Snipping!")
                                # Buy wall -> Entry LONG (buy), Sell wall -> Entry SHORT (sell)
                                await self.execute_snipe(price, "buy" if wall_type == 'buy' else "sell", mid_price)
                                self.tracked_walls.clear()
                                break
                        else:
                            self.tracked_walls[price] = {
                                "vol": info['vol'],
                                "type": info['type'],
                                "first_seen": current_time,
                                "last_seen": current_time
                            }
                    
                    # ৩. ভ্যানিশ হওয়া ওয়ালগুলো সরানো
                    spoofed = [p for p in self.tracked_walls if p not in current_walls]
                    for p in spoofed:
                        del self.tracked_walls[p]
                
                else:
                    # ৪. রিস্ক ম্যানেজমেন্ট (TSL, TP)
                    await self.manage_risk(mid_price)

                self._publish_status(mid_price)
                await asyncio.sleep(0.001)

            except Exception as e:
                logger.error(f"Futures Hunter Loop Error: {e}")
                await asyncio.sleep(2)

    async def execute_snipe(self, wall_price: float, side: str, current_mid_price: float):
        """অর্ডার এক্সিকিউট করা"""
        try:
            entry_price = current_mid_price
            base_amount = float(f"{self.amount_per_trade / entry_price:.6f}")
            
            logger.info(f"⚡ [FuturesHunter] Entering {side.upper()} at {entry_price} (Amount: {base_amount})")
            
            res = await self.engine.execute_trade(side, base_amount, entry_price)
            if res:
                actual_entry = res.get('average') or res.get('price') or entry_price
                
                if side == "buy": # LONG
                    self.active_pos = {
                        "entry": float(actual_entry),
                        "amount": base_amount,
                        "sl": actual_entry * (1 - (self.initial_risk_pct / 100)),
                        "tp": actual_entry + self.target_spread,
                        "side": "long"
                    }
                else: # SHORT
                    self.active_pos = {
                        "entry": float(actual_entry),
                        "amount": base_amount,
                        "sl": actual_entry * (1 + (self.initial_risk_pct / 100)),
                        "tp": actual_entry - self.target_spread,
                        "side": "short"
                    }
                
                self.extreme_price = actual_entry
                logger.info(f"✅ Position Opened: {side.upper()} | Entry {actual_entry}, SL {self.active_pos['sl']}, TP {self.active_pos['tp']}")
                
        except Exception as e:
            logger.error(f"Snipe Execution Error: {e}")

    async def manage_risk(self, current_price: float):
        """রিস্ক ম্যানেজমেন্ট (TP/SL/TSL)"""
        if not self.active_pos: return
        
        side = self.active_pos['side']

        # Trailing Stop Update
        if side == "long":
            if current_price > self.extreme_price:
                self.extreme_price = current_price
                new_sl = self.extreme_price * (1 - (self.tsl_pct / 100))
                self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)
        else: # short
            if current_price < self.extreme_price or self.extreme_price == 0:
                self.extreme_price = current_price
                new_sl = self.extreme_price * (1 + (self.tsl_pct / 100))
                self.active_pos['sl'] = min(self.active_pos['sl'], new_sl)

        # TP / SL চেক
        should_exit = False
        reason = ""
        
        if side == "long":
            if current_price >= self.active_pos['tp']:
                should_exit = True
                reason = "Take Profit"
            elif current_price <= self.active_pos['sl']:
                should_exit = True
                reason = "Stop Loss"
        else: # short
            if current_price <= self.active_pos['tp']:
                should_exit = True
                reason = "Take Profit"
            elif current_price >= self.active_pos['sl']:
                should_exit = True
                reason = "Stop Loss"

        if should_exit:
            logger.info(f"🚩 Exiting {side.upper()} Position: {reason} at {current_price}")
            
            # ফিউচার ক্লোজের জন্য বিপরীত অর্ডার
            exit_side = "sell" if side == "long" else "buy"
            
            res = await self.engine.execute_trade(exit_side, self.active_pos['amount'], current_price)
            if res:
                logger.info(f"✅ {side.upper()} Position Closed: {reason}")
                self.active_pos = None

    def _publish_status(self, current_price: float):
        try:
            pnl_val = 0.0
            pnl_pct = 0.0
            if self.active_pos:
                entry = self.active_pos['entry']
                side = self.active_pos['side']
                if side == "long":
                    pnl_val = (current_price - entry) * self.active_pos['amount']
                    pnl_pct = ((current_price - entry) / entry) * 100
                else:
                    pnl_val = (entry - current_price) * self.active_pos['amount']
                    pnl_pct = ((entry - current_price) / entry) * 100

            status_payload = {
                "id": self.bot_id,
                "status": "active" if self.running else "inactive",
                "pnl": round(pnl_val, 2),
                "pnl_percent": round(pnl_pct, 2),
                "price": current_price,
                "position": self.active_pos is not None,
                "entry_price": self.active_pos['entry'] if self.active_pos else 0,
                "sl_price": self.active_pos['sl'] if self.active_pos else 0,
                "tp_price": self.active_pos['tp'] if self.active_pos else 0,
                "trading_mode": "futures",
                "side": self.active_pos['side'] if self.active_pos else None
            }
            self.redis.publish(f"bot_status:{self.bot_id}", json.dumps(status_payload))
        except Exception:
            pass

    async def stop(self):
        self.running = False
        if self._main_task: self._main_task.cancel()
        if self._heartbeat_task: self._heartbeat_task.cancel()
        
        if self.public_exchange: await self.public_exchange.close()
        if self.private_exchange: await self.private_exchange.close()
        
        logger.info(f"🔴 [FuturesHunter {self.bot_id}] Stopped.")
