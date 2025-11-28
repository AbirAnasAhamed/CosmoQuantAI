from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
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
from .services.market_service import MarketService
from .services.backtest_engine import BacktestEngine
from .services import ai_service

UPLOAD_DIR = "app/strategies/custom"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ডাটাবেস টেবিল তৈরি
models.Base.metadata.create_all(bind=database.engine)

# 🔴 পরিবর্তন: টাইটেল এবং মেটাডেটা যোগ করা হয়েছে
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

@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    # crud.seed_strategy_templates(db) # Removed
    db.close()

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
@app.post("/api/backtest/run")
def run_backtest(
    request: schemas.BacktestRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # শুধুমাত্র লগড-ইন ইউজার
):
    result = backtest_engine.run(
        db=db, 
        symbol=request.symbol, 
        timeframe=request.timeframe, 
        strategy_name=request.strategy,
        initial_cash=request.initial_cash,
        params=request.params,
        start_date=request.start_date,
        end_date=request.end_date
    )
    return result
