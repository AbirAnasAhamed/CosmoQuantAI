import httpx
import praw
import logging
import asyncio
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.core.config import settings

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        # 1. CryptoPanic Config
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        
        # 2. Reddit Config (New Source)
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

        # 3. Enhanced Sentiment Engine (VADER)
        self.vader = SentimentIntensityAnalyzer()

        # Cache Config
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 minutes
        
        # Fear & Greed Cache
        self.fng_api_url = "https://api.alternative.me/fng/"
        self.fng_cache = None
        self.last_fng_fetch = None
        self.fng_cache_duration = 3600

    def analyze_sentiment_advanced(self, text):
        """
        TextBlob এর বদলে VADER ব্যবহার করা হচ্ছে যা সোশ্যাল মিডিয়া টেক্সট ভালো বোঝে।
        """
        scores = self.vader.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= 0.05:
            return "Positive"
        elif compound <= -0.05:
            return "Negative"
        else:
            return "Neutral"

    async def fetch_news_from_cryptopanic(self):
        """CryptoPanic থেকে নিউজ ফেচ করা"""
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
                    items.append({
                        "id": f"cp_{item.get('id')}", # Unique ID prefix
                        "source": item.get('source', {}).get('title', 'CryptoPanic'),
                        "content": title,
                        "url": item.get('url'),
                        "sentiment": self.analyze_sentiment_advanced(title),
                        "timestamp": item.get('published_at'),
                        "type": "news"
                    })
                return items
        except Exception as e:
            logger.error(f"CryptoPanic Error: {e}")
            return []

    async def fetch_reddit_discussions(self):
        """Reddit (r/Cryptocurrency, r/Bitcoin) থেকে টপ পোস্ট ফেচ করা"""
        if not self.reddit: return []

        try:
            # PRAW is blocking, so we run it in a separate thread
            def get_reddit_data():
                posts = []
                # r/CryptoCurrency + r/Bitcoin থেকে Hot পোস্ট নেওয়া
                for submission in self.reddit.subreddit("CryptoCurrency+Bitcoin").hot(limit=10):
                    posts.append({
                        "id": f"rd_{submission.id}",
                        "source": f"r/{submission.subreddit}",
                        "content": submission.title,
                        "url": submission.url,
                        "sentiment": self.analyze_sentiment_advanced(submission.title),
                        "timestamp": datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                        "type": "social"
                    })
                return posts

            return await asyncio.to_thread(get_reddit_data)
        except Exception as e:
            logger.error(f"Reddit Fetch Error: {e}")
            return []

    async def fetch_news(self):
        """
        মেইন ফাংশন যা সব সোর্স থেকে ডাটা এনে মার্জ করে।
        """
        # 1. Check Cache
        if self.cache and self.last_fetch and (datetime.utcnow() - self.last_fetch).total_seconds() < self.cache_duration:
            return self.cache

        # 2. Parallel Fetching (News + Social)
        # Mock Data if credentials missing
        if not self.api_key and not self.reddit:
            return self._get_mock_news()

        news_task = self.fetch_news_from_cryptopanic()
        reddit_task = self.fetch_reddit_discussions()
        
        results = await asyncio.gather(news_task, reddit_task)
        combined_data = results[0] + results[1]

        # 3. Sort by Timestamp (Newest First)
        combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 4. Update Cache
        self.cache = combined_data[:30] # Keep top 30 items
        self.last_fetch = datetime.utcnow()
        
        return self.cache

    async def fetch_fear_greed_index(self):
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
        # Mock data teo VADER logic apply hobe
        data = [
            {"id": "m1", "source": "CoinDesk", "content": "Bitcoin Hits All Time High! 🚀", "timestamp": datetime.utcnow().isoformat()},
            {"id": "m2", "source": "r/Bitcoin", "content": "Why is the market crashing so hard?", "timestamp": datetime.utcnow().isoformat()},
            {"id": "m3", "source": "Bloomberg", "content": "SEC approves new regulations.", "timestamp": datetime.utcnow().isoformat()},
        ]
        for d in data:
            d['sentiment'] = self.analyze_sentiment_advanced(d['content'])
        return data

news_service = NewsService()
