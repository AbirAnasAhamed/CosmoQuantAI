from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from . import models, database, schemas, crud, utils, auth, email_utils
from datetime import timedelta

# ডাটাবেস টেবিল তৈরি
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

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
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    # ... আগের ভেরিফিকেশন লজিক ... (User Check & Pass Check)
    
    user = crud.get_user_by_email(db, email=user_credentials.email)
    if not user or not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    
    # দুইটি টোকেন জেনারেট করা হচ্ছে
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