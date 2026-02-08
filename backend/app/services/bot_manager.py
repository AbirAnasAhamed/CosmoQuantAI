
import asyncio
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app import models
from app.db.session import SessionLocal
from app.services.async_bot_instance import AsyncBotInstance
from app.services.shared_stream import SharedMarketStream
import logging

logger = logging.getLogger(__name__)

class BotManager:
    """
    Singleton Manager for all running bots.
    Replaces Celery for bot execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
            cls._instance.active_bots = {} # {bot_id: AsyncBotInstance}
            cls._instance.streams = {}     # {stream_key: SharedMarketStream}
            cls._instance.is_running = False
        return cls._instance

    def start_service(self):
        """Called on app startup"""
        self.is_running = True
        logger.info("✅ BotManager Service Started")

    async def stop_service(self):
        """Called on app shutdown"""
        self.is_running = False
        logger.info("🛑 Stopping All Bots...")
        
        # Stop all bots
        for bot_id in list(self.active_bots.keys()):
            await self.stop_bot(bot_id)
            
        # Stop all streams
        for stream in self.streams.values():
            await stream.stop()
            
        self.active_bots.clear()
        self.streams.clear()

    async def start_bot(self, bot_id: int, db: Session = None):
        """Start a specific bot."""
        if bot_id in self.active_bots:
            return {"status": "error", "message": "Bot already running"}

        logger.info(f"🔄 Starting Bot {bot_id}...")
        
        # Create new DB session if not provided
        local_db = db or SessionLocal()
        
        try:
            bot = local_db.query(models.Bot).filter(models.Bot.id == bot_id).first()
            if not bot:
                return {"status": "error", "message": "Bot not found"}

            # 1. Create Instance
            bot_instance = AsyncBotInstance(bot, local_db)
            
            # 2. Get/Create Shared Stream
            stream_key = f"{bot.exchange}_{bot.market}_{bot.timeframe}"
            if stream_key not in self.streams:
                self.streams[stream_key] = SharedMarketStream(
                    bot.exchange or 'binance', 
                    bot.market, 
                    bot.timeframe
                )
            
            stream = self.streams[stream_key]
            
            # 3. Link Bot to Stream
            await stream.subscribe(bot_instance)
            
            # 4. Start Bot Internal Tasks (User Stream, etc.)
            await bot_instance.start()
            
            self.active_bots[bot_id] = bot_instance
            
            # Update DB Status
            bot.status = "active"
            local_db.commit()
            
            return {"status": "success", "message": f"Bot {bot_id} started"}

        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if not db: local_db.close() # Close if we created it

    async def stop_bot(self, bot_id: int, db: Session = None):
        """Stop a specific bot."""
        # 1. Prepare DB Session
        local_db = db or SessionLocal()
        
        try:
            # 2. Stop In-Memory Instance if exists
            if bot_id in self.active_bots:
                logger.info(f"🛑 Stopping Bot {bot_id}...")
                bot_instance = self.active_bots[bot_id]
                
                # Unsubscribe from Stream
                stream_key = f"{bot_instance.bot.exchange}_{bot_instance.symbol}_{bot_instance.timeframe}"
                if stream_key in self.streams:
                    stream = self.streams[stream_key]
                    await stream.unsubscribe(bot_instance)
                    
                    # Cleanup unused streams
                    if not stream.subscribers:
                        await stream.stop()
                        del self.streams[stream_key]

                # Stop Bot Internals
                await bot_instance.stop()
                del self.active_bots[bot_id]
            else:
                logger.warning(f"⚠️ Bot {bot_id} not found in memory. Checking DB for zombie state...")

            # 3. Update DB Status (Always, to ensure consistency)
            bot = local_db.query(models.Bot).filter(models.Bot.id == bot_id).first()
            if bot:
                if bot.status == "active":
                    logger.info(f"🧹 Cleaning up zombie bot {bot_id} (active in DB -> inactive)")
                bot.status = "inactive"
                local_db.commit()

            return {"status": "success", "message": f"Bot {bot_id} stopped (or was already stopped)"}

        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if not db: local_db.close()
