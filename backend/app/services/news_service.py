import httpx
import praw
import logging
import asyncio
import feedparser
import time
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.core.config import settings
from gnews import GNews  # ✅ NEW: Google News Library

logger = logging.getLogger(__name__)

# ✅ Reliable RSS Sources (Backup)
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/"
]

class NewsService:
    def __init__(self):
        # 1. API Config
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        
        # 2. Reddit Config
        self.reddit = None
        if hasattr(settings, 'REDDIT_CLIENT_ID') and settings.REDDIT_CLIENT_ID:
            try:
                self.reddit = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent="CosmoQuant/1.0"
                )
            except Exception as e:
                logger.warning(f"Reddit Init Failed: {e}")

        # 3. Google News Init (No API Key Needed)
        # We fetch top crypto news from the last 24 hours
        self.google_news = GNews(language='en', country='US', period='24h', max_results=5)

        # 4. Sentiment Analyzer
        self.vader = SentimentIntensityAnalyzer()
        
        # 5. Caching
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 Minutes cache
        
        # Fear & Greed Cache
        self.fng_cache = None
        self.last_fng_fetch = None

    def analyze_sentiment_advanced(self, text):
        """Analyze text and return a compound score."""
        if not text: return 0
        scores = self.vader.polarity_scores(str(text))
        return scores['compound']

    # ✅ 1. Google News Fetcher (Async Wrapper)
    async def fetch_google_news(self):
        def get_gnews_sync():
            try:
                # Search for general crypto market news
                news_items = self.google_news.get_news('Cryptocurrency Bitcoin Market')
                formatted_items = []
                
                for item in news_items:
                    title = item.get('title', 'No Title')
                    score = self.analyze_sentiment_advanced(title)
                    
                    # Parse Date
                    pub_date = item.get('published date')
                    try:
                        # GNews usually returns RFC format
                        dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        timestamp = dt_obj.isoformat()
                    except:
                        timestamp = datetime.utcnow().isoformat()

                    formatted_items.append({
                        "id": f"gn_{abs(hash(title))}",
                        "source": item.get('publisher', {}).get('title', 'Google News'),
                        "content": title,
                        "url": item.get('url'),
                        "sentiment_score": score,
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": timestamp,
                        "type": "news"
                    })
                return formatted_items
            except Exception as e:
                logger.error(f"Google News Fetch Error: {e}")
                return []
        
        # Run synchronous library in a separate thread to not block async loop
        return await asyncio.to_thread(get_gnews_sync)

    # ✅ 2. RSS Fetcher (Robust with User-Agent)
    async def fetch_rss_news(self):
        async def get_single_feed(client, url):
            try:
                # Browser-like headers to prevent blocking
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code != 200: return []
                
                feed = feedparser.parse(response.text)
                items = []
                for entry in feed.entries[:5]: 
                    score = self.analyze_sentiment_advanced(entry.title)
                    
                    # Date Handling
                    published_time = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))

                    items.append({
                        "id": f"rss_{getattr(entry, 'id', entry.link)[-10:]}",
                        "source": getattr(feed.feed, 'title', 'CryptoNews'),
                        "content": entry.title,
                        "url": entry.link,
                        "sentiment_score": score,
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": published_time.isoformat(),
                        "type": "news"
                    })
                return items
            except Exception:
                return []

        async with httpx.AsyncClient() as client:
            tasks = [get_single_feed(client, url) for url in RSS_FEEDS]
            results = await asyncio.gather(*tasks)
            return [item for sublist in results for item in sublist]

    # ✅ 3. CryptoPanic API (Optional)
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
                        "sentiment_score": score,
                        "sentiment": "Positive" if score > 0.05 else "Negative" if score < -0.05 else "Neutral",
                        "timestamp": item.get('published_at'),
                        "type": "news"
                    })
                return items
        except Exception:
            return []

    # ✅ 4. Main Fetch Function (Hybrid)
    async def fetch_news(self):
        # Check Cache
        if self.cache and self.last_fetch:
            if (datetime.utcnow() - self.last_fetch).total_seconds() < self.cache_duration:
                return self.cache

        # Fetch from ALL sources in parallel
        tasks = [
            self.fetch_google_news(),            # Free & Reliable
            self.fetch_rss_news(),               # Free & Reliable
            self.fetch_news_from_cryptopanic(),  # API Key dependent
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        combined_data = []
        for res in results:
            if isinstance(res, list):
                combined_data.extend(res)

        # Remove Duplicates based on content similarity or ID
        seen_titles = set()
        unique_data = []
        for item in combined_data:
            if item['content'] not in seen_titles:
                seen_titles.add(item['content'])
                unique_data.append(item)

        # Fallback if absolutely everything fails
        if not unique_data:
            return [{
                "id": "m1", "source": "System", 
                "content": "Market data is syncing...", 
                "sentiment": "Neutral", "sentiment_score": 0, 
                "timestamp": datetime.utcnow().isoformat(), "type": "news"
            }]

        # Sort by latest
        try:
            unique_data.sort(key=lambda x: x['timestamp'], reverse=True)
            self.cache = unique_data[:60]
            self.last_fetch = datetime.utcnow()
        except:
            self.cache = unique_data[:40]
        
        return self.cache

    # Fear & Greed Index
    async def fetch_fear_greed_index(self):
        # 1-Hour Cache for F&G
        if self.fng_cache and self.last_fng_fetch:
            if (datetime.utcnow() - self.last_fng_fetch).total_seconds() < 3600:
                return self.fng_cache
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.alternative.me/fng/", params={"limit": 1}, timeout=10.0)
                data = response.json()
                if data.get('data'):
                    self.fng_cache = data['data'][0]
                    self.last_fng_fetch = datetime.utcnow()
                    return self.fng_cache
        except: pass
        return {"value": "50", "value_classification": "Neutral"}

news_service = NewsService()
