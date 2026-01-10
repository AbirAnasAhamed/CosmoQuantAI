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
from app.strategies.live_strategies import LiveStrategyFactory

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
        self.take_profits = []
        raw_tp = risk_params.get('takeProfit')
        if isinstance(raw_tp, list):
            self.take_profits = sorted(raw_tp, key=lambda x: x['target'])
        elif raw_tp and float(raw_tp) > 0:
            self.take_profits = [{"target": float(raw_tp), "amount": 100}]

        # Position State (In-Memory)
        self.position = { "amount": 0.0, "entry_price": 0.0 }

        # ✅ EXCHANGE INITIALIZATION WITH SECURITY
        self.exchange = self._initialize_exchange()

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
            
            self.log(f"✅ Authenticated with {api_key_record.exchange}", "SYSTEM")
            return exchange_class(exchange_options)
            
        except Exception as e:
            self.log(f"❌ Exchange Auth Error: {e}", "ERROR")
            return None

    def log(self, message: str, type: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{type}] {self.symbol}: {message}", flush=True)

        log_payload = {
            "channel": f"logs_{self.bot.id}",
            "data": { "time": timestamp, "type": type, "message": message }
        }
        try:
            redis_log_client.publish("bot_logs", json.dumps(log_payload))
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
        if not self.exchange: return True # সিমুলেশন মোডে সবসময় True

        try:
            # ব্যালেন্স ফেচ করা (Sync বা Async ব্যবহারের উপর ভিত্তি করে)
            # যেহেতু এটি লুপের মধ্যে চলবে, আমরা এখানে ব্লকিং কল ব্যবহার করছি (ccxt sync) 
            # অথবা যদি async ccxt ব্যবহার করেন তবে await দিতে হবে। 
            # এখানে আমরা ধরে নিচ্ছি লাইব্রেরি sync মোডে চলছে অথবা wrapper ব্যবহার হচ্ছে।
            
            # NOTE: LiveBotEngine যদি Async হয়, তবে এটি await করতে হবে
            # যেহেতু ccxt import করা হয়েছে (sync version), তাই সরাসরি কল করা যাবে।
            balance = self.exchange.fetch_balance()
            
            # কারেন্সি ডিটেকশন (যেমন: BTC/USDT)
            base_currency = self.symbol.split('/')[0] # BTC
            quote_currency = self.symbol.split('/')[1] # USDT
            
            # BUY সিগনালের জন্য আমাদের QUOTE কারেন্সি (USDT) চেক করতে হবে
            if side == "BUY":
                available = float(balance[quote_currency]['free'])
                cost = required_amount * price if self.trade_unit == "ASSET" else required_amount
                
                if available < cost:
                    self.log(f"❌ Insufficient Funds! Required: {cost} {quote_currency}, Available: {available}", "WARNING")
                    return False
                return True

            # SELL সিগনালের জন্য (Spot) আমাদের BASE কারেন্সি (BTC) চেক করতে হবে
            elif side == "SELL":
                # Futures হলে মার্জিন (USDT) চেক করতে হবে, Spot হলে Asset
                if self.deployment_target == 'future':
                    available = float(balance[quote_currency]['free'])
                    # ফিউচারসে সেলিং বা শর্ট করার জন্য মার্জিন লাগে
                    return True # আপাতত ফিউচারস ব্যালেন্স চেক সরল রাখা হলো
                else:
                    available = float(balance[base_currency]['free'])
                    # Spot Sell মানে আমাদের কাছে Asset থাকতে হবে
                    # এখানে required_amount হলো কতটা BTC বিক্রি করব
                    if available < required_amount:
                        self.log(f"❌ Insufficient Asset! Required: {required_amount} {base_currency}, Available: {available}", "WARNING")
                        return False
                    return True

        except Exception as e:
            self.log(f"⚠️ Balance Check Failed: {e}", "ERROR")
            return False # সেফটির জন্য False রিটার্ন করা ভালো

    def check_strategy_signal(self, df):
        try:
            signal, reason, price = self.strategy_executor.check_signal(df)
            return signal, reason, price
        except Exception as e:
            self.log(f"Strategy Error: {e}", "ERROR")
            return "HOLD", "Error", df['close'].iloc[-1]

    async def execute_trade(self, side, price, reason):
        if not self.exchange:
            self.log(f"🕵️ Simulated {side} at {price}", "TRADE")
            return True

        try:
            # ১. অ্যামাউন্ট ক্যালকুলেশন
            amount = 0.0
            if self.trade_unit == "ASSET":
                amount = self.trade_value 
            else:
                amount = self.trade_value / price

            # এক্সচেঞ্জ প্রিসিশন অনুযায়ী ঠিক করা
            # amount = self.exchange.amount_to_precision(self.symbol, amount) # Uncomment if strict checking needed

            # ---------------------------------------------------------
            # ✅ ধাপ ৩: ট্রেডের আগে ব্যালেন্স ভ্যালিডেশন
            # ---------------------------------------------------------
            has_funds = self.check_balance(side, amount, price)
            if not has_funds:
                return False

            # ২. অর্ডার প্লেসমেন্ট
            self.log(f"🚀 Executing {side} | Amt: {amount:.4f} | Price: {price}", "TRADE")
            
            order = None
            if self.order_type == 'market':
                # Async context এ থাকলে await ব্যবহার করতে হবে যদি ccxt.async_support ব্যবহার করেন
                # বর্তমানে আমরা sync ccxt ব্যবহার করছি
                order = self.exchange.create_market_order(self.symbol, side.lower(), amount)
            else:
                order = self.exchange.create_limit_order(self.symbol, side.lower(), amount, price)
            
            if order:
                self.log(f"✅ Order Placed: ID {order['id']}", "TRADE")
                
                # পজিশন আপডেট
                if side == "BUY":
                    self.position["amount"] += float(order['amount'])
                    self.position["entry_price"] = float(order.get('average', price))
                elif side == "SELL":
                    self.position["amount"] = 0.0
                    self.position["entry_price"] = 0.0
                
                return True

        except Exception as e:
            self.log(f"❌ Trade Execution Error: {e}", "ERROR")
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
                    
                    # BUY CHECK
                    if self.position["amount"] <= 0:
                        signal, reason, _ = self.check_strategy_signal(df)
                        if signal == "BUY":
                            self.log(f"🔔 Buy Signal: {reason}", "TRADE")
                            await self.execute_trade("BUY", current_price, reason)
                    
                    # SELL CHECK
                    elif self.position["amount"] > 0:
                        signal, reason, _ = self.check_strategy_signal(df)
                        if signal == "SELL":
                             self.log(f"🔔 Sell Signal: {reason}", "TRADE")
                             await self.execute_trade("SELL", current_price, reason)
                        
                        # এখানে আপনি Stop Loss / Take Profit লজিকও যোগ করতে পারেন
                        # await self.monitor_risk(current_price)

                await asyncio.sleep(5) 

            except Exception as e:
                self.log(f"Loop Error: {e}", "ERROR")
                await asyncio.sleep(5)
        
        self.log("Bot Stopped.", "SYSTEM")
