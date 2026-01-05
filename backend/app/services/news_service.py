import httpx
import praw
import logging
import asyncio
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.core.config import settings

logger = logging.getLogger(__name__)

# ✅ 1. Source Importance Weights (Tier System)
SOURCE_WEIGHTS = {
    # Tier 1: High Impact
    "Bloomberg": 1.0,
    "Reuters": 1.0,
    "CoinDesk": 0.8,
    "CoinTelegraph": 0.8,
    "Official": 1.0,
    
    # Tier 2: Medium Impact
    "CryptoPanic": 0.6,
    "News": 0.6,
    
    # Tier 3: Social/Noise
    "Reddit": 0.4,
    "Twitter": 0.4,
    "X": 0.4,
    "Unknown": 0.3
}

class NewsService:
    def __init__(self):
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        
        self.reddit = None
        if hasattr(settings, 'REDDIT_CLIENT_ID') and settings.REDDIT_CLIENT_ID:
            try:
                self.reddit = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT or "CosmoQuant/1.0"
                )
            except Exception as e:
                logger.warning(f"Reddit Init Failed: {e}")

        self.vader = SentimentIntensityAnalyzer()
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 minutes
        
        self.fng_api_url = "https://api.alternative.me/fng/"
        self.fng_cache = None
        self.last_fng_fetch = None
        self.fng_cache_duration = 3600

    def get_source_weight(self, source_name):
        """সোর্সের নাম অনুযায়ী ওয়েট বের করা"""
        for key, weight in SOURCE_WEIGHTS.items():
            if key.lower() in source_name.lower():
                return weight
        return 0.3  # Default low weight

    def analyze_sentiment_advanced(self, text):
        scores = self.vader.polarity_scores(text)
        return scores['compound']  # সরাসরি স্কোর রিটার্ন করছি (-1 to 1)

    # ✅ 2. New Logic for Weighted Calculation
    def calculate_weighted_metrics(self, news_items):
        if not news_items:
            return 0.0, 0, 0.0

        total_weighted_score = 0
        total_weights = 0
        
        for item in news_items:
            sentiment_score = item['sentiment_score'] # এখন আমরা সরাসরি float স্কোর রাখবো
            source_weight = self.get_source_weight(item['source'])
            
            total_weighted_score += (sentiment_score * source_weight)
            total_weights += source_weight

        # Normalize Score (-1 to 1)
        final_score = total_weighted_score / total_weights if total_weights > 0 else 0
        
        # Social Volume (Count)
        volume = len(news_items)

        return round(final_score, 4), volume

    async def fetch_news_from_cryptopanic(self):
        if not self.api_key: return []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url, 
                    params={"auth_token": self.api_key, "public": "true", "filter": "important"},
                    timeout=10.0
                )
                if response.status_code != 200: return []
                
                data = response.json()
                items = []
                for item in data.get('results', []):
                    title = item.get('title')
                    score = self.analyze_sentiment_advanced(title)
                    
                    items.append({
                        "id": f"cp_{item.get('id')}",
                        "source": item.get('source', {}).get('title', 'CryptoPanic'),
                        "content": title,
                        "url": item.get('url'),
                        "sentiment_score": score, # Raw Float
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": item.get('published_at'),
                        "type": "news"
                    })
                return items
        except Exception as e:
            logger.error(f"CryptoPanic Error: {e}")
            return []

    async def fetch_reddit_discussions(self):
        if not self.reddit: return []
        try:
            def get_reddit_data():
                posts = []
                for submission in self.reddit.subreddit("CryptoCurrency+Bitcoin").hot(limit=15): # Limit increased
                    score = self.analyze_sentiment_advanced(submission.title)
                    posts.append({
                        "id": f"rd_{submission.id}",
                        "source": f"r/{submission.subreddit}",
                        "content": submission.title,
                        "url": submission.url,
                        "sentiment_score": score,
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                        "type": "social"
                    })
                return posts
            return await asyncio.to_thread(get_reddit_data)
        except Exception as e:
            logger.error(f"Reddit Fetch Error: {e}")
            return []

    async def fetch_news(self):
        if self.cache and self.last_fetch and (datetime.utcnow() - self.last_fetch).total_seconds() < self.cache_duration:
            return self.cache

        if not self.api_key and not self.reddit:
            return self._get_mock_news()

        news_task = self.fetch_news_from_cryptopanic()
        reddit_task = self.fetch_reddit_discussions()
        
        results = await asyncio.gather(news_task, reddit_task)
        combined_data = results[0] + results[1]
        combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
        
        self.cache = combined_data[:50] # Cache size increased
        self.last_fetch = datetime.utcnow()
        
        return self.cache

    async def fetch_fear_greed_index(self):
        # ... (Existing code kept same)
        if self.fng_cache and self.last_fng_fetch and (datetime.utcnow() - self.last_fng_fetch).total_seconds() < self.fng_cache_duration:
            return self.fng_cache
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.fng_api_url, params={"limit": 1, "format": "json"}, timeout=10.0)
                data = response.json()
                if data.get('data'):
                    latest = data['data'][0]
                    self.fng_cache = {"value": latest.get('value'), "value_classification": latest.get('value_classification')}
                    self.last_fng_fetch = datetime.utcnow()
                    return self.fng_cache
        except: pass
        return self.fng_cache or {"value": "50", "value_classification": "Neutral"}

    def _get_mock_news(self):
        data = [
            {"id": "m1", "source": "CoinDesk", "content": "Bitcoin Hits All Time High! 🚀", "timestamp": datetime.utcnow().isoformat()},
            {"id": "m2", "source": "r/Bitcoin", "content": "Why is the market crashing so hard?", "timestamp": datetime.utcnow().isoformat()},
            {"id": "m3", "source": "Bloomberg", "content": "SEC approves new regulations.", "timestamp": datetime.utcnow().isoformat()},
        ]
        for d in data:
            d['sentiment_score'] = self.analyze_sentiment_advanced(d['content'])
            d['sentiment'] = "Positive" if d['sentiment_score'] > 0.05 else "Negative" if d['sentiment_score'] < -0.05 else "Neutral"
        return data

news_service = NewsService()

