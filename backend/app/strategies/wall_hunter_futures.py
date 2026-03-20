import logging
import asyncio
import time
import json
import ccxt
import ccxt.pro as ccxt_pro
from app.utils import get_redis_client
from app.strategies.order_block_bot import OrderBlockExecutionEngine
from app.strategies.helpers.absorption_tracker import AbsorptionTracker

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
        self.sell_order_type = self.config.get("sell_order_type", "market")
        
        # --- NEW FEATURES: Partial TP & Triggers ---
        self.partial_tp_pct = self.config.get("partial_tp_pct", 50.0)
        self.vpvr_enabled = self.config.get("vpvr_enabled", False)
        self.vpvr_tolerance = self.config.get("vpvr_tolerance", 0.2)
        self.top_hvns = []
        
        self.atr_sl_enabled = self.config.get("atr_sl_enabled", False)
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_multiplier = self.config.get("atr_multiplier", 2.0)
        self.current_atr = 0.0
        
        self.enable_wall_trigger = self.config.get("enable_wall_trigger", True)
        self.enable_liq_trigger = self.config.get("enable_liq_trigger", False)
        self.liq_threshold = self.config.get("liq_threshold", 50000.0)
        self.enable_micro_scalp = self.config.get("enable_micro_scalp", False)
        self.micro_scalp_profit_ticks = self.config.get("micro_scalp_profit_ticks", 2)
        self.micro_scalp_min_wall = self.config.get("micro_scalp_min_wall", 100000.0)
        
        from collections import deque
        self.liq_history = deque()
        self.liq_cascade_window = self.config.get("liq_cascade_window", 5)
        self.enable_liq_cascade = self.config.get("enable_liq_cascade", False)
        self.follow_btc_liq = self.config.get("follow_btc_liq", False)
        self.btc_liq_threshold = self.config.get("btc_liq_threshold", 500000.0)
        self.enable_dynamic_liq = self.config.get("enable_dynamic_liq", False)
        self.dynamic_liq_multiplier = self.config.get("dynamic_liq_multiplier", 1.0)
        
        # --- Tape Reading / Imbalance ---
        self.enable_ob_imbalance = self.config.get("enable_ob_imbalance", False)
        self.ob_imbalance_ratio = self.config.get("ob_imbalance_ratio", 1.5)
        self.liquidation_safety_pct = self.config.get("liquidation_safety_pct", 5.0)

        # --- CVD Absorption Trigger ---
        self.enable_absorption = self.config.get("enable_absorption", False)
        self.absorption_threshold = self.config.get("absorption_threshold", 50000.0)
        self.absorption_window = self.config.get("absorption_window", 10)
        self.absorption_tracker = AbsorptionTracker(
            threshold=self.absorption_threshold,
            window_seconds=self.absorption_window
        )
        
        # --- BRAND NEW: BTC Correlation Filter ---
        self.enable_btc_correlation = self.config.get("enable_btc_correlation", False)
        self.btc_correlation_threshold = self.config.get("btc_correlation_threshold", 0.7)
        self.btc_time_window = self.config.get("btc_time_window", 15)
        self.btc_min_move_pct = self.config.get("btc_min_move_pct", 0.1)
        self.btc_correlation_tracker = None
        
        # State
        self.running = False
        self.redis = get_redis_client()
        self.active_pos = None
        self.extreme_price = 0.0 # Will track Highest for Long, Lowest for Short
        self.tracked_walls = {} # {price: {first_seen, last_seen, vol, type}}
        self.last_debug_log_time = 0
        
        # Tasks
        self._main_task = None
        self._heartbeat_task = None
        self._vpvr_task = None
        self._atr_task = None
        self._liq_task = None
        self._trades_task = None
        
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
            exchange_id = self.exchange_id
            if exchange_id == 'kucoin':
                exchange_id = 'kucoinfutures'
                
            exchange_class = getattr(ccxt_pro, exchange_id)
            
            # Format Symbol for Futures
            from app.services.ccxt_service import ccxt_service
            self.symbol = ccxt_service.format_futures_symbol(self.symbol, self.exchange_id)
            
            # Public instance for data
            self.public_exchange = exchange_class({'enableRateLimit': True})
            
            # Private instance for trading
            exchange_params = {
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000 if self.exchange_id == 'mexc' else 30000,
                    'new_updates': True if self.exchange_id == 'mexc' else False
                }
            }
            
            try:
                await self.public_exchange.load_markets()
            except Exception as e:
                logger.warning(f"Could not load public markets: {e}")

            if not self.is_paper_trading and api_key_record:
                from app.core.security import decrypt_key
                exchange_params.update({
                    'apiKey': decrypt_key(api_key_record.api_key),
                    'secret': decrypt_key(api_key_record.secret_key)
                })
                if hasattr(api_key_record, 'passphrase') and api_key_record.passphrase:
                    exchange_params['password'] = decrypt_key(api_key_record.passphrase)
            
            self.private_exchange = exchange_class(exchange_params)
            
            try:
                await self.private_exchange.load_markets()
            except Exception as e:
                logger.warning(f"Could not load private markets: {e}")

            # ২. ফিউচার সেটিংস সেটআপ (লেভারেজ, মার্জিন মোড)
            await self.initialize_futures_settings()
            
            # ৩. এক্সিকিউশন ইঞ্জিন
            engine_config = self.config.copy()
            engine_config['symbol'] = self.symbol
            engine_config['trading_mode'] = 'futures'
            engine_config['is_paper_trading'] = self.is_paper_trading
            engine_config['exchange'] = self.exchange_id # Pass actual exchange ID (kucoin)
            self.engine = OrderBlockExecutionEngine(engine_config, exchange=self.private_exchange)
            
            # ৪. মেইন লুপ এবং হার্টবিট শুরু করা
            from app.strategies.helpers.btc_correlation_tracker import BtcCorrelationTracker
            self.btc_correlation_tracker = BtcCorrelationTracker(
                self.public_exchange, 
                self.symbol, 
                threshold=self.btc_correlation_threshold,
                window_minutes=self.btc_time_window,
                min_move_pct=self.btc_min_move_pct
            )

            self._main_task = asyncio.create_task(self._run_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._vpvr_task = asyncio.create_task(self._vpvr_updater_loop())
            self._atr_task = asyncio.create_task(self._atr_updater_loop())
            self._liq_task = asyncio.create_task(self._liquidation_listener())
            self._trades_task = asyncio.create_task(self._trades_listener())
            
            if self.enable_btc_correlation:
                self._btc_task = asyncio.create_task(self.btc_correlation_tracker.start())
            else:
                self._btc_task = None
            
            logger.info(f"✅ [FuturesHunter {self.bot_id}] Initialization Complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Futures Bot {self.bot_id}: {str(e)}")
            await self.stop()
            self.running = False
            raise e

    async def stop(self):
        """বট স্টপ করার জন্য রিসোর্স ক্লিনআপ"""
        self.running = False
        logger.info(f"🛑 [FuturesHunter {self.bot_id}] Stopping...")
        try:
            if self.public_exchange:
                await self.public_exchange.close()
            if self.private_exchange:
                await self.private_exchange.close()
        except Exception as e:
            logger.error(f"Error closing exchanges: {e}")

    async def initialize_futures_settings(self):
        """এক্সচেঞ্জে লেভারেজ এবং মার্জিন মোড সেট করবে"""
        try:
            logger.info(f"[{self.bot_id}] Setting up Futures Market: {self.symbol}, Leverage {self.leverage}x, Mode: {self.margin_mode}")
            
            if self.is_paper_trading:
                self.private_exchange.set_sandbox_mode(True)
                
            # সেট লেভারেজ
            try:
                if self.exchange_id == 'mexc':
                    # MEXC requires both long and short leverage to be set separately
                    open_type = 1 if self.margin_mode == 'isolated' else 2
                    await self.private_exchange.set_leverage(self.leverage, self.symbol, {'openType': open_type, 'positionType': 1}) # Long
                    await self.private_exchange.set_leverage(self.leverage, self.symbol, {'openType': open_type, 'positionType': 2}) # Short
                elif self.exchange_id == 'kucoin':
                    if self.margin_mode.lower() == 'cross':
                        await self.private_exchange.set_leverage(self.leverage, self.symbol, {'marginMode': 'cross'})
                    else:
                        # CCXT Kucoin only supports setting Cross leverage. Isolated is default or unsupported.
                        pass
                else:
                    await self.private_exchange.set_leverage(self.leverage, self.symbol)
            except Exception as e:
                logger.warning(f"Could not set leverage (might already be set): {e}")
                
            try:
                if self.exchange_id == 'mexc':
                    # MEXC setMarginMode requires leverage as well, and symbol must be in params for some versions
                    await self.private_exchange.set_margin_mode(self.margin_mode.lower(), self.symbol, {'leverage': self.leverage, 'symbol': self.symbol})
                elif self.exchange_id == 'kucoin':
                    # CCXT handles marginMode casing natively for Kucoin, passing it in params overrides it and breaks it
                    await self.private_exchange.set_margin_mode(self.margin_mode.lower(), self.symbol)
                else:
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
                    # Use exchange service to format symbol for fetch_order_book if needed
                    fetch_symbol = self.symbol
                    orderbook = await self.public_exchange.fetch_order_book(fetch_symbol, limit=20)
                
                if not orderbook['bids'] or not orderbook['asks']:
                    await asyncio.sleep(1)
                    continue

                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2
                current_time = time.time()

                # Periodic debug info (every 10 seconds)
                if current_time - self.last_debug_log_time >= 10:
                    self.last_debug_log_time = current_time
                    max_bid = max([level[1] for level in orderbook['bids']]) if orderbook['bids'] else 0
                    max_ask = max([level[1] for level in orderbook['asks']]) if orderbook['asks'] else 0
                    logger.info(f"🔍 [Debug {self.bot_id}] {self.symbol} Mid: {mid_price:.6f} | Max Bid: {max_bid:,.0f} | Max Ask: {max_ask:,.0f} | Threshold: {self.vol_threshold:,.0f}")

                if not self.active_pos:
                    if not self.enable_wall_trigger:
                        self._publish_status(mid_price)
                        continue

                    current_walls = {}
                    potential_triggers = []
                    
                    # ১. বড় ওয়াল ডিটেক্ট করা
                    bid_vol_total = 0.0
                    ask_vol_total = 0.0
                    
                    # Accumulate volume for imbalance check + detect walls
                    for level in orderbook['bids']:
                        price, vol = level[0], level[1]
                        bid_vol_total += vol
                        if self.direction in ['long', 'auto'] and vol >= self.vol_threshold:
                            dist_pct = abs(price - mid_price) / mid_price * 100
                            if dist_pct <= self.max_wall_distance_pct:
                                current_walls[price] = {'vol': vol, 'type': 'buy'}
                        elif self.direction in ['long', 'auto'] and vol >= (self.vol_threshold * 0.5):
                            # Log walls that are at least 50% of threshold to help user tune settings
                            if current_time - self.last_debug_log_time >= 10:
                                logger.debug(f"ℹ️ Found wall at {price} with vol {vol:,.0f} (Too small, threshold: {self.vol_threshold:,.0f})")
                    
                        if self.direction in ['short', 'auto'] and vol >= self.vol_threshold:
                            dist_pct = abs(price - mid_price) / mid_price * 100
                            if dist_pct <= self.max_wall_distance_pct:
                                current_walls[price] = {'vol': vol, 'type': 'sell'}
                        elif self.direction in ['short', 'auto'] and vol >= (self.vol_threshold * 0.5):
                            # Log walls that are at least 50% of threshold to help user tune settings
                            if current_time - self.last_debug_log_time >= 10:
                                logger.debug(f"ℹ️ Found wall at {price} with vol {vol:,.0f} (Too small, threshold: {self.vol_threshold:,.0f})")

                    # ২. ট্র্যাকিং এবং স্পুফিং ডিটেকশন (Collect all confirmed walls)
                    for price, info in current_walls.items():
                        if price in self.tracked_walls:
                            self.tracked_walls[price]['last_seen'] = current_time
                            alive_time = current_time - self.tracked_walls[price]['first_seen']
                            
                            if alive_time >= self.min_wall_lifetime:
                                wall_type = self.tracked_walls[price]['type']
                                
                                # VPVR Confirmation
                                if self.vpvr_enabled and self.top_hvns:
                                    is_hvn_aligned = any(abs(price - hvn) / hvn <= (self.vpvr_tolerance / 100.0) for hvn in self.top_hvns)
                                    if not is_hvn_aligned:
                                        if not self.tracked_walls[price].get('hvn_rejected'):
                                            logger.info(f"🚫 Wall at {price} rejected: Not near any HVN.")
                                            self.tracked_walls[price]['hvn_rejected'] = True
                                        continue
                                
                                potential_triggers.append({
                                    'price': price,
                                    'vol': info['vol'],
                                    'type': wall_type
                                })
                        else:
                            self.tracked_walls[price] = {
                                "vol": info['vol'],
                                "type": info['type'],
                                "first_seen": current_time,
                                "last_seen": current_time
                            }
                    
                    # ৩. সেরা ওয়াল নির্বাচন (Highest Volume Wall)
                    if potential_triggers:
                        # Sort by volume descending
                        potential_triggers.sort(key=lambda x: x['vol'], reverse=True)
                        
                        # Apply Imbalance check if enabled
                        imbalance_ratio = (bid_vol_total / ask_vol_total) if ask_vol_total > 0 else 10.0
                        
                        best_wall = None
                        for wall in potential_triggers:
                            # If AUTO mode, check imbalance
                            if self.direction == 'auto' and self.enable_ob_imbalance:
                                if wall['type'] == 'buy' and imbalance_ratio < self.ob_imbalance_ratio:
                                    continue # Not enough buy pressure
                                if wall['type'] == 'sell' and imbalance_ratio > (1 / self.ob_imbalance_ratio):
                                    continue # Not enough sell pressure
                            
                            best_wall = wall
                            break
                        
                        if best_wall:
                            logger.info(f"🟢 [BEST WALL] {best_wall['type'].upper()} Confirmed at {best_wall['price']} (Vol: {best_wall['vol']}). Snipping!")
                            if self.enable_ob_imbalance:
                                logger.info(f"📊 Market Imbalance: {imbalance_ratio:.2f}x (Threshold: {self.ob_imbalance_ratio}x)")
                            
                            reason = f"Wall confirmed at {best_wall['price']}"
                            if self.enable_ob_imbalance:
                                reason += f" (Imbalance: {imbalance_ratio:.2f}x)"
                            
                            # CVD Absorption Check
                            if self.enable_absorption:
                                wall_type = best_wall['type'] # 'buy' or 'sell'
                                # In Futures, 'buy' wall means we want to go LONG (reversal from shorts hitting the wall)
                                # AbsorptionTracker.is_absorption_detected(side) expects the side of the WALL
                                if not self.absorption_tracker.is_absorption_detected(wall_type):
                                    continue
                                logger.info(f"🧬 [ABSORPTION] Confirmed {wall_type.upper()} absorption at {best_wall['price']}!")
                            
                            # BTC Correlation Anti-Fakeout Check
                            if self.enable_btc_correlation and self.btc_correlation_tracker:
                                target_side = "buy" if best_wall['type'] == 'buy' else "sell"
                                if not self.btc_correlation_tracker.is_aligned(target_side):
                                    metrics = self.btc_correlation_tracker.get_metrics_string()
                                    logger.info(f"🚫 [BTC Divergence] Wall at {best_wall['price']} rejected! {metrics}")
                                    continue
                            
                            await self.execute_snipe(best_wall['price'], "buy" if best_wall['type'] == 'buy' else "sell", mid_price, reason=reason)
                            self.tracked_walls.clear()
                    
                    # ৪. ভ্যানিশ হওয়া ওয়ালগুলো সরানো
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

    async def execute_snipe(self, wall_price: float, side: str, current_mid_price: float, reason: str = "Wall Detection"):
        """অর্ডার এক্সিকিউট করা"""
        pos_side = "LONG" if side == "buy" else "SHORT"
        try:
            entry_price = current_mid_price
            # Total Position Size = Amount * Leverage
            total_notional = self.amount_per_trade * self.leverage
            base_amount_tokens = total_notional / entry_price
            
            # Convert tokens to contracts (essential for Kucoin, OKX, Bybit, etc.)
            contract_size = 1.0
            if self.public_exchange and getattr(self.public_exchange, 'markets', None):
                market = self.public_exchange.markets.get(self.symbol, {})
                contract_size = market.get('contractSize', 1.0)
                
            contracts = base_amount_tokens / contract_size
            
            # Fetch minimum contract size from CCXT (usually 1.0)
            min_amount = 1.0
            if self.public_exchange and getattr(self.public_exchange, 'markets', None):
                market = self.public_exchange.markets.get(self.symbol, {})
                limits = market.get('limits', {})
                min_amount = limits.get('amount', {}).get('min', 1.0)
                if min_amount is None:
                    min_amount = 1.0
            
            # Integer rounding for Kucoin/MEXC futures if min_amount is integer-like
            if min_amount >= 1.0:
                base_amount = float(int(contracts))
            else:
                base_amount = float(f"{contracts:.6f}")
                
            if base_amount < min_amount:
                logger.warning(f"Calculated contracts ({base_amount}) < minimum ({min_amount}). Trying to place min_amount, but might fail with Insufficient Balance.")
                base_amount = min_amount
            
            logger.info(f"⚡ [FuturesHunter] Entering {pos_side} at {entry_price} (Amount: {base_amount} contracts)")
            logger.info(f"📝 Reason: {reason}")
            
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
                
                # --- NEW: Partial TP1 calculation ---
                if self.enable_micro_scalp:
                    tick_profit_pct = self.micro_scalp_profit_ticks * 0.0001
                    tp_price = actual_entry * (1 + tick_profit_pct) if side == "buy" else actual_entry * (1 - tick_profit_pct)
                    self.active_pos.update({
                        "tp": tp_price,
                        "tp1": tp_price, 
                        "tp1_hit": True, # No partial for micro-scalp
                        "limit_order_id": None
                    })
                else:
                    tp_dist = abs(self.active_pos['tp'] - actual_entry)
                    if side == "buy": # LONG
                        self.active_pos.update({
                            "tp1": actual_entry + (tp_dist * 0.5),
                            "tp1_hit": False,
                            "limit_order_id": None
                        })
                    else: # SHORT
                        self.active_pos.update({
                            "tp1": actual_entry - (tp_dist * 0.5),
                            "tp1_hit": False,
                            "limit_order_id": None
                        })

                # --- PLACE LIMIT ORDER ---
                if self.sell_order_type == 'limit':
                    exit_side = "sell" if side == "buy" else "buy"
                    limit_res = await self.engine.execute_trade(exit_side, base_amount, self.active_pos['tp'], order_type="limit")
                    if limit_res and 'id' in limit_res:
                        self.active_pos['limit_order_id'] = limit_res['id']
                        logger.info(f"Placed Limit TP Order {limit_res['id']} at {self.active_pos['tp']}")

                logger.info(f"✅ Position Opened: {pos_side} | Entry {actual_entry}, SL {self.active_pos['sl']}, TP {self.active_pos['tp']}")
                asyncio.create_task(self._send_telegram(f"🚀 *{pos_side} Opened*\nPair: {self.symbol}\nEntry: {actual_entry}\nReason: {reason}"))
                
        except Exception as e:
            logger.error(f"Snipe Execution Error: {e}")

    async def manage_risk(self, current_price: float):
        """রিস্ক ম্যানেজমেন্ট (TP/SL/TSL)"""
        if not self.active_pos: return
        
        side = self.active_pos['side']

        # 1. Check if the limit TP order has already been filled by the exchange
        if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id') and not self.is_paper_trading:
            try:
                order_status = await self.private_exchange.fetch_order(self.active_pos['limit_order_id'], self.symbol)
                if order_status and order_status.get('status') == 'closed':
                    filled_price = order_status.get('average') or order_status.get('price') or self.active_pos['tp']
                    executed_amount = order_status.get('filled') or self.active_pos.get('amount')
                    
                    if side == "long":
                        pnl_val = (filled_price - self.active_pos['entry']) * executed_amount
                    else:
                        pnl_val = (self.active_pos['entry'] - filled_price) * executed_amount
                        
                    await self._send_telegram(f"🎯 Futures EXIT - Limit TP Filled!\nPair: {self.symbol}\nExit Price: {filled_price:.6f}\nPnL: ${pnl_val:.2f}")
                    logger.info(f"✅ Limit TP Order {self.active_pos['limit_order_id']} was filled by exchange at {filled_price}")
                    self.active_pos = None
                    return
            except Exception as e:
                logger.warning(f"Error checking limit order status: {e}")

        # Trailing Stop Update
        if side == "long":
            if current_price > self.extreme_price:
                self.extreme_price = current_price
                new_sl = self.extreme_price * (1 - (self.tsl_pct / 100))
                # ATR Support
                if self.atr_sl_enabled and self.current_atr > 0:
                    atr_sl = self.extreme_price - (self.current_atr * self.atr_multiplier)
                    new_sl = max(new_sl, atr_sl)
                self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)
        else: # short
            if current_price < self.extreme_price or self.extreme_price == 0:
                self.extreme_price = current_price
                new_sl = self.extreme_price * (1 + (self.tsl_pct / 100))
                # ATR Support
                if self.atr_sl_enabled and self.current_atr > 0:
                    atr_sl = self.extreme_price + (self.current_atr * self.atr_multiplier)
                    new_sl = min(new_sl, atr_sl)
                self.active_pos['sl'] = min(self.active_pos['sl'], new_sl)

        # TP / SL চেক
        should_exit = False
        reason = ""
        
        if side == "long":
            # Scale-Out (Partial TP1)
            if self.partial_tp_pct > 0 and not self.active_pos.get('tp1_hit') and current_price >= self.active_pos['tp1']:
                await self.execute_partial_close(current_price)
                return

            if current_price >= self.active_pos['tp']:
                should_exit = True
                reason = "Take Profit"
            elif current_price <= self.active_pos['sl']:
                should_exit = True
                reason = "Stop Loss"
        else: # short
            # Scale-Out (Partial TP1)
            if self.partial_tp_pct > 0 and not self.active_pos.get('tp1_hit') and current_price <= self.active_pos['tp1']:
                await self.execute_partial_close(current_price)
                return

            if current_price <= self.active_pos['tp']:
                should_exit = True
                reason = "Take Profit"
            elif current_price >= self.active_pos['sl']:
                should_exit = True
                reason = "Stop Loss"

        if should_exit:
            logger.info(f"🚩 Exiting {side.upper()} Position: {reason} at {current_price}")
            
            # Cancel open limit order if SL/TSL hits
            if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
                try:
                    await self.engine.cancel_order(self.active_pos['limit_order_id'])
                    logger.info("Successfully cancelled Limit TP Order due to Stop Loss hit/Emergency Sell.")
                except Exception as e:
                    logger.warning(f"Failed to cancel Limit TP Order: {e}")
            
            # ফিউচার ক্লোজের জন্য বিপরীত অর্ডার
            exit_side = "sell" if side == "long" else "buy"
            
            res = await self.engine.execute_trade(exit_side, self.active_pos['amount'], current_price)
            if res:
                logger.info(f"✅ {side.upper()} Position Closed: {reason}")
                await self._send_telegram(f"🏁 *{side.upper()} Closed* ({reason})\nPrice: {current_price}\nPair: {self.symbol}")
                self.active_pos = None

    async def execute_partial_close(self, current_price: float):
        """TP1 এ পজিশনের একাংশ ক্লোজ করা এবং SL ব্রেক-ইভেনে আনা"""
        side = self.active_pos['side']
        entry = self.active_pos['entry']
        amount = self.active_pos['amount']
        
        sell_amount_raw = amount * (self.partial_tp_pct / 100)
        
        # Determine precision based on minimum contract size
        min_amount = 1.0
        if self.public_exchange and getattr(self.public_exchange, 'markets', None):
            market = self.public_exchange.markets.get(self.symbol, {})
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 1.0)
            if min_amount is None: min_amount = 1.0

        if min_amount >= 1.0:
            sell_amount = float(int(sell_amount_raw))
        else:
            sell_amount = float(f"{sell_amount_raw:.6f}")
            
        if sell_amount < min_amount:
            logger.warning(f"Partial TP amount {sell_amount_raw} is less than minimum {min_amount}. Skipping Partial TP.")
            self.active_pos['tp1_hit'] = True
            
            # Move SL to Break-Even anyway since we hit TP1 target
            buffer = abs(self.active_pos['tp'] - entry) * 0.1
            if side == "long":
                self.active_pos['sl'] = max(self.active_pos['sl'], entry + buffer)
            else:
                self.active_pos['sl'] = min(self.active_pos['sl'], entry - buffer)
            return
            
        logger.info(f"🔓 [PARTIAL TP] Closing {self.partial_tp_pct}% ({sell_amount} contracts) of {side.upper()} at {current_price}")
        
        exit_side = "sell" if side == "long" else "buy"
        res = None
        
        if self.sell_order_type == 'limit':
            res = await self.engine.execute_trade(exit_side, sell_amount, current_price, order_type="limit")
            if res: logger.info(f"Placed Limit Order for Partial TP at {current_price}")
            if res and self.is_paper_trading:
                # Mock instant fill for paper trade limit at current price
                await self.engine.execute_trade(exit_side, sell_amount, current_price)
        else:
            res = await self.engine.execute_trade(exit_side, sell_amount, current_price)
            if res: logger.info(f"Executed Market Order for Partial TP at {current_price}")
            
        # Update Limit order to prevent over-selling
        if res and self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
            try:
                await self.engine.cancel_order(self.active_pos['limit_order_id'])
                remain_amount = self.active_pos['amount'] - sell_amount
                limit_res = await self.engine.execute_trade(exit_side, remain_amount, self.active_pos['tp'], order_type="limit")
                if limit_res and 'id' in limit_res:
                    self.active_pos['limit_order_id'] = limit_res['id']
            except Exception as e:
                logger.error(f"Failed to update Limit order after TP1: {e}")
        
        if res:
            self.active_pos['amount'] -= sell_amount
            # Move SL to Break-Even (Entry + tiny buffer)
            buffer = abs(self.active_pos['tp'] - entry) * 0.1
            if side == "long":
                self.active_pos['sl'] = max(self.active_pos['sl'], entry + buffer)
            else:
                self.active_pos['sl'] = min(self.active_pos['sl'], entry - buffer)
            
            self.active_pos['tp1_hit'] = True
            logger.info(f"✅ Partial TP Completed. Remaining: {self.active_pos['amount']}, New SL: {self.active_pos['sl']}")
            await self._send_telegram(f"🔓 *Partial TP1 Hit!* ({self.partial_tp_pct}%)\nRemaining amount closed at Break-Even SL.")
        else:
            logger.warning("❌ Partial TP execution failed. Marking tp1_hit as True to prevent infinite loop spam, position size unchanged.")
            self.active_pos['tp1_hit'] = True

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
                "side": self.active_pos['side'] if self.active_pos else None,
                "absorption_delta": float(f"{self.absorption_tracker.get_current_delta():.2f}"),
                "is_absorbing": self.absorption_tracker.is_absorption_detected('buy') or self.absorption_tracker.is_absorption_detected('sell')
            }
            self.redis.publish(f"bot_status:{self.bot_id}", json.dumps(status_payload))
        except Exception:
            pass

    async def stop(self):
        self.running = False
        if self.public_exchange: await self.public_exchange.close()
        if self.private_exchange: await self.private_exchange.close()
        
        if self._vpvr_task: self._vpvr_task.cancel()
        if self._atr_task: self._atr_task.cancel()
        if self._liq_task: self._liq_task.cancel()
        if self._trades_task: self._trades_task.cancel()
        if getattr(self, '_btc_task', None): self._btc_task.cancel()
        
        if hasattr(self, 'btc_correlation_tracker') and self.btc_correlation_tracker:
            await self.btc_correlation_tracker.stop()
        
        logger.info(f"🔴 [FuturesHunter {self.bot_id}] Stopped.")
        await self._send_telegram(f"🔴 Futures Bot [ID: {self.bot_id}] Stopped.")

    async def emergency_sell(self, sell_type: str):
        """Emergency liquidate the active position."""
        if not self.active_pos:
            logger.info(f"No active position to emergency sell for bot {self.bot_id}")
            return
            
        side = self.active_pos['side']
        amount = self.active_pos['amount']
        
        # Determine current market price
        try:
            ob = await self.public_exchange.fetch_order_book(self.symbol, limit=5)
            best_bid = ob['bids'][0][0] if ob['bids'] else 0
            best_ask = ob['asks'][0][0] if ob['asks'] else 0
            current_price = (best_bid + best_ask) / 2 if best_bid and best_ask else best_bid or best_ask
        except Exception as e:
            logger.warning(f"Could not fetch precise price for emergency sell: {e}")
            current_price = self.active_pos['entry']

        # Cancel any open limit orders first
        if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
            try:
                await self.engine.cancel_order(self.active_pos['limit_order_id'])
                logger.info(f"Cancelled open limit order {self.active_pos['limit_order_id']} for emergency sell.")
            except Exception as e:
                logger.warning(f"Failed to cancel open limit order during emergency sell: {e}")

        # Determine exit side
        exit_side = "sell" if side == "long" else "buy"
        
        logger.info(f"🚨 [EMERGENCY] Closing {side.upper()} position for bot {self.bot_id} via {sell_type.upper()}")
        
        res = await self.engine.execute_trade(exit_side, amount, current_price, order_type=sell_type)
        if res:
            pnl_val = (current_price - self.active_pos['entry']) * amount if side == "long" else (self.active_pos['entry'] - current_price) * amount
            await self._send_telegram(f"🚨 *EMERGENCY EXIT* triggered!\nPair: {self.symbol}\nSide: {side.upper()}\nExit Price: {current_price}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info(f"✅ Emergency exit completed.")

    def update_config(self, new_config: dict):
        """Update strategy parameters dynamically."""
        logger.info(f"🔄 [FuturesHunter {self.bot_id}] Live config update: {new_config}")
        
        updates = []
        if "vol_threshold" in new_config:
            updates.append(f"Vol Threshold: {self.vol_threshold} -> {new_config['vol_threshold']}")
            self.vol_threshold = new_config["vol_threshold"]
        
        if "target_spread" in new_config:
            updates.append(f"Spread: {self.target_spread} -> {new_config['target_spread']}")
            self.target_spread = new_config["target_spread"]
            
        if "risk_pct" in new_config:
            updates.append(f"Risk: {self.initial_risk_pct}% -> {new_config['risk_pct']}%")
            self.initial_risk_pct = new_config["risk_pct"]
            
        if "trailing_stop" in new_config:
            updates.append(f"TSL: {self.tsl_pct}% -> {new_config['trailing_stop']}%")
            self.tsl_pct = new_config["trailing_stop"]

        if "leverage" in new_config:
            updates.append(f"Leverage: {self.leverage}x -> {new_config['leverage']}x")
            self.leverage = new_config["leverage"]
            # Apply leverage to exchange live
            asyncio.create_task(self.private_exchange.set_leverage(self.leverage, self.symbol))

        if "amount_per_trade" in new_config:
            updates.append(f"Amount: {self.amount_per_trade} -> {new_config['amount_per_trade']}")
            self.amount_per_trade = new_config["amount_per_trade"]

        if "sell_order_type" in new_config:
            updates.append(f"Order Type: {self.sell_order_type} -> {new_config['sell_order_type']}")
            self.sell_order_type = new_config["sell_order_type"]

        if "ob_imbalance_ratio" in new_config:
            updates.append(f"OB Ratio: {self.ob_imbalance_ratio} -> {new_config['ob_imbalance_ratio']}")
            self.ob_imbalance_ratio = new_config["ob_imbalance_ratio"]

        if "liq_threshold" in new_config:
            updates.append(f"Liq Threshold: {self.liq_threshold} -> {new_config['liq_threshold']}")
            self.liq_threshold = new_config["liq_threshold"]

        if "btc_correlation_threshold" in new_config:
            updates.append(f"BTC Corr Threshold: {self.btc_correlation_threshold} -> {new_config['btc_correlation_threshold']}")
            self.btc_correlation_threshold = new_config.get("btc_correlation_threshold")
            if self.btc_correlation_tracker: self.btc_correlation_tracker.update_params(threshold=self.btc_correlation_threshold)

        if "btc_time_window" in new_config:
            updates.append(f"BTC Time Window: {self.btc_time_window}m -> {new_config['btc_time_window']}m")
            self.btc_time_window = new_config.get("btc_time_window")
            if self.btc_correlation_tracker: self.btc_correlation_tracker.update_params(window_minutes=self.btc_time_window)

        if "btc_min_move_pct" in new_config:
            updates.append(f"BTC Min Move %: {self.btc_min_move_pct}% -> {new_config['btc_min_move_pct']}%")
            self.btc_min_move_pct = new_config.get("btc_min_move_pct")
            if self.btc_correlation_tracker: self.btc_correlation_tracker.update_params(min_move_pct=self.btc_min_move_pct)
        
        if "enable_btc_correlation" in new_config:
            status = "ON" if new_config["enable_btc_correlation"] else "OFF"
            updates.append(f"BTC Correlation Filter: {status}")
            self.enable_btc_correlation = new_config.get("enable_btc_correlation")
            if self.enable_btc_correlation and self.btc_correlation_tracker:
                asyncio.create_task(self.btc_correlation_tracker.start())
            elif not self.enable_btc_correlation and self.btc_correlation_tracker:
                asyncio.create_task(self.btc_correlation_tracker.stop())

        if updates:
            self.config.update(new_config)
            
            # --- Sync internal parameters ---
            if "partial_tp_pct" in new_config: self.partial_tp_pct = new_config["partial_tp_pct"]
            if "vpvr_enabled" in new_config: self.vpvr_enabled = new_config["vpvr_enabled"]
            if "vpvr_tolerance" in new_config: self.vpvr_tolerance = new_config["vpvr_tolerance"]
            if "atr_sl_enabled" in new_config: self.atr_sl_enabled = new_config["atr_sl_enabled"]
            if "enable_wall_trigger" in new_config: self.enable_wall_trigger = new_config["enable_wall_trigger"]
            if "enable_liq_trigger" in new_config: self.enable_liq_trigger = new_config["enable_liq_trigger"]
            if "enable_ob_imbalance" in new_config: self.enable_ob_imbalance = new_config["enable_ob_imbalance"]
            if "ob_imbalance_ratio" in new_config: self.ob_imbalance_ratio = new_config["ob_imbalance_ratio"]
            if "enable_liq_cascade" in new_config: self.enable_liq_cascade = new_config["enable_liq_cascade"]
            if "enable_dynamic_liq" in new_config: self.enable_dynamic_liq = new_config["enable_dynamic_liq"]
            if "enable_btc_correlation" in new_config: self.enable_btc_correlation = new_config["enable_btc_correlation"]
            if "btc_correlation_threshold" in new_config: self.btc_correlation_threshold = new_config["btc_correlation_threshold"]
            if "btc_time_window" in new_config: self.btc_time_window = new_config["btc_time_window"]
            if "btc_min_move_pct" in new_config: self.btc_min_move_pct = new_config["btc_min_move_pct"]
            if "dynamic_liq_multiplier" in new_config: self.dynamic_liq_multiplier = new_config["dynamic_liq_multiplier"]
            if "follow_btc_liq" in new_config: self.follow_btc_liq = new_config["follow_btc_liq"]
            if "btc_liq_threshold" in new_config: self.btc_liq_threshold = new_config["btc_liq_threshold"]
            
            # CVD Absorption Sync
            if "enable_absorption" in new_config: self.enable_absorption = new_config["enable_absorption"]
            if "absorption_threshold" in new_config: 
                self.absorption_threshold = new_config["absorption_threshold"]
                self.absorption_tracker.update_params(threshold=self.absorption_threshold)
            if "absorption_window" in new_config:
                self.absorption_window = new_config["absorption_window"]
                self.absorption_tracker.update_params(window_seconds=self.absorption_window)
            
            asyncio.create_task(self._send_telegram(f"⚙️ *Live Config Update*\n{self.symbol} Futures Bot\n\n" + "\n".join([f"• {u}" for u in updates])))

    async def _vpvr_updater_loop(self):
        """VPVR High Volume Nodes আপডেট করবে (প্রতি ৫ মিনিটে)"""
        while self.running:
            if not self.vpvr_enabled:
                await asyncio.sleep(60)
                continue
            try:
                ohlcv = await self.public_exchange.fetch_ohlcv(self.symbol, timeframe='5m', limit=100)
                if ohlcv:
                    prices = [c[4] for c in ohlcv]
                    vols = [c[5] for c in ohlcv]
                    min_p, max_p = min(prices), max(prices)
                    bins = 50
                    step = (max_p - min_p) / bins
                    profile = [0.0] * bins
                    for i, p in enumerate(prices):
                        idx = int((p - min_p) / step) if step > 0 else 0
                        if idx >= bins: idx = bins - 1
                        profile[idx] += vols[i]
                    top_indices = sorted(range(bins), key=lambda i: profile[i], reverse=True)[:3]
                    self.top_hvns = [min_p + (i * step) + (step/2) for i in top_indices]
                    logger.info(f"📊 [FuturesHunter {self.bot_id}] VPVR HVNs: {self.top_hvns}")
            except Exception as e: logger.error(f"VPVR Error: {e}")
            await asyncio.sleep(300)

    async def _trades_listener(self):
        """Background task to watch trades and feed the AbsorptionTracker."""
        logger.info(f"📣 [FuturesHunter {self.bot_id}] Starting Trades Listener for CVD Absorption...")
        while self.running:
            try:
                # We use public exchange for trades
                trades = await self.public_exchange.watch_trades(self.symbol)
                if not trades:
                    continue
                    
                for trade in trades:
                    p = float(trade['price'])
                    a = float(trade['amount'])
                    s = trade['side'] # 'buy' (hits ask) or 'sell' (hits bid)
                    self.absorption_tracker.add_trade(p, a, s)
                    
            except Exception as e:
                if self.running:
                    logger.warning(f"Trade Listener Error: {e}")
                await asyncio.sleep(1)

    async def _atr_updater_loop(self):
        """ATR ভ্যালু আপডেট করবে (প্রতি মিনিটে)"""
        while self.running:
            if not self.atr_sl_enabled:
                await asyncio.sleep(60)
                continue
            try:
                ohlcv = await self.public_exchange.fetch_ohlcv(self.symbol, timeframe='1m', limit=self.atr_period + 1)
                if len(ohlcv) > self.atr_period:
                    tr_list = []
                    for i in range(1, len(ohlcv)):
                        h, l, pc = ohlcv[i][2], ohlcv[i][3], ohlcv[i-1][4]
                        tr = max(h - l, abs(h - pc), abs(l - pc))
                        tr_list.append(tr)
                    self.current_atr = sum(tr_list[-self.atr_period:]) / self.atr_period
                    logger.info(f"📈 [FuturesHunter {self.bot_id}] ATR: {self.current_atr}")
            except Exception as e: logger.error(f"ATR Error: {e}")
            await asyncio.sleep(60)

    async def _liquidation_listener(self):
        """লিকুইডেশন ইভেন্ট লিসেনার (রেডিস সাবস্ক্রিপশন)"""
        pubsub = self.redis.pubsub()
        current_ch = None
        while self.running:
            try:
                if not self.enable_liq_trigger:
                    if current_ch:
                        pubsub.unsubscribe(current_ch)
                        current_ch = None
                    await asyncio.sleep(5)
                    continue
                
                target_ch = f"stream:liquidations:BTC/USDT" if self.follow_btc_liq else f"stream:liquidations:{self.symbol}"
                if current_ch != target_ch:
                    if current_ch: pubsub.unsubscribe(current_ch)
                    pubsub.subscribe(target_ch)
                    current_ch = target_ch
                    logger.info(f"🎧 [FuturesHunter {self.bot_id}] Monitoring Liquidations: {current_ch}")

                msg = pubsub.get_message(ignore_subscribe_messages=True)
                if msg and msg['type'] == 'message':
                    data = json.loads(msg['data'].decode('utf-8'))
                    liq_amount = float(data.get('amount', 0))
                    liq_side = data.get('side', '').lower() # 'buy' means Longs liquidated, 'sell' means Shorts liquidated
                    now = time.time()
                    
                    # 1. Cascade Logic
                    if self.enable_liq_cascade:
                        self.liq_history.append((now, liq_amount))
                        while self.liq_history and now - self.liq_history[0][0] > self.liq_cascade_window:
                            self.liq_history.popleft()
                        active_amount = sum(a for t, a in self.liq_history)
                    else:
                        active_amount = liq_amount

                    # 2. Dynamic Threshold Logic
                    base_threshold = self.btc_liq_threshold if self.follow_btc_liq else self.liq_threshold
                    active_threshold = base_threshold
                    
                    if self.enable_dynamic_liq and self.current_atr > 0 and not self.follow_btc_liq:
                        # Threshold = Multiplier * ATR * Side-specific heuristics
                        # A simple effective one: Price * ATR_PCT * Multiplier
                        try:
                            # Use ATR as volatility proxy
                            active_threshold = base_threshold * (1 + (self.current_atr * self.dynamic_liq_multiplier))
                        except: pass

                    # 3. Trigger Decision
                    if active_amount >= active_threshold:
                        if not self.active_pos:
                            side = "buy" if liq_side == "sell" else "sell"
                            if self.enable_liq_cascade: self.liq_history.clear()
                            
                            reason = f"Liquidation Trigger ({liq_side.upper()} ${active_amount:,.0f} [Thresh: ${active_threshold:,.0f}])"
                            logger.info(f"🔥 [LIQ TRIGGER] {reason} on {target_ch}")
                            await self._handle_liquidation_trigger(side, reason=reason)
            except Exception as e: 
                logger.error(f"Liq Listener Error: {e}")
                await asyncio.sleep(2)
            await asyncio.sleep(0.1)

    async def _handle_liquidation_trigger(self, side: str, reason: str):
        if self.active_pos: return
        try:
            # 1. Fetch current price and orderbook for filters
            ob = await self.public_exchange.fetch_order_book(self.symbol, limit=20)
            if not ob['bids'] or not ob['asks']: return
            
            mid = (ob['bids'][0][0] + ob['asks'][0][0]) / 2
            
            # 2. Imbalance Filter (Confluence)
            if self.enable_ob_imbalance:
                bid_vol = sum(v for p, v in ob['bids'])
                ask_vol = sum(v for p, v in ob['asks'])
                if side == "buy":
                    ratio = bid_vol / ask_vol if ask_vol > 0 else 999
                else:
                    ratio = ask_vol / bid_vol if bid_vol > 0 else 999
                
                if ratio < self.ob_imbalance_ratio:
                    logger.info(f"⏭️ [LIQ] Rejected: OB Imbalance Ratio {ratio:.2f} < {self.ob_imbalance_ratio}")
                    return
                logger.info(f"✅ [LIQ] OB Imbalance Confirmed: {ratio:.2f}x")

            # 3. Wall Confirmation Filter
            if self.enable_wall_trigger:
                strong_wall = False
                target_levels = ob['bids'] if side == "buy" else ob['asks']
                # Check for any wall meeting the threshold
                for level in target_levels:
                    price, v = level[0], level[1]
                    if v >= self.micro_scalp_min_wall:
                        strong_wall = True
                        logger.info(f"🔥 [LIQ] Wall Confluence: Found {v:,.0f} wall at {price}")
                        break
                
                if not strong_wall:
                    logger.info(f"⏭️ [LIQ] Rejected: No supporting wall >= {self.micro_scalp_min_wall}")
                    return

            await self.execute_snipe(mid, side, mid, reason=reason)
        except Exception as e: logger.error(f"Liq Handler Error: {e}")

    async def _send_telegram(self, msg: str):
        if not self.owner_id: return
        from app.services.notification import NotificationService
        from app.db.session import SessionLocal
        try:
            db = SessionLocal()
            await NotificationService.send_message(db, self.owner_id, msg)
            db.close()
        except Exception as e:
            logger.error(f"Telegram notify error: {e}")
