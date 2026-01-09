import httpx
import asyncio
import feedparser
import time
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from gnews import GNews
import pandas as pd

class NewsService:
    def __init__(self):
        # Google News Init (No API Key Needed)
        self.google_news = GNews(language='en', country='US', period='7d', max_results=50)
        # Vader Sentiment Init
        self.vader = SentimentIntensityAnalyzer()

    def analyze_sentiment(self, text):
        """Analyze text and return a compound score."""
        if not text: return 0
        scores = self.vader.polarity_scores(str(text))
        return scores['compound']

    async def fetch_news(self):
        """Fetch latest news for the news feed card"""
        return await self.fetch_google_news_data(period='24h')

    async def fetch_historical_sentiment(self, days=7):
        """
        Fetch last 7 days news and calculate hourly sentiment history.
        """
        try:
            # Synchrounous call wrapped in async
            news_items = await asyncio.to_thread(self.google_news.get_news, 'Bitcoin Crypto Market')
            
            processed_data = []
            for item in news_items:
                pub_date = item.get('published date')
                title = item.get('title', '')
                
                # Date parsing
                try:
                    dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    dt_obj = datetime.utcnow()

                score = self.analyze_sentiment(title)
                processed_data.append({
                    "timestamp": dt_obj,
                    "score": score
                })
            
            # Convert to DataFrame
            if not processed_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(processed_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Hourly Resampling
            hourly_sentiment = df.resample('1h').mean().fillna(0)
            return hourly_sentiment

        except Exception as e:
            print(f"Historical News Error: {e}")
            return pd.DataFrame()

    async def fetch_google_news_data(self, period='24h'):
        """Helper to fetch news format for frontend"""
        def get_sync():
            self.google_news.period = period
            news = self.google_news.get_news('Cryptocurrency Bitcoin')
            results = []
            for item in news:
                title = item.get('title', '')
                score = self.analyze_sentiment(title)
                results.append({
                    "id": f"gn_{abs(hash(title))}",
                    "source": item.get('publisher', {}).get('title', 'Google News'),
                    "content": title,
                    "url": item.get('url'),
                    "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                    "timestamp": item.get('published date'),
                    "type": "news"
                })
            return results
        return await asyncio.to_thread(get_sync)

    async def fetch_fear_greed_index(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.alternative.me/fng/", params={"limit": 1})
                return response.json()['data'][0]
        except:
            return {"value": "50", "value_classification": "Neutral"}

news_service = NewsService()
