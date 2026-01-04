from fastapi import APIRouter, HTTPException
from typing import List
from app.services.news_service import news_service
# Pydantic schema import is better, but returning dict directly for now

router = APIRouter()

@router.get("/news")
async def get_sentiment_news():
    """
    Fetch crypto news with sentiment analysis.
    """
    try:
        # fetch data from news_service
        news = await news_service.fetch_news()
        return news
    except Exception as e:
        print(f"Error in sentiment endpoint: {e}")
        # return empty list on error to prevent frontend crash
        return []

@router.get("/fear-greed")
async def get_fear_greed():
    """
    Mock Fear & Greed Index (Real API can be attached later)
    """
    return {"value": "55", "value_classification": "Greed"}

@router.post("/summary")
async def generate_summary(payload: dict):
    """
    Mock AI Summary endpoint
    """
    return {"summary": "Market sentiment is currently showing signs of recovery based on recent institutional inflows."}
