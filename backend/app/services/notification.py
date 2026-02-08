import logging
import telegram
from sqlalchemy.orm import Session
from app.models.notification import NotificationSettings

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def send_message(db: Session, user_id: int, message: str):
        """
        Sends a Telegram message to the user if notifications are enabled.
        """
        try:
            settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()
            
            if not settings:
                logger.info(f"Notification settings not found for user {user_id}")
                return

            if not settings.is_enabled:
                logger.info(f"Notifications disabled for user {user_id}")
                return

            if not settings.telegram_bot_token or not settings.telegram_chat_id:
                logger.warning(f"Incomplete notification settings for user {user_id}")
                return

            bot = telegram.Bot(token=settings.telegram_bot_token)
            await bot.send_message(chat_id=settings.telegram_chat_id, text=message)
            logger.info(f"Notification sent to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")

    @staticmethod
    async def force_send_message(bot_token: str, chat_id: str, message: str):
        """
        Sends a test message using provided credentials.
        """
        try:
            bot = telegram.Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=message)
            return True, "Message sent successfully"
        except Exception as e:
            return False, str(e)
