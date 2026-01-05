from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.sql import func
from app.db.base_class import Base

class SentimentHistory(Base):
    __tablename__ = "sentiment_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Basic Score
    score = Column(Float)  # -1.0 (Extreme Bearish) to 1.0 (Extreme Bullish)
    news_count = Column(Integer) # Total number of items analyzed
    dominant_sentiment = Column(String) # "Positive", "Negative", "Neutral"
    
    # ✅ New "Enterprise Grade" Fields
    sentiment_momentum = Column(Float, default=0.0) # Velocity of sentiment change (Previous vs Current)
    social_volume = Column(Integer, default=0)      # Raw count of mentions/posts
    top_source = Column(String, nullable=True)      # Source that contributed most to the score
