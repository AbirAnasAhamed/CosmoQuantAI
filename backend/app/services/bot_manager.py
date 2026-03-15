
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

            if bot.strategy == "wall_hunter":
                from app.strategies.wall_hunter_bot import WallHunterBot
                from app.strategies.wall_hunter_futures import WallHunterFuturesStrategy
                from app.services.ccxt_service import ccxt_service
                from app.models import ApiKey
                
                config = {
                    "exchange": bot.exchange or "binance",
                    "symbol": bot.market,
                    "is_paper_trading": bot.is_paper_trading,
                }
                if bot.config:
                    config.update(bot.config)
                    
                trading_mode = config.get('trading_mode', 'spot')
                
                if trading_mode == 'futures':
                    # সম্পূর্ণ নতুন এবং আলাদা ফিউচার লজিক রান হবে
                    bot_instance = WallHunterFuturesStrategy(bot, ccxt_service)
                    logger.info(f"Starting Wall Hunter in FUTURES mode for {bot.market}")
                else:
                    # এক্সিস্টিং স্পট বট রান হবে
                    bot_instance = WallHunterBot(bot.id, config, local_db, owner_id=bot.owner_id)
                    logger.info(f"Starting Wall Hunter in SPOT mode for {bot.market}")

                bot_instance.bot = bot # keep reference
                
                api_key_record = None
                if not bot.is_paper_trading and bot.api_key_id:
                    api_key_record = local_db.query(ApiKey).filter_by(id=bot.api_key_id).first()
                    
                # স্ট্র্যাটেজি স্টার্ট করা
                if hasattr(bot_instance, 'start') and callable(getattr(bot_instance, 'start')):
                    await bot_instance.start(api_key_record)
                
                self.active_bots[bot_id] = bot_instance
            else:
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
            
            trading_mode = bot.config.get('trading_mode', 'spot').upper()
            logger.info("="*50)
            logger.info(f"🚀 BOT ACTIVATED: ID {bot_id} | {bot.market} on {bot.exchange}")
            logger.info(f"🛠️  Trading Mode: {trading_mode}")
            
            from app.services.notification import NotificationService
            msg_lines = [
                f"🚀 *BOT ACTIVATED: ID {bot_id}*",
                f"💎 Pair: {bot.market} | {bot.exchange}",
                f"🛠️ Mode: {trading_mode}"
            ]
            
            if bot.strategy == "wall_hunter":
                logger.info(f"📈 Strategy: WallHunter Level 2 Sniper")
                msg_lines.append("📈 Strategy: WallHunter Level 2 Sniper")
                
                # Futures Specific Info
                if trading_mode == 'FUTURES':
                    leverage = bot.config.get('leverage', 10)
                    margin = bot.config.get('margin_mode', 'cross').upper()
                    direction = bot.config.get('position_direction', 'auto').upper()
                    
                    logger.info(f"⚙️  Futures: {leverage}x | {margin} Margin | {direction} Dir")
                    msg_lines.append(f"⚙️ Futures: {leverage}x | {margin} | {direction}")
                    
                    if bot.config.get('liquidation_safety_pct'):
                        dist = bot.config.get('liquidation_safety_pct')
                        logger.info(f"📐 Liq Safety Distance: {dist}%")
                        msg_lines.append(f"📐 Liq Distance: {dist}%")

                    if bot.config.get('enable_ob_imbalance'):
                        ratio = bot.config.get('ob_imbalance_ratio', 1.5)
                        logger.info(f"📊 Heatmap Imbalance: {ratio}x")
                        msg_lines.append(f"📊 Heatmap Imbalance: {ratio}x")

                logger.info(f"🎯 Target Spread: {bot.config.get('target_spread', 0)}")
                msg_lines.append(f"🎯 Target Spread: {bot.config.get('target_spread', 0)}")
                
                # Trigger Modes
                triggers = []
                if bot.config.get('enable_wall_trigger', True):
                    triggers.append(f"Wall ({bot.config.get('vol_threshold', 0)})")
                if bot.config.get('enable_liq_trigger'):
                    triggers.append(f"Liq Event ({'BTC' if bot.config.get('follow_btc_liq') else 'Local'})")
                
                if triggers:
                    trigger_str = " | ".join(triggers)
                    logger.info(f"🔔 Triggers: {trigger_str}")
                    msg_lines.append(f"🔔 Triggers: {trigger_str}")
                
                # Advanced Settings
                adv = []
                if bot.config.get('vpvr_enabled'):
                    adv.append(f"VPVR ({bot.config.get('vpvr_tolerance', 0.2)}%)")
                if bot.config.get('atr_sl_enabled'):
                    adv.append(f"ATR (P:{bot.config.get('atr_period', 14)})")
                if bot.config.get('partial_tp_pct', 0) > 0:
                    adv.append(f"Scale-Out ({bot.config.get('partial_tp_pct')}%)")
                if bot.config.get('enable_micro_scalp'):
                    adv.append(f"Micro-Scalp")
                
                if adv:
                    adv_str = " | ".join(adv)
                    logger.info(f"⚡ Advanced: {adv_str}")
                    msg_lines.append(f"⚡ Advanced: {adv_str}")

                logger.info(f"⚖️ Risk Pct: {bot.config.get('risk_pct', 0)}% | TSL: {bot.config.get('trailing_stop', 0)}%")
                msg_lines.append(f"⚖️ Risk: {bot.config.get('risk_pct', 0)}% | TSL: {bot.config.get('trailing_stop', 0)}%")
                
                logger.info(f"💰 Trade Amount: {bot.config.get('amount_per_trade', 0)} (Quote Asset)")
                msg_lines.append(f"💰 Amount: {bot.config.get('amount_per_trade', 0)}")
                
                logger.info(f"📋 Sell Order: {bot.config.get('sell_order_type', 'market').upper()}")
                msg_lines.append(f"📋 Order Type: {bot.config.get('sell_order_type', 'market').upper()}")
            else:
                logger.info(f"📈 Strategy: {bot.strategy} | Timeframe: {bot.timeframe}")
                msg_lines.append(f"📈 Strategy: {bot.strategy} | Timeframe: {bot.timeframe}")
                
                logger.info(f"💰 Trade Value: {bot.trade_value}")
                msg_lines.append(f"💰 Trade Value: {bot.trade_value}")
                
            logger.info("="*50)
            
            # Send Telegram Notification explicitly for bot startup
            if bot.owner_id:
                asyncio.create_task(NotificationService.send_message(local_db, bot.owner_id, "\n".join(msg_lines)))
            
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
                
                if isinstance(bot_instance, AsyncBotInstance):
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

    async def update_live_bot(self, bot_id: int, new_config: dict):
        """Update a running bot's configuration without stopping it."""
        if bot_id not in self.active_bots:
            return {"status": "error", "message": "Bot is not currently active in memory"}
            
        bot_instance = self.active_bots[bot_id]
        
        # Check if the active bot supports dynamic config updates (e.g. WallHunterBot)
        if hasattr(bot_instance, "update_config") and callable(bot_instance.update_config):
            try:
                bot_instance.update_config(new_config)
                return {"status": "success", "message": f"Successfully updated live configuration for bot {bot_id}"}
            except Exception as e:
                logger.error(f"Error updating live bot {bot_id}: {e}")
                return {"status": "error", "message": f"Failed to apply live update: {str(e)}"}
        else:
            return {"status": "error", "message": f"Bot strategy does not support live updates"}
            
    async def emergency_sell_bot(self, bot_id: int, sell_type: str):
        """Emergency sell for a running bot's active position."""
        if bot_id not in self.active_bots:
            return {"status": "error", "message": "Bot is not currently active in memory"}
            
        bot_instance = self.active_bots[bot_id]
        
        if hasattr(bot_instance, "emergency_sell") and callable(bot_instance.emergency_sell):
            try:
                await bot_instance.emergency_sell(sell_type)
                return {"status": "success", "message": f"Emergency {sell_type} sell triggered for bot {bot_id}"}
            except Exception as e:
                logger.error(f"Error triggering emergency sell for bot {bot_id}: {e}")
                return {"status": "error", "message": f"Failed to execute emergency sell: {str(e)}"}
        else:
            return {"status": "error", "message": f"Bot strategy does not support emergency sell"}
