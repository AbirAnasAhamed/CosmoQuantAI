import ccxt.async_support as ccxt
import ccxt as ccxt_sync # সিঙ্ক্রোনাস অপারেশনের জন্য (list markets)
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app import models
from app.constants import VALID_TIMEFRAMES

class MarketService:
    def __init__(self):
        # ডিফল্ট বাইনান্স (Async)
        self.exchange = ccxt.binance()

    # ১. টাইমফ্রেম কনভার্সন হেল্পার
    def timeframe_to_ms(self, timeframe):
        seconds = 0
        if 'm' in timeframe: seconds = int(timeframe[:-1]) * 60
        elif 'h' in timeframe: seconds = int(timeframe[:-1]) * 3600
        elif 'd' in timeframe: seconds = int(timeframe[:-1]) * 86400
        elif 'w' in timeframe: seconds = int(timeframe[:-1]) * 604800
        elif 'M' in timeframe: seconds = int(timeframe[:-1]) * 2592000
        return seconds * 1000

    # ২. সিঙ্ক ফাংশন (পাজিনেশন লুপ সহ)
    async def fetch_and_store_candles(self, db: Session, symbol: str, timeframe: str, start_date: str = None, end_date: str = None, limit: int = 1000):
        if timeframe not in VALID_TIMEFRAMES:
            return {"status": "error", "message": f"Timeframe '{timeframe}' is not supported."}

        since_ts = None
        end_ts = int(datetime.utcnow().timestamp() * 1000)

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            since_ts = int(start_dt.timestamp() * 1000)
        
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            end_ts = int(end_dt.timestamp() * 1000)

        # যদি স্টার্ট ডেট না থাকে, লেটেস্ট ১০০০ ডেটা আনবে (লুপ ছাড়া)
        if not since_ts:
             try:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                self._save_candles(db, ohlcv, symbol, timeframe)
                return {"status": "success", "message": "Latest data synced", "count": len(ohlcv)}
             except Exception as e:
                 return {"status": "error", "message": str(e)}

        # স্টার্ট ডেট থাকলে লুপ চালাবো
        try:
            total_saved = 0
            tf_ms = self.timeframe_to_ms(timeframe)
            current_since = since_ts

            while current_since < end_ts:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=1000, since=current_since)
                if not ohlcv:
                    break
                
                # ফিল্টার এবং সেভ
                filtered_ohlcv = [c for c in ohlcv if c[0] <= end_ts]
                saved_count = self._save_candles(db, filtered_ohlcv, symbol, timeframe)
                total_saved += saved_count
                
                if not filtered_ohlcv:
                    break

                last_time = filtered_ohlcv[-1][0]
                
                # পরের ব্যাচের সময় ঠিক করা
                if last_time == current_since:
                    current_since += tf_ms * 1000 # ফোর্স আপডেট যদি একই টাইম আসে
                else:
                    current_since = last_time + tf_ms

            return {"status": "success", "new_candles_stored": total_saved, "range": f"{start_date} to {end_date or 'Now'}"}

        except Exception as e:
            print(f"Sync Error: {e}")
            return {"status": "error", "message": str(e)}

    # ডাটাবেসে সেভ করার ইন্টারনাল মেথড (রিপিটেশন কমানোর জন্য)
    def _save_candles(self, db: Session, ohlcv: list, symbol: str, timeframe: str):
        count = 0
        for candle in ohlcv:
            timestamp_ms = candle[0]
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            
            existing = db.query(models.MarketData).filter(
                models.MarketData.exchange == 'binance',
                models.MarketData.symbol == symbol,
                models.MarketData.timeframe == timeframe,
                models.MarketData.timestamp == dt_object
            ).first()

            if not existing:
                db_candle = models.MarketData(
                    exchange='binance',
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=dt_object,
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5]
                )
                db.add(db_candle)
                count += 1
        db.commit()
        return count

    # ৩. নির্দিষ্ট এক্সচেঞ্জের মার্কেট পেয়ার খোঁজা (এই মেথডটিই মিসিং ছিল)
    async def get_exchange_markets(self, exchange_id: str):
        try:
            # ডাইনামিক এক্সচেঞ্জ লোডিং (Async ক্লায়েন্ট দিয়ে)
            if hasattr(ccxt, exchange_id):
                exchange_class = getattr(ccxt, exchange_id)
                # নতুন ইনস্ট্যান্স তৈরি করছি শুধু পেয়ার লোড করার জন্য
                temp_exchange = exchange_class()
                markets = await temp_exchange.load_markets()
                await temp_exchange.close()
                
                # সিম্বল লিস্ট
                return list(markets.keys())
            return []
        except Exception as e:
            print(f"Error fetching markets for {exchange_id}: {e}")
            return []

    # ৪. সাপোর্টেড এক্সচেঞ্জ লিস্ট
    def get_supported_exchanges(self):
        # জনপ্রিয় এক্সচেঞ্জ লিস্ট
        return ['binance', 'kraken', 'kucoin', 'bybit', 'okx', 'gateio', 'bitget', 'coinbase']

    # ৫. ব্যাকটেস্টিং এর জন্য ডাটা রিড করা
    def get_candles_from_db(self, db: Session, symbol: str, timeframe: str, start_date: str = None, end_date: str = None):
        query = db.query(models.MarketData).filter(
            models.MarketData.symbol == symbol,
            models.MarketData.timeframe == timeframe
        )
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(models.MarketData.timestamp >= start_dt)
            except: pass
        if end_date:
             try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(models.MarketData.timestamp <= end_dt)
             except: pass
             
        return query.order_by(models.MarketData.timestamp.asc()).all()