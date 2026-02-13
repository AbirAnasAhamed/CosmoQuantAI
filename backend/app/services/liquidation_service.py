import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, Callable, Awaitable

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiquidationService:
    """
    Service to fetch real-time liquidation data from Binance Futures WebSocket.
    """

    BINANCE_WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"
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

    async def _process_message(self, message: str):
        """
        Parse and process the incoming WebSocket message.
        
        Args:
            message: The raw JSON string from the WebSocket.
        """
        try:
            payload = json.loads(message)
            # The payload depends on the stream. For !forceOrder@arr, it's a dict or list.
            # According to Binance docs: {"e":"forceOrder", ...} or {"stream":"...", "data": {...}}
            
            # Identify if it's a raw event or wrapped stream event
            data = payload.get('data', payload)
            
            # forceOrder event structure:
            # {
            #   "e": "forceOrder",
            #   "E": 1568014460893,
            #   "o": {
            #     "s": "BTCUSDT",
            #     "S": "SELL",
            #     "o": "LIMIT",
            #     "f": "IOC",
            #     "q": "0.014",
            #     "p": "9910.41",
            #     "ap": "9910.41",
            #     "X": "FILLED",
            #     "l": "0.014",
            #     "z": "0.014",
            #     "T": 1568014460893
            #   }
            # }

            if data.get('e') == 'forceOrder':
                order_data = data.get('o', {})
                symbol = order_data.get('s')
                side = order_data.get('S') # SELL means Long Liquidation, BUY means Short Liquidation
                price = float(order_data.get('p', 0))
                quantity = float(order_data.get('q', 0))
                timestamp = order_data.get('T')
                
                usd_value = price * quantity

                # Map side to liquidation type
                # If the force order is SELL, it means a Long position was liquidated.
                # If the force order is BUY, it means a Short position was liquidated.
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
                # For debugging/logging purposes
                # logger.info(f"Liquidation: {symbol} {liquidation_type} ${usd_value:,.2f}")

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

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
                    logger.info(f"Connecting to {self.BINANCE_WS_URL}...")
                    
                    async with session.ws_connect(self.BINANCE_WS_URL) as ws:
                        self._ws = ws
                        logger.info("Connected to Binance Liquidation Stream.")
                        reconnect_delay = self.RECONNECT_DELAY_BASE # Reset delay on success

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
