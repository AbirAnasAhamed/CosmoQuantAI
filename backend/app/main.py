from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
import asyncio
import json
import random  # ডামি ডাটার জন্য, প্রোডাকশনে CCXT Pro ব্যবহার করবেন
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os
import shutil
import importlib.util
import inspect
import backtrader as bt
import sys
import ast

from . import models, database, schemas, crud, utils, auth, email_utils
from .utils import get_redis_client
from .services.market_service import MarketService
from .services.backtest_engine import BacktestEngine
from .services import ai_service
from celery.result import AsyncResult
from .tasks import run_backtest_task, run_optimization_task
from .celery_app import celery_app

UPLOAD_DIR = "app/strategies/custom"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ডাটাবেস টেবিল তৈরি
# models.Base.metadata.create_all(bind=database.engine)

# 🔴 পরিবর্তন: টাইটেল এবং মেটাডেটা যোগ করা হয়েছে
import logging

app = FastAPI(
    title="FastAPI Backend for CosmoQuantAI",
    description="CosmoQuantAI_Api Server__Developed by 'ABIR AHAMED'",
    version="1.0.0",
    contact={
        "name": "ABIR AHAMED",
        "email": "abir.ahamed.01931645993@gmail.com",
        "mobile": "01931645993"
    }
)

# ✅ ১. কাস্টম লগ ফিল্টার ক্লাস
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # যদি লগের মেসেজে এই পাথটি থাকে, তবে False রিটার্ন করবে (প্রিন্ট হবে না)
        return record.getMessage().find("/api/backtest/status") == -1

@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    db.close()
    
    # ✅ ২. Uvicorn এর এক্সেস লগারের সাথে ফিল্টারটি জুড়ে দেওয়া
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# ডাটাবেস সেশন ডিপেন্ডেন্সি
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "CosmoQuantAI Backend is Live! 🚀"}
    
# --- User Registration Endpoint ---
@app.post("/api/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # চেক করি ইউজার অলরেডি আছে কিনা
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )
    
    # নতুন ইউজার তৈরি করি
    return crud.create_user(db=db, user=user)

# --- Login Endpoint ---
@app.post("/api/login", response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    # Swagger Form এ 'username' ফিল্ড থাকে, কিন্তু আমরা ইমেইল ব্যবহার করি।
    # তাই form data-র username কে আমরা ইমেইল হিসেবে ধরবো।
    user = crud.get_user_by_email(db, email=user_credentials.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
    
    if not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
    
    access_token = auth.create_access_token(data={"sub": user.email, "user_id": user.id})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, 
        "token_type": "bearer"
    }

# --- নতুন Endpoint: Token Refresh ---
@app.post("/api/refresh-token", response_model=schemas.Token)
def refresh_access_token(token_data: dict, db: Session = Depends(get_db)):
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token missing")

    # টোকেন যাচাই করা
    payload = auth.verify_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    email = payload.get("sub")
    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # সব ঠিক থাকলে নতুন পেয়ার ইস্যু করা
    new_access_token = auth.create_access_token(data={"sub": user.email, "user_id": user.id})
    
    # চাইলে রিফ্রেশ টোকেন রোটেট করতে পারেন (সিকিউর), অথবা আগেরটাই রাখতে পারেন
    # আমরা আগেরটাই ফেরত দিচ্ছি সুবিধার জন্য
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# --- API Key Endpoints ---

# ১. নতুন API Key সেভ করা (Protected Route)
@app.post("/api/api-keys", response_model=schemas.ApiKeyResponse)
def add_api_key(
    api_key_data: schemas.ApiKeyCreate, 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.create_user_api_key(db=db, api_key=api_key_data, user_id=current_user.id)

# ২. সব API Key দেখা (Protected Route)
@app.get("/api/api-keys", response_model=List[schemas.ApiKeyResponse])
def read_api_keys(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_user_api_keys(db=db, user_id=current_user.id)

# ৩. নিজের প্রোফাইল দেখার জন্য (Protected Route)
@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# ১. Forgot Password Endpoint (ইমেইল পাঠাবে)
@app.post("/api/forgot-password")
async def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # চেক করি ইউজার আছে কি না
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        # সিকিউরিটির স্বার্থে আমরা বলবো না যে ইউজার নেই, 
        # যাতে হ্যাকাররা ইমেইল ভেরিফাই করতে না পারে।
        return {"message": "If the email exists, a reset link has been sent."}

    # রিসেট টোকেন তৈরি (১৫ মিনিটের মেয়াদ)
    reset_token = auth.create_token(
        data={"sub": user.email, "type": "reset"}, 
        expires_delta=timedelta(minutes=15)
    )

    # ইমেইল পাঠানো
    await email_utils.send_reset_email(request.email, reset_token)
    
    return {"message": "If the email exists, a reset link has been sent."}


# ২. Reset Password Endpoint (লিংক থেকে এসে পাসওয়ার্ড বদলাবে)
@app.post("/api/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # টোকেন যাচাই
    payload = auth.verify_token(request.token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    email = payload.get("sub")
    
    # পাসওয়ার্ড আপডেট
    user = crud.update_user_password(db, email, request.new_password)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "Password has been reset successfully. Please login with new password."}

# মার্কেট সার্ভিস ইনিশিয়ালইজেশন
market_service = MarketService()
# ইঞ্জিন ইনস্ট্যান্স
backtest_engine = BacktestEngine()

# --- Market & Exchange Info Endpoints ---

# ১. সাপোর্টেড এক্সচেঞ্জ লিস্ট
@app.get("/api/exchanges")
def get_exchanges():
    return market_service.get_supported_exchanges()

# ২. এক্সচেঞ্জ অনুযায়ী সিম্বল/মার্কেট পেয়ার
@app.get("/api/markets/{exchange_id}")
async def get_markets(exchange_id: str):
    symbols = await market_service.get_exchange_markets(exchange_id)
    if not symbols:
        raise HTTPException(status_code=404, detail="Exchange not found or error loading markets")
    return symbols

# --- Market Data Endpoints ---

# ১. লাইভ ডাটা সিঙ্ক করার জন্য
@app.post("/api/market-data/sync")
async def sync_market_data(
    symbol: str = "BTC/USDT", 
    timeframe: str = "1h", 
    limit: int = 1000, 
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    result = await market_service.fetch_and_store_candles(db, symbol, timeframe, start_date, end_date)
    return result

# ২. চার্ট বা ব্যাকটেস্টিং এর জন্য ডেটা রিড করার জন্য
@app.get("/api/market-data")
def get_market_data(
    symbol: str = "BTC/USDT", 
    timeframe: str = "1h", 
    db: Session = Depends(get_db)
):
    candles = market_service.get_candles_from_db(db, symbol, timeframe)
    
    # ফ্রন্টএন্ডের (Recharts/TradingView) ফরম্যাটে ডাটা পাঠানো
    formatted_data = []
    for c in candles:
        formatted_data.append({
            "time": c.timestamp.isoformat(), # Recharts এ ISO স্ট্রিং সুবিধা দেয়
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        })
    
    return formatted_data

# WebSocket এন্ডপয়েন্ট
@app.websocket("/ws/market-data/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket)
    try:
        while True:
            # এখানে CCXT Pro বা অন্য সোর্স থেকে রিয়েল ডাটা আসবে।
            # উদাহরণের জন্য আমরা ডামি প্রাইস জেনারেট করছি:
            
            # TODO: Replace with real CCXT Pro logic
            # example: ticker = await exchange.watch_ticker(symbol)
            
            dummy_price = 60000 + random.uniform(-50, 50)
            data = {
                "symbol": symbol,
                "price": round(dummy_price, 2),
                "timestamp": str(datetime.utcnow())
            }
            
            # ক্লায়েন্টকে ডাটা পাঠানো
            await websocket.send_json(data)
            
            # ১ সেকেন্ড বিরতি (রিয়েল লাইফে ইভেন্ট-ড্রিভেন হবে)
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected from {symbol} stream")

# --- Strategy Upload Endpoint ---
@app.post("/api/strategies/upload")
async def upload_strategy(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user)):
    # ১. ফাইলের এক্সটেনশন চেক করা (নিরাপত্তার জন্য)
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are allowed")

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    # ২. ফাইলটি সার্ভারে সেভ করা
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    # ৩. সফল মেসেজ রিটার্ন করা
    return {
        "filename": file.filename, 
        "message": "Strategy uploaded successfully. It will be available for backtesting."
    }

# --- Get Custom Strategy List Endpoint ---
@app.get("/api/strategies/list")
def get_custom_strategies(current_user: models.User = Depends(auth.get_current_user)):
    try:
        # ফোল্ডার চেক করা
        if not os.path.exists(UPLOAD_DIR):
            return []
            
        files = os.listdir(UPLOAD_DIR)
        
        # শুধুমাত্র .py ফাইলগুলো নিব এবং এক্সটেনশন (.py) বাদ দিয়ে নাম নিব
        strategies = [f[:-3] for f in files if f.endswith(".py")]
        
        return strategies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Get Strategy Code & Auto-Detected Params ---
@app.get("/api/strategies/source/{strategy_name}")
def get_strategy_source(strategy_name: str, current_user: models.User = Depends(auth.get_current_user)):
    try:
        # ফাইলের নাম ঠিক করা
        filename = f"{strategy_name}.py" if not strategy_name.endswith(".py") else strategy_name
        file_path = f"{UPLOAD_DIR}/{filename}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Strategy file not found")
            
        # 🔴 ফিক্স: encoding="utf-8" এর সাথে errors="ignore" যোগ করা হয়েছে
        # এটি ক্র্যাশ আটকাবে যদি ফাইলে কোনো অদ্ভুত ক্যারেক্টার থাকে
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        # ২. ডাইনামিকালি প্যারামিটার এক্সট্রাক্ট করা
        extracted_params = {}
        
        try:
            spec = importlib.util.spec_from_file_location("temp_strategy_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            target_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                    target_class = obj
                    break
            
            if target_class and hasattr(target_class, 'params'):
                raw_params = target_class.params._getitems()
                
                for key, default_val in raw_params:
                    if isinstance(default_val, (int, float)) and not isinstance(default_val, bool):
                        # প্যারামিটার ডিটেকশন লজিক...
                        is_int = isinstance(default_val, int)
                        min_val = 0 if default_val >= 0 else default_val * 2
                        if default_val > 0:
                            min_val = 1 if is_int else 0.1
                        
                        max_val = default_val * 5 if default_val > 0 else 0
                        if max_val == 0: max_val = 100
                        
                        step = 1 if is_int else round(default_val / 10, 3) or 0.01

                        extracted_params[key] = {
                            "type": "number",
                            "label": key.replace('_', ' ').title(),
                            "default": default_val,
                            "min": min_val,
                            "max": max_val,
                            "step": step
                        }

        except Exception as e:
            print(f"Auto-param detection failed: {e}")
            pass
            
        return {
            "code": code,
            "inferred_params": extracted_params
        }
        
    except Exception as e:
        print(f"Critical error in get_strategy_source: {e}")
        raise HTTPException(status_code=500, detail=f"File read error: {str(e)}")

# --- AI Strategy Generation Endpoint ---
@app.post("/api/strategies/generate")
async def generate_strategy(request: schemas.GenerateStrategyRequest, current_user: models.User = Depends(auth.get_current_user)):
    # ১. AI সার্ভিস কল করে কোড জেনারেট করা
    generated_code = ai_service.generate_strategy_code(request.prompt)
    
    if not generated_code:
        raise HTTPException(status_code=500, detail="Failed to generate strategy code.")

    # ২. ফাইলের নাম জেনারেট করা (ইউনিক)
    filename = f"AI_Strategy_{len(os.listdir(UPLOAD_DIR)) + 1}.py"
    file_location = f"{UPLOAD_DIR}/{filename}"
    
    # ৩. কোড ফাইলে সেভ করা
    try:
        with open(file_location, "w") as f:
            f.write(generated_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save generated file: {str(e)}")
    
    # ৪. রেসপন্স রিটার্ন করা
    return {
        "filename": filename,
        "code": generated_code,
        "message": "Strategy generated successfully!"
    }

# --- Backtest Endpoint ---

# ১. ব্যাকটেস্ট শুরু করার এন্ডপয়েন্ট (Async)
@app.post("/api/backtest/run")
def run_backtest(
    request: schemas.BacktestRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    # টাস্কটি কিউতে পাঠানো হচ্ছে
    task = run_backtest_task.delay(
        symbol=request.symbol,
        timeframe=request.timeframe,
        strategy_name=request.strategy,
        initial_cash=request.initial_cash,
        params=request.params,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    # সাথে সাথে Task ID রিটার্ন করা হবে
    return {"task_id": task.id, "status": "Processing"}

# ২. টাস্ক স্ট্যাটাস চেক করার এন্ডপয়েন্ট
@app.get("/api/backtest/status/{task_id}")
def get_backtest_status(task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"status": "Pending", "percent": 0, "result": None}
    
    elif task_result.state == 'PROGRESS':
        # প্রগ্রেস ইনফো রিটার্ন করা
        info = task_result.info
        return {
            "status": "Processing",
            "percent": info.get('percent', 0),
            "current": info.get('current', 0),
            "total": info.get('total', 0),
            "result": None
        }
        
    elif task_result.state == 'SUCCESS':
        return {"status": "Completed", "percent": 100, "result": task_result.result}
        
    elif task_result.state == 'FAILURE':
        return {"status": "Failed", "error": str(task_result.result)}
    
    return {"status": task_result.state}

# --- Optimization Endpoint ---
# --- Optimization Endpoint ---
@app.post("/api/backtest/optimize")
def run_optimization(
    request: schemas.OptimizationRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    # 🔴 ফিক্স: Pydantic মডেলকে সাধারণ ডিকশনারিতে কনভার্ট করা হচ্ছে
    # request.params হলো dict[str, OptimizationParam]
    # আমরা একে dict[str, dict] এ কনভার্ট করব
    params_dict = {k: v.model_dump() for k, v in request.params.items()}
    
    # Celery টাস্কে পাঠানো
    task = run_optimization_task.delay(
        symbol=request.symbol,
        timeframe=request.timeframe,
        strategy_name=request.strategy,
        initial_cash=request.initial_cash,
        params=params_dict,
        start_date=request.start_date,
        end_date=request.end_date,
        # ✅ নতুন প্যারামিটার
        method=request.method,
        population_size=request.population_size,
        generations=request.generations
    )
    
    return {"task_id": task.id, "status": "Processing"}

# ✅ নতুন: টাস্ক ফোর্স স্টপ করার এন্ডপয়েন্ট
@app.post("/api/backtest/revoke/{task_id}")
def revoke_task(task_id: str, current_user: models.User = Depends(auth.get_current_user)):
    # ১. স্ট্যান্ডার্ড Celery Revoke (এটি প্রসেস কিলের চেষ্টা করবে)
    celery_app.control.revoke(task_id, terminate=True)
    
    # ২. ✅ ফোর্স স্টপ (Redis Flag): লুপ ব্রেক করার জন্য ফ্ল্যাগ সেট করা
    try:
        r = utils.get_redis_client()
        # ফ্ল্যাগ সেট করা যা ১ ঘণ্টা পর অটো ডিলিট হবে (ex=3600)
        r.set(f"abort_task:{task_id}", "true", ex=3600)
    except Exception as e:
        print(f"⚠️ Redis Error in revoke: {e}")
        
    return {"status": "Revoked", "message": f"Stop signal sent for Task {task_id}."}
