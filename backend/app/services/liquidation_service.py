import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, Callable, Awaitable, Set

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiquidationService:
    """
    Service to fetch real-time liquidation data from Binance Futures WebSocket.
    Supports dynamic subscription to specific symbol streams.
    """

    # Base URL for combined streams
    BINANCE_WS_BASE_URL = "wss://fstream.binance.com/stream"
    RECONNECT_DELAY_BASE = 1  # Seconds
    MAX_RECONNECT_DELAY = 60  # Seconds

    def __init__(self):
        """
        Initialize the LiquidationService.
        """
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._callbacks: list[Callable[[Dict[str, Any]], Awaitable[None]]] = []
        
        # Track active subscriptions
        # We start with no subscriptions, or a default set if needed
        self._active_symbols: Set[str] = set()
        self._lock = asyncio.Lock()

    def register_callback(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Register a callback function to receive liquidation data.
        
        Args:
            callback: An async function that accepts a dictionary of liquidation data.
        """
        self._callbacks.append(callback)

    async def _broadcast(self, data: Dict[str, Any]):
        """
        Broadcast the liquidation data to registered callbacks.
        
        Args:
            data: The processed liquidation data dictionary.
        """
        for callback in self._callbacks:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    async def subscribe(self, symbols: list[str]):
        """
        Subscribe to specific symbol liquidation streams.
        
        Args:
            symbols: List of symbols to subscribe to (e.g., ['BTCUSDT', 'ETHUSDT']).
        """
        if not self._ws or self._ws.closed:
            # If not connected, just update the set; they will be subscribed on connect
            async with self._lock:
                for s in symbols:
                    self._active_symbols.add(s.lower())
            return

        # Filter out already subscribed symbols to avoid redundant requests
        new_symbols = [s.lower() for s in symbols if s.lower() not in self._active_symbols]
        if not new_symbols:
            return

        params = [f"{s}@forceOrder" for s in new_symbols]
        payload = {
            "method": "SUBSCRIBE",
            "params": params,
            "id": int(time.time() * 1000)
        }
        
        try:
            await self._ws.send_json(payload)
            async with self._lock:
                for s in new_symbols:
                    self._active_symbols.add(s)
            logger.info(f"Subscribed to: {new_symbols}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {new_symbols}: {e}")

    async def unsubscribe(self, symbols: list[str]):
        """
        Unsubscribe from specific symbol liquidation streams.
        
        Args:
            symbols: List of symbols to unsubscribe from.
        """
        if not self._ws or self._ws.closed:
            async with self._lock:
                for s in symbols:
                    self._active_symbols.discard(s.lower())
            return

        # Only unsubscribe if we are actually subscribed
        remove_symbols = [s.lower() for s in symbols if s.lower() in self._active_symbols]
        if not remove_symbols:
            return

        params = [f"{s}@forceOrder" for s in remove_symbols]
        payload = {
            "method": "UNSUBSCRIBE",
            "params": params,
            "id": int(time.time() * 1000)
        }

        try:
            await self._ws.send_json(payload)
            async with self._lock:
                for s in remove_symbols:
                    self._active_symbols.discard(s)
            logger.info(f"Unsubscribed from: {remove_symbols}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {remove_symbols}: {e}")

    async def _process_message(self, message: str):
        """
        Parse and process the incoming WebSocket message.
        
        Args:
            message: The raw JSON string from the WebSocket.
        """
        try:
            payload = json.loads(message)
            
            # Handle subscription responses (id/result fields)
            if 'result' in payload and 'id' in payload:
                # This is just a control message response
                return

            # Combine stream payloads look like:
            # {"stream": "<streamName>", "data": <rawEvent>}
            
            stream_name = payload.get('stream')
            data = payload.get('data')

            if not data:
                return

            if data.get('e') == 'forceOrder':
                order_data = data.get('o', {})
                symbol = order_data.get('s')
                side = order_data.get('S') # SELL means Long Liquidation, BUY means Short Liquidation
                price = float(order_data.get('p', 0))
                quantity = float(order_data.get('q', 0))
                timestamp = order_data.get('T')
                
                usd_value = price * quantity

                # Map side to liquidation type
                liquidation_type = "Long Liquidation" if side == "SELL" else "Short Liquidation"

                processed_data = {
                    "symbol": symbol,
                    "side": side,
                    "type": liquidation_type,
                    "price": price,
                    "quantity": quantity,
                    "usd_value": usd_value,
                    "timestamp": timestamp,
                    "time_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp / 1000))
                }
                
                await self._broadcast(processed_data)

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def get_klines(self, symbol: str, interval: str = '15m', limit: int = 50) -> list[Dict[str, Any]]:
        """
        Fetch historical klines (candles) from Binance REST API.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            interval: Time interval (e.g., '15m').
            limit: Number of candles to fetch.
            
        Returns:
            List of formatted candle data.
        """
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        raw_data = await response.json()
                        # Format: [open_time, open, high, low, close, volume, ...]
                        formatted_data = []
                        for d in raw_data:
                            formatted_data.append({
                                "time": d[0],
                                "open": float(d[1]),
                                "high": float(d[2]),
                                "low": float(d[3]),
                                "close": float(d[4]),
                                "volume": float(d[5])
                            })
                        return formatted_data
                    else:
                        logger.error(f"Failed to fetch klines: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error fetching klines: {e}")
                return []

    async def start(self):
        """
        Start the WebSocket connection loop with auto-reconnection.
        """
        self._running = True
        reconnect_delay = self.RECONNECT_DELAY_BASE

        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    self._session = session
                    
                    # Construct initial URL. If we have active symbols, we can connect directly to them?
                    # Actually, for Combined Streams, we can just connect to base URL and then send SUBSCRIBE.
                    # Or we can pass streams in query param: ?streams=btcusdt@forceOrder/ethusdt@forceOrder
                    
                    # Strategy: Connect to base, then immediately subscribe to tracked symbols.
                    url = self.BINANCE_WS_BASE_URL
                    
                    logger.info(f"Connecting to {url}...")
                    
                    async with session.ws_connect(url) as ws:
                        self._ws = ws
                        logger.info("Connected to Binance Liquidation Stream.")
                        reconnect_delay = self.RECONNECT_DELAY_BASE # Reset delay on success
                        
                        # Resubscribe to tracked symbols
                        async with self._lock:
                            current_symbols = list(self._active_symbols)
                        
                        if current_symbols:
                            logger.info(f"Resubscribing to: {current_symbols}")
                            # We must release lock before calling subscribe because subscribe takes the lock
                            # So we call the internal logic or just send raw JSON here?
                            # Let's just use the `active_symbols` set and standard subscribe frame manually 
                            # to avoid re-adding to set logic, or just call subscribe?
                            # Calling subscribe checks if active_symbols has it, but here we ARE inside the connection loop.
                            # Simpler: Just send the SUBCRIBE frame for all in `current_symbols`
                            params = [f"{s}@forceOrder" for s in current_symbols]
                            sub_payload = {
                                "method": "SUBSCRIBE",
                                "params": params,
                                "id": int(time.time() * 1000)
                            }
                            await ws.send_json(sub_payload)

                        async for msg in ws:
                            if not self._running:
                                break
                            
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self._process_message(msg.data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket connection closed with error: {ws.exception()}")
                                break
            
            except Exception as e:
                logger.error(f"Connection error: {e}")
            
            if self._running:
                logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self.MAX_RECONNECT_DELAY)

    async def stop(self):
        """
        Stop the service and close connections.
        """
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        logger.info("LiquidationService stopped.")

# Global Singleton Instance
liquidation_service = LiquidationService()

