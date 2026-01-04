from fastapi import APIRouter
# ১. sentiment ইম্পোর্ট করো
from app.api.v1.endpoints import auth, users, market_data, strategies, backtest, bots, dashboard, trading, indicators, sentiment 

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(bots.router, prefix="/bots", tags=["bots"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(indicators.router, prefix="/indicators", tags=["indicators"])

# ২. রাউটারটি রেজিস্টার করো
api_router.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
