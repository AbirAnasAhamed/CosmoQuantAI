from fastapi import APIRouter
# ১. sentiment ইম্পোর্ট করো
from app.api.v1.endpoints import auth, users, market_data, strategies, backtest, bots, dashboard, trading, indicators, sentiment, education, arbitrage, system, notifications, grid_bot, analytics, on_chain, fng, market_discovery

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
api_router.include_router(fng.router, prefix="/fng", tags=["fng"])
api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(arbitrage.router, prefix="/arbitrage", tags=["arbitrage-engine"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(grid_bot.router, prefix="/grid-bot", tags=["grid-bot"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
from app.api.v1.endpoints import whale_alerts
api_router.include_router(whale_alerts.router, prefix="/whale-alerts", tags=["whale-alerts"])
api_router.include_router(on_chain.router, prefix="/on-chain", tags=["on-chain"])
api_router.include_router(market_discovery.router, prefix="/market", tags=["market-discovery"])
