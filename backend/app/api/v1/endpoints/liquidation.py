from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio
from app.services.liquidation_service import LiquidationService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global instance for the service (Singleton pattern for this module)
liquidation_service = LiquidationService()
service_task = None

@router.websocket("/ws/stream")
async def websocket_liquidation_stream(websocket: WebSocket):
    """
    WebSocket endpoint to stream real-time liquidation data.
    """
    global service_task
    
    await websocket.accept()
    logger.info("Client connected to Liquidation Stream")

    # Start the service if not already running
    if not liquidation_service._running:
         service_task = asyncio.create_task(liquidation_service.start())
         logger.info("Liquidation Service started on demand.")

    async def send_to_client(data):
        try:
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
        logger.info("Client disconnected from Liquidation Stream")
        # Remove callback? verify simplistic removal or just handle error in broadcast
        # simple list.remove might be risky if not exact object ref, but here we defined inner function
        if send_to_client in liquidation_service._callbacks:
            liquidation_service._callbacks.remove(send_to_client)
            
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if send_to_client in liquidation_service._callbacks:
            liquidation_service._callbacks.remove(send_to_client)
