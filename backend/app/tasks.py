from .celery_app import celery_app
from app.db.session import SessionLocal
from .services.backtest_engine import BacktestEngine
import sys
import math
import time
from . import utils 
from app.services.report_generator import generate_report
from app.strategies import STRATEGY_MAP
from app.services.live_engine import LiveBotEngine
import asyncio
import json
from app.models.sentiment import SentimentHistory
from app.models.sentiment import SentimentHistory
from app.models.whale_alert import WhaleAlert
from app.services.notification import NotificationService
from app.services.news_scraper import fetch_crypto_news
# ❌ REMOVED: Top-level import removed to fix Circular Import Error
# from app.services.news_service import news_service 

@celery_app.task
def task_fetch_latest_news():
    """
    Background task to fetch crypto news automatically every hour.
    """
    db = SessionLocal()
    try:
        fetch_crypto_news(db)
    finally:
        db.close()

def publish_task_status(task_type, task_id, status, progress, data=None):
    try:
        r = utils.get_redis_client()
        message = {
            "task_type": task_type,
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "data": data
        }
        r.publish("task_updates", json.dumps(message, default=str))
    except Exception as e:
        print(f"⚠️ Redis Publish Error: {e}")

# ✅ Innovative Progress Bar Helper
def print_custom_progress_bar(percent, prefix='', suffix='', length=40):
    percent = max(0, min(100, percent))
    filled_length = int(length * percent // 100)
    
    # Custom UTF-8 Blocks for smoother look
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    # Color Codes
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    color = BLUE if percent < 100 else GREEN
    sys.stdout.write(f"\r{color}{BOLD}{prefix} |{bar}| {percent}% {suffix}{RESET}")
    sys.stdout.flush()

def clean_metric(value):
    try:
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return 0
        return value
    except:
        return 0

def print_pretty_result(result):
    if result.get("status") != "success":
        print(f"❌ Backtest Failed: {result.get('message')}")
        return

    print("\n" + "="*50)
    print(f"🚀 BACKTEST RESULTS: {result['symbol']} ({result['strategy']})")
    print("="*50)
    print(f"💰 Initial Cash  : ${result['initial_cash']:,.2f}")
    print(f"🏁 Final Value   : ${result['final_value']:,.2f}")
    
    profit = result['profit_percent']
    color = "\033[92m" if profit >= 0 else "\033[91m" 
    reset = "\033[0m"
    
    print(f"📈 Profit/Loss   : {color}{profit}%{reset}")
    print(f"🔄 Total Trades  : {result['total_trades']}")
    
    metrics = result.get('advanced_metrics', {})
    print("-" * 30)
    print(f"📊 Win Rate      : {metrics.get('win_rate', 0)}%")
    print(f"📉 Max Drawdown  : {metrics.get('max_drawdown', 0)}%")
    print(f"⚖️ Sharpe Ratio  : {metrics.get('sharpe', 0)}")
    print("="*50 + "\n")

@celery_app.task(bind=True)
def run_backtest_task(self, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None, custom_data_file: str = None, commission: float = 0.001, slippage: float = 0.0, leverage: float = 1.0, secondary_timeframe: str = None, stop_loss: float = 0.0, take_profit: float = 0.0, trailing_stop: float = 0.0, indicator_id: int = None):
    db = SessionLocal()
    engine = BacktestEngine()
    
    last_percent = -1
    def on_progress(percent):
        nonlocal last_percent
        if percent != last_percent:
            last_percent = percent
            self.update_state(
                state='PROGRESS',
                meta={'percent': percent, 'status': 'Running Strategy...'}
            )
            publish_task_status('BACKTEST', self.request.id, 'processing', percent)

            if percent % 10 == 0:
                print(f"⏳ Backtest Progress: {percent}%", flush=True)

    try:
        publish_task_status('BACKTEST', self.request.id, 'processing', 0)
        result = engine.run(
            db=db,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            initial_cash=initial_cash,
            params=params,
            start_date=start_date,
            end_date=end_date,
            custom_data_file=custom_data_file,
            progress_callback=on_progress,
            commission=commission,
            slippage=slippage,
            leverage=leverage,
            secondary_timeframe=secondary_timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            indicator_id=indicator_id
        )
        if result.get("status") == "success":
            generate_report(self.request.id, result.get("daily_returns", "{}"), symbol, timeframe)

        print_pretty_result(result)
        publish_task_status('BACKTEST', self.request.id, 'completed', 100, result)
        return result
        
    except Exception as e:
        import traceback
        print(f"❌ Backtest Error Traceback:\n{traceback.format_exc()}", flush=True)
        publish_task_status('BACKTEST', self.request.id, 'failed', 0, {"error": str(e)})
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()

@celery_app.task(bind=True)
def run_optimization_task(self, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None, method="grid", population_size=50, generations=10, commission: float = 0.001, slippage: float = 0.0, leverage: float = 1.0):
    db = SessionLocal()
    engine = BacktestEngine()
    
    def on_progress(percent, meta=None):
        if meta is None: meta = {}
        current = meta.get('current', 0)
        total = meta.get('total', 0)
        best_profit = meta.get('best_profit', 0)

        print_custom_progress_bar(
            percent, 
            prefix=f"🧬 OPTIMIZING", 
            suffix=f"[Iter: {current}/{total} | Best: {best_profit}%]"
        )

        if percent == 100:
            print("\n✅ Optimization Completed!") 

        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percent': percent,
                'status': 'Processing',
                'best_profit': meta.get('best_profit', 0)
            }
        )
        publish_task_status('OPTIMIZE', self.request.id, 'processing', percent, data=meta)

    def check_abort():
        try:
            r = utils.get_redis_client()
            if r.exists(f"abort_task:{self.request.id}"):
                return True
        except Exception:
            pass
        return False

    try:
        print(f"🔄 Starting Optimization for {strategy_name} on {symbol}...")
        results = engine.optimize(
            db=db,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            initial_cash=initial_cash,
            params=params,
            start_date=start_date,
            end_date=end_date,
            method=method,
            population_size=population_size,
            generations=generations,
            progress_callback=on_progress,
            abort_callback=check_abort,
            commission=commission,
            slippage=slippage,
            leverage=leverage
        )
        
        try:
            r = utils.get_redis_client()
            r.delete(f"abort_task:{self.request.id}")
        except: pass

        publish_task_status('OPTIMIZE', self.request.id, 'completed', 100, results)
        return results
        
    except Exception as e:
        print(f"\n❌ Optimization Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        publish_task_status('OPTIMIZE', self.request.id, 'failed', 0, {"error": str(e)})
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()

@celery_app.task(bind=True)
def run_walk_forward_task(self, symbol, timeframe, strategy_name, initial_cash, params, start_date, end_date, 
                          train_window_days, test_window_days, method, population_size, generations, 
                          commission, slippage, leverage, opt_target='profit', min_trades=2):
    
    def progress_callback(percent, meta=None):
        self.update_state(
            state='PROGRESS',
            meta={
                'percent': percent,
                'status': meta.get('status', 'Processing...') if meta else 'Processing...',
                'current_equity': meta.get('current_equity', 0) if meta else 0
            }
        )
        publish_task_status('WFA', self.request.id, 'processing', percent, data=meta)

    db = SessionLocal()
    engine = BacktestEngine()
    
    try:
        progress_callback(0, meta={"status": "Initializing WFA..."})

        result = engine.walk_forward(
            db=db,
            symbol=symbol, timeframe=timeframe, strategy_name=strategy_name,
            initial_cash=initial_cash, params=params,
            start_date=start_date, end_date=end_date,
            train_window_days=train_window_days, test_window_days=test_window_days,
            method=method, population_size=population_size, generations=generations,
            commission=commission, slippage=slippage, leverage=leverage,
            opt_target=opt_target, min_trades=min_trades,
            progress_callback=progress_callback
        )
        
        if result.get("status") == "success":
             publish_task_status('WFA', self.request.id, 'completed', 100, result)
        else:
             publish_task_status('WFA', self.request.id, 'failed', 0, result)
             
        return result

    except Exception as e:
        print(f"❌ WFA Task Error: {e}", flush=True)
        publish_task_status('WFA', self.request.id, 'failed', 0, {"error": str(e)})
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()

@celery_app.task(bind=True)
def run_batch_backtest_task(self, symbol: str, timeframe: str, initial_cash: float, strategies: list = None, start_date: str = None, end_date: str = None, commission: float = 0.001, slippage: float = 0.0, custom_data_file: str = None):
    db = SessionLocal()
    engine = BacktestEngine()
    
    results = []
    errors = []
    
    if strategies and len(strategies) > 0:
        available_strategies = [s for s in strategies if s in STRATEGY_MAP]
        if not available_strategies:
            available_strategies = list(STRATEGY_MAP.keys())
    else:
        available_strategies = list(STRATEGY_MAP.keys())

    total = len(available_strategies)
    print(f"🚀 Starting Batch Task for {total} strategies on {symbol}")

    r = utils.get_redis_client()

    for i, strategy_name in enumerate(available_strategies):
        if r.exists(f"abort_task:{self.request.id}"):
            print(f"🛑 Batch Task Aborted by User at {strategy_name}")
            publish_task_status('BATCH', self.request.id, 'REVOKED', 0, {"message": "Batch testing stopped."})
            return {"status": "Revoked", "message": "Stopped by user"}

        current_progress = int((i / total) * 100)
        print(f"🔄 [{i+1}/{total}] Testing {strategy_name}... ({current_progress}%)", flush=True)

        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': total,
                'percent': current_progress,
                'status': f"Testing {strategy_name}..."
            }
        )
        publish_task_status('BATCH', self.request.id, 'processing', current_progress)
        
        time.sleep(0.1) 

        try:
            result = engine.run(
                db=db,
                symbol=symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                initial_cash=initial_cash,
                params={}, 
                start_date=start_date,
                end_date=end_date,
                custom_data_file=custom_data_file,
                commission=commission,
                slippage=slippage
            )
            
            if result.get("status") != "success":
                error_msg = result.get("message") or result.get("error") or "Unknown error occurred"
                errors.append({"strategy": strategy_name, "error": str(error_msg)})
                print(f"⚠️ Batch Skip {strategy_name}: {error_msg}")
            else:
                metrics = result.get('advanced_metrics', {})
                summary = {
                    "strategy": strategy_name,
                    "profit_percent": clean_metric(result.get("profit_percent")),
                    "total_trades": result.get("total_trades", 0),
                    "final_value": clean_metric(result.get("final_value")),
                    "win_rate": clean_metric(metrics.get('win_rate')),
                    "max_drawdown": clean_metric(metrics.get('max_drawdown')),
                    "sharpe_ratio": clean_metric(metrics.get('sharpe'))
                }
                results.append(summary)
                
        except Exception as e:
            print(f"❌ Batch Error for {strategy_name}: {e}")
            errors.append({"strategy": strategy_name, "error": str(e)})

    db.close()
    
    results.sort(key=lambda x: x['profit_percent'], reverse=True)
    
    print(f"✅ Batch Task Completed! Scanned {len(results)} strategies.")

    final_result = {
        "status": "completed",
        "symbol": symbol,
        "total_tested": total,
        "results": results,
        "errors": errors
    }
    publish_task_status('BATCH', self.request.id, 'completed', 100, final_result)
    return final_result

@celery_app.task(bind=True)
def run_live_bot_task(self, bot_id: int):
    db = SessionLocal()
    try:
        from app.models import Bot
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        
        if not bot:
            print(f"❌ Bot {bot_id} not found in DB")
            return "Bot not found"

        r = utils.get_redis_client()
        task_key = f"bot_task:{bot_id}"
        r.set(task_key, "running")

        engine = LiveBotEngine(bot, db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(engine.run_loop())
        loop.close()

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        db.close()
        r = utils.get_redis_client()
        r.delete(f"bot_task:{bot_id}")

import ccxt
import os
import csv
from datetime import datetime, timedelta
from .celery_app import celery_app
from celery import current_task
from tqdm import tqdm
from .utils import get_redis_client

DATA_FEED_DIR = "app/data_feeds"
os.makedirs(DATA_FEED_DIR, exist_ok=True)

def get_last_timestamp(file_path):
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return None
        with open(file_path, 'rb') as f:
            try:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                f.seek(0)
            
            last_line = f.readline().decode().strip()
            if not last_line: return None
            data = last_line.split(',')
            
            if len(data) > 0:
                 try:
                    dt_obj = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
                    return int(dt_obj.timestamp() * 1000)
                 except ValueError:
                    pass
    except Exception:
        return None
    return None

def safe_parse_date(exchange, date_str):
    if not date_str: return None
    ts = exchange.parse8601(date_str)
    if ts is not None:
        return ts
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)
    except:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp() * 1000)
        except:
            return None

@celery_app.task(bind=True)
def download_candles_task(self, exchange_id, symbol, timeframe, start_date, end_date=None):
    try:
        if exchange_id not in ccxt.exchanges:
            return {"status": "failed", "error": f"Exchange {exchange_id} not found"}
            
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'timeout': 10000,
        })
        redis_client = get_redis_client()
        
        safe_symbol = symbol.replace('/', '-')
        filename = f"{exchange_id}_{safe_symbol}_{timeframe}.csv"
        save_path = f"{DATA_FEED_DIR}/{filename}"
        
        since = safe_parse_date(exchange, start_date)
        if since is None:
            return {"status": "failed", "error": f"Invalid start_date format: {start_date}"}
        
        if end_date:
            end_ts = safe_parse_date(exchange, end_date)
            if end_ts is None:
                return {"status": "failed", "error": f"Invalid end_date format: {end_date}"}
        else:
            end_ts = exchange.milliseconds()

        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1].strip().split(',')
                    try:
                        last_ts_obj = datetime.strptime(last_line[0], "%Y-%m-%d %H:%M:%S")
                        last_ts = int(last_ts_obj.timestamp() * 1000)
                        if last_ts:
                            since = last_ts + 1
                            print(f"🔄 Resuming {symbol} download from {last_line[0]}")
                    except: pass

        total_duration = end_ts - since
        if total_duration <= 0:
             return {"status": "completed", "message": "Data is already up to date."}

        start_ts = since
        mode = 'a' if os.path.exists(save_path) else 'w'
        
        print(f"🚀 Starting download: {symbol} ({timeframe}) | Target: {end_date or 'NOW'}")

        with open(save_path, mode, newline='') as f:
            writer = csv.writer(f)
            if mode == 'w' or os.path.getsize(save_path) == 0:
                writer.writerow(['datetime', 'open', 'high', 'low', 'close', 'volume'])
            
            with tqdm(total=total_duration, unit="ms", desc=f"📥 {symbol}", ncols=80) as pbar:
                while True:
                    if self.request.id and redis_client.exists(f"abort_task:{self.request.id}"):
                        print(f"🛑 Stop signal received via Redis for task {self.request.id}")
                        return {"status": "Revoked", "message": "Stopped by user"}

                    try:
                        if since >= end_ts: break
                        exchange.timeout = 10000 
                        candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
                        
                        if self.request.id and redis_client.exists(f"abort_task:{self.request.id}"):
                             return {"status": "Revoked", "message": "Stopped by user"}
                        
                        if not candles: break
                        
                        rows = []
                        for c in candles:
                            if c[0] > end_ts: continue
                            dt_str = datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M:%S')
                            rows.append([dt_str, c[1], c[2], c[3], c[4], c[5]])
                        
                        if rows:
                            writer.writerows(rows)
                            f.flush()
                        
                        current_ts = candles[-1][0]
                        step = current_ts - since
                        pbar.update(step)
                        since = current_ts + 1
                        
                        progress_pct = min(100, int(((current_ts - start_ts) / total_duration) * 100))
                        self.update_state(state='PROGRESS', meta={'percent': progress_pct, 'status': 'Downloading...'})
                        publish_task_status('DOWNLOAD', self.request.id, 'processing', progress_pct)
                        
                        if current_ts >= end_ts: break
                        
                    except Exception as e:
                        print(f"Fetch Error: {e}")
                        time.sleep(2)
                        continue

        publish_task_status('DOWNLOAD', self.request.id, 'completed', 100, {"filename": filename})
        return {"status": "completed", "filename": filename}

    except Exception as e:
        return {"status": "failed", "error": str(e)}

@celery_app.task(bind=True)
def download_trades_task(self, exchange_id, symbol, start_date, end_date=None):
    try:
        if exchange_id not in ccxt.exchanges:
             return {"status": "failed", "error": f"Exchange {exchange_id} not found"}
        
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'timeout': 10000,
        })
        redis_client = get_redis_client() 
        
        safe_symbol = symbol.replace('/', '-')
        filename = f"trades_{exchange_id}_{safe_symbol}.csv"
        save_path = f"{DATA_FEED_DIR}/{filename}"
        
        since = safe_parse_date(exchange, start_date)
        if since is None:
            return {"status": "failed", "error": f"Invalid start_date format: {start_date}"}

        if end_date:
            end_ts = safe_parse_date(exchange, end_date)
        else:
            end_ts = exchange.milliseconds()

        if os.path.exists(save_path):
            last_ts = get_last_timestamp(save_path)
            if last_ts: 
                since = last_ts + 1
                print(f"🔄 Resuming Trades {symbol} from timestamp {last_ts}")
        
        total_duration = end_ts - since
        if total_duration <= 0:
             return {"status": "completed", "message": "Trades already up to date."}

        start_ts = since
        mode = 'a' if os.path.exists(save_path) else 'w'
        
        print(f"🚀 Starting Trade DL: {symbol} | Target: {end_date or 'NOW'}")

        with open(save_path, mode, newline='') as f:
            writer = csv.writer(f)
            if mode == 'w' or os.path.getsize(save_path) == 0:
                writer.writerow(['id', 'timestamp', 'datetime', 'symbol', 'side', 'price', 'amount', 'cost'])
            
            with tqdm(total=total_duration, unit="ms", desc=f"Tick {symbol}", ncols=80) as pbar:
                while True:
                    if self.request.id and redis_client.exists(f"abort_task:{self.request.id}"):
                          return {"status": "Revoked", "message": "Stopped by user"}

                    try:
                        if since >= end_ts: break
                        exchange.timeout = 10000 
                        trades = exchange.fetch_trades(symbol, since, limit=1000)
                        
                        if self.request.id and redis_client.exists(f"abort_task:{self.request.id}"):
                             return {"status": "Revoked", "message": "Stopped by user"}
                        
                        if not trades: break
                        
                        rows = []
                        for t in trades:
                            if t['timestamp'] > end_ts: continue
                            rows.append([t['id'], t['timestamp'], t['datetime'], t['symbol'], t['side'], t['price'], t['amount'], t['cost']])
                        
                        if rows:
                            writer.writerows(rows)
                            f.flush()
                        
                        current_ts = trades[-1]['timestamp']
                        step = current_ts - since
                        pbar.update(step)
                        since = current_ts + 1
                        
                        progress_pct = min(100, int(((current_ts - start_ts) / total_duration) * 100))
                        self.update_state(state='PROGRESS', meta={'percent': progress_pct, 'status': 'Fetching Trades...'})
                        publish_task_status('DOWNLOAD', self.request.id, 'processing', progress_pct)
                        
                        if current_ts >= end_ts: break
                        
                    except Exception as e:
                        print(f"Fetch Trades Error: {e}")
                        time.sleep(2)
                        continue
                    
        publish_task_status('DOWNLOAD', self.request.id, 'completed', 100, {"filename": filename})
        return {"status": "completed", "filename": filename}

    except Exception as e:
        return {"status": "failed", "error": str(e)}

@celery_app.task(bind=True)
def fetch_and_store_sentiment(self):
    """
    Background Task: Fetch news, calculate sentiment score, and save to DB.
    """
    db = SessionLocal()
    try:
        # ✅ MOVED: Import moved here to prevent Circular Import
        from app.services.news_service import news_service 
        
        print("🔄 Fetching periodic sentiment data...")
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        news_items = loop.run_until_complete(news_service.fetch_news())

        if not news_items:
            print("⚠️ No news found to analyze.")
            return "No Data"

        total_score = 0
        sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}

        for item in news_items:
            s_label = item.get('sentiment', 'Neutral')
            sentiment_counts[s_label] = sentiment_counts.get(s_label, 0) + 1
            if s_label == "Positive":
                total_score += 1
            elif s_label == "Negative":
                total_score -= 1
        
        count = len(news_items)
        avg_score = total_score / count if count > 0 else 0
        dominant = max(sentiment_counts, key=sentiment_counts.get)

        sentiment_entry = SentimentHistory(
            score=round(avg_score, 2),
            news_count=count,
            dominant_sentiment=dominant
        )
        db.add(sentiment_entry)
        db.commit()
        
        print(f"✅ Sentiment Saved: Score={avg_score}, Count={count}")
        return {"status": "saved", "score": avg_score}

    except Exception as e:
        print(f"❌ Sentiment Task Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task
def monitor_whale_movements():
    """
    Background task to monitor large volume spikes.
    Triggers alert if volume > 500 BTC in the last hour.
    """
    db = SessionLocal()
    try:
        # Initialize exchange
        exchange = ccxt.binance({'enableRateLimit': True})
        symbol = 'BTC/USDT'  # Monitoring BTC primarily
        
        # Fetch 1h ticker data
        ticker = exchange.fetch_ticker(symbol)
        volume_btc = ticker.get('baseVolume', 0)
        current_price = ticker.get('last', 0)
        
        print(f"🐋 Tracking Whale Activity: {volume_btc} BTC Vol (1h)")
        
        # Threshold: 500 BTC
        THRESHOLD = 500 
        
        if volume_btc > THRESHOLD:
            # Check for recent alert to avoid spam (last 1 hour)
            last_alert = db.query(WhaleAlert).filter(
                WhaleAlert.symbol == symbol,
                WhaleAlert.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ).order_by(WhaleAlert.timestamp.desc()).first()
            
            if not last_alert:
                print(f"🚨 WHALE ALERT: {volume_btc} BTC Volume Detected!")
                
                # 1. Save to DB
                alert = WhaleAlert(
                    symbol=symbol,
                    volume=volume_btc,
                    price=current_price,
                    exchange="binance"
                )
                db.add(alert)
                db.commit()
                
                # 2. Notify User via Telegram (assuming user_id=1 for now, or broadcast)
                # In a real app, we might want to notify all subscribed users.
                # For demo, we notify user ID 1 if they have enabled notifications.
                
                # We need an async loop to call the async notification service from a sync celery task
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                msg = f"🐋 *Whale Alert!* \nLarge Volume Spike Detected on {symbol}\nVolume: {volume_btc:.2f} BTC\nPrice: ${current_price:,.2f}"
                loop.run_until_complete(NotificationService.send_message(db, 1, msg))
                
    except Exception as e:
        print(f"❌ Whale Monitor Error: {e}")
    finally:
        # if 'exchange' in locals():
            # exchange.close()
        db.close()
