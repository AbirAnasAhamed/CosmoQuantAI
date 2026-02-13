from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio
from app.services.liquidation_service import liquidation_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/candles")
async def get_candles(symbol: str, interval: str = "15m", limit: int = 50):
    """
    Get historical candle data (klines).
    """
    return await liquidation_service.get_klines(symbol, interval, limit)

@router.websocket("/ws/stream")
async def websocket_liquidation_stream(websocket: WebSocket, symbol: str = "BTCUSDT"):
    """
    WebSocket endpoint to stream real-time liquidation data.
    args:
        symbol: The trading pair symbol to subscribe to (default: BTCUSDT).
    """
    await websocket.accept()
    logger.info(f"Client connected to Liquidation Stream for {symbol}")

    # Ensure symbol is uppercase for consistency
    target_symbol = symbol.upper()

    # Subscribe to the requested symbol
    await liquidation_service.subscribe([target_symbol])

    async def send_to_client(data):
        try:
            # Filter messages: Only send data for the requested symbol
            if data.get('symbol') == target_symbol:
                await websocket.send_json(data)
        except Exception as e:
            # If sending fails, we assume client disconnected or error state
            # The loop below will catch disconnect, but this handles send errors
            logger.error(f"Error sending to client: {e}")
            raise e

    # Register the callback
    liquidation_service.register_callback(send_to_client)

    try:
        # Keep the connection alive
        while True:
            # We just listen for messages (ping/pong) but don't expect specific commands for now
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from Liquidation Stream ({target_symbol})")
        # Remove callback
        if send_to_client in liquidation_service._callbacks:
            liquidation_service._callbacks.remove(send_to_client)
            
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if send_to_client in liquidation_service._callbacks:
            liquidation_service._callbacks.remove(send_to_client)
