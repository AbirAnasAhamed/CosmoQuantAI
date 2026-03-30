import asyncio
import logging
import time
from typing import Dict, Any, Optional
import ccxt.pro as ccxt
import json
from app.utils import get_redis_client
from app.strategies.order_block_bot import OrderBlockExecutionEngine
from app.services.notification import NotificationService
from app.db.session import SessionLocal
from app.strategies.helpers.absorption_tracker import AbsorptionTracker
from app.services.market_depth_service import market_depth_service
from app.strategies.helpers.trend_finder import AdaptiveTrendFinder

try:
    from app.core.security import decrypt_key
except ImportError:
    # Forward compatibility if it doesn't exist
    def decrypt_key(key):
        return key


class WallHunterLogger:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        import logging
        self._logger = logging.getLogger("WallHunter" + str(bot_id))

    def _push_redis(self, log_type: str, message: str):
        try:
            import datetime, json, redis
            from app.core.config import settings
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = {"time": timestamp, "type": log_type, "message": str(message)}
            stream_payload = {"channel": f"logs_{self.bot_id}", "data": log_entry}
            r.publish("bot_logs", json.dumps(stream_payload))
            r.publish(f"bot_logs:{self.bot_id}", json.dumps(log_entry))
            list_key = f"bot_logs_list:{self.bot_id}"
            r.rpush(list_key, json.dumps(log_entry))
            r.ltrim(list_key, -50, -1)
        except Exception:
            pass

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
        self._push_redis("INFO", (str(msg) % args) if args else str(msg))

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
        self._push_redis("WARNING", (str(msg) % args) if args else str(msg))

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
        self._push_redis("ERROR", (str(msg) % args) if args else str(msg))
        
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)


logger = logging.getLogger(__name__)

class WallHunterBot:
    def __init__(self, bot_id: int, config: Dict[str, Any], db_session=None, owner_id: int = None):
        self.bot_id = bot_id
        self.owner_id = owner_id
        self.config = config
        self.symbol = config.get("symbol", "DOGE/USDT")
        self.exchange_id = config.get("exchange", "binance").lower()
        self.is_paper_trading = config.get("is_paper_trading", True)
        self.logger = WallHunterLogger(self.bot_id)
        
        # Strategy Params
        self.vol_threshold = config.get("vol_threshold", 500000)
        self.target_spread = config.get("target_spread", 0.0002)
        self.initial_risk_pct = config.get("risk_pct", 0.5)
        self.tsl_pct = config.get("trailing_stop", 0.2)
        self.sell_order_type = config.get("sell_order_type", "market")
        self.trading_mode = config.get("trading_mode", "spot").lower()
        self.strategy_mode = config.get("strategy_mode", "long").lower()
        
        # --- NEW FEATURES: Partial TP & Break-Even SL ---
        self.partial_tp_pct = config.get("partial_tp_pct", 50.0) # TP1 এ কত পার্সেন্ট সেল করবে
        self.partial_tp_trigger_pct = config.get("partial_tp_trigger_pct", 0.0)
        self.sl_breakeven_trigger_pct = config.get("sl_breakeven_trigger_pct", 0.0)
        self.sl_breakeven_target_pct = config.get("sl_breakeven_target_pct", 0.0)
        
        # --- NEW FEATURES: VPVR Confirmation ---
        self.vpvr_enabled = config.get("vpvr_enabled", False)
        self.vpvr_tolerance = config.get("vpvr_tolerance", 0.2)
        self.top_hvns = []
        
        # --- NEW FEATURES: Dynamic ATR Stop-Loss ---
        self.atr_sl_enabled = config.get("atr_sl_enabled", False)
        self.atr_period = config.get("atr_period", 14)
        self.atr_multiplier = config.get("atr_multiplier", 2.0)
        self.current_atr = 0.0

        # --- NEW FEATURES: Liquidation & Scalp ---
        self.enable_wall_trigger = config.get("enable_wall_trigger", True)
        self.max_wall_distance_pct = config.get("max_wall_distance_pct", 1.0)
        self.enable_liq_trigger = config.get("enable_liq_trigger", False)
        self.liq_threshold = config.get("liq_threshold", 50000.0)
        self.liq_target_side = config.get("liq_target_side", "auto").lower()
        self.enable_micro_scalp = config.get("enable_micro_scalp", False)
        self.micro_scalp_profit_ticks = config.get("micro_scalp_profit_ticks", 2)
        self.micro_scalp_min_wall = config.get("micro_scalp_min_wall", 100000.0)
        
        # --- SMART LIQUIDATION FEATURES ---
        from collections import deque
        self.enable_liq_cascade = config.get("enable_liq_cascade", False)
        self.liq_cascade_window = config.get("liq_cascade_window", 5) # in seconds
        self.liq_history = deque() # Stores tuples: (timestamp, amount)
        
        self.enable_dynamic_liq = config.get("enable_dynamic_liq", False)
        self.dynamic_liq_multiplier = config.get("dynamic_liq_multiplier", 1.0)
        
        self.enable_ob_imbalance = config.get("enable_ob_imbalance", False)
        self.ob_imbalance_ratio = config.get("ob_imbalance_ratio", 1.5)

        # --- BRAND NEW: BTC Liquidation Follower ---
        self.follow_btc_liq = config.get("follow_btc_liq", False)
        self.btc_liq_threshold = config.get("btc_liq_threshold", 500000.0)

        # --- NEW FEATURES: Spoofing Detection ---
        self.min_wall_lifetime = config.get("min_wall_lifetime", 3.0) # ওয়ালকে অন্তত কত সেকেন্ড টিকে থাকতে হবে
        self.tracked_walls = {} # ওয়ালগুলোকে ট্র্যাক করার জন্য ডিকশনারি

        # --- NEW FEATURES: CVD Absorption Confirmation ---
        self.enable_absorption = config.get("enable_absorption", False)
        self.absorption_threshold = config.get("absorption_threshold", 50000.0)
        self.absorption_window = config.get("absorption_window", 10.0)
        self.absorption_tracker = AbsorptionTracker(
            window_seconds=self.absorption_window, 
            threshold=self.absorption_threshold
        )
        
        # --- BRAND NEW: BTC Correlation Filter ---
        self.enable_btc_correlation = config.get("enable_btc_correlation", False)
        self.btc_correlation_threshold = config.get("btc_correlation_threshold", 0.7)
        self.btc_time_window = config.get("btc_time_window", 15)
        self.btc_min_move_pct = config.get("btc_min_move_pct", 0.1)
        self.btc_correlation_tracker = None
        
        # --- NEW: Adaptive Trend Filter ---
        self.enable_trend_filter = config.get("enable_trend_filter", False)
        self.trend_filter_lookback = config.get("trend_filter_lookback", 200)
        self.trend_filter_threshold = config.get("trend_filter_threshold", "Strong")
        self.trend_finder = AdaptiveTrendFinder(
            lookback=self.trend_filter_lookback, 
            threshold=self.trend_filter_threshold
        ) if self.enable_trend_filter else None
        
        # --- NEW: Custom Buy Order Type & Buffer ---
        self.buy_order_type = config.get("buy_order_type", "market")
        self.limit_buffer = config.get("limit_buffer", 1.0)
        self.tsl_activation_pct = config.get("tsl_activation_pct", 0.0)
        # ----------------------------------------
        
        self.engine = OrderBlockExecutionEngine(config)
        self.active_pos = None
        self.highest_price = 0.0
        self.running = False
        self._heartbeat_task = None
        self.redis = get_redis_client()
        self.total_executed_orders = 0
        self.total_realized_pnl = 0.0
        self.total_wins = 0
        self.total_losses = 0

    def update_config(self, new_config: dict):
        """Update strategy parameters dynamically without stopping the bot."""
        self.logger.info(f"🔄 [WallHunter {self.bot_id}] Live config update requested: {new_config}")
        
        if "trading_mode" in new_config:
            self.trading_mode = new_config["trading_mode"].lower()
            
        if "strategy_mode" in new_config:
            self.strategy_mode = new_config["strategy_mode"].lower()
        
        # Keep track of old values for logging
        updates = []
        
        if "vol_threshold" in new_config and new_config["vol_threshold"] != self.vol_threshold:
            updates.append(f"Volume Threshold: {self.vol_threshold} -> {new_config['vol_threshold']}")
            self.vol_threshold = new_config.get("vol_threshold")
            
        if "target_spread" in new_config and new_config["target_spread"] != self.target_spread:
            updates.append(f"Target Spread: {self.target_spread} -> {new_config['target_spread']}")
            self.target_spread = new_config.get("target_spread")
            
        if "trailing_stop" in new_config and new_config["trailing_stop"] != self.tsl_pct:
            updates.append(f"Trailing SL: {self.tsl_pct}% -> {new_config['trailing_stop']}%")
            self.tsl_pct = new_config.get("trailing_stop")
            
        if "tsl_activation_pct" in new_config and new_config["tsl_activation_pct"] != getattr(self, "tsl_activation_pct", 0.0):
            updates.append(f"TSL Activation: {getattr(self, 'tsl_activation_pct', 0.0)}% -> {new_config['tsl_activation_pct']}%")
            self.tsl_activation_pct = new_config.get("tsl_activation_pct")
            
        if "risk_pct" in new_config and new_config["risk_pct"] != self.initial_risk_pct:
            updates.append(f"Risk Pct: {self.initial_risk_pct}% -> {new_config['risk_pct']}%")
            self.initial_risk_pct = new_config.get("risk_pct")
            
        if "amount_per_trade" in new_config and self.engine and hasattr(self.engine, 'config'):
            old_amount = self.engine.config.get("amount_per_trade")
            if new_config["amount_per_trade"] != old_amount:
                updates.append(f"Trade Amount: {old_amount} -> {new_config['amount_per_trade']}")
                self.engine.config["amount_per_trade"] = new_config["amount_per_trade"]
                
        if "min_wall_lifetime" in new_config and new_config["min_wall_lifetime"] != self.min_wall_lifetime:
            updates.append(f"Spoof Detect (s): {self.min_wall_lifetime} -> {new_config['min_wall_lifetime']}")
            self.min_wall_lifetime = new_config.get("min_wall_lifetime")
            
        if "partial_tp_pct" in new_config and new_config["partial_tp_pct"] != self.partial_tp_pct:
            updates.append(f"Partial TP: {self.partial_tp_pct}% -> {new_config['partial_tp_pct']}%")
            self.partial_tp_pct = new_config.get("partial_tp_pct")
            
        if "sl_breakeven_trigger_pct" in new_config and new_config["sl_breakeven_trigger_pct"] != getattr(self, "sl_breakeven_trigger_pct", 0.0):
            old_trigger = getattr(self, "sl_breakeven_trigger_pct", 0.0)
            updates.append(f"Breakeven Trigger: {old_trigger}% -> {new_config['sl_breakeven_trigger_pct']}%")
            self.sl_breakeven_trigger_pct = new_config.get("sl_breakeven_trigger_pct")
            
        if "sl_breakeven_target_pct" in new_config and new_config["sl_breakeven_target_pct"] != getattr(self, "sl_breakeven_target_pct", 0.0):
            old_target = getattr(self, "sl_breakeven_target_pct", 0.0)
            updates.append(f"Breakeven Target: {old_target}% -> {new_config['sl_breakeven_target_pct']}%")
            self.sl_breakeven_target_pct = new_config.get("sl_breakeven_target_pct")
            
        if "vpvr_enabled" in new_config and new_config["vpvr_enabled"] != self.vpvr_enabled:
            status = "Enabled" if new_config["vpvr_enabled"] else "Disabled"
            updates.append(f"VPVR Confirmation: {status}")
            self.vpvr_enabled = new_config.get("vpvr_enabled")
            
        if "vpvr_tolerance" in new_config and new_config["vpvr_tolerance"] != self.vpvr_tolerance:
            updates.append(f"VPVR Tolerance: {self.vpvr_tolerance}% -> {new_config['vpvr_tolerance']}%")
            self.vpvr_tolerance = new_config.get("vpvr_tolerance")

        if "atr_sl_enabled" in new_config and new_config["atr_sl_enabled"] != self.atr_sl_enabled:
            status = "Enabled" if new_config["atr_sl_enabled"] else "Disabled"
            updates.append(f"ATR Dynamic SL: {status}")
            self.atr_sl_enabled = new_config.get("atr_sl_enabled")
            
        if "atr_period" in new_config and new_config["atr_period"] != self.atr_period:
            updates.append(f"ATR Period: {self.atr_period} -> {new_config['atr_period']}")
            self.atr_period = new_config.get("atr_period")
            
        if "atr_multiplier" in new_config and new_config["atr_multiplier"] != self.atr_multiplier:
            updates.append(f"ATR Multiplier: {self.atr_multiplier} -> {new_config['atr_multiplier']}")
            self.atr_multiplier = new_config.get("atr_multiplier")
            
        if "enable_wall_trigger" in new_config and new_config["enable_wall_trigger"] != self.enable_wall_trigger:
            status = "ON" if new_config["enable_wall_trigger"] else "OFF"
            updates.append(f"Wall Trigger: {status}")
            self.enable_wall_trigger = new_config.get("enable_wall_trigger")
            
        if "max_wall_distance_pct" in new_config and new_config["max_wall_distance_pct"] != self.max_wall_distance_pct:
            updates.append(f"Max Wall Distance %: {self.max_wall_distance_pct} -> {new_config['max_wall_distance_pct']}")
            self.max_wall_distance_pct = new_config.get("max_wall_distance_pct")
            
        if "enable_liq_trigger" in new_config and new_config["enable_liq_trigger"] != self.enable_liq_trigger:
            status = "ON" if new_config["enable_liq_trigger"] else "OFF"
            updates.append(f"Liquidation Trigger: {status}")
            self.enable_liq_trigger = new_config.get("enable_liq_trigger")
            
        if "liq_threshold" in new_config and new_config["liq_threshold"] != self.liq_threshold:
            updates.append(f"{self.symbol} Liq Threshold: {self.liq_threshold} -> {new_config['liq_threshold']}")
            self.liq_threshold = new_config.get("liq_threshold")
            
        if "liq_target_side" in new_config and new_config["liq_target_side"] != getattr(self, 'liq_target_side', 'auto'):
            updates.append(f"Liq Target Side: {getattr(self, 'liq_target_side', 'auto')} -> {new_config['liq_target_side']}")
            self.liq_target_side = new_config.get("liq_target_side").lower()
            
        if "enable_micro_scalp" in new_config and new_config["enable_micro_scalp"] != self.enable_micro_scalp:
            status = "ON" if new_config["enable_micro_scalp"] else "OFF"
            updates.append(f"Micro-Scalp: {status}")
            self.enable_micro_scalp = new_config.get("enable_micro_scalp")
            
        if "micro_scalp_profit_ticks" in new_config and new_config["micro_scalp_profit_ticks"] != self.micro_scalp_profit_ticks:
            updates.append(f"Micro-Scalp Ticks: {self.micro_scalp_profit_ticks} -> {new_config['micro_scalp_profit_ticks']}")
            self.micro_scalp_profit_ticks = new_config.get("micro_scalp_profit_ticks")
            
        if "micro_scalp_min_wall" in new_config and new_config["micro_scalp_min_wall"] != self.micro_scalp_min_wall:
            updates.append(f"Micro-Scalp Min Wall: {self.micro_scalp_min_wall} -> {new_config['micro_scalp_min_wall']}")
            self.micro_scalp_min_wall = new_config.get("micro_scalp_min_wall")
            
        if "follow_btc_liq" in new_config and new_config["follow_btc_liq"] != self.follow_btc_liq:
            status = "ON" if new_config["follow_btc_liq"] else "OFF"
            updates.append(f"Follow BTC Liq: {status}")
            self.follow_btc_liq = new_config.get("follow_btc_liq")
            
        if "btc_liq_threshold" in new_config and new_config["btc_liq_threshold"] != self.btc_liq_threshold:
            updates.append(f"BTC Liq Threshold: {self.btc_liq_threshold} -> {new_config['btc_liq_threshold']}")
            self.btc_liq_threshold = new_config.get("btc_liq_threshold")

        if "enable_absorption" in new_config and new_config["enable_absorption"] != self.enable_absorption:
            status = "ON" if new_config["enable_absorption"] else "OFF"
            updates.append(f"CVD Absorption: {status}")
            self.enable_absorption = new_config.get("enable_absorption")

        if "absorption_threshold" in new_config and new_config["absorption_threshold"] != self.absorption_threshold:
            updates.append(f"Absorption Threshold: ${self.absorption_threshold} -> ${new_config['absorption_threshold']}")
            self.absorption_threshold = new_config.get("absorption_threshold")
            self.absorption_tracker.update_params(threshold=self.absorption_threshold)

        if "absorption_window" in new_config and new_config["absorption_window"] != self.absorption_window:
            updates.append(f"Absorption Window: {self.absorption_window}s -> {new_config['absorption_window']}s")
            self.absorption_window = new_config.get("absorption_window")
            self.absorption_tracker.update_params(window_seconds=self.absorption_window)
            
        if "enable_btc_correlation" in new_config and new_config["enable_btc_correlation"] != self.enable_btc_correlation:
            status = "ON" if new_config["enable_btc_correlation"] else "OFF"
            updates.append(f"BTC Correlation Filter: {status}")
            self.enable_btc_correlation = new_config.get("enable_btc_correlation")
            if self.enable_btc_correlation and self.btc_correlation_tracker:
                asyncio.create_task(self.btc_correlation_tracker.start())
            elif not self.enable_btc_correlation and self.btc_correlation_tracker:
                asyncio.create_task(self.btc_correlation_tracker.stop())

        if "btc_correlation_threshold" in new_config and new_config["btc_correlation_threshold"] != self.btc_correlation_threshold:
            updates.append(f"BTC Corr Threshold: {self.btc_correlation_threshold} -> {new_config['btc_correlation_threshold']}")
            self.btc_correlation_threshold = new_config.get("btc_correlation_threshold")
            if self.btc_correlation_tracker:
                self.btc_correlation_tracker.update_params(threshold=self.btc_correlation_threshold)

        if "btc_time_window" in new_config and new_config["btc_time_window"] != self.btc_time_window:
            updates.append(f"BTC Time Window: {self.btc_time_window}m -> {new_config['btc_time_window']}m")
            self.btc_time_window = new_config.get("btc_time_window")
            if self.btc_correlation_tracker:
                self.btc_correlation_tracker.update_params(window_minutes=self.btc_time_window)

        if "btc_min_move_pct" in new_config and new_config["btc_min_move_pct"] != self.btc_min_move_pct:
            updates.append(f"BTC Min Move %: {self.btc_min_move_pct}% -> {new_config['btc_min_move_pct']}%")
            self.btc_min_move_pct = new_config.get("btc_min_move_pct")
            if self.btc_correlation_tracker:
                self.btc_correlation_tracker.update_params(min_move_pct=self.btc_min_move_pct)
                
        if "enable_trend_filter" in new_config and new_config["enable_trend_filter"] != self.enable_trend_filter:
            status = "ON" if new_config["enable_trend_filter"] else "OFF"
            updates.append(f"Adaptive Trend Filter: {status}")
            self.enable_trend_filter = new_config.get("enable_trend_filter")
            if self.enable_trend_filter and not self.trend_finder:
                self.trend_finder = AdaptiveTrendFinder(mode=self.trend_filter_mode, threshold=self.trend_filter_threshold)
            elif not self.enable_trend_filter:
                self.trend_finder = None
                
        if "trend_filter_lookback" in new_config and new_config["trend_filter_lookback"] != self.trend_filter_lookback:
            updates.append(f"Trend Lookback: {self.trend_filter_lookback} -> {new_config['trend_filter_lookback']}")
            self.trend_filter_lookback = new_config.get("trend_filter_lookback")
            if self.trend_finder:
                self.trend_finder.lookback = self.trend_filter_lookback
                
        if "trend_filter_threshold" in new_config and new_config["trend_filter_threshold"] != self.trend_filter_threshold:
            updates.append(f"Trend Threshold: {self.trend_filter_threshold} -> {new_config['trend_filter_threshold']}")
            self.trend_filter_threshold = new_config.get("trend_filter_threshold")
            if self.trend_finder:
                self.trend_finder.threshold = self.trend_filter_threshold
            
        if "buy_order_type" in new_config and new_config["buy_order_type"] != self.buy_order_type:
            updates.append(f"Buy Order Type: {self.buy_order_type} -> {new_config['buy_order_type']}")
            self.buy_order_type = new_config.get("buy_order_type")
            
        if "limit_buffer" in new_config and new_config["limit_buffer"] != self.limit_buffer:
            updates.append(f"Limit Buffer: {self.limit_buffer}% -> {new_config['limit_buffer']}%")
            self.limit_buffer = new_config.get("limit_buffer")
            if self.engine:
                self.engine.config["limit_buffer"] = self.limit_buffer

        # Update internal config dictionary
        self.config.update(new_config)
        
        if updates:
            msg = f"⚡ [WallHunter {self.bot_id}] Live Configuration Updated:\n" + "\n".join([f"- {u}" for u in updates])
            self.logger.info(msg)
            # Fire and forget telegram notification
            asyncio.create_task(self._send_telegram(f"⚙️ *Live Config Update*\n{self.symbol} Bot #{self.bot_id}\n\n" + "\n".join([f"• {u}" for u in updates])))
        else:
            self.logger.info(f"⚡ [WallHunter {self.bot_id}] Config update received, but no changes detected.")

    async def _send_telegram(self, msg: str):
        if not self.owner_id:
            return
            
        # Append Performance Summary for Exits
        if "EXIT" in msg or "Partial TP" in msg:
            total_closed = getattr(self, 'total_wins', 0) + getattr(self, 'total_losses', 0)
            pnl = getattr(self, 'total_realized_pnl', 0.0)
            summary = (
                f"\n-------------------------\n"
                f"📊 *Bot {self.bot_id} Report:*\n"
                f"🔹 Closed Trades: {total_closed}\n"
                f"✅ Wins: {getattr(self, 'total_wins', 0)} | ❌ Losses: {getattr(self, 'total_losses', 0)}\n"
                f"💰 Total Net PnL: ${pnl:.2f}"
            )
            msg += summary
        try:
            db = SessionLocal()
            await NotificationService.send_message(db, self.owner_id, msg)
            db.close()
        except Exception as e:
            self.logger.error(f"Failed to send Telegram in WallHunterBot: {e}")

    def _publish_status(self, current_price: float):
        try:
            pnl_val = 0.0
            pnl_pct = 0.0
            entry_price = 0.0
            sl_price = 0.0
            tp_price = 0.0
            position = False

            if self.active_pos:
                position = True
                entry_price = self.active_pos.get('entry', 0)
                sl_price = self.active_pos.get('sl', 0)
                tp_price = self.active_pos.get('tp', 0)
                
                amount = self.active_pos.get('amount', 0)
                if getattr(self, 'strategy_mode', 'long') == 'short':
                    pnl_val = (entry_price - current_price) * amount
                    if entry_price > 0:
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                else:
                    pnl_val = (current_price - entry_price) * amount
                    if entry_price > 0:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100

            status_payload = {
                "id": self.bot_id,
                "status": "active" if self.running else "inactive",
                "mode": getattr(self, 'strategy_mode', 'long'),
                "pnl": float(f"{pnl_val:.2f}"),
                "pnl_percent": float(f"{pnl_pct:.2f}"),
                "total_pnl": float(f"{self.total_realized_pnl:.2f}"),
                "total_orders": self.total_executed_orders,
                "total_wins": self.total_wins,
                "total_losses": self.total_losses,
                "price": float(f"{current_price:.10f}"),
                "position": position,
                "entry_price": float(f"{entry_price:.10f}"),
                "sl_price": float(f"{sl_price:.10f}"),
                "tp_price": float(f"{tp_price:.10f}"),
                "target_spread": self.target_spread,
                "vol_threshold": self.vol_threshold,
                "absorption_delta": float(f"{self.absorption_tracker.get_current_delta():.2f}"),
                "is_absorbing": self.absorption_tracker.is_absorption_detected('buy') or self.absorption_tracker.is_absorption_detected('sell')
            }
            self.redis.publish(f"bot_status:{self.bot_id}", json.dumps(status_payload))
        except Exception as e:
            pass

    async def start(self, api_key_record=None):
        self.running = True
        # Dynamic Exchange Initialization
        exchange_class = getattr(ccxt, self.exchange_id)
        exchange_params = {
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000 if self.exchange_id == 'mexc' else 30000,
                'new_updates': True if self.exchange_id == 'mexc' else False
            }
        }
        
        # Public instance for fetching market data without triggering auth checks (MEXC /api/v3/capital/config/getall)
        self.public_exchange = exchange_class({'enableRateLimit': True})
        
        # Live Mode-e API select kora
        if not self.is_paper_trading and api_key_record:
            exchange_params.update({
                'apiKey': decrypt_key(api_key_record.api_key),
                'secret': decrypt_key(api_key_record.secret_key)
            })
            
            # Optional Passphrase for KuCoin/OKX/MEXC
            if hasattr(api_key_record, 'passphrase') and api_key_record.passphrase:
                try:
                    exchange_params['password'] = decrypt_key(api_key_record.passphrase)
                except Exception:
                     # Fallback if not encrypted or error
                    exchange_params['password'] = api_key_record.passphrase
            
        self.exchange = exchange_class(exchange_params)
        
        # Initialize execution engine with the correct exchange instance
        self.engine = OrderBlockExecutionEngine(self.config, exchange=self.exchange)
        
        try:
            await self.public_exchange.load_markets()
            # If public load succeeds, we can share the markets with the private exchange
            # to avoid MEXC hitting the failing /api/v3/capital/config/getall endpoint
            if self.exchange:
                self.exchange.markets = self.public_exchange.markets
                self.exchange.symbols = self.public_exchange.symbols
                self.exchange.currencies = self.public_exchange.currencies
                # Still call load_markets on the private one but it should be fast/skipped if already populated
                # and we wrap it in a tray catch just in case.
                try:
                    await self.exchange.load_markets()
                except Exception as inner_e:
                    self.logger.warning(f"Private exchange load_markets skipped/failed (expected on MEXC): {inner_e}")
                    
            self.logger.info(f"✅ [WallHunter {self.bot_id}] Markets loaded successfully for {self.symbol}")
        except Exception as e:
            self.logger.warning(f"Could not load markets during startup: {e}")

        # Initialize BTC Tracker
        from app.strategies.helpers.btc_correlation_tracker import BtcCorrelationTracker
        self.btc_correlation_tracker = BtcCorrelationTracker(
            self.public_exchange, 
            self.symbol, 
            threshold=self.btc_correlation_threshold,
            window_minutes=self.btc_time_window,
            min_move_pct=self.btc_min_move_pct
        )

        self._main_task = asyncio.create_task(self._run_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._vpvr_task = asyncio.create_task(self._vpvr_updater_loop())
        self._atr_task = asyncio.create_task(self._atr_updater_loop())
        self._liq_task = asyncio.create_task(self._liquidation_listener())
        self._trades_task = asyncio.create_task(self._trades_listener())
        
        if self.enable_btc_correlation:
            self._btc_task = asyncio.create_task(self.btc_correlation_tracker.start())
        else:
            self._btc_task = None
        
        mode = "Live Trading" if not self.is_paper_trading else "Paper Trading"
        
        trigger_logs = []
        if getattr(self, 'enable_wall_trigger', True):
            trigger_logs.append(f"Vol Threshold: {self.vol_threshold}")
        if getattr(self, 'enable_liq_trigger', False):
            trigger_logs.append(f"Liq Threshold: {self.liq_threshold}")
        trigger_str = "\n".join(trigger_logs)
        
        trigger_logs_console = []
        if getattr(self, 'enable_wall_trigger', True):
            trigger_logs_console.append(f"- Vol Threshold: {self.vol_threshold}")
        if getattr(self, 'enable_liq_trigger', False):
            trigger_logs_console.append(f"- Liq Threshold: {self.liq_threshold}")
        trigger_console_str = "\n".join(trigger_logs_console)

        startup_msg = (
            f"🟢 WallHunter Bot [ID: {self.bot_id}] Started!\n"
            f"Pair: {self.symbol}\n"
            f"Mode: {mode}\n"
            f"Buy Order: {self.buy_order_type.upper()}\n"
            f"Limit Buffer: {self.limit_buffer}%\n"
            f"{trigger_str}"
        )
        
        self.logger.info(f"🚀 [WallHunter {self.bot_id}] Booting up with config:\n"
                    f"- Symbol: {self.symbol}\n"
                    f"- Buy Type: {self.buy_order_type}\n"
                    f"- Limit Buffer: {self.limit_buffer}%\n"
                    f"{trigger_console_str}")
        
        await self._send_telegram(startup_msg)

    async def _heartbeat_loop(self):
        """Prints a friendly heartbeat to the terminal every 5 seconds"""
        while self.running:
            self.logger.info(f"💓 [WallHunter {self.bot_id}] active and monitoring Level 2 data on {self.symbol}...")
            await asyncio.sleep(5)

    async def _run_loop(self):
        while self.running:
            try:
                # Real-time L2 Data Fetching via WebSocket
                limit = market_depth_service._normalize_order_book_limit(self.exchange_id, 20)
                try:
                    orderbook = await self.public_exchange.watch_order_book(self.symbol, limit=limit)
                except Exception as e:
                    self.logger.warning(f"WebSocket orderbook error: {e}, falling back to REST")
                    await asyncio.sleep(1.5) # Rate limit protection for REST fallback
                    orderbook = await self.public_exchange.fetch_order_book(self.symbol, limit=limit)
                    
                if not orderbook['bids'] or not orderbook['asks']:
                    await asyncio.sleep(1)
                    continue

                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2
                current_time = time.time()

                if not self.active_pos:
                    if not self.enable_wall_trigger:
                        self._publish_status(mid_price)
                        continue

                    # 1. বর্তমান অর্ডার বুকের ওয়ালগুলো ফিল্টার করা
                    current_walls = {}
                    if getattr(self, 'strategy_mode', 'long') != 'short' or self.trading_mode == 'futures':
                        for level in orderbook['bids']:
                            price, vol = level[0], level[1]
                            if vol >= self.vol_threshold:
                                # Validate distance from current mid_price
                                distance_pct = abs(price - mid_price) / mid_price * 100.0
                                if distance_pct <= self.max_wall_distance_pct:
                                    current_walls[price] = {'vol': vol, 'type': 'buy'}

                    # Scan SELL walls for Futures mode OR Spot Short mode
                    if self.trading_mode == 'futures' or getattr(self, 'strategy_mode', 'long') == 'short':
                        for level in orderbook['asks']:
                            price, vol = level[0], level[1]
                            if vol >= self.vol_threshold:
                                # Validate distance from current mid_price
                                distance_pct = abs(price - mid_price) / mid_price * 100.0
                                if distance_pct <= self.max_wall_distance_pct:
                                    current_walls[price] = {'vol': vol, 'type': 'sell'}

                    # 2. ওয়াল অ্যানালাইসিস এবং স্পুফিং ডিটেকশন
                    for price, wall_info in current_walls.items():
                        vol = wall_info['vol']
                        side = wall_info['type']
                        
                        if self.min_wall_lifetime <= 0:
                            # 0-সেকেন্ড হলে সাথে সাথেই কিনে ফেলবে
                            if self.vpvr_enabled and self.top_hvns:
                                is_hvn_aligned = any(abs(price - hvn) / hvn <= (self.vpvr_tolerance / 100.0) for hvn in self.top_hvns)
                                if not is_hvn_aligned:
                                    self.logger.info(f"🚫 Instant Snipe at {price} rejected: Not near any HVN.")
                                    continue
                            
                            # CVD Absorption Check
                            if self.enable_absorption:
                                if not self.absorption_tracker.is_absorption_detected(side):
                                    continue
                                self.logger.info(f"🔥 [ABSORPTION] Confirmed at {price} for {side.upper()} wall. Delta: {self.absorption_tracker.get_current_delta():.2f}")

                            # BTC Correlation Anti-Fakeout Check
                            if self.enable_btc_correlation and self.btc_correlation_tracker:
                                if not self.btc_correlation_tracker.is_aligned(side):
                                    metrics = self.btc_correlation_tracker.get_metrics_string()
                                    self.logger.info(f"🚫 [BTC Divergence] Snipe at {price} rejected! {metrics}")
                                    continue
                                else:
                                    self.logger.info(f"✅ [BTC Correlation] Aligned for {side.upper()}! {self.btc_correlation_tracker.get_metrics_string()}")

                            # Adaptive Trend Filter Check
                            if self.enable_trend_filter and self.trend_finder:
                                target_trade_dir = "buy" if getattr(self, 'strategy_mode', 'long') == 'long' else "sell" 
                                try:
                                    klines = await market_depth_service.getOHLCV(self.symbol, self.exchange_id, '1m', 1200)
                                    if klines:
                                        close_prices = [float(k['close']) for k in klines]
                                        trend_analysis = self.trend_finder.analyze_trend(close_prices)
                                        is_acceptable, tb_reason = self.trend_finder.is_trend_acceptable(trend_analysis, target_trade_dir)
                                        if not is_acceptable:
                                            self.logger.info(f"🚫 [Trend Filter] Instant Snipe at {price} rejected! {tb_reason}")
                                            continue
                                        else:
                                            self.logger.info(f"📈 [Trend Filter] {tb_reason}")
                                except Exception as e:
                                    self.logger.error(f"Failed to execute trend filter check: {e}")
                                    continue

                            self.logger.info(f"🟢 Instant Snipe at {price} (Spoof Detect is 0s) {'[HVN Confirmed]' if self.vpvr_enabled else ''}. Executing!")
                            await self.execute_snipe(price, side, mid_price, best_bid, best_ask)
                            self.tracked_walls.clear()
                            current_walls.clear()
                            break

                        if price in self.tracked_walls:
                            # ওয়ালটি এখনও আছে, তাই লাস্ট আপডেট টাইম চেঞ্জ করছি
                            self.tracked_walls[price]['last_seen'] = current_time
                            self.tracked_walls[price]['vol'] = vol
                            
                            # চেক করছি ওয়ালটি পর্যাপ্ত সময় ধরে টিকে আছে কিনা
                            time_alive = current_time - self.tracked_walls[price]['first_seen']
                            if time_alive >= self.min_wall_lifetime:
                                if self.tracked_walls[price].get('hvn_rejected'):
                                    continue

                                if self.vpvr_enabled and self.top_hvns:
                                    is_hvn_aligned = any(abs(price - hvn) / hvn <= (self.vpvr_tolerance / 100.0) for hvn in self.top_hvns)
                                    if not is_hvn_aligned:
                                        self.logger.info(f"🚫 Wall at {price} rejected: Not near any HVN (Tolerance: {self.vpvr_tolerance}%).")
                                        self.tracked_walls[price]['hvn_rejected'] = True
                                        continue

                                # CVD Absorption Check
                                if self.enable_absorption:
                                    if not self.absorption_tracker.is_absorption_detected(side):
                                        continue
                                    self.logger.info(f"🧬 [ABSORPTION] Confirmed Genuine Wall at {price} for {side.upper()} wall!")

                                # BTC Correlation Anti-Fakeout Check
                                if self.enable_btc_correlation and self.btc_correlation_tracker:
                                    if self.tracked_walls[price].get('btc_rejected'):
                                        continue
                                    if not self.btc_correlation_tracker.is_aligned(side):
                                        metrics = self.btc_correlation_tracker.get_metrics_string()
                                        self.logger.info(f"🚫 [BTC Divergence] Confirmed Wall at {price} rejected! {metrics}")
                                        self.tracked_walls[price]['btc_rejected'] = True
                                        continue
                                    else:
                                        self.logger.info(f"✅ [BTC Correlation] Aligned for {side.upper()}! {self.btc_correlation_tracker.get_metrics_string()}")
                                        
                                # Adaptive Trend Filter Check
                                if self.enable_trend_filter and self.trend_finder:
                                    if self.tracked_walls[price].get('trend_rejected'):
                                        continue
                                    target_trade_dir = "buy" if getattr(self, 'strategy_mode', 'long') == 'long' else "sell" 
                                    try:
                                        klines = await market_depth_service.getOHLCV(self.symbol, self.exchange_id, '1m', 1200)
                                        if klines:
                                            close_prices = [float(k['close']) for k in klines]
                                            trend_analysis = self.trend_finder.analyze_trend(close_prices)
                                            is_acceptable, tb_reason = self.trend_finder.is_trend_acceptable(trend_analysis, target_trade_dir)
                                            if not is_acceptable:
                                                self.logger.info(f"🚫 [Trend Filter] Confirmed Snipe at {price} rejected! {tb_reason}")
                                                self.tracked_walls[price]['trend_rejected'] = True
                                                continue
                                            else:
                                                self.logger.info(f"📈 [Trend Filter] {tb_reason}")
                                    except Exception as e:
                                        self.logger.error(f"Failed to execute trend filter check: {e}")
                                        continue
                                        
                                self.logger.info(f"🟢 Genuine Wall detected at {price} (Alive for {time_alive:.1f}s) {'[HVN Confirmed]' if self.vpvr_enabled else ''}. Executing Snipe!")
                                await self.execute_snipe(price, side, mid_price, best_bid, best_ask)
                                self.tracked_walls.clear() # এন্ট্রি নেওয়ার পর ট্র্যাকিং ক্লিয়ার
                                break
                        else:
                            # নতুন একটি বড় ওয়াল পাওয়া গেছে, ট্র্যাকিং শুরু
                            self.tracked_walls[price] = {
                                "vol": vol,
                                "type": side,
                                "first_seen": current_time,
                                "last_seen": current_time
                            }
                    
                    # 3. ফেইক বা স্পুফ করা ওয়ালগুলো রিমুভ করা (Grace Period: 2 Seconds)
                    spoofed_prices = []
                    for price, data in self.tracked_walls.items():
                        if price not in current_walls:
                            # Allow a 2-second grace period for network lag or partial fills
                            if current_time - data['last_seen'] > 2.0:
                                spoofed_prices.append(price)
                    
                    for p in spoofed_prices:
                        time_alive = current_time - self.tracked_walls[p]['first_seen']
                        self.logger.info(f"⚠️ Spoofing Detected: Wall at {p} disappeared after {time_alive:.1f}s. Ignoring.")
                        del self.tracked_walls[p]

                else:
                    # Trailing Stop-Loss Engine
                    await self.manage_risk(mid_price)

                self._publish_status(mid_price)
                # Yield control, watch_order_book automatically pauses until the next orderbook update
                await asyncio.sleep(0.001) 
            
            except Exception as e:
                self.logger.error(f"Hunter Loop Error: {e}")
                await asyncio.sleep(1)

    async def execute_snipe(self, wall_price: float, side: str, current_mid_price: float, best_bid: float = None, best_ask: float = None):
        # Select correct entry order type depending on the strategy mode
        snipe_order_type = self.sell_order_type if getattr(self, 'strategy_mode', 'long') == 'short' else self.buy_order_type
        
        # Determine Maker vs Taker pricing based on the chosen entry order type
        if snipe_order_type == "limit":
            # True Maker Limit Order: stay on the same side of the book
            if side == "buy":
                base_limit_price = best_bid if best_bid else current_mid_price
            else:
                base_limit_price = best_ask if best_ask else current_mid_price
        else:
            # Taker Execution (Market or Marketable Limit): cross the spread
            if side == "buy":
                base_limit_price = best_ask if best_ask else current_mid_price
            else:
                base_limit_price = best_bid if best_bid else current_mid_price
            
        entry_price = base_limit_price
        
        # Calculate base asset amount
        input_amount = self.config.get("amount_per_trade", 10.0)
        if getattr(self, 'strategy_mode', 'long') == 'short':
            # In Short/Accumulate mode, the UI input is directly the Base Asset amount
            base_amount = float(f"{input_amount:.6f}")
        else:
            # In Long mode, the UI input is Quote Asset, so convert to Base Asset
            base_amount = float(f"{input_amount / entry_price:.6f}")
        
        # In Paper Trading, simulating a market buy exactly at the bid wall gives an artificial instant PnL advantage (Bid-Ask spread). 
        # Using mid_price prevents instant fake TP triggers.
        execution_price = current_mid_price if self.is_paper_trading else entry_price
        
        self.logger.info(f"⚡ [WallHunter {self.bot_id}] Executing Snipe: {side.upper()} {base_amount} {self.symbol} at {execution_price} (Order Type: {snipe_order_type.upper()})")
        
        if snipe_order_type == "marketable_limit":
             # "marketable_limit" is a special instruction for our engine to use LIMIT with buffer on MEXC
             # but we pass "market" to it so it knows to apply the conversion logic if it's MEXC
             snipe_order_type = "market"
             
        order_params = {"postOnly": True} if snipe_order_type == "limit" else {}
             
        res = await self.engine.execute_trade(side, base_amount, execution_price, order_type=snipe_order_type, params=order_params)
        if res:
            self.logger.info(f"✅ [WallHunter {self.bot_id}] Trade executed successfully. Order ID: {res.get('id')}")
            
            # --- NEW: Partial Fill Management for Entry ---
            entry_type = self.sell_order_type if getattr(self, 'strategy_mode', 'long') == "short" else self.buy_order_type
            if entry_type in ['limit', 'marketable_limit'] and res.get('id') and not self.is_paper_trading:
                try:
                    order_status = None
                    # For Maker Limit, wait 30 seconds (60 * 0.5s). For Marketable Limit, wait 2 seconds (5 * 0.4s).
                    max_attempts = 60 if snipe_order_type == "limit" else 5
                    sleep_time = 0.5 if snipe_order_type == "limit" else 0.4
                    
                    for attempt in range(max_attempts):
                        await asyncio.sleep(sleep_time)
                        try:
                            # To avoid CCXT rate limits on long 30s waits, only fetch every ~1.5 seconds
                            if attempt % 3 == 0 or max_attempts <= 5:
                                order_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                                if order_status and order_status.get('status') != 'open':
                                    break
                        except Exception: pass
                    
                    if order_status and order_status.get('status') == 'open':
                        self.logger.warning(f"⚠️ Entry order {res['id']} is still open! Cancelling remainder...")
                        await self.engine.cancel_order(res['id'])
                        await asyncio.sleep(0.5)
                        
                        final_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                        filled = final_status.get('filled', 0.0)
                        
                        if filled <= 0:
                            self.logger.error(f"❌ Entry order was completely unfilled before cancellation. Aborting snipe.")
                            return
                            
                        self.logger.info(f"🔄 Partial Fill Detected! Requested: {base_amount}, Filled: {filled}. Adjusting position size.")
                        # Parse precision natively so exchange math doesn't break later
                        base_amount_raw = float(self.engine.exchange.amount_to_precision(self.symbol, filled)) if hasattr(self.engine.exchange, 'amount_to_precision') else filled
                        base_amount = base_amount_raw
                        
                        res['average'] = final_status.get('average') or res.get('average')
                        res['price'] = final_status.get('price') or res.get('price')
                except Exception as e:
                    self.logger.error(f"Error handling partial fill verification on entry: {e}")
            # ---------------------------------------------
            
            # Safely extract average fill price. Fallback to requested entry_price if not provided or 0
            avg_price = res.get('average')
            fill_price = res.get('price')
            
            # If CCXT did not return average price initially, launch a background task
            # We will use current_mid_price (or fill price) temporarily so we can proceed instantly.
            if not self.is_paper_trading and res.get('id') and self.engine.exchange and not (avg_price and avg_price > 0):
                self.logger.info(f"⚡ Price not instantly available for {res.get('id')}. Spawning background tracker...")
                asyncio.create_task(self._fetch_and_update_entry(res['id'], base_amount, current_mid_price))
                # For now, we proceed to set up SL/TP using intermediate price
                pass

            actual_entry = avg_price if avg_price and avg_price > 0 else (fill_price if fill_price and fill_price > 0 else execution_price)
            actual_entry = float(actual_entry)
            
            # Sanity Check to prevent instant SL logic if CCXT returns an outdated or widely inaccurate fill price
            slippage_pct = abs(actual_entry - current_mid_price) / current_mid_price
            if slippage_pct > 0.02: # If the executed price differs from the mid price by more than 2%
                self.logger.warning(f"Suspicious fill price from CCXT: {actual_entry}. Overriding with mid_price: {current_mid_price}")
                actual_entry = current_mid_price
            
            # --- UPDATED: Position tracking for TP1 and TP2 ---
            if self.enable_micro_scalp:
                tick_profit_pct = self.micro_scalp_profit_ticks * 0.0001
                tp_price = actual_entry * (1 - tick_profit_pct) if getattr(self, 'strategy_mode', 'long') == 'short' else actual_entry * (1 + tick_profit_pct)
                sl_price = actual_entry * (1 + (self.initial_risk_pct / 100)) if getattr(self, 'strategy_mode', 'long') == 'short' else actual_entry * (1 - (self.initial_risk_pct / 100))
                
                self.active_pos = {
                    "entry": actual_entry,
                    "amount": base_amount,
                    "sl": sl_price,
                    "tp1": tp_price,
                    "tp": tp_price,
                    "tp1_hit": True, # Ignore partial TP
                    "breakeven_hit": False,
                    "tsl_activated": False,
                    "limit_order_id": None,
                    "micro_scalp": True
                }
                self.highest_price = actual_entry
                self.lowest_price = actual_entry
                
                close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
                close_amount = (base_amount * actual_entry * 0.995) / tp_price if getattr(self, 'strategy_mode', 'long') == "short" else base_amount
                
                limit_res = await self.engine.execute_trade(close_side, close_amount, tp_price, order_type="limit", params={"postOnly": True})
                if limit_res and 'id' in limit_res:
                    self.active_pos['limit_order_id'] = limit_res['id']
                    self.logger.info(f"⚡ Micro-Scalp: Placed Limit TP Order {limit_res['id']} at {tp_price}")
                    
                await self._send_telegram(f"⚡ Micro-Scalp Entered!\nPair: {self.symbol}\nEntry: {actual_entry:.6f}\nTick Target: {tp_price:.6f}\nSL: {self.active_pos['sl']:.6f}")
                
            else:
                if getattr(self, 'strategy_mode', 'long') == 'short':
                    tp1_price = actual_entry * (1 - (getattr(self, 'partial_tp_trigger_pct', 0.0) / 100)) if getattr(self, 'partial_tp_trigger_pct', 0.0) > 0 else actual_entry - (self.target_spread * 0.5)
                    tp_price = actual_entry - self.target_spread
                    sl_price = actual_entry * (1 + (self.initial_risk_pct / 100))
                else:
                    tp1_price = actual_entry * (1 + (getattr(self, 'partial_tp_trigger_pct', 0.0) / 100)) if getattr(self, 'partial_tp_trigger_pct', 0.0) > 0 else actual_entry + (self.target_spread * 0.5)
                    tp_price = actual_entry + self.target_spread
                    sl_price = actual_entry * (1 - (self.initial_risk_pct / 100))

                self.active_pos = {
                    "entry": actual_entry,
                    "amount": base_amount,
                    "sl": sl_price,
                    "tp1": tp1_price,
                    "tp": tp_price,          # Final TP
                    "tp1_hit": False,
                    "breakeven_hit": False,
                    "tsl_activated": False,
                    "limit_order_id": None,
                    "micro_scalp": False
                }
                self.highest_price = actual_entry
                self.lowest_price = actual_entry
                
                # Place Limit Order immediately if configured
                exit_order_type = self.buy_order_type if getattr(self, 'strategy_mode', 'long') == "short" else self.sell_order_type
                if exit_order_type == 'limit':
                    close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
                    close_amount = (base_amount * actual_entry * 0.995) / self.active_pos['tp'] if getattr(self, 'strategy_mode', 'long') == "short" else base_amount
                    limit_res = await self.engine.execute_trade(close_side, close_amount, self.active_pos['tp'], order_type="limit", params={"postOnly": True})
                    if limit_res and 'id' in limit_res:
                        self.active_pos['limit_order_id'] = limit_res['id']
                        self.logger.info(f"Placed Limit TP Order {limit_res['id']} at {self.active_pos['tp']}")
                
                self.logger.info(f"Entered Trade at {actual_entry}. SL: {self.active_pos['sl']}")
                await self._send_telegram(f"⚡ WallHunter Entered!\nPair: {self.symbol}\nEntry {actual_entry:.6f}\nTP1: {self.active_pos['tp1']:.6f}\nFinal TP: {self.active_pos['tp']:.6f}\nSL: {self.active_pos['sl']:.6f}")

    async def _fetch_and_update_entry(self, order_id: str, amount: float, mid_price: float):
        """Background task to fetch precise execution price without blocking strategy"""
        await asyncio.sleep(0.5) # Give the exchange half a second to settle
        try:
            fetched_order = await self.engine.exchange.fetch_order(order_id, self.symbol)
            if not fetched_order:
                return
            
            avg_price = fetched_order.get('average')
            fill_price = fetched_order.get('price')
            actual_entry = avg_price if avg_price and avg_price > 0 else (fill_price if fill_price and fill_price > 0 else mid_price)
            actual_entry = float(actual_entry)
            
            # Sanity Check
            slippage_pct = abs(actual_entry - mid_price) / mid_price
            if slippage_pct > 0.02:
                self.logger.warning(f"Suspicious delayed fill price: {actual_entry}. Keeping previous {mid_price}.")
                return
                
            # Update only if position is still active
            if self.active_pos and self.active_pos.get('entry') != actual_entry:
                old_entry = self.active_pos['entry']
                self.active_pos['entry'] = actual_entry
                
                # Recalculate SL/TP targets based on exact price
                if self.active_pos.get('micro_scalp'):
                    tick_profit_pct = self.micro_scalp_profit_ticks * 0.0001
                    if getattr(self, 'strategy_mode', 'long') == 'short':
                        tp_price = actual_entry * (1 - tick_profit_pct)
                        self.active_pos['sl'] = actual_entry * (1 + (self.initial_risk_pct / 100))
                    else:
                        tp_price = actual_entry * (1 + tick_profit_pct)
                        self.active_pos['sl'] = actual_entry * (1 - (self.initial_risk_pct / 100))
                    self.active_pos['tp'] = tp_price
                    self.active_pos['tp1'] = tp_price
                else:
                    if getattr(self, 'strategy_mode', 'long') == 'short':
                        self.active_pos['sl'] = actual_entry * (1 + (self.initial_risk_pct / 100))
                        self.active_pos['tp1'] = actual_entry - (self.target_spread * 0.5)
                        self.active_pos['tp'] = actual_entry - self.target_spread
                    else:
                        self.active_pos['sl'] = actual_entry * (1 - (self.initial_risk_pct / 100))
                        self.active_pos['tp1'] = actual_entry + (self.target_spread * 0.5)
                        self.active_pos['tp'] = actual_entry + self.target_spread
                    
                self.highest_price = actual_entry
                self.lowest_price = actual_entry
                self.logger.info(f"🔄 Entry precision updated in background: {old_entry:.6f} -> {actual_entry:.6f}")
                
                # If there's an active limit order, we might need to adjust it
                active_limit_id = self.active_pos.get('limit_order_id')
                if active_limit_id:
                    # Cancel the old limit order and replace it with the precise one
                    try:
                        await self.engine.cancel_order(active_limit_id)
                        close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
                        close_amount = (self.active_pos['amount'] * actual_entry * 0.995) / self.active_pos['tp'] if getattr(self, 'strategy_mode', 'long') == "short" else self.active_pos['amount']
                        limit_res = await self.engine.execute_trade(close_side, close_amount, self.active_pos['tp'], order_type="limit")
                        if limit_res and 'id' in limit_res:
                            self.active_pos['limit_order_id'] = limit_res['id']
                            self.logger.info(f"🔄 Adjusted Limit TP Order to exact price {self.active_pos['tp']}")
                    except Exception as limit_err:
                        self.logger.error(f"Failed to adjust limit order in background precision update: {limit_err}")
                        
        except Exception as e:
            self.logger.warning(f"Background fetch_order failed for {order_id}: {e}")

    async def manage_risk(self, current_price: float):
        if not self.active_pos: return
        
        exit_order_type = self.buy_order_type if getattr(self, 'strategy_mode', 'long') == "short" else self.sell_order_type

        # 1. Check if the limit TP order has already been filled by the exchange
        if (exit_order_type == 'limit' or self.active_pos.get('micro_scalp')) and self.active_pos.get('limit_order_id') and not self.is_paper_trading:
            try:
                order_status = await self.engine.exchange.fetch_order(self.active_pos['limit_order_id'], self.symbol)
                if order_status and order_status.get('status') == 'closed':
                    # The limit order was filled!
                    filled_price = order_status.get('average') or order_status.get('price') or self.active_pos['tp']
                    sell_amount = order_status.get('filled') or self.active_pos.get('amount')
                    
                    pnl_val = (filled_price - self.active_pos['entry']) * sell_amount
                    self.total_realized_pnl += pnl_val
                    self.total_executed_orders += 1
                    if pnl_val > 0:
                        self.total_wins += 1
                    else:
                        self.total_losses += 1
                    await self._send_telegram(f"🎯 WallHunter EXIT - Limit TP Filled!\nPair: {self.symbol}\nExit Price: {filled_price:.6f}\nPnL: ${pnl_val:.2f}")
                    self.logger.info(f"✅ Limit TP Order {self.active_pos['limit_order_id']} was filled by exchange at {filled_price}")
                    self.active_pos = None
                    return
            except Exception as e:
                self.logger.warning(f"Error checking limit order status: {e}")

        if getattr(self, 'strategy_mode', 'long') == 'short':
            if not hasattr(self, 'lowest_price') or self.lowest_price == 0:
                self.lowest_price = current_price
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                
                # Check TSL Activation
                activation_pct = getattr(self, 'tsl_activation_pct', 0.0)
                if activation_pct > 0 and not self.active_pos.get('tsl_activated'):
                    trigger = self.active_pos['entry'] * (1 - (activation_pct / 100))
                    if current_price <= trigger:
                        self.active_pos['tsl_activated'] = True
                        self.logger.info(f"🚀 Trailing SL Activated for SHORT at {current_price:.6f}!")
                
                if activation_pct == 0.0 or self.active_pos.get('tsl_activated'):
                    if self.atr_sl_enabled and getattr(self, 'current_atr', 0) > 0:
                        new_sl = self.lowest_price + (self.current_atr * self.atr_multiplier)
                        self.active_pos['sl'] = min(self.active_pos['sl'], new_sl)
                    elif getattr(self, 'tsl_pct', 0.0) > 0:
                        new_sl = self.lowest_price * (1 + (self.tsl_pct / 100))
                        self.active_pos['sl'] = min(self.active_pos['sl'], new_sl)

            if getattr(self, 'sl_breakeven_trigger_pct', 0.0) > 0 and not self.active_pos.get('breakeven_hit'):
                trigger_price = self.active_pos['entry'] * (1 - (self.sl_breakeven_trigger_pct / 100))
                if current_price <= trigger_price:
                    new_breakeven_sl = self.active_pos['entry'] * (1 - (self.sl_breakeven_target_pct / 100))
                    if new_breakeven_sl < self.active_pos['sl']:
                        self.active_pos['sl'] = new_breakeven_sl
                        self.active_pos['breakeven_hit'] = True
                        self.logger.info(f"🛡️ Set SL to Risk-Free Breakeven at {new_breakeven_sl:.6f}")
                        asyncio.create_task(self._send_telegram(f"🛡️ Stop-Loss moved to Risk-Free!\nPair: {self.symbol}\nNew SL: {new_breakeven_sl:.6f}"))
        else:
            if current_price > self.highest_price:
                self.highest_price = current_price
                
                # Check TSL Activation
                activation_pct = getattr(self, 'tsl_activation_pct', 0.0)
                if activation_pct > 0 and not self.active_pos.get('tsl_activated'):
                    trigger = self.active_pos['entry'] * (1 + (activation_pct / 100))
                    if current_price >= trigger:
                        self.active_pos['tsl_activated'] = True
                        self.logger.info(f"🚀 Trailing SL Activated for LONG at {current_price:.6f}!")
                
                # Update Trailing SL
                if activation_pct == 0.0 or self.active_pos.get('tsl_activated'):
                    if self.atr_sl_enabled and getattr(self, 'current_atr', 0) > 0:
                        new_sl = self.highest_price - (self.current_atr * self.atr_multiplier)
                        self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)
                    elif getattr(self, 'tsl_pct', 0.0) > 0:
                        new_sl = self.highest_price * (1 - (self.tsl_pct / 100))
                        self.active_pos['sl'] = max(self.active_pos['sl'], new_sl)

            # --- NEW: Independent Breakeven SL Logic ---
            if getattr(self, 'sl_breakeven_trigger_pct', 0.0) > 0 and not self.active_pos.get('breakeven_hit'):
                trigger_price = self.active_pos['entry'] * (1 + (self.sl_breakeven_trigger_pct / 100))
                if current_price >= trigger_price:
                    new_breakeven_sl = self.active_pos['entry'] * (1 + (self.sl_breakeven_target_pct / 100))
                    # Only move if the new breakeven SL is higher than current SL AND current max price
                    if new_breakeven_sl > self.active_pos['sl']:
                        self.active_pos['sl'] = new_breakeven_sl
                        self.active_pos['breakeven_hit'] = True
                        self.logger.info(f"🛡️ Set SL to Risk-Free Breakeven at {new_breakeven_sl:.6f}")
                        asyncio.create_task(self._send_telegram(f"🛡️ Stop-Loss moved to Risk-Free!\nPair: {self.symbol}\nNew SL: {new_breakeven_sl:.6f}"))

        # --- Partial TP Logic ---
        # Only execute TP1 logic if partial_tp_pct > 0
        hit_tp1 = current_price <= self.active_pos['tp1'] if getattr(self, 'strategy_mode', 'long') == 'short' else current_price >= self.active_pos['tp1']
        
        if not self.active_pos.get('micro_scalp') and self.partial_tp_pct > 0 and not self.active_pos.get('tp1_hit') and hit_tp1:
            self.logger.info("🟢 TP1 Hit! Executing Partial Close.")
            sell_amount_raw = self.active_pos['amount'] * (self.partial_tp_pct / 100)
            
            # --- Min Notional Check (Dust Position Preventer) ---
            remaining_amount = self.active_pos['amount'] - sell_amount_raw
            try:
                min_cost = 0.0
                if self.engine.exchange and hasattr(self.engine.exchange, 'markets') and self.symbol in self.engine.exchange.markets:
                    min_cost = self.engine.exchange.markets[self.symbol].get('limits', {}).get('cost', {}).get('min', 0.0)
                
                if min_cost and min_cost > 0:
                    remaining_value = remaining_amount * current_price
                    if remaining_value < min_cost:
                        self.logger.warning(f"Dust Position Prevented: Remaining value ${remaining_value:.2f} < Min Notional ${min_cost:.2f}. Executing 100% close at TP1.")
                        sell_amount_raw = self.active_pos['amount']
            except Exception as e:
                self.logger.error(f"Error checking min notional for TP1: {e}")
            # ----------------------------------------------------

            close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
            
            if getattr(self, 'strategy_mode', 'long') == "short":
                calc_price = self.active_pos['tp1']
                if exit_order_type == 'market' or exit_order_type == 'marketable_limit':
                    calc_price = current_price * (1 + (self.config.get("limit_buffer", 1.0) / 100.0))
                close_amount_raw = (sell_amount_raw * self.active_pos['entry'] * 0.99) / calc_price
            else:
                close_amount_raw = sell_amount_raw
            sell_amount = float(self.engine.exchange.amount_to_precision(self.symbol, close_amount_raw))
            
            exit_order_type_actual = exit_order_type
            if exit_order_type_actual == 'marketable_limit':
                exit_order_type_actual = 'market'

            res = None
            if exit_order_type_actual == 'limit':
                res = await self.engine.execute_trade(close_side, sell_amount, self.active_pos['tp1'], order_type="limit", params={"postOnly": True})
                if res:
                    self.logger.info(f"Placed Limit Order for Partial TP at {self.active_pos['tp1']}")
                if res and self.is_paper_trading:
                    # Instantly filled in simulation: Finalize paper balance
                    await self.engine.execute_trade(close_side, sell_amount, self.active_pos['tp1'])
            else:
                res = await self.engine.execute_trade(close_side, sell_amount, current_price)
                if res:
                    self.logger.info(f"Executed Market Order for Partial TP at {current_price}")
            
            # Update Limit order to prevent over-selling
            if res and exit_order_type == 'limit' and self.active_pos.get('limit_order_id'):
                try:
                    await self.engine.cancel_order(self.active_pos['limit_order_id'])
                    remaining_raw = self.active_pos['amount'] - sell_amount_raw
                    # Only replace limit if not fully closed
                    if remaining_raw > 0.00000001:
                        rem_close_amount_raw = (remaining_raw * self.active_pos['entry'] * 0.99) / self.active_pos['tp'] if getattr(self, 'strategy_mode', 'long') == "short" else remaining_raw
                        limit_res = await self.engine.execute_trade(close_side, rem_close_amount_raw, self.active_pos['tp'], order_type="limit", params={"postOnly": True})
                        if limit_res and 'id' in limit_res:
                            self.active_pos['limit_order_id'] = limit_res['id']
                except Exception as e:
                    self.logger.error(f"Failed to update limit order after TP1: {e}")
            
            if res:
                remaining_raw = self.active_pos['amount'] - sell_amount_raw
                exit_price = self.active_pos['tp1'] if exit_order_type == 'limit' else current_price
                if getattr(self, 'strategy_mode', 'long') == "short":
                    pnl_val = (self.active_pos['entry'] - exit_price) * sell_amount_raw
                else:
                    pnl_val = (exit_price - self.active_pos['entry']) * sell_amount_raw
                
                self.total_realized_pnl += pnl_val
                
                if remaining_raw <= 0.00000001:  # 100% close
                    self.total_wins += 1
                    self.total_executed_orders += 1
                    await self._send_telegram(f"🎯 WallHunter EXIT - Full TP Hit (Dust Prevented)!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nLocked Profit: ${pnl_val:.2f}")
                    self.active_pos = None
                else:
                    self.active_pos['amount'] = float(self.engine.exchange.amount_to_precision(self.symbol, remaining_raw))
                    self.active_pos['tp1_hit'] = True
                    await self._send_telegram(f"🔓 Partial TP Hit!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nLocked Profit: ${pnl_val:.2f}")
            else:
                self.logger.warning("❌ Partial TP execution failed on exchange. Skipping partial TP size reduction to stay in sync with exchange.")
                self.active_pos['tp1_hit'] = True

        elif (current_price >= self.active_pos['sl'] if getattr(self, 'strategy_mode', 'long') == 'short' else current_price <= self.active_pos['sl']):
            self.logger.info(f"⚠️ Triggering SL: Current Price ({current_price:.6f}) hit SL ({self.active_pos['sl']:.6f})")
            
            sell_amount_raw = self.active_pos['amount']
            close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
            
            if getattr(self, 'strategy_mode', 'long') == "short":
                calc_price = current_price * (1 + (self.config.get("limit_buffer", 1.0) / 100.0))
                close_amount_raw = (sell_amount_raw * self.active_pos['entry'] * 0.99) / calc_price
            else:
                close_amount_raw = sell_amount_raw
            sell_amount = float(self.engine.exchange.amount_to_precision(self.symbol, close_amount_raw))
            
            # Cancel open limit order if SL/TSL hits (handles both limit sell orders and micro_scalp)
            if (exit_order_type == 'limit' or self.active_pos.get('micro_scalp')) and self.active_pos.get('limit_order_id'):
                canceled = False
                for attempt in range(3):
                    try:
                        self.logger.info(f"Attempting to cancel Limit TP Order {self.active_pos['limit_order_id']} before SL market order (Attempt {attempt+1}/3)")
                        await self.engine.cancel_order(self.active_pos['limit_order_id'])
                        canceled = True
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to cancel Limit TP Order on attempt {attempt+1}: {e}")
                        await asyncio.sleep(0.2)
                
                if canceled:
                    self.logger.info("Successfully cancelled Limit TP Order due to Stop Loss hit. Extracting remaining position...")
                    await asyncio.sleep(0.5) # Wait for exchange to release the locked base asset balance
                    
                    # --- NEW: Extract remaining balance from the cancelled Limit Order ---
                    try:
                        if not self.is_paper_trading:
                            cancelled_status = await self.engine.exchange.fetch_order(self.active_pos['limit_order_id'], self.symbol)
                            filled = cancelled_status.get('filled', 0.0)
                            if filled > 0:
                                self.logger.info(f"🔄 Open Limit Order was partially filled ({filled}). Adjusting SL Market Sweep amount.")
                                filled_proper = float(self.engine.exchange.amount_to_precision(self.symbol, filled)) if hasattr(self.engine.exchange, 'amount_to_precision') else filled
                                sell_amount_raw = max(0.0, self.active_pos['amount'] - filled_proper)
                                
                                if sell_amount_raw <= 0:
                                    self.logger.info("✅ Partial fill actually completely closed out the remaining position. SL sweep aborted.")
                                    
                                    pnl_val = 0
                                    # Fallback simple PNL
                                    self.total_wins += 1
                                    await self._send_telegram(f"🛡️ WallHunter EXIT - Stopped out via Partial Fill Sweep!\nPair: {self.symbol}")
                                    self.active_pos = None
                                    return
                                    
                                # Re-calculate correct sizing
                                close_amount_raw = (sell_amount_raw * self.active_pos['entry'] * 0.995) / current_price if getattr(self, 'strategy_mode', 'long') == "short" else sell_amount_raw
                                sell_amount = float(self.engine.exchange.amount_to_precision(self.symbol, close_amount_raw))
                    except Exception as e:
                        self.logger.error(f"Error fetching filled status of cancelled limit order: {e}")
                    # -------------------------------------------------------------
                else:
                    self.logger.error("COULD NOT CANCEL LIMIT TP ORDER! SL Market order might fail with Insufficient Balance.")
                
            exit_order_type_actual = exit_order_type
            if exit_order_type_actual == 'marketable_limit':
                exit_order_type_actual = 'market'
            
            # SL/TSL is always market-type execution (or converted by engine)
            res = await self.engine.execute_trade(close_side, sell_amount, current_price, order_type=exit_order_type_actual if exit_order_type_actual != "limit" else "market")
            
            # --- NEW: Partial Fill Management for Active SL Exits ---
            if res and res.get('id') and not self.is_paper_trading:
                try:
                    order_status = None
                    for _ in range(5):
                        await asyncio.sleep(0.4)
                        try:
                            order_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                            if order_status and order_status.get('status') != 'open':
                                break
                        except Exception: pass
                    
                    if order_status and order_status.get('status') == 'open':
                        self.logger.warning(f"⚠️ Exit SL order {res['id']} is hanging open! Cancelling remainder...")
                        await self.engine.cancel_order(res['id'])
                        await asyncio.sleep(0.5)
                        
                        final_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                        filled = final_status.get('filled', 0.0)
                        
                        filled_proper = float(self.engine.exchange.amount_to_precision(self.symbol, filled)) if hasattr(self.engine.exchange, 'amount_to_precision') else filled
                        remaining_base = max(0.0, sell_amount_raw - filled_proper)
                        
                        if remaining_base > 0:
                            self.logger.info(f"🧹 Sweeping SL remainder at Pure Market: {remaining_base} {self.symbol}")
                            if getattr(self, 'strategy_mode', 'long') == "short":
                                # Calculate exact remaining USDC budget from the sold amount to prevent Insufficient Balance
                                padded_price = current_price * (1 + (self.config.get("limit_buffer", 1.0) / 100.0))
                                total_usd_budget = self.active_pos['amount'] * self.active_pos['entry'] * 0.99
                                avg_fill = final_status.get('average') or final_status.get('price') or current_price
                                spent_usd = filled_proper * avg_fill
                                remaining_usd = max(0.0, total_usd_budget - spent_usd)
                                sweep_amount_raw = remaining_usd / padded_price
                            else:
                                sweep_amount_raw = remaining_base

                            sweep_amount = float(self.engine.exchange.amount_to_precision(self.symbol, sweep_amount_raw))
                            
                            await self.engine.execute_trade(close_side, sweep_amount, current_price, order_type="market")
                            self.logger.info("✅ Market sweep completed.")
                except Exception as e:
                    self.logger.error(f"Error checking SL partial fill sweep: {e}")
            # --------------------------------------------------------
            self.total_executed_orders += 1
            
            if getattr(self, 'strategy_mode', 'long') == "short":
                pnl_val = (self.active_pos['entry'] - current_price) * sell_amount_raw
            else:
                pnl_val = (current_price - self.active_pos['entry']) * sell_amount_raw
                
            if self.active_pos.get('tp1_hit'):
                 self.total_realized_pnl += pnl_val
                 self.total_wins += 1
                 await self._send_telegram(f"🛡️ WallHunter EXIT - Stopped out at Profitable Break-even!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nExit Price: {current_price:.6f}\nSecured PnL: ${pnl_val:.2f}")
            else:
                 self.total_realized_pnl += pnl_val
                 if pnl_val > 0:
                     self.total_wins += 1
                     await self._send_telegram(f"🛡️ WallHunter EXIT - Stopped out in Profit!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nExit Price: {current_price:.6f}\nSecured PnL: ${pnl_val:.2f}")
                 else:
                     self.total_losses += 1
                     await self._send_telegram(f"🛑 WallHunter EXIT - Stopped Out!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            self.logger.info("Exit: Stop Loss / TSL Hit")
            
        elif (current_price <= self.active_pos['tp'] if getattr(self, 'strategy_mode', 'long') == 'short' else current_price >= self.active_pos['tp']):
            self.logger.info(f"✅ Triggering Final TP: Current Price ({current_price:.6f}) hit TP ({self.active_pos['tp']:.6f})")
            
            sell_amount_raw = self.active_pos['amount']
            close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
            
            if getattr(self, 'strategy_mode', 'long') == "short":
                sell_order_type = getattr(self, 'sell_order_type', 'market')
                calc_price = self.active_pos['tp']
                if sell_order_type == 'market' or sell_order_type == 'marketable_limit':
                     calc_price = current_price * (1 + (self.config.get("limit_buffer", 1.0) / 100.0))
                close_amount_raw = (sell_amount_raw * self.active_pos['entry'] * 0.99) / calc_price
            else:
                close_amount_raw = sell_amount_raw
            
            sell_order_type = self.sell_order_type
            if sell_order_type == 'marketable_limit':
                sell_order_type = 'market'

            if sell_order_type == 'market':
                res = await self.engine.execute_trade(close_side, sell_amount, current_price)
                
                # --- NEW: Partial Fill Management for Active TP Exits ---
                if res and res.get('id') and not self.is_paper_trading:
                    try:
                        order_status = None
                        for _ in range(5):
                            await asyncio.sleep(0.4)
                            try:
                                order_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                                if order_status and order_status.get('status') != 'open':
                                    break
                            except Exception: pass
                        
                        if order_status and order_status.get('status') == 'open':
                            self.logger.warning(f"⚠️ Exit Final TP order {res['id']} is hanging open! Cancelling remainder...")
                            await self.engine.cancel_order(res['id'])
                            await asyncio.sleep(0.5)
                            
                            final_status = await self.engine.exchange.fetch_order(res['id'], self.symbol)
                            filled = final_status.get('filled', 0.0)
                            
                            filled_proper = float(self.engine.exchange.amount_to_precision(self.symbol, filled)) if hasattr(self.engine.exchange, 'amount_to_precision') else filled
                            remaining_base = max(0.0, sell_amount_raw - filled_proper)
                            
                            if remaining_base > 0:
                                self.logger.info(f"🧹 Sweeping Final TP remainder at Pure Market: {remaining_base} {self.symbol}")
                                sweep_amount_raw = (remaining_base * self.active_pos['entry'] * 0.995) / current_price if getattr(self, 'strategy_mode', 'long') == "short" else remaining_base
                                sweep_amount = float(self.engine.exchange.amount_to_precision(self.symbol, sweep_amount_raw))
                                
                                await self.engine.execute_trade(close_side, sweep_amount, current_price, order_type="market")
                                self.logger.info("✅ Market sweep for Final TP completed.")
                    except Exception as e:
                        self.logger.error(f"Error checking Final TP partial fill sweep: {e}")
                # --------------------------------------------------------
            else:
                self.logger.info(f"Target Profit {self.active_pos['tp']} reached. Assuming Limit Order {self.active_pos.get('limit_order_id', 'Unknown')} is filled.")
                if self.is_paper_trading:
                    # Finalize the initial limit order mock by executing a market sell at the TP price
                    await self.engine.execute_trade(close_side, sell_amount, self.active_pos['tp'])
            
            # Calculate PnL
            if getattr(self, 'strategy_mode', 'long') == "short":
                pnl_val = (self.active_pos['entry'] - current_price) * sell_amount_raw
            else:
                pnl_val = (current_price - self.active_pos['entry']) * sell_amount_raw
                
            self.total_realized_pnl += pnl_val
            self.total_executed_orders += 1
            if pnl_val > 0:
                self.total_wins += 1
            else:
                self.total_losses += 1
            await self._send_telegram(f"🎯 WallHunter EXIT - Final Take Profit Hit!\nPair: {self.symbol}\nMode: {getattr(self, 'strategy_mode', 'long').upper()}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            self.logger.info("Exit: Take Profit Hit")

    async def stop(self):
        """বট স্টপ করার জন্য রিসোর্স ক্লিনআপ"""
        self.running = False
        self.logger.info(f"🛑 [WallHunter {self.bot_id}] Stopping...")
        
        # --- FIX: Task Memory Leak / CPU Spike Prevention ---
        for task_attr in ['_main_task', '_heartbeat_task', '_vpvr_task', '_atr_task', '_liq_task', '_trades_task', '_btc_task']:
            task = getattr(self, task_attr, None)
            if task and not task.done():
                try:
                    task.cancel()
                except Exception as e:
                    self.logger.error(f"Error cancelling task {task_attr}: {e}")
                    
        if hasattr(self, 'btc_correlation_tracker') and self.btc_correlation_tracker:
            try:
                await self.btc_correlation_tracker.stop()
            except: pass
            
        try:
            if hasattr(self, 'public_exchange') and self.public_exchange:
                await self.public_exchange.close()
        except: pass
            
        self.logger.info(f"Bot {self.bot_id} (WallHunter) stopped.")
        await self._send_telegram(f"🔴 WallHunter Bot [ID: {self.bot_id}] Stopped.")

    async def emergency_sell(self, sell_type: str):
        """Emergency liquidate the active position."""
        if not self.active_pos:
            self.logger.info(f"No active position to emergency sell for bot {self.bot_id}")
            return
            
        sell_amount = self.active_pos['amount']
        
        # Determine the execution price
        try:
            limit = market_depth_service._normalize_order_book_limit(self.exchange_id, 5)
            ob = await self.public_exchange.fetch_order_book(self.symbol, limit=limit)
            best_bid = ob['bids'][0][0] if ob['bids'] else 0
            best_ask = ob['asks'][0][0] if ob['asks'] else 0
            current_price = (best_bid + best_ask) / 2 if best_bid and best_ask else best_bid or best_ask
        except Exception as e:
            self.logger.warning(f"Could not fetch precise market price for emergency sell: {e}")
            current_price = self.active_pos['entry'] # Fallback
            
        if current_price <= 0:
            raise Exception("Invalid market price fetched.")
            
        # Cancel any open limit orders first
        if self.active_pos.get('limit_order_id'):
            try:
                await self.engine.cancel_order(self.active_pos['limit_order_id'])
                self.logger.info(f"Cancelled open limit order {self.active_pos['limit_order_id']} for emergency sell.")
            except Exception as e:
                self.logger.warning(f"Failed to cancel open limit order during emergency sell: {e}")
                
        close_side = "buy" if getattr(self, 'strategy_mode', 'long') == "short" else "sell"
        action_name = "BUY" if close_side == "buy" else "SELL"
        
        if sell_type in ["market", "marketable_limit"]:
            actual_type = "market" # Engine will convert to marketable limit if needed
            self.logger.info(f"🚨 Executing EMERGENCY {sell_type.upper()} {action_name} for bot {self.bot_id} at ~{current_price}")
            await self.engine.execute_trade(close_side, sell_amount, current_price, order_type=actual_type)
            self.total_executed_orders += 1
            
            # Finalize position and PnL
            if getattr(self, 'strategy_mode', 'long') == "short":
                pnl_val = (self.active_pos['entry'] - current_price) * sell_amount
            else:
                pnl_val = (current_price - self.active_pos['entry']) * sell_amount
                
            self.total_realized_pnl += pnl_val
            if pnl_val > 0:
                self.total_wins += 1
            else:
                self.total_losses += 1
            await self._send_telegram(f"🚨 WallHunter EMERGENCY EXIT - {sell_type.upper()} {action_name}!\nPair: {self.symbol}\nExit Price: {current_price:.6f}\nPnL: ${pnl_val:.2f}")
            self.active_pos = None
            
        elif sell_type == "limit":
            # For a limit exit, we'll try to place it at the best ask/bid or current market mid-price 
            close_price = best_bid if close_side == "buy" and best_bid > 0 else (best_ask if best_ask > 0 else current_price)
            self.logger.info(f"🎯 Executing EMERGENCY LIMIT {action_name} for bot {self.bot_id} at {close_price}")
            limit_res = await self.engine.execute_trade(close_side, sell_amount, close_price, order_type="limit")
            
            if limit_res and 'id' in limit_res:
                self.active_pos['limit_order_id'] = limit_res['id']
                # We also update the TP tracking to this new limit price
                self.active_pos['tp'] = close_price
                self.sell_order_type = 'limit' # Force limit mode if it wasn't
                await self._send_telegram(f"🎯 WallHunter EMERGENCY EXIT - Limit Placed!\nPair: {self.symbol}\nLimit Price: {close_price:.6f}")
            else:
                raise Exception("Failed to place emergency limit order.")
        else:
            raise ValueError(f"Unknown sell_type: {sell_type}")

    async def _vpvr_updater_loop(self):
        """Background task to update High Volume Nodes every 5 minutes."""
        while self.running:
            if not self.vpvr_enabled:
                await asyncio.sleep(60) # Check again in 1 min if disabled
                continue
                
            try:
                # Fetch last 100 5m candles
                ohlcv = await self.public_exchange.fetch_ohlcv(self.symbol, timeframe='5m', limit=100)
                if not ohlcv:
                    await asyncio.sleep(60)
                    continue
                    
                # Simple Volume Profile calculation (50 bins)
                low_prices = [candle[3] for candle in ohlcv]
                high_prices = [candle[2] for candle in ohlcv]
                
                min_price = min(low_prices)
                max_price = max(high_prices)
                
                if max_price == min_price:
                    await asyncio.sleep(300)
                    continue
                    
                bin_count = 50
                bin_size = (max_price - min_price) / bin_count
                bins = [0.0] * bin_count
                
                for candle in ohlcv:
                    c_low, c_high, c_vol = candle[3], candle[2], candle[5]
                    c_mid = (c_low + c_high) / 2
                    bin_idx = int((c_mid - min_price) / bin_size)
                    if bin_idx >= bin_count: bin_idx = bin_count - 1
                    bins[bin_idx] += c_vol
                
                # Find top 3 bins
                sorted_bins = sorted([(vol, idx) for idx, vol in enumerate(bins)], reverse=True)
                top_3 = sorted_bins[:3]
                
                self.top_hvns = [min_price + (idx * bin_size) + (bin_size / 2) for vol, idx in top_3]
                self.logger.info(f"📊 [WallHunter {self.bot_id}] VPVR Updated. Top 3 HVNs: {[f'{h:.6f}' for h in self.top_hvns]}")
                
            except Exception as e:
                self.logger.error(f"VPVR Update Error: {e}")
                
            await asyncio.sleep(300) # Every 5 minutes

    async def _trades_listener(self):
        """Background task to watch trades and feed the AbsorptionTracker."""
        self.logger.info(f"📣 [WallHunter {self.bot_id}] Starting Trades Listener for CVD Absorption...")
        while self.running:
            try:
                # We use public exchange for trades as it's typically faster/unthrottled
                trades = await self.public_exchange.watch_trades(self.symbol)
                if not trades:
                    continue
                    
                for trade in trades:
                    # price, amount, side
                    p = float(trade['price'])
                    a = float(trade['amount'])
                    s = trade['side'] # 'buy' (hits ask) or 'sell' (hits bid)
                    
                    self.absorption_tracker.add_trade(p, a, s)
                    
            except Exception as e:
                if self.running:
                    self.logger.warning(f"Trade Listener Error: {e}")
                await asyncio.sleep(1)

    async def _atr_updater_loop(self):
        """Background task to calculate ATR every 1 minute."""
        while self.running:
            if not self.atr_sl_enabled:
                await asyncio.sleep(60)
                continue
                
            try:
                # Fetch last N candles
                limit = self.atr_period + 1
                ohlcv = await self.public_exchange.fetch_ohlcv(self.symbol, timeframe='1m', limit=limit)
                
                if ohlcv and len(ohlcv) >= 2:
                    tr_list = []
                    for i in range(1, len(ohlcv)):
                        high = ohlcv[i][2]
                        low = ohlcv[i][3]
                        prev_close = ohlcv[i-1][4]
                        
                        tr1 = high - low
                        tr2 = abs(high - prev_close)
                        tr3 = abs(low - prev_close)
                        tr = max(tr1, tr2, tr3)
                        tr_list.append(tr)
                        
                    # Calculate simple moving average of True Range
                    if len(tr_list) >= self.atr_period:
                        recent_trs = tr_list[-self.atr_period:]
                        self.current_atr = sum(recent_trs) / self.atr_period
                        self.logger.info(f"📈 [WallHunter {self.bot_id}] ATR Updated: {self.current_atr:.6f} (Period: {self.atr_period})")
            except Exception as e:
                self.logger.error(f"ATR Update Error: {e}")
                
            await asyncio.sleep(60) # Update every minute

    async def _liquidation_listener(self):
        """Listen to global Redis stream for liquidations"""
        self.logger.info(f"🎧 [WallHunter {self.bot_id}] Starting Liquidation Listener for {self.symbol}...")
        if not self.redis:
            await asyncio.sleep(5)
            self.redis = get_redis_client()
            
        pubsub = self.redis.pubsub()
        current_channel = None
        
        while self.running:
            try:
                if self.enable_liq_trigger:
                    
                    # --- NEW: Dynamic Channel Switching ---
                    target_channel = f"stream:liquidations:BTC/USDT" if self.follow_btc_liq else f"stream:liquidations:{self.symbol}"
                    
                    if current_channel != target_channel:
                        if current_channel:
                            pubsub.unsubscribe(current_channel)
                            self.logger.info(f"🎧 [WallHunter {self.bot_id}] Unsubscribed from {current_channel}")
                        pubsub.subscribe(target_channel)
                        current_channel = target_channel
                        self.logger.info(f"🎧 [WallHunter {self.bot_id}] Subscribed to {current_channel}")
                        
                    message = pubsub.get_message(ignore_subscribe_messages=True)
                    if message and message['type'] == 'message':
                        try:
                            # Handle different data structures safely
                            if isinstance(message['data'], bytes):
                                data = json.loads(message['data'].decode('utf-8'))
                            else:
                                data = json.loads(message['data'])
                            
                            # Custom Terminal Logs based on feature
                            liq_side = data.get("side", "").upper()
                            liq_amount_raw = float(data.get("amount", 0))
                            
                            if self.follow_btc_liq:
                                self.logger.info(f"\n==============================================")
                                self.logger.info(f"🔥 [BTC LIQUIDATION] {liq_side} | Amount: ${liq_amount_raw:,.2f}")
                                self.logger.info(f"==============================================\n")
                            else:
                                self.logger.info(f"🔍 [WallHunter {self.bot_id}] Raw Liq Alert: {data}")
                            
                            custom_side = getattr(self, 'liq_target_side', 'auto')
                            if custom_side in ["long", "short"]:
                                target_liq_side = custom_side
                            else:
                                target_liq_side = "long" if getattr(self, 'strategy_mode', 'long') == "short" else "short"
                                
                            if data.get("side") == target_liq_side:
                                current_raw_time = time.time()
                                liq_amount = float(data.get("amount", 0))
                                
                                # 1. Cascade Logic
                                cascade_total = liq_amount
                                if self.enable_liq_cascade:
                                    self.liq_history.append((current_raw_time, liq_amount))
                                    # Clean old entries
                                    while self.liq_history and current_raw_time - self.liq_history[0][0] > self.liq_cascade_window:
                                        self.liq_history.popleft()
                                    cascade_total = sum(amount for _, amount in self.liq_history)
                                
                                # 2. Dynamic Threshold Logic & BTC Follower
                                base_threshold = self.btc_liq_threshold if self.follow_btc_liq else self.liq_threshold
                                active_threshold = base_threshold
                                
                                if self.enable_dynamic_liq and self.current_atr > 0 and not self.follow_btc_liq:
                                    try:
                                        current_price = float(data.get("price", 0))
                                        if current_price > 0:
                                           atr_pct = self.current_atr / current_price
                                           active_threshold = base_threshold * (1 + (atr_pct * 10 * self.dynamic_liq_multiplier))
                                    except: pass
                                
                                # 3. Trigger check
                                if cascade_total >= active_threshold:
                                    triggered_symbol = "BTC/USDT" if self.follow_btc_liq else self.symbol
                                    self.logger.info(f"💥 {target_liq_side.capitalize()} Liquidation Triggered! Stream: {triggered_symbol} | Cascade Total: ${cascade_total:.2f} | Threshold: ${active_threshold:.2f}")
                                    if self.enable_liq_cascade:
                                        self.liq_history.clear() # Reset after triggering
                                    await self._handle_liquidation_trigger(data)
                                    
                        except json.JSONDecodeError:
                            self.logger.error(f"Failed to decode Redis liquidation message: {message['data']}")
            except Exception as e:
                self.logger.error(f"Liquidation Listener Error: {e}")
            await asyncio.sleep(0.1)

    async def _handle_liquidation_trigger(self, liq_data):
        if self.active_pos: return
        
        try:
            limit = market_depth_service._normalize_order_book_limit(self.exchange_id, 20)
            ob = await self.public_exchange.fetch_order_book(self.symbol, limit=limit)
            if not ob['bids'] or not ob['asks']: return
            
            best_bid = ob['bids'][0][0]
            best_ask = ob['asks'][0][0]
            mid_price = (best_bid + best_ask) / 2
            
            # --- 1. Orderbook Imbalance Check (Tape Reading) ---
            if self.enable_ob_imbalance:
                # Calculate volume ratio near mid price
                bid_vol = sum(level[1] for level in ob['bids'])
                ask_vol = sum(level[1] for level in ob['asks'])
                
                if ask_vol > 0:
                    current_ratio = bid_vol / ask_vol
                    if current_ratio < self.ob_imbalance_ratio:
                        self.logger.info(f"⏭️ Liquidation ignoring: OB Imbalance Ratio too low ({current_ratio:.2f} < {self.ob_imbalance_ratio})")
                        return
                    else:
                        self.logger.info(f"✅ OB Imbalance check passed ({current_ratio:.2f} >= {self.ob_imbalance_ratio})")
                else:
                    return # No asks, weird state
                
            # --- 2. Confluence Mode (Wall Check) ---
            entry_side = "sell" if getattr(self, 'strategy_mode', 'long') == "short" else "buy"
            target_price = best_ask if entry_side == "sell" else best_bid
            
            if self.enable_wall_trigger:
                # Check for walls
                strong_wall_found = False
                wall_price = 0
                search_levels = ob['asks'] if entry_side == "sell" else ob['bids']
                
                for level in search_levels:
                    price, vol = level[0], level[1]
                    if vol >= self.micro_scalp_min_wall:
                        strong_wall_found = True
                        wall_price = price
                        break
                        
                if strong_wall_found:
                    self.logger.info(f"🔥 Confluence Met: Liquidation + Wall at {wall_price}. Sniping ({entry_side.upper()})!")
                    await self.execute_snipe(wall_price, entry_side, mid_price)
                else:
                    self.logger.info(f"⏭️ Liquidation ignoring: No supporting wall (Needed >= {self.micro_scalp_min_wall})")
            else:
                # Only Liquidation mode
                self.logger.info(f"🔥 Liquidation Snipe at {target_price}")
                await self.execute_snipe(target_price, entry_side, mid_price)
                
        except Exception as e:
             self.logger.error(f"Liquidation Handling Error: {e}")
