import feedparser
from sqlalchemy.orm import Session
from app.models.education import EducationResource
from datetime import datetime
from dateutil import parser

RSS_FEEDS = {
    "CoinDesk": "https://feeds.feedburner.com/CoinDesk",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}

def fetch_crypto_news(db: Session):
    count = 0
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # Latest 5 news
                existing = db.query(EducationResource).filter(EducationResource.link == entry.link).first()
                if existing: continue

                # Category detection
                cat = "General"
                if "bitcoin" in entry.title.lower(): cat = "Bitcoin"
                elif "ethereum" in entry.title.lower(): cat = "Ethereum"
                elif "defi" in entry.title.lower(): cat = "DeFi"

                img = None
                if 'media_content' in entry: img = entry.media_content[0]['url']
                
                resource = EducationResource(
                    title=entry.title,
                    description=entry.summary[:300] + "..." if hasattr(entry, 'summary') else "",
                    type="News",
                    category=cat,
                    source=source,
                    link=entry.link,
                    image_url=img,
                    published_at=datetime.now()
                )
                db.add(resource)
                count += 1
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    db.commit()
    return count
