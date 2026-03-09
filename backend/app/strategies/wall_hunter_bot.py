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
        self.vol_threshold = config.get("vol_threshold", 500000)
        self.target_spread = config.get("target_spread", 0.0002)
        self.initial_risk_pct = config.get("risk_pct", 0.5)
        self.tsl_pct = config.get("trailing_stop", 0.2)
        self.sell_order_type = config.get("sell_order_type", "market")
        
        # --- NEW FEATURES: Partial TP & Break-Even SL ---
        self.partial_tp_pct = config.get("partial_tp_pct", 50.0) # TP1 এ কত পার্সেন্ট সেল করবে
        
        # --- NEW FEATURES: Spoofing Detection ---
        self.min_wall_lifetime = config.get("min_wall_lifetime", 3.0) # ওয়ালকে অন্তত কত সেকেন্ড টিকে থাকতে হবে
        self.tracked_walls = {} # ওয়ালগুলোকে ট্র্যাক করার জন্য ডিকশনারি
        # ----------------------------------------
        
        self.engine = OrderBlockExecutionEngine(config)
        self.active_pos = None
        self.highest_price = 0.0
        self.running = False
        self._heartbeat_task = None
        self.redis = get_redis_client()

    def update_config(self, new_config: dict):
        """Update strategy parameters dynamically without stopping the bot."""
        logger.info(f"🔄 [WallHunter {self.bot_id}] Live config update requested: {new_config}")
        
        # Keep track of old values for logging
        updates = []
        
        if "vol_threshold" in new_config and new_config["vol_threshold"] != self.vol_threshold:
            updates.append(f"Volume Threshold: {self.vol_threshold} -> {new_config['vol_threshold']}")
            self.vol_threshold = new_config.get("vol_threshold")
            
        if "target_spread" in new_config and new_config["target_spread"] != self.target_spread:
            updates.append(f"Target Spread: {self.target_spread} -> {new_config['target_spread']}")
            self.target_spread = new_config.get("target_spread")
            
        if "trailing_stop" in new_config and new_config["trailing_stop"] != self.tsl_pct:
            updates.append(f"Trailing SL: {self.tsl_pct}% -> {new_config['trailing_stop']}%")
            self.tsl_pct = new_config.get("trailing_stop")
            
        if "risk_pct" in new_config and new_config["risk_pct"] != self.initial_risk_pct:
            updates.append(f"Risk Pct: {self.initial_risk_pct}% -> {new_config['risk_pct']}%")
            self.initial_risk_pct = new_config.get("risk_pct")
            
        if "amount_per_trade" in new_config and self.engine and hasattr(self.engine, 'config'):
            old_amount = self.engine.config.get("amount_per_trade")
            if new_config["amount_per_trade"] != old_amount:
                updates.append(f"Trade Amount: {old_amount} -> {new_config['amount_per_trade']}")
                self.engine.config["amount_per_trade"] = new_config["amount_per_trade"]
                
        if "min_wall_lifetime" in new_config and new_config["min_wall_lifetime"] != self.min_wall_lifetime:
            updates.append(f"Spoof Detect (s): {self.min_wall_lifetime} -> {new_config['min_wall_lifetime']}")
            self.min_wall_lifetime = new_config.get("min_wall_lifetime")
            
        if "partial_tp_pct" in new_config and new_config["partial_tp_pct"] != self.partial_tp_pct:
            updates.append(f"Partial TP: {self.partial_tp_pct}% -> {new_config['partial_tp_pct']}%")
            self.partial_tp_pct = new_config.get("partial_tp_pct")
            
        # Update internal config dictionary
        self.config.update(new_config)
        
        if updates:
            msg = f"⚡ [WallHunter {self.bot_id}] Live Configuration Updated:\n" + "\n".join([f"- {u}" for u in updates])
            logger.info(msg)
            # Fire and forget telegram notification
            asyncio.create_task(self._send_telegram(f"⚙️ *Live Config Update*\n{self.symbol} Bot #{self.bot_id}\n\n" + "\n".join([f"• {u}" for u in updates])))
        else:
            logger.info(f"⚡ [WallHunter {self.bot_id}] Config update received, but no changes detected.")

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
                
                amount = self.active_pos.get('amount', 0)
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
                if not orderbook['bids'] or not orderbook['asks']:
                    await asyncio.sleep(1)
                    continue

                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2
                current_time = time.time()

                if not self.active_pos:
                    # 1. বর্তমান অর্ডার বুকের ওয়ালগুলো ফিল্টার করা
                    current_walls = {}
                    max_vol = 0
                    for price, vol in orderbook['bids']:
                        if vol > max_vol:
                            max_vol = vol
                        if vol >= self.vol_threshold:
                            current_walls[price] = vol
                    
                    if current_time % 5 < 0.05: # Print approx every 5 seconds
                        logger.info(f"🔍 [Debug] Max Bid Vol: {max_vol}, Threshold: {self.vol_threshold}, Walls Configured: {len(current_walls)}, Tracked: {len(self.tracked_walls)}")
                    
                    # 2. ওয়াল অ্যানালাইসিস এবং স্পুফিং ডিটেকশন
                    for price, vol in current_walls.items():
                        if self.min_wall_lifetime <= 0:
                            # 0-সেকেন্ড হলে সাথে সাথেই কিনে ফেলবে (পুরোনো লজিকের মতো)
                            logger.info(f"🟢 Instant Snipe at {price} (Spoof Detect is 0s). Executing!")
                            await self.execute_snipe(price, "buy", mid_price)
                            self.tracked_walls.clear()
                            current_walls.clear() # Prevent further processing
                            break

                        if price in self.tracked_walls:
                            # ওয়ালটি এখনও আছে, তাই লাস্ট আপডেট টাইম চেঞ্জ করছি
                            self.tracked_walls[price]['last_seen'] = current_time
                            self.tracked_walls[price]['vol'] = vol
                            
                            # চেক করছি ওয়ালটি পর্যাপ্ত সময় ধরে টিকে আছে কিনা
                            time_alive = current_time - self.tracked_walls[price]['first_seen']
                            if time_alive >= self.min_wall_lifetime:
                                logger.info(f"🟢 Genuine Wall detected at {price} (Alive for {time_alive:.1f}s). Executing Snipe!")
                                await self.execute_snipe(price, "buy", mid_price)
                                self.tracked_walls.clear() # এন্ট্রি নেওয়ার পর ট্র্যাকিং ক্লিয়ার
                                break
                        else:
                            # নতুন একটি বড় ওয়াল পাওয়া গেছে, ট্র্যাকিং শুরু
                            self.tracked_walls[price] = {
                                "vol": vol,
                                "first_seen": current_time,
                                "last_seen": current_time
                            }
                    
                    # 3. ফেইক বা স্পুফ করা ওয়ালগুলো রিমুভ করা
                    spoofed_prices = []
                    for price, data in self.tracked_walls.items():
                        if price not in current_walls:
                            spoofed_prices.append(price)
                    
                    for p in spoofed_prices:
                        time_alive = current_time - self.tracked_walls[p]['first_seen']
                        logger.info(f"⚠️ Spoofing Detected: Wall at {p} disappeared after {time_alive:.1f}s. Ignoring.")
                        del self.tracked_walls[p]

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
            
            # If CCXT did not return average price initially, fetch the order from the exchange
            if not self.is_paper_trading and res.get('id') and self.engine.exchange and not (avg_price and avg_price > 0):
                try:
                    logger.info(f"Fetching order {res.get('id')} to get accurate execution price...")
                    await asyncio.sleep(0.5) # Wait for exchange to process market order
                    fetched_order = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                    if fetched_order:
                        res = fetched_order
                        avg_price = res.get('average')
                        fill_price = res.get('price')
                except Exception as e:
                    logger.warning(f"Failed to fetch updated order info for {res.get('id')}: {e}")

            actual_entry = avg_price if avg_price and avg_price > 0 else (fill_price if fill_price and fill_price > 0 else entry_price)
            actual_entry = float(actual_entry)
            
            # Sanity Check to prevent instant SL logic if CCXT returns an outdated or widely inaccurate fill price
            slippage_pct = abs(actual_entry - current_mid_price) / current_mid_price
            if slippage_pct > 0.02: # If the executed price differs from the mid price by more than 2%
                logger.warning(f"Suspicious fill price from CCXT: {actual_entry}. Overriding with mid_price: {current_mid_price}")
                actual_entry = current_mid_price
            
            # --- UPDATED: Position tracking for TP1 and TP2 ---
            self.active_pos = {
                "entry": actual_entry,
                "amount": base_amount,
                "sl": actual_entry * (1 - (self.initial_risk_pct / 100)),
                "tp1": actual_entry + (self.target_spread * 0.5), # TP1 at 50% target
                "tp": actual_entry + self.target_spread,          # Final TP
                "tp1_hit": False,
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
            await self._send_telegram(f"⚡ WallHunter Entered!\nPair: {self.symbol}\nEntry: {actual_entry:.6f}\nTP1 (Scale Out): {self.active_pos['tp1']:.6f}\nFinal TP: {self.active_pos['tp']:.6f}\nSL: {self.active_pos['sl']:.6f}")

    async def manage_risk(self, current_price: float):
        if not self.active_pos: return

        # 1. Check if the limit TP order has already been filled by the exchange
        if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id') and not self.is_paper_trading:
            try:
                order_status = await self.engine.exchange.fetch_order(self.active_pos['limit_order_id'], self.symbol)
                if order_status and order_status.get('status') == 'closed':
                    # The limit order was filled!
                    filled_price = order_status.get('average') or order_status.get('price') or self.active_pos['tp']
                    sell_amount = order_status.get('filled') or self.active_pos.get('amount')
                    
                    pnl_val = (filled_price - self.active_pos['entry']) * sell_amount
                    await self._send_telegram(f"🎯 WallHunter EXIT - Limit TP Filled!\nPair: {self.symbol}\nExit Price: {filled_price:.6f}\nPnL: ${pnl_val:.2f}")
                    logger.info(f"✅ Limit TP Order {self.active_pos['limit_order_id']} was filled by exchange at {filled_price}")
                    self.active_pos = None
                    return
            except Exception as e:
                logger.warning(f"Error checking limit order status: {e}")

        if current_price > self.highest_price:
            self.highest_price = current_price
            # Update Trailing SL
            new_sl = self.highest_price * (1 - (self.tsl_pct / 100))
            self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)

        # --- NEW: Partial TP & Break-Even SL Logic ---
        # Only execute TP1 logic if partial_tp_pct > 0
        if self.partial_tp_pct > 0 and not self.active_pos.get('tp1_hit') and current_price >= self.active_pos['tp1']:
            logger.info("🟢 TP1 Hit! Executing Partial Close & Moving SL to Break-Even.")
            sell_amount = self.active_pos['amount'] * (self.partial_tp_pct / 100)
            
            # Use limit order if configured for selling to prevent slippage on TP1
            if self.sell_order_type == 'limit':
                await self.engine.execute_trade("sell", sell_amount, self.active_pos['tp1'], order_type="limit")
                logger.info(f"Placed Limit Order for Partial TP at {self.active_pos['tp1']}")
            else:
                await self.engine.execute_trade("sell", sell_amount, current_price)
                logger.info(f"Executed Market Order for Partial TP at {current_price}")
            
            # Update Limit order to prevent over-selling
            if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
                try:
                    await self.engine.cancel_order(self.active_pos['limit_order_id'])
                    limit_res = await self.engine.execute_trade("sell", self.active_pos['amount'] - sell_amount, self.active_pos['tp'], order_type="limit")
                    if limit_res and 'id' in limit_res:
                        self.active_pos['limit_order_id'] = limit_res['id']
                except Exception as e:
                    logger.error(f"Failed to update limit order after TP1: {e}")
            
            self.active_pos['amount'] -= sell_amount
            # Move SL to Entry + a small fraction of the target spread to ensure it's profitable but below TP1
            # We use 10% of the target spread as the profitable break-even distance
            profitable_be = self.active_pos['entry'] + (self.target_spread * 0.1)
            self.active_pos['sl'] = max(self.active_pos['sl'], profitable_be)
            self.active_pos['tp1_hit'] = True
            
            pnl_val = (self.active_pos['tp1'] if self.sell_order_type == 'limit' else current_price - self.active_pos['entry']) * sell_amount
            await self._send_telegram(f"🔓 Partial TP Hit!\nPair: {self.symbol}\nLocked Profit: ${pnl_val:.2f}\n✅ Stop-Loss is now Risk-Free at Entry + {(self.target_spread * 0.1):.6f}!")

        elif current_price <= self.active_pos['sl']:
            logger.info(f"⚠️ Triggering SL: Current Price ({current_price:.6f}) <= SL ({self.active_pos['sl']:.6f})")
            sell_amount = self.active_pos['amount']
            
            # Cancel open limit order if TSL hits
            if self.sell_order_type == 'limit' and self.active_pos.get('limit_order_id'):
                await self.engine.cancel_order(self.active_pos['limit_order_id'])
                logger.info("Cancelled Limit TP Order due to Stop Loss hit")
                
            await self.engine.execute_trade("sell", sell_amount, current_price)
            
            if self.active_pos.get('tp1_hit') and current_price >= self.active_pos['entry']:
                 # Calculate the small guaranteed PnL from the profitable break-even
                 pnl_val = (current_price - self.active_pos['entry']) * sell_amount
                 await self._send_telegram(f"🛡️ WallHunter EXIT - Stopped out at Profitable Break-even!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nSecured PnL: ${pnl_val:.2f}")
            else:
                 # Calculate PnL
                 pnl_val = (current_price - self.active_pos['entry']) * sell_amount
                 await self._send_telegram(f"🛑 WallHunter EXIT - Stopped Out!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Stop Loss / TSL Hit")
            
        elif current_price >= self.active_pos['tp']:
            logger.info(f"✅ Triggering Final TP: Current Price ({current_price:.6f}) >= TP ({self.active_pos['tp']:.6f})")
            sell_amount = self.active_pos['amount']
            
            if self.sell_order_type == 'market':
                await self.engine.execute_trade("sell", sell_amount, current_price)
            else:
                logger.info(f"Target Profit {self.active_pos['tp']} reached. Assuming Limit Order {self.active_pos.get('limit_order_id', 'Unknown')} is filled.")
            
            # Calculate PnL
            pnl_val = (current_price - self.active_pos['entry']) * sell_amount
            await self._send_telegram(f"🎯 WallHunter EXIT - Final Take Profit Hit!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            logger.info("Exit: Take Profit Hit")

    async def stop(self):
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"Bot {self.bot_id} (WallHunter) stopped.")
        await self._send_telegram(f"🔴 WallHunter Bot [ID: {self.bot_id}] Stopped.")
