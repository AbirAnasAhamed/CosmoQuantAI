import feedparser
import asyncio
from datetime import datetime
from dateutil import parser
import logging
import urllib.parse
import requests
import praw # type: ignore
from app.core.config import settings

# Setup logger
logger = logging.getLogger(__name__)

class NewsScraper:
    COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"
    COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    CRYPTOPANIC_RSS = "https://cryptopanic.com/news/rss/"
    CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/?auth_token={token}&public=true"
    GOOGLE_NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}+when:{period}&hl={lang}-{country}&gl={country}&ceid={country}:{lang}"

    def __init__(self):
        self.reddit = None
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            try:
                self.reddit = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT
                )
                logger.info("Reddit PRAW initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit PRAW: {e}")
        else:
            logger.warning("Reddit credentials missing. Skipping Reddit integration.")

    def fetch_rss_feed(self, url: str, source_name: str) -> list[dict]:
        """
        Generic RSS fetcher and parser.
        Returns a list of dictionaries with normalized keys.
        """
        news_items = []
        try:
            # feedparser is blocking, but we will run this method in a thread via get_crypto_news
            feed = feedparser.parse(url)
            
            if feed.bozo:
                logger.warning(f"Feedparser reported issue with {source_name}: {feed.bozo_exception}")

            for entry in feed.entries[:10]: # Limit to 10 latest per source
                # Normalization
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                
                # Published Date Parsing
                pub_date = datetime.now()
                if 'published' in entry:
                    try:
                        pub_date = parser.parse(entry.published)
                    except:
                        pass
                elif 'updated' in entry:
                     try:
                        pub_date = parser.parse(entry.updated)
                     except:
                        pass
                
                # Ensure timezone aware if possible, or naive. 
                # For simplicity in this scraper, we keep the object but might need standardization later.

                item = {
                    'title': title,
                    'url': link,
                    'source': source_name,
                    'published_at': pub_date
                }
                news_items.append(item)
                
        except Exception as e:
            logger.error(f"Error fetching RSS from {source_name} ({url}): {e}")
            # Do NOT crash, just return what we have (or empty)
            
        return news_items

    def fetch_reddit_posts(self, limit: int = 10) -> list[dict]:
        """
        Fetches top discussions from r/Cryptocurrency and r/Bitcoin using PRAW.
        """
        if not self.reddit:
            return []

        reddit_news = []
        subreddits = ['Cryptocurrency', 'Bitcoin']

        for sub_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                # Fetch hot posts
                for post in subreddit.hot(limit=limit):
                    if post.stickied:
                        continue
                        
                    # Normalize data
                    item = {
                        'title': post.title,
                        'url': post.url,
                        'source': f'Reddit (r/{sub_name})',
                        'published_at': datetime.fromtimestamp(post.created_utc)
                    }
                    reddit_news.append(item)
            except Exception as e:
                logger.error(f"Error fetching from r/{sub_name}: {e}")

        return reddit_news

    def fetch_google_news(self, query="Cryptocurrency", period="1d") -> list[dict]:
        """
        Fetches news from Google News RSS.
        """
        url = self.GOOGLE_NEWS_RSS_TEMPLATE.format(
            query=urllib.parse.quote(query),
            period=period,
            lang="en",
            country="US"
        )
        # Re-use the generic fetcher, though Google News structure is standard RSS mostly.
        return self.fetch_rss_feed(url, "Google News")

    def fetch_cryptopanic_api(self) -> list[dict]:
        """
        Fetches news from CryptoPanic API.
        """
        api_key = settings.CRYPTOPANIC_API_KEY
        if not api_key:
            logger.warning("CryptoPanic API key not found. Skipping API fetch.")
            return []

        url = self.CRYPTOPANIC_API_URL.format(token=api_key)
        news_items = []
        
        # Add basic User-Agent to avoid Cloudflare blocking API calls
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"CryptoPanic API returned status {response.status_code}: {response.text[:200]}")
                return []
            
            try:
                data = response.json()
            except ValueError: # requests.json() raises ValueError (or JSONDecodeError)
                logger.error(f"CryptoPanic API returned non-JSON response (likely Cloudflare blocking): {response.text[:200]}")
                return []
            
            if 'results' in data:
                for post in data['results']:
                    # Normalize
                    title = post.get('title', 'No Title')
                    # CryptoPanic returns 'url' which is the source url (usually).
                    # Sometimes it might be a bit different, but 'url' is best bet.
                    link = post.get('url', '') 
                    
                    published_at = datetime.now()
                    if 'published_at' in post:
                        try:
                            published_at = parser.parse(post['published_at'])
                        except:
                            pass
                            
                    item = {
                        'title': title,
                        'url': link,
                        'source': 'CryptoPanic',
                        'published_at': published_at
                    }
                    news_items.append(item)
            else:
                logger.warning(f"CryptoPanic API returned unexpected format: {list(data.keys())}")

        except Exception as e:
            logger.error(f"Error fetching from CryptoPanic API: {e}")
            
        return news_items

    async def get_crypto_news(self) -> list[dict]:
        """
        Aggregates news from all sources asynchronously.
        """
        tasks = []
        
        # Define tasks for each source
        # We verify feedparser is IO bound but blocking, so we use to_thread
        
        # 1. Google News
        tasks.append(asyncio.to_thread(self.fetch_google_news))
        
        # 2. CoinTelegraph
        tasks.append(asyncio.to_thread(self.fetch_rss_feed, self.COINTELEGRAPH_RSS, "CoinTelegraph"))
        
        # 3. CoinDesk
        tasks.append(asyncio.to_thread(self.fetch_rss_feed, self.COINDESK_RSS, "CoinDesk"))
        
        # 4. CryptoPanic
        if settings.CRYPTOPANIC_API_KEY:
             tasks.append(asyncio.to_thread(self.fetch_cryptopanic_api))
        else:
             tasks.append(asyncio.to_thread(self.fetch_rss_feed, self.CRYPTOPANIC_RSS, "CryptoPanic"))
        
        # 5. Reddit
        tasks.append(asyncio.to_thread(self.fetch_reddit_posts, 10))

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)
            else:
                logger.error(f"Task failed with error: {res}")

        # Sort by published_at descending (newest first)
        # Handle cases where published_at might be None or invalid if something slipped through
        all_news.sort(key=lambda x: x.get('published_at') or datetime.min, reverse=True)
        
        return all_news

# Basic usage for testing (if run directly)
if __name__ == "__main__":
    scraper = NewsScraper()
    news = asyncio.run(scraper.get_crypto_news())
    print(f"Fetched {len(news)} items.")
    for n in news[:5]:
        print(f"[{n['source']}] {n['title']} ({n['published_at']})")
