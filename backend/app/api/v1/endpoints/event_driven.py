
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.event_driven.engine import EventDrivenEngine
import asyncio

router = APIRouter()

@router.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await websocket.accept()
    
    engine = None
    
    try:
        while True:
            # Wait for command from client
            data = await websocket.receive_json()
            
            if data.get("action") == "START":
                symbol = data.get("symbol", "BTC/USDT")
                # Initialize Engine
                engine = EventDrivenEngine(symbol=symbol, websocket=websocket)
                
                # Run the engine in background so we can listen for STOP command
                asyncio.create_task(engine.run())
                
            elif data.get("action") == "STOP":
                if engine:
                    engine.stop()
                    await websocket.send_json({"type": "SYSTEM", "message": "Simulation Stopped"})

    except WebSocketDisconnect:
        print("Client disconnected from Simulation Socket")
        if engine:
            engine.stop()
    except Exception as e:
        print(f"Error in Simulation Socket: {e}")
        if engine:
            engine.stop()
        try:
            await websocket.close()
        except:
            pass
