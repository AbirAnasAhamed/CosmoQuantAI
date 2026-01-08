import httpx
import praw
import logging
import asyncio
import feedparser  # ✅ New Library for RSS
import time
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.core.config import settings

logger = logging.getLogger(__name__)

# ✅ 1. Source Importance Weights (Tier System)
SOURCE_WEIGHTS = {
    "Bloomberg": 1.0, "Reuters": 1.0, "CoinDesk": 0.8, "CoinTelegraph": 0.8, "Official": 1.0,
    "CryptoPanic": 0.6, "News": 0.6,
    "Reddit": 0.4, "Twitter": 0.4, "X": 0.4, "Unknown": 0.3
}

# ✅ 2. Free RSS Feeds List (Backup/Hybrid Sources)
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/"
]

class NewsService:
    def __init__(self):
        # API Configuration
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        
        # Reddit Configuration
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
        
        # ✅ IMPROVED CACHING STATE
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 Minutes cache
        
        self.fng_api_url = "https://api.alternative.me/fng/"
        self.fng_cache = None
        self.last_fng_fetch = None
        self.fng_cache_duration = 3600

    def get_source_weight(self, source_name):
        for key, weight in SOURCE_WEIGHTS.items():
            if key.lower() in source_name.lower():
                return weight
        return 0.3

    def analyze_sentiment_advanced(self, text):
        scores = self.vader.polarity_scores(text)
        return scores['compound']
        
    def calculate_weighted_metrics(self, news_items):
        if not news_items:
            return 0.0, 0, 0.0
        total_weighted_score = 0
        total_weights = 0
        for item in news_items:
            # Ensure sentiment_score is a number
            score = item.get('sentiment_score', 0)
            if not isinstance(score, (int, float)):
                score = 0
                
            source_weight = self.get_source_weight(item['source'])
            total_weighted_score += (score * source_weight)
            total_weights += source_weight

        final_score = total_weighted_score / total_weights if total_weights > 0 else 0
        return round(final_score, 4), len(news_items)

    # ✅ 3. NEW: Fetch from RSS Feeds (Library Based - No API Key)
    async def fetch_rss_news(self):
        def get_rss_data():
            items = []
            for url in RSS_FEEDS:
                try:
                    feed = feedparser.parse(url)
                    # Take top 5 news from each feed to avoid spam
                    for entry in feed.entries[:5]:
                        # Handle Date Parsing
                        published_time = datetime.utcnow()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        
                        score = self.analyze_sentiment_advanced(entry.title)
                        
                        items.append({
                            "id": f"rss_{entry.link[-10:]}", # Creating a pseudo-unique ID
                            "source": feed.feed.title if hasattr(feed.feed, 'title') else "CryptoNews",
                            "content": entry.title,
                            "url": entry.link,
                            "sentiment_score": score,
                            "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                            "timestamp": published_time.isoformat(),
                            "type": "news" # Treating as standard news
                        })
                except Exception as e:
                    logger.error(f"RSS Fetch Error ({url}): {e}")
            return items
        
        # Run synchronous feedparser in a thread
        return await asyncio.to_thread(get_rss_data)

    async def fetch_news_from_cryptopanic(self):
        if not self.api_key: return [] # API Key না থাকলে খালি লিস্ট রিটার্ন করবে
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url, 
                    params={"auth_token": self.api_key, "public": "true", "filter": "important"},
                    timeout=10.0
                )
                
                if response.status_code == 429:
                    logger.warning("⚠️ CryptoPanic Rate Limit Hit (429).")
                    return None
                
                if response.status_code != 200:
                    return None

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
                        "sentiment_score": score,
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": item.get('published_at'),
                        "type": "news"
                    })
                return items
        except Exception as e:
            logger.error(f"CryptoPanic Fetch Exception: {e}")
            return None

    async def fetch_reddit_discussions(self):
        if not self.reddit: return []
        try:
            def get_reddit_data():
                posts = []
                for submission in self.reddit.subreddit("CryptoCurrency+Bitcoin").hot(limit=8):
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

    # ✅ 4. Main Fetch Function (Hybrid Logic)
    async def fetch_news(self):
        # 1. Serve Fresh Cache if available
        if self.cache and self.last_fetch:
            age = (datetime.utcnow() - self.last_fetch).total_seconds()
            if age < self.cache_duration:
                return self.cache

        # 2. Async Gather - Fetch from ALL sources in parallel
        # এখানে API এবং RSS দুটোই একসাথে কল হবে
        tasks = [
            self.fetch_rss_news(),               # Always runs (Library)
            self.fetch_news_from_cryptopanic(),  # Runs if Key exists (API)
            self.fetch_reddit_discussions()      # Runs if Credentials exist (API)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        rss_news = results[0] if isinstance(results[0], list) else []
        cp_news = results[1] if isinstance(results[1], list) else []
        reddit_news = results[2] if isinstance(results[2], list) else []

        # 3. Combine Data
        # যদি API Data থাকে ভালো, না থাকলে RSS Data ব্যাকআপ হিসেবে কাজ করবে।
        # আর যদি দুটোই থাকে, তাহলে ইউজার বেশি সোর্স পাবে।
        combined_data = rss_news + cp_news + reddit_news
        
        # 4. If everything fails, use mock
        if not combined_data:
            return self._get_mock_news()

        # 5. Sort by Timestamp (Newest First) & Update Cache
        try:
            # Timestamp parsing handled inside respective fetchers to ensure ISO format
            combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Keep top 80 items to keep payload light
            self.cache = combined_data[:80]
            self.last_fetch = datetime.utcnow()
        except Exception as e:
            logger.error(f"Sorting Error: {e}")
            self.cache = combined_data[:60] # Fallback unsorted
        
        return self.cache

    async def fetch_fear_greed_index(self):
        # ... (Existing Fear Greed logic remains same) ...
        if self.fng_cache and self.last_fng_fetch:
            if (datetime.utcnow() - self.last_fng_fetch).total_seconds() < self.fng_cache_duration:
                return self.fng_cache
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.fng_api_url, params={"limit": 1, "format": "json"}, timeout=10.0)
                data = response.json()
                if data.get('data'):
                    latest = data['data'][0]
                    self.fng_cache = {
                        "value": latest.get('value'), 
                        "value_classification": latest.get('value_classification')
                    }
                    self.last_fng_fetch = datetime.utcnow()
                    return self.fng_cache
        except Exception:
            if self.fng_cache: return self.fng_cache     
        return {"value": "50", "value_classification": "Neutral"}

    def _get_mock_news(self):
        # ... (Existing mock logic) ...
        return [
            {"id": "m1", "source": "System", "content": "Waiting for live market data...", "sentiment": "Neutral", "sentiment_score": 0, "timestamp": datetime.utcnow().isoformat(), "type": "news"}
        ]

news_service = NewsService()
