from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import json
import redis.asyncio as aioredis
from app.core.config import settings
from app.api.v1.api import api_router
from app.services.websocket_manager import manager
from app.utils import RedisLogHandler
import ccxt.async_support as ccxt
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="CosmoQuantAI Backend API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# ✅ Global variable to hold references to background tasks
# এটি Garbage Collection আটকাবে এবং "Task destroyed" এরর ফিক্স করবে
running_tasks = set()

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/api/backtest/status") == -1

# --- Background Tasks ---

async def subscribe_to_redis_logs():
    print("📡 Listening to Redis Log Stream...")
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("bot_logs")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    target_channel = payload.get("channel")
                    log_data = payload.get("data")
                    
                    # 1. Worker Logs Forwarding
                    if target_channel and target_channel.startswith("logs_") and target_channel != "logs_backend":
                         await manager.broadcast_to_symbol(target_channel, log_data)
                    
                    # 2. Backend System Logs Forwarding
                    elif target_channel == "logs_backend":
                        for channel in list(manager.active_connections.keys()):
                            if channel.startswith("logs_"): 
                                await manager.broadcast_to_symbol(channel, log_data)

                except Exception as e:
                    print(f"Log Forward Error: {e}")
    except asyncio.CancelledError:
        print("Redis Subscriber Task Cancelled.")
    finally:
        await redis.close()

async def subscribe_to_task_updates():
    print("📡 Listening to Redis Task Updates...")
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("task_updates")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # data expected format: { "task_type":..., "task_id":..., "status":..., "progress":..., "data":... }
                    await manager.broadcast_status(
                        task_type=data.get("task_type"),
                        task_id=data.get("task_id"),
                        status=data.get("status"),
                        progress=data.get("progress"),
                        data=data.get("data")
                    )
                except Exception as e:
                    print(f"Task Update Forward Error: {e}")
    except asyncio.CancelledError:
        print("Task Update Subscriber Cancelled.")
    finally:
        await redis.close()

async def fetch_market_data_background():
    local_exchange_client = None
    print("🚀 Background Market Data Task Started")
    
    try:
        local_exchange_client = ccxt.binance({'enableRateLimit': True})
        await local_exchange_client.load_markets()
    except Exception as e:
        print(f"⚠️ Failed to initialize exchange client: {e}")

    # Rate limiting control
    last_depth_update = {}
    
    while True:
        try:
            active_symbols = list(manager.active_connections.keys())
            if not active_symbols:
                await asyncio.sleep(1)
                continue

            for symbol in active_symbols:
                if symbol == "general" or symbol.startswith("logs_") or symbol == "backtest":
                    continue
                
                # Re-initialize client if needed
                if not local_exchange_client:
                     local_exchange_client = ccxt.binance({'enableRateLimit': True})
                     await local_exchange_client.load_markets()
                
                # Normalize symbol (BTCUSDT -> BTC/USDT)
                # Frontend might send "BTCUSDT", CCXT needs "BTC/USDT"
                target_symbol = symbol
                if "/" not in symbol:
                    # Try to find the unified symbol from the exchange markets
                    # markets_by_id maps 'BTCUSDT' -> Market Structure
                    # We iterate to find a match if direct lookup fails or if simplistic approach works
                    # For Binance, id is usually the symbol without slash
                    
                    # Simple heuristic first (if markets loaded)
                    if local_exchange_client.markets:
                        # try to find by id
                        market = None
                        try:
                           # finding manually to be safe or use ccxt helper if available, 
                           # but accessing .markets dictionary is direct. 
                           # In ccxt, markets_by_id is often available after load_markets()
                           pass # logic below
                        except: pass

                        # Let's try to find a market where id == symbol
                        for m_symbol, m_info in local_exchange_client.markets.items():
                            if m_info.get('id') == symbol:
                                target_symbol = m_symbol
                                break
                
                try:
                    # 1. Ticker (Fast update)
                    ticker = await local_exchange_client.fetch_ticker(target_symbol)
                    
                    # Safe float conversion helper
                    def safe_float(val):
                        try:
                            return float(val) if val is not None else 0.0
                        except:
                            return 0.0

                    ticker_data = {
                        "symbol": symbol,
                        "price": safe_float(ticker.get('last')),
                        "change": safe_float(ticker.get('change')),
                        "changePercent": safe_float(ticker.get('percentage')),
                        "high": safe_float(ticker.get('high')),
                        "low": safe_float(ticker.get('low')),
                        "volume": safe_float(ticker.get('baseVolume')), # 24h Volume
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.broadcast_market_data(symbol, "ticker", ticker_data)

                    # 2. Recent Trades (Fast update)
                    # Fetching only last 20 trades to save bandwidth
                    trades = await local_exchange_client.fetch_trades(symbol, limit=20)
                    formatted_trades = []
                    for t in trades:
                        try:
                            formatted_trades.append({
                                "id": t.get('id'),
                                "time": datetime.fromtimestamp(t.get('timestamp')/1000).strftime('%H:%M:%S'),
                                "price": t.get('price'),
                                "amount": t.get('amount'),
                                "type": t.get('side'), # 'buy' or 'sell'
                            })
                        except: pass
                    
                    if formatted_trades:
                        await manager.broadcast_market_data(symbol, "trade", formatted_trades)


                    # 3. Order Book (Slower update - every 2 seconds)
                    now = asyncio.get_event_loop().time()
                    if symbol not in last_depth_update or (now - last_depth_update[symbol]) > 2:
                        orderbook = await local_exchange_client.fetch_order_book(symbol, limit=20)
                        depth_data = {
                            "bids": [{"price": b[0], "amount": b[1], "total": 0} for b in orderbook.get('bids', [])], # Total will be calc on frontend or here
                            "asks": [{"price": a[0], "amount": a[1], "total": 0} for a in orderbook.get('asks', [])]
                        }
                        
                        # Calculate cumulative totals for visual depth bars if needed, 
                        # but for now let's just send raw data to be lightweight
                        await manager.broadcast_market_data(symbol, "depth", depth_data)
                        last_depth_update[symbol] = now

                except Exception as e:
                    # print(f"Error fetching data for {symbol}: {e}")
                    pass

            await asyncio.sleep(1) # Global Loop Interval
        except asyncio.CancelledError:
            print("Market Data Task Cancelled.")
            if local_exchange_client: await local_exchange_client.close()
            break
        except Exception as e:
            print(f"Background Task Error: {e}")
            await asyncio.sleep(5)

# --- Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    # 1. Logging Setup
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
    
    redis_handler = RedisLogHandler()
    redis_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Hook Uvicorn Loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        log = logging.getLogger(logger_name)
        log.addHandler(redis_handler)
        log.setLevel(logging.INFO)

    print("✅ Backend System Logging attached to Redis.")

    # 2. Start & Track Background Tasks
    # টাস্কগুলোকে running_tasks সেটে অ্যাড করা হচ্ছে
    
    # Task A: Market Data
    market_task = asyncio.create_task(fetch_market_data_background())
    running_tasks.add(market_task)
    market_task.add_done_callback(running_tasks.discard) # শেষ হলে সেট থেকে মুছে যাবে

    # Task B: Redis Logs
    log_task = asyncio.create_task(subscribe_to_redis_logs())
    running_tasks.add(log_task)
    log_task.add_done_callback(running_tasks.discard)

    # Task C: Task Updates (Unified WebSocket)
    task_update_task = asyncio.create_task(subscribe_to_task_updates())
    running_tasks.add(task_update_task)
    task_update_task.add_done_callback(running_tasks.discard)

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Server Shutdown Initiated...")
    
    # 3. Graceful Shutdown (সব টাস্ক ক্যানসেল করা)
    for task in running_tasks:
        task.cancel()
    
    # সব টাস্ক বন্ধ হওয়া পর্যন্ত অপেক্ষা করা
    if running_tasks:
        await asyncio.gather(*running_tasks, return_exceptions=True)
    
    print("✅ All background tasks stopped.")

# --- WebSocket Endpoints ---

@app.websocket("/ws/market-data/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, symbol)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)

@app.websocket("/ws/logs/{bot_id}")
async def websocket_logs(websocket: WebSocket, bot_id: str):
    channel_id = f"logs_{bot_id}"
    await manager.connect(websocket, channel_id)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)

@app.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    await manager.connect(websocket, "general")
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "general")

@app.websocket("/ws/backtest")
async def websocket_backtest(websocket: WebSocket):
    await manager.connect(websocket, "backtest")
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "backtest")
