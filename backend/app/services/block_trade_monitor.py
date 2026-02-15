
import ccxt.async_support as ccxt
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_FILE = "block_trade_config.json"

class BlockTradeMonitor:
    def __init__(self):
        self.config = self._load_config()
        self.exchanges = {}
        self.error_counts = {}
        self._initialize_exchanges()

    def _load_config(self) -> Dict:
        """Loads configuration from a JSON file or sets defaults."""
        default_config = {
            "min_block_value": 10000.0,  # Minimum value to be considered a block trade (USD)
            "whale_value": 500000.0,     # Value to be considered a whale trade (USD)
            "active_exchanges": ["binance", "bybit", "okx"]
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}. Using defaults.")
                return default_config
        
        # Save defaults if file doesn't exist
        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict):
        """Saves configuration to a JSON file."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def _initialize_exchanges(self):
        """Initializes CCXT exchange instances based on configuration."""
        self.exchanges = {}
        for exchange_id in self.config.get("active_exchanges", []):
            try:
                if hasattr(ccxt, exchange_id):
                    exchange_class = getattr(ccxt, exchange_id)
                    # Enable rate limiting and async mode
                    options = {
                        'enableRateLimit': True,
                        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    }
                    if exchange_id == 'okx':
                        options['options'] = {'defaultType': 'spot'}
                        
                    self.exchanges[exchange_id] = exchange_class(options)
                else:
                    logger.warning(f"Exchange {exchange_id} not found in ccxt.")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_id}: {e}")

    async def close_exchanges(self):
        """Closes all exchange connections."""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")

    def update_config(self, new_config: Dict):
        """Updates the configuration and re-initializes exchanges if needed."""
        self.config.update(new_config)
        self._save_config(self.config)
        
        # Re-initialize only if active_exchanges changed
        if "active_exchanges" in new_config:
            # We need to close existing ones first, but since this is sync and they are async,
            # we might leave dangling sessions if we just overwrite.
            # ideally this method should be async or schedule a close task.
            # For now, we will just re-init (old objects will be GC'd but might leave open connections)
             self._initialize_exchanges()
            
        return self.config

    def get_config(self) -> Dict:
        """Returns the current configuration."""
        return self.config

    def _handle_exchange_error(self, exchange_id: str, error: Exception):
        """Rate limits error logging for persistent exchange issues."""
        count = self.error_counts.get(exchange_id, 0) + 1
        self.error_counts[exchange_id] = count
        
        # Log immediately if it's the first time, or every 60th time
        if count == 1 or count % 60 == 0:
            msg = str(error)
            if "403" in msg or "Forbidden" in msg:
                 logger.warning(f"{exchange_id} API returned 403 Forbidden. Suppressing frequent logs. (Count: {count})")
            else:
                 logger.warning(f"Error fetching from {exchange_id}: {type(error).__name__} - {msg}. (Count: {count})")

    async def fetch_recent_trades(self, symbol: str, limit: int = 100) -> Dict[str, List[Dict]]:
        """
        Fetches recent trades from all active exchanges for a given symbol.
        Filters trades based on min_block_value.
        """
        all_block_trades = {}

        for exchange_id, exchange in self.exchanges.items():
            # logger.info(f"Fetching trades from {exchange_id} for {symbol}...")
            try:
                # CCXT Unified API (Async)
                trades = await exchange.fetch_trades(symbol, limit=limit)
                
                # Reset error count on success
                self.error_counts[exchange_id] = 0
                
                block_trades = []
                for trade in trades:
                    price = trade.get('price', 0)
                    amount = trade.get('amount', 0)
                    cost = trade.get('cost', 0) 
                    
                    if cost is None or cost == 0:
                        cost = price * amount

                    # Filter Logic
                    if cost >= self.config["min_block_value"]:
                        is_whale = cost >= self.config["whale_value"]
                        
                        trade_data = {
                            "exchange": exchange_id,
                            "symbol": symbol,
                            "price": price,
                            "amount": amount,
                            "value": cost,
                            "side": trade.get('side'),
                            "timestamp": trade.get('timestamp'),
                            "datetime": trade.get('datetime'),
                            "is_whale": is_whale
                        }
                        block_trades.append(trade_data)
                
                if block_trades:
                    all_block_trades[exchange_id] = block_trades
                    
            except Exception as e:
                self._handle_exchange_error(exchange_id, e)
                
        return all_block_trades

block_trade_monitor = BlockTradeMonitor()
