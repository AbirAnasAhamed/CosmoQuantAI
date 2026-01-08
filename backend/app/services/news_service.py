import httpx
import praw
import logging
import asyncio
import feedparser
import time
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.core.config import settings
from gnews import GNews  # ✅ Google News Library

logger = logging.getLogger(__name__)

# ✅ 1. সোর্স ওয়েট (কার নিউজ কতটা গুরুত্বপূর্ণ)
SOURCE_WEIGHTS = {
    "Bloomberg": 1.0, "Reuters": 1.0, "CoinDesk": 0.8, "CoinTelegraph": 0.8, 
    "Google News": 0.7, "CryptoPanic": 0.6, "Reddit": 0.4, "Unknown": 0.3
}

# ✅ 2. ব্যাকআপ RSS Feeds (যদি API কাজ না করে)
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/"
]

class NewsService:
    def __init__(self):
        # --- API কনফিগারেশন ---
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        
        # --- Reddit কনফিগারেশন ---
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

        # --- Google News কনফিগারেশন (No API Key Needed) ---
        # এটি অটোমেটিক লেটেস্ট ক্রিপ্টো নিউজ খুঁজে আনবে
        self.google_news = GNews(language='en', country='US', period='4h', max_results=5)

        # --- সেন্টিমেন্ট অ্যানালাইজার ---
        self.vader = SentimentIntensityAnalyzer()
        
        # --- ক্যাশিং (Caching) ---
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 মিনিট ডাটা ক্যাশ থাকবে
        
        # Fear & Greed Cache
        self.fng_cache = None
        self.last_fng_fetch = None

    def analyze_sentiment_advanced(self, text):
        """টেক্সট থেকে সেন্টিমেন্ট স্কোর বের করা"""
        scores = self.vader.polarity_scores(text)
        return scores['compound']

    # ✅ 3. Google News Fetcher (লাইব্রেরি বেসড - ডাইনামিক)
    async def fetch_google_news(self):
        def get_gnews():
            try:
                # 'Cryptocurrency Market' এবং 'Bitcoin' নিয়ে লেটেস্ট নিউজ সার্চ করবে
                news_items = self.google_news.get_news('Cryptocurrency Market Bitcoin')
                formatted_items = []
                
                for item in news_items:
                    title = item.get('title', '')
                    score = self.analyze_sentiment_advanced(title)
                    
                    # তারিখ পার্সিং
                    pub_date = item.get('published date')
                    try:
                        # Google News তারিখ ফরম্যাট হ্যান্ডেল করা
                        dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        timestamp = dt_obj.isoformat()
                    except:
                        timestamp = datetime.utcnow().isoformat()

                    formatted_items.append({
                        "id": f"gn_{abs(hash(title))}", # ইউনিক আইডি তৈরি
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
        
        # থ্রেডে রান করানো যাতে মেইন লুপ ব্লক না হয়
        return await asyncio.to_thread(get_gnews)

    # ✅ 4. RSS Feed Fetcher (উন্নত ভার্সন - ব্লকিং এড়াতে হেডারসহ)
    async def fetch_rss_news(self):
        async def get_single_feed(client, url):
            try:
                # ব্রাউজারের মতো হেডার পাঠানো (যাতে 403 Forbidden না আসে)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code != 200: return []
                
                feed = feedparser.parse(response.text)
                items = []
                for entry in feed.entries[:5]: # প্রতি ফিড থেকে টপ ৫টি নিউজ
                    score = self.analyze_sentiment_advanced(entry.title)
                    
                    # তারিখ হ্যান্ডলিং
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
            except Exception as e:
                logger.error(f"RSS Error {url}: {e}")
                return []

        # সব RSS ফিড একসাথে প্যারালালি ফেচ করা
        async with httpx.AsyncClient() as client:
            tasks = [get_single_feed(client, url) for url in RSS_FEEDS]
            results = await asyncio.gather(*tasks)
            # সব লিস্টকে ফ্ল্যাট (Flatten) করা
            return [item for sublist in results for item in sublist]

    # ✅ 5. CryptoPanic API (যদি API Key থাকে)
    async def fetch_news_from_cryptopanic(self):
        if not self.api_key: return [] # কি না থাকলে স্কিপ করবে
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

    # ✅ 6. Reddit Discussions (যদি ক্রিডেনশিয়াল থাকে)
    async def fetch_reddit_discussions(self):
        if not self.reddit: return []
        try:
            def get_reddit_data():
                posts = []
                for submission in self.reddit.subreddit("CryptoCurrency+Bitcoin").hot(limit=5):
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
        except Exception:
            return []

    # ✅ 7. মেইন ফাংশন (সব সোর্স একসাথে কল করবে)
    async def fetch_news(self):
        # ১. ক্যাশ চেক করা
        if self.cache and self.last_fetch:
            if (datetime.utcnow() - self.last_fetch).total_seconds() < self.cache_duration:
                return self.cache

        # ২. প্যারালাল ফেচিং (সব ফাংশন একসাথে রান হবে)
        # গুগল নিউজ, আরএসএস, এপিআই, রেডডিট - সব একসাথে কল হবে
        tasks = [
            self.fetch_google_news(),            # লাইব্রেরি (ফ্রি)
            self.fetch_rss_news(),               # লাইব্রেরি (ফ্রি)
            self.fetch_news_from_cryptopanic(),  # API (যদি থাকে)
            self.fetch_reddit_discussions()      # API (যদি থাকে)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # ৩. রেজাল্ট মার্জ করা (Merge)
        combined_data = []
        for res in results:
            if isinstance(res, list):
                combined_data.extend(res)

        # ৪. ফলব্যাক (যদি সব ফেইল করে)
        if not combined_data:
            return [{
                "id": "m1", "source": "System", 
                "content": "No live news found. Checking sources...", 
                "sentiment": "Neutral", "sentiment_score": 0, 
                "timestamp": datetime.utcnow().isoformat(), "type": "news"
            }]

        # ৫. সর্টিং এবং ডুপ্লিকেট রিমুভ (অপশনাল)
        # টাইমস্ট্যাম্প অনুযায়ী নতুন থেকে পুরাতন সাজানো
        try:
            combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
            self.cache = combined_data[:80] # সেরা ৮০টি নিউজ রাখা
            self.last_fetch = datetime.utcnow()
        except:
            self.cache = combined_data[:60]
        
        return self.cache

    # Fear & Greed Index (আগের মতোই)
    async def fetch_fear_greed_index(self):
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
