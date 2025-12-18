import httpx
import logging
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.api_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.api_key = settings.CRYPTOPANIC_API_KEY if hasattr(settings, 'CRYPTOPANIC_API_KEY') else None
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300  # 5 minutes

    async def fetch_news(self):
        # Return cached news if valid
        if self.cache and self.last_fetch and (datetime.utcnow() - self.last_fetch).total_seconds() < self.cache_duration:
            return self.cache

        if not self.api_key:
            # Return Mock Data if no API key
            return self._get_mock_news()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url, 
                    params={
                        "auth_token": self.api_key,
                        "public": "true",
                        "filter": "important" 
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Transform data
                news_items = []
                for item in data.get('results', []):
                    news_items.append({
                        "id": item.get('id'),
                        "source": item.get('source', {}).get('title', 'Unknown'),
                        "text": item.get('title'),
                        "url": item.get('url'),
                        "sentiment": "neutral", # API doesn't provide this free usually, can add analysis later
                        "published_at": item.get('published_at')
                    })
                
                self.cache = news_items
                self.last_fetch = datetime.utcnow()
                return self.cache

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return self.cache or self._get_mock_news()

    def _get_mock_news(self):
        return [
            {"id": 1, "source": "CoinDesk", "text": "Bitcoin Reclaims $68k Support Level as Volume Spikes", "sentiment": "positive"},
            {"id": 2, "source": "CoinTelegraph", "text": "SEC Delays Decision on Ethereum ETF Applications", "sentiment": "negative"},
            {"id": 3, "source": "Decrypt", "text": "Solana Network Hits New Daily Transaction Record", "sentiment": "positive"},
            {"id": 4, "source": "TheBlock", "text": "Binance US Market Share Dips Amidst Regulatory Pressure", "sentiment": "negative"},
            {"id": 5, "source": "Bloomberg", "text": "Crypto Markets Stabilize Ahead of FOMC Meeting", "sentiment": "neutral"},
        ]

news_service = NewsService()
