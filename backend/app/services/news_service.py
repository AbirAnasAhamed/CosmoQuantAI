import httpx
import asyncio
import feedparser
import time
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from gnews import GNews
import pandas as pd
import random

class NewsService:
    def __init__(self):
        # Google News Init
        self.google_news = GNews(language='en', country='US', period='7d', max_results=50)
        self.vader = SentimentIntensityAnalyzer()

    def analyze_sentiment(self, text):
        """Analyze text and return a compound score."""
        if not text: return 0
        scores = self.vader.polarity_scores(str(text))
        return scores['compound']

    async def fetch_news(self):
        """Fetch latest news with Fallback"""
        try:
            data = await self.fetch_google_news_data(period='24h')
            if not data:
                print("⚠️ Warning: Empty news data, using fallback.")
                return self.get_mock_news()
            return data
        except Exception as e:
            print(f"❌ News Fetch Error: {e}. Using fallback data.")
            return self.get_mock_news()

    async def fetch_historical_sentiment(self, days=7):
        try:
            # Async wrapper with timeout safety
            news_items = await asyncio.to_thread(self._safe_get_news, 'Bitcoin Crypto Market')
            
            if not news_items:
                # Return dummy dataframe to prevent chart crash
                return self._get_mock_historical_data(days)

            processed_data = []
            for item in news_items:
                pub_date = item.get('published date')
                title = item.get('title', '')
                
                try:
                    dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    dt_obj = datetime.utcnow()

                score = self.analyze_sentiment(title)
                processed_data.append({
                    "timestamp": dt_obj,
                    "score": score
                })
            
            if not processed_data:
                return self._get_mock_historical_data(days)
            
            df = pd.DataFrame(processed_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            hourly_sentiment = df.resample('1h').mean().fillna(0)
            return hourly_sentiment

        except Exception as e:
            print(f"Historical News Error: {e}")
            return self._get_mock_historical_data(days)

    def _safe_get_news(self, query):
        """Safe wrapper for GNews to catch connection errors"""
        try:
            return self.google_news.get_news(query)
        except Exception as e:
            print(f"GNews Connection Refused: {e}")
            return []

    async def fetch_google_news_data(self, period='24h'):
        def get_sync():
            try:
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
            except Exception as e:
                print(f"Google News Fetch Failed: {e}")
                return []
        
        return await asyncio.to_thread(get_sync)

    async def fetch_fear_greed_index(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.alternative.me/fng/", params={"limit": 1}, timeout=5.0)
                if response.status_code == 200:
                    return response.json()['data'][0]
                return {"value": "50", "value_classification": "Neutral"}
        except:
            return {"value": "50", "value_classification": "Neutral"}

    # --- MOCK DATA GENERATORS (For when API fails) ---
    
    def get_mock_news(self):
        """Returns dummy news when connection fails"""
        return [
            {
                "id": "mock_1",
                "source": "CryptoDaily (Mock)",
                "content": "Bitcoin shows resilience above $95k despite global uncertainty.",
                "url": "#",
                "sentiment": "Positive",
                "timestamp": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "type": "news"
            },
            {
                "id": "mock_2",
                "source": "MarketWatch (Mock)",
                "content": "Ethereum network activity surges to new highs.",
                "url": "#",
                "sentiment": "Positive",
                "timestamp": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "type": "news"
            },
            {
                "id": "mock_3",
                "source": "CoinDesk (Mock)",
                "content": "Analysts warn of potential short-term volatility in altcoins.",
                "url": "#",
                "sentiment": "Negative",
                "timestamp": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "type": "news"
            }
        ]

    def _get_mock_historical_data(self, days):
        """Returns dummy historical sentiment for charts"""
        dates = pd.date_range(end=datetime.now(), periods=days*24, freq='H')
        data = [random.uniform(-0.5, 0.5) for _ in range(len(dates))]
        df = pd.DataFrame(data, index=dates, columns=['score'])
        return df

news_service = NewsService()
