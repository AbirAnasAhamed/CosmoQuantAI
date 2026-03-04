from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Any
import json
import asyncio
import websockets
from app.services.market_depth_service import market_depth_service

router = APIRouter()

@router.get("/heatmap", response_model=Any)
async def get_order_book_heatmap(
    symbol: str = Query(..., description="Trading pair, e.g., 'BTC/USDT'"),
    exchange: str = Query("binance", description="Exchange name, e.g., 'binance'"),
    bucket_size: float = Query(50.0, description="Price bucket size for aggregation"),
    depth: int = Query(100, description="Depth of order book to fetch")
) -> Any:
    """
    Get aggregated order book data for heatmap visualization.
    """
    try:
        data = await market_depth_service.fetch_order_book_heatmap(
            symbol=symbol,
            exchange_id=exchange,
            depth=depth,
            bucket_size=bucket_size
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/exchanges", response_model=list[str])
async def get_exchanges() -> Any:
    """List available exchanges."""
    return await market_depth_service.get_available_exchanges()

@router.get("/markets", response_model=list[str])
async def get_markets(
    exchange: str = Query(..., description="Exchange ID")
) -> Any:
    """List markets (symbols) for an exchange."""
    try:
        return await market_depth_service.get_exchange_markets(exchange)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ohlcv", response_model=Any)
async def get_ohlcv(
    symbol: str = Query(..., description="Trading Pair"),
    exchange: str = Query(..., description="Exchange ID"),
    timeframe: str = Query("1h", description="Timeframe (1m, 1h, 1d)"),
    limit: int = Query(100, description="Number of candles")
) -> Any:
    """Get OHLCV data for chart."""
    try:
        return await market_depth_service.fetch_ohlcv(symbol, exchange, timeframe, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{symbol}")
async def websocket_market_depth(websocket: WebSocket, symbol: str):
    await websocket.accept()
    
    clean_symbol = symbol.replace("/", "").replace("-", "").lower()
    binance_ws_url = f"wss://stream.binance.com:9443/ws/{clean_symbol}@depth20@100ms"
    
    try:
        async with websockets.connect(binance_ws_url) as ws:
            while True:
                data = await ws.recv()
                parsed_data = json.loads(data)
                
                bids = []
                bid_total = 0
                for price_str, size_str in parsed_data.get('bids', []):
                    price = float(price_str)
                    size = float(size_str)
                    bid_total += size
                    bids.append({"price": price, "size": size, "total": bid_total})
                    
                asks = []
                ask_total = 0
                for price_str, size_str in parsed_data.get('asks', []):
                    price = float(price_str)
                    size = float(size_str)
                    ask_total += size
                    asks.append({"price": price, "size": size, "total": ask_total})
                
                is_doge = "doge" in clean_symbol
                wall_threshold = 200000 if is_doge else 3.0
                
                walls = []
                for ask in asks:
                    if ask["size"] >= wall_threshold:
                        walls.append({"price": ask["price"], "type": "sell", "size": ask["size"]})
                for bid in bids:
                    if bid["size"] >= wall_threshold:
                        walls.append({"price": bid["price"], "type": "buy", "size": bid["size"]})
                        
                current_price = 0
                if asks and bids:
                    current_price = (asks[0]["price"] + bids[0]["price"]) / 2
                
                payload = {
                    "bids": bids,
                    "asks": asks,
                    "walls": walls,
                    "currentPrice": current_price
                }
                
                await websocket.send_json(payload)
                
    except WebSocketDisconnect:
        print(f"Client disconnected from market depth stream for {symbol}")
    except Exception as e:
        print(f"Error in market depth websocket: {e}")
        try:
            await websocket.close()
        except:
            pass
