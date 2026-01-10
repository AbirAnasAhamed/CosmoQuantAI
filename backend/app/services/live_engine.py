import ccxt
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import asyncio
import json
import redis
from app import models
from app.utils import get_redis_client
from app.core.config import settings
# ✅ নতুন ইমপোর্ট: আমাদের তৈরি করা Factory
from app.strategies.live_strategies import LiveStrategyFactory

redis_log_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class LiveBotEngine:
    def __init__(self, bot: models.Bot, db_session):
        self.bot = bot
        self.db = db_session
        self.symbol = bot.market
        self.timeframe = bot.timeframe
        self.redis = get_redis_client()
        
        # কনফিগারেশন লোড
        self.config = bot.config or {}
        
        # ✅ DYNAMIC STRATEGY LOADING (বটের নাম অনুযায়ী স্ট্র্যাটেজি সেট হবে)
        # ফ্রন্টএন্ড থেকে আসা bot.strategy (যেমন: "MACD Trend") অনুযায়ী ক্লাস লোড হবে
        strategy_name = bot.strategy or "RSI Strategy"
        self.strategy_executor = LiveStrategyFactory.get_strategy(strategy_name, self.config)
        
        self.deployment_target = self.config.get('deploymentTarget', 'Spot').lower()
        if 'future' in self.deployment_target: self.deployment_target = 'future'
        self.trade_value = bot.trade_value or 100.0
        self.trade_unit = bot.trade_unit or "QUOTE"
        self.order_type = self.config.get('orderType', 'Market').lower()
        
        # Risk Params
        risk_params = self.config.get('riskParams', {})
        self.stop_loss_pct = float(risk_params.get('stopLoss', 0))
        self.take_profits = []
        raw_tp = risk_params.get('takeProfit')
        if isinstance(raw_tp, list):
            self.take_profits = sorted(raw_tp, key=lambda x: x['target'])
        elif raw_tp and float(raw_tp) > 0:
            self.take_profits = [{"target": float(raw_tp), "amount": 100}]

        # Position State
        self.position = { "amount": 0.0, "entry_price": 0.0, "tp_hits": [] }

        # Exchange Setup
        exchange_options = { 'enableRateLimit': True, 'options': {'defaultType': self.deployment_target} }
        self.exchange = ccxt.binance(exchange_options)

    def log(self, message: str, type: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{type}] {self.symbol}: {message}", flush=True)

        log_payload = {
            "channel": f"logs_{self.bot.id}",
            "data": {
                "time": timestamp,
                "type": type,
                "message": message
            }
        }
        try:
            redis_log_client.publish("bot_logs", json.dumps(log_payload))
        except Exception as e:
            print(f"⚠️ Redis Publish Error: {e}")

    def setup_futures_settings(self):
        if self.deployment_target == 'future':
            try:
                self.exchange.load_markets()
                # আপনার লিভারেজ লজিক এখানে থাকবে
            except Exception: pass

    def fetch_market_data(self, limit=100):
        try:
            candles = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.log(f"Data Fetch Error: {e}", "ERROR")
            return None

    # ✅ আপগ্রেডেড ফাংশন: এখন এটি হার্ডকোডেড নয়, ডাইনামিক
    def check_strategy_signal(self, df):
        try:
            # Factory থেকে লোড করা স্ট্র্যাটেজি ক্লাস ব্যবহার করা হচ্ছে
            signal, reason, price = self.strategy_executor.check_signal(df)
            return signal, reason, price
        except Exception as e:
            self.log(f"Strategy Error: {e}", "ERROR")
            return "HOLD", "Error in calculation", df['close'].iloc[-1]

    async def monitor_risk_management(self, current_price):
        # আপনার রিস্ক ম্যানেজমেন্ট লজিক অপরিবর্তিত রাখুন
        pass

    async def execute_trade(self, signal, price, reason, size_pct=100):
        # আপনার ট্রেড লজিক অপরিবর্তিত রাখুন
        self.log(f"EXECUTING {signal} | {reason} | Price: {price}", "TRADE")
        # TODO: Real API call here
        return True

    async def run_loop(self):
        task_key = f"bot_task:{self.bot.id}"
        
        self.log(f"🚀 Bot {self.bot.name} Started on {self.symbol}", "SYSTEM")
        self.log(f"🧠 Strategy: {self.bot.strategy}", "SYSTEM") # লগ করা হচ্ছে কোন স্ট্র্যাটেজি চলছে

        if self.deployment_target == 'future':
            self.setup_futures_settings()

        while True:
            if not self.redis.exists(task_key):
                self.log(f"🛑 Stopping Bot {self.bot.name}...", "SYSTEM")
                break

            try:
                self.log(f"Waiting for next candle analysis...", "WAIT")

                df = self.fetch_market_data()
                if df is not None:
                    current_price = df.iloc[-1]['close']
                    
                    # শুধু পজিশন না থাকলে বাই চেক করবে
                    if self.position["amount"] <= 0:
                        signal, reason, _ = self.check_strategy_signal(df)
                        
                        if signal == "BUY":
                            self.log(f"🔔 Buy Signal Detected: {reason}", "TRADE")
                            await self.execute_trade("BUY", current_price, reason)
                        else:
                            # অপশনাল: হোল্ড সিগনাল লগ করা (ডিবাগিংয়ের জন্য)
                            # self.log(f"Hold: {reason}", "INFO")
                            pass
                    
                    # পজিশন থাকলে রিস্ক ম্যানেজমেন্ট দেখবে
                    if self.position["amount"] > 0:
                        await self.monitor_risk_management(current_price)

                await asyncio.sleep(5) 

            except Exception as e:
                self.log(f"Loop Error: {e}", "ERROR")
                await asyncio.sleep(5)
        
        self.log("Bot Stopped Successfully.", "SYSTEM")
