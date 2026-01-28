from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cosmoquant",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "fetch-news-every-10-mins": {
            "task": "app.tasks.fetch_market_news",
            "schedule": 600.0,  # 10 minutes in seconds
        },
    }
)

# Auto-discover tasks in packages
celery_app.autodiscover_tasks(["app.tasks"])
