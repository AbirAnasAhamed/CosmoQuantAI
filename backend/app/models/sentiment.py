from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.sql import func
from app.db.base_class import Base

class SentimentHistory(Base):
    __tablename__ = "sentiment_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    score = Column(Float)  # -1.0 (Negative) to 1.0 (Positive)
    news_count = Column(Integer) # Number of news items used for this score
    dominant_sentiment = Column(String) # "Positive", "Negative", "Neutral"
