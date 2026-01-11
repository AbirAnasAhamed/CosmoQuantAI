import ccxt
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import asyncio
import json
import redis
from sqlalchemy.orm import Session
from app import models
from app.utils import get_redis_client
from app.core.config import settings
# ✅ সিকিউরিটি এবং স্ট্র্যাটেজি ইমপোর্ট
from app.core.security import decrypt_key
from app.core.security import decrypt_key
from app.strategies.live_strategies import LiveStrategyFactory
from app.models.trade import Trade

redis_log_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class LiveBotEngine:
    def __init__(self, bot: models.Bot, db_session: Session):
        self.bot = bot
        self.db = db_session
        self.symbol = bot.market
        self.timeframe = bot.timeframe
        self.redis = get_redis_client()
        
        # কনফিগারেশন লোড
        self.config = bot.config or {}
        
        # ✅ DYNAMIC STRATEGY LOADING
        strategy_name = bot.strategy or "RSI Strategy"
        self.strategy_executor = LiveStrategyFactory.get_strategy(strategy_name, self.config)
        
        # ট্রেডিং কনফিগারেশন
        self.deployment_target = self.config.get('deploymentTarget', 'Spot').lower()
        if 'future' in self.deployment_target: self.deployment_target = 'future'
        
        self.trade_value = bot.trade_value or 100.0
        self.trade_unit = bot.trade_unit or "QUOTE" # 'QUOTE' (USDT) or 'ASSET' (BTC)
        self.order_type = self.config.get('orderType', 'market').lower()
        
        # Risk Params
        risk_params = self.config.get('riskParams', {})
        self.stop_loss_pct = float(risk_params.get('stopLoss', 0))
        
        # Take Profits: [ {target: 2.0, amount: 50, executed: False}, ... ]
        self.take_profits = []
        raw_tps = risk_params.get('takeProfits', [])
        for tp in raw_tps:
            self.take_profits.append({
                "target": float(tp['target']),
                "amount": float(tp['amount']),
                "executed": False
            })
        # Sort by target percentage (ascending)
        self.take_profits.sort(key=lambda x: x['target'])
        
        # Trailing Stop
        self.trailing_config = risk_params.get('trailingStop', {})
        self.is_trailing_enabled = self.trailing_config.get('enabled', False)
        self.trailing_callback = float(self.trailing_config.get('callbackRate', 1.0))
        self.highest_price = 0.0 # To track high water mark

        # Position State (In-Memory)
        self.position = { "amount": 0.0, "entry_price": 0.0, "trade_id": None }
        
        self._load_state()

        # ✅ EXCHANGE INITIALIZATION WITH SECURITY
        self.exchange = self._initialize_exchange()

    def _load_state(self):
        """ডাটাবেস চেক করে দেখবে কোনো ওপেন ট্রেড আছে কিনা"""
        try:
            open_trade = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                Trade.status == "OPEN"
            ).first()

            if open_trade:
                self.position = {
                    "amount": open_trade.quantity,
                    "entry_price": open_trade.entry_price,
                    "trade_id": open_trade.id
                }
                self.highest_price = open_trade.entry_price
                self.log(f"🔄 Restored Open Position: {open_trade.quantity} @ {open_trade.entry_price}", "SYSTEM")
            else:
                self.log("✅ No open positions found. Starting fresh.", "SYSTEM")
                
        except Exception as e:
            self.log(f"⚠️ Error loading state: {e}", "ERROR")

    # ---------------------------------------------------------
    # ✅ ধাপ ১: এনক্রিপ্টেড API Key লোড এবং ডিক্রিপ্ট করা
    # ---------------------------------------------------------
    def _initialize_exchange(self):
        """ডাটাবেস থেকে API Key এনে ডিক্রিপ্ট করে এক্সচেঞ্জ কানেক্ট করা"""
        api_key_record = None
        
        # ১. বট কনফিগ থেকে নির্দিষ্ট API Key খোঁজা
        if self.bot.api_key_id:
            api_key_record = self.db.query(models.ApiKey).filter(
                models.ApiKey.id == int(self.bot.api_key_id),
                models.ApiKey.user_id == self.bot.owner_id
            ).first()
        
        # ২. না পেলে, এক্সচেঞ্জ নাম দিয়ে ডিফল্ট Active Key খোঁজা
        if not api_key_record:
            exchange_name = self.bot.exchange or 'binance'
            api_key_record = self.db.query(models.ApiKey).filter(
                models.ApiKey.exchange == exchange_name,
                models.ApiKey.user_id == self.bot.owner_id,
                models.ApiKey.is_enabled == True
            ).first()

        if not api_key_record:
            self.log("⚠️ No Valid API Key Found! Bot is running in SIMULATION mode.", "WARNING")
            return None

        try:
            # 🔐 SECRET KEY DECRYPTION
            decrypted_secret = decrypt_key(api_key_record.secret_key)
            
            exchange_class = getattr(ccxt, api_key_record.exchange.lower(), ccxt.binance)
            exchange_options = {
                'apiKey': api_key_record.api_key,
                'secret': decrypted_secret,
                'enableRateLimit': True,
                'options': {'defaultType': self.deployment_target}
            }

            # Optional Passphrase for KuCoin/OKX
            if hasattr(api_key_record, 'passphrase') and api_key_record.passphrase:
                try:
                    exchange_options['password'] = decrypt_key(api_key_record.passphrase)
                except Exception:
                     # Fallback if not encrypted or error
                    exchange_options['password'] = api_key_record.passphrase
            
            self.log(f"✅ Authenticated with {api_key_record.exchange}", "SYSTEM")
            return exchange_class(exchange_options)
            
        except Exception as e:
            self.log(f"❌ Exchange Auth Error: {e}", "ERROR")
            return None

    def log(self, message: str, type: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{type}] {self.symbol}: {message}", flush=True)

        log_payload = {
            "time": timestamp,
            "type": type,
            "message": message
        }
        
        # ✅ Publish to specific bot channel
        channel_name = f"bot_logs:{self.bot.id}"
        
        try:
            redis_log_client.publish(channel_name, json.dumps(log_payload))
        except Exception as e:
            print(f"⚠️ Redis Publish Error: {e}")

    def setup_futures_settings(self):
        if self.deployment_target == 'future' and self.exchange:
            try:
                self.exchange.load_markets()
                leverage = int(self.config.get('leverage', 1))
                margin_mode = self.config.get('marginMode', 'cross').lower()
                
                try:
                    self.exchange.set_margin_mode(margin_mode, self.symbol)
                except: pass

                try:
                    self.exchange.set_leverage(leverage, self.symbol)
                    self.log(f"⚙️ Futures Config: {margin_mode.upper()} | Leverage {leverage}x", "SYSTEM")
                except: pass
            except Exception as e:
                self.log(f"Futures Setup Error: {e}", "ERROR")

    def fetch_market_data(self, limit=100):
        try:
            if not self.exchange: return None # সিমুলেশন মোডের জন্য এখানে মক ডাটা ব্যবহার করতে পারেন
            
            candles = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.log(f"Data Fetch Error: {e}", "ERROR")
            return None

    # ---------------------------------------------------------
    # ✅ ধাপ ২: ব্যালেন্স চেক ফাংশন
    # ---------------------------------------------------------
    def check_balance(self, side, required_amount, price):
        """ট্রেড করার আগে ওয়ালেটে পর্যাপ্ত টাকা আছে কিনা চেক করা"""
        if not self.exchange: return True 

        try:
            balance = self.exchange.fetch_balance()
            
            base_currency = self.symbol.split('/')[0]
            quote_currency = self.symbol.split('/')[1]
            
            if side == "BUY":
                available = float(balance[quote_currency]['free'])
                
                # ✅ FIX: Always calculate cost as quantity * price
                cost = required_amount * price
                
                if available < cost:
                    self.log(f"❌ Insufficient Funds! Required: {cost:.4f} {quote_currency}, Available: {available:.4f}", "WARNING")
                    return False
                return True

            elif side == "SELL":
                if self.deployment_target == 'future':
                    available = float(balance[quote_currency]['free'])
                    leverage = float(self.config.get('leverage', 1))
                    cost = (required_amount * price) / leverage
                    
                    if available < cost:
                        self.log(f"❌ Insufficient Futures Margin! Required: {cost:.4f} {quote_currency}, Available: {available:.4f}", "WARNING")
                        return False
                    return True
                else:
                    available = float(balance[base_currency]['free'])
                    if available < required_amount:
                        self.log(f"❌ Insufficient Asset! Required: {required_amount} {base_currency}, Available: {available}", "WARNING")
                        return False
                    return True

        except Exception as e:
            self.log(f"⚠️ Balance Check Failed: {e}", "ERROR")
            return False

    def check_strategy_signal(self, df):
        try:
            signal, reason, price = self.strategy_executor.check_signal(df)
            return signal, reason, price
        except Exception as e:
            self.log(f"Strategy Error: {e}", "ERROR")
            return "HOLD", "Error", df['close'].iloc[-1]

    async def monitor_risk(self, current_price: float):
        """
        Check Stop Loss, Take Profit, and Trailing Stop logic.
        """
        if self.position["amount"] == 0:
            return

        entry_price = self.position["entry_price"]
        
        # ১. Stop Loss Check
        if self.stop_loss_pct > 0:
            sl_price = entry_price * (1 - self.stop_loss_pct / 100)
            if current_price <= sl_price:
                self.log(f"🛑 Stop Loss Hit! Price: {current_price} <= SL: {sl_price}", "RISK")
                await self.execute_trade("SELL", current_price, "Stop Loss", amount_pct=100)
                return

        # ২. Trailing Stop Check
        if self.is_trailing_enabled:
            # Update Highest Price (High Water Mark)
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            # Calculate Dynamic SL
            trailing_sl_price = self.highest_price * (1 - self.trailing_callback / 100)
            
            if current_price <= trailing_sl_price:
                self.log(f"📉 Trailing Stop Hit! Price: {current_price} <= TSL: {trailing_sl_price:.2f}", "RISK")
                await self.execute_trade("SELL", current_price, "Trailing Stop", amount_pct=100)
                return

        # ৩. Take Profit Check (Partial Sell supported)
        for tp in self.take_profits:
            if not tp.get("executed", False):
                target_price = entry_price * (1 + tp["target"] / 100)
                
                if current_price >= target_price:
                    self.log(f"🎯 Take Profit Target {tp['target']}% Hit at {current_price}", "PROFIT")
                    
                    # Partial Sell Execute
                    success = await self.execute_trade("SELL", current_price, f"TP {tp['target']}%", amount_pct=tp["amount"])
                    
                    if success:
                        tp["executed"] = True # Mark as executed to avoid duplicate sells

    async def execute_trade(self, side, price, reason, amount_pct=100):
        if not self.exchange:
            self.log(f"🕵️ Simulated {side} ({amount_pct}%) at {price}", "TRADE")
             # Simulation Logic Update
            if side == "BUY":
                quantity = self.trade_value / price
                self.position = {"amount": quantity, "entry_price": price, "trade_id": "SIM_ID"}
                self.highest_price = price # Reset Trailing High
                # Reset TP flags
                for tp in self.take_profits: tp["executed"] = False
            elif side == "SELL":
                sell_ratio = amount_pct / 100.0
                self.position["amount"] = self.position["amount"] * (1 - sell_ratio)
            return True

        try:
            # ১. অ্যামাউন্ট ক্যালকুলেশন
            amount = 0.0
            if side == "BUY":
                if self.trade_unit == "ASSET":
                    amount = self.trade_value 
                else:
                    amount = self.trade_value / price
            elif side == "SELL":
                 # Partial Sell Logic
                 amount = self.position["amount"] * (amount_pct / 100.0)

            # এক্সচেঞ্জ প্রিসিশন অনুযায়ী ঠিক করা
            # এক্সচেঞ্জ প্রিসিশন অনুযায়ী ঠিক করা
            amount = float(self.exchange.amount_to_precision(self.symbol, amount))
            
            # লিমিট অর্ডারের জন্য প্রাইসও ঠিক করতে হবে
            if self.order_type != 'market':
                price = float(self.exchange.price_to_precision(self.symbol, price))

            # ---------------------------------------------------------
            # ✅ ধাপ ৩: ট্রেডের আগে ব্যালেন্স ভ্যালিডেশন
            # ---------------------------------------------------------
            has_funds = self.check_balance(side, amount, price)
            if not has_funds:
                return False

            # ২. অর্ডার প্লেসমেন্ট
            self.log(f"🚀 Executing {side} | Amt: {amount:.4f} | Reason: {reason}", "TRADE")
            
            order = None
            if self.order_type == 'market':
                # Async context এ থাকলে await ব্যবহার করতে হবে যদি ccxt.async_support ব্যবহার করেন
                # বর্তমানে আমরা sync ccxt ব্যবহার করছি
                order = self.exchange.create_market_order(self.symbol, side.lower(), amount)
            else:
                order = self.exchange.create_limit_order(self.symbol, side.lower(), amount, price)
            
            if order:
                # ✅ FIX: Handle None values safely for Price and Quantity
                # KuCoin often returns 'average': None for market orders immediately after placement
                
                avg_price = order.get('average')
                if avg_price is None:
                    executed_price = float(price) # এক্সচেঞ্জ প্রাইস না দিলে আমাদের পাঠানো প্রাইস ব্যবহার হবে
                else:
                    executed_price = float(avg_price)

                # Qty এর ক্ষেত্রেও সেফটি চেক
                ord_amount = order.get('amount')
                if ord_amount is None:
                    # যদি amount না থাকে, filled দেখবো, তাও না থাকলে আমাদের পাঠানো amount
                    executed_qty = float(order.get('filled') or amount)
                else:
                    executed_qty = float(ord_amount)

                self.log(f"✅ Order Placed: ID {order['id']} @ {executed_price}", "TRADE")
                
                # ✅ ৫. ডাটাবেস আপডেট লজিক
                if side == "BUY":
                    # নতুন ট্রেড তৈরি করা
                    new_trade = Trade(
                        bot_id=self.bot.id,
                        symbol=self.symbol,
                        side="BUY", # Long
                        entry_price=executed_price,
                        quantity=executed_qty,
                        status="OPEN"
                    )
                    self.db.add(new_trade)
                    self.db.commit()
                    self.db.refresh(new_trade)

                    # ইন-মেমোরি স্টেট আপডেট
                    self.position = {
                        "amount": executed_qty, 
                        "entry_price": executed_price,
                        "trade_id": new_trade.id
                    }
                    self.highest_price = executed_price
                    for tp in self.take_profits: tp["executed"] = False

                elif side == "SELL":
                    # পজিশন কমানো
                    self.position["amount"] -= executed_qty
                    
                    # ট্রেড আপডেট করা (যদি সম্পূর্ণ বিক্রি হয়)
                    if self.position["amount"] < 0.00001: 
                        self.position["amount"] = 0
                        
                        # ডাটাবেসে ট্রেড ক্লোজ করা
                        if self.position["trade_id"]:
                            trade_record = self.db.query(Trade).get(self.position["trade_id"])
                            if trade_record:
                                trade_record.exit_price = executed_price
                                trade_record.status = "CLOSED"
                                trade_record.closed_at = datetime.now()
                                
                                # PnL ক্যালকুলেশন
                                trade_record.pnl = (executed_price - trade_record.entry_price) * trade_record.quantity
                                trade_record.pnl_percent = ((executed_price - trade_record.entry_price) / trade_record.entry_price) * 100
                                
                                self.db.commit()
                                self.log(f"💰 PnL: {trade_record.pnl:.2f} ({trade_record.pnl_percent:.2f}%)", "PROFIT" if trade_record.pnl > 0 else "LOSS")
                                
                                # ইন-মেমোরি ট্রেড আইডি রিসেট
                                self.position["trade_id"] = None
                
                return True

        except Exception as e:
            self.log(f"❌ Trade Execution Error: {e}", "ERROR")
            self.db.rollback()
            return False

    async def run_loop(self):
        task_key = f"bot_task:{self.bot.id}"
        self.log(f"🚀 Bot {self.bot.name} Started on {self.symbol}", "SYSTEM")

        if self.deployment_target == 'future':
            self.setup_futures_settings()

        while True:
            if not self.redis.exists(task_key):
                self.log(f"🛑 Stopping Bot...", "SYSTEM")
                break

            try:
                df = self.fetch_market_data()
                if df is not None:
                    current_price = df.iloc[-1]['close']
                    
                    # ১. পজিশন থাকলে আগে রিস্ক চেক করো
                    if self.position["amount"] > 0:
                        await self.monitor_risk(current_price)

                    # ২. স্ট্র্যাটেজি সিগনাল চেক
                    # BUY CHECK
                    if self.position["amount"] <= 0:
                        signal, reason, _ = self.check_strategy_signal(df)
                        if signal == "BUY":
                            self.log(f"🔔 Buy Signal: {reason}", "TRADE")
                            await self.execute_trade("BUY", current_price, reason)
                    
                    # SELL CHECK (Strategy Exit)
                    elif self.position["amount"] > 0:
                        signal, reason, _ = self.check_strategy_signal(df)
                        if signal == "SELL":
                             self.log(f"🔔 Sell Signal: {reason}", "TRADE")
                             await self.execute_trade("SELL", current_price, reason, amount_pct=100)
                        
                await asyncio.sleep(5) 

            except Exception as e:
                self.log(f"Loop Error: {e}", "ERROR")
                await asyncio.sleep(5)
        
        self.log("Bot Stopped.", "SYSTEM")
