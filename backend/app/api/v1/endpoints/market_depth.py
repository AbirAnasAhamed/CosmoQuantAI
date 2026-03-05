from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Any
import json
import asyncio
import websockets
from app.services.market_depth_service import market_depth_service
from app.helpers.orderbook_math import calculate_dynamic_wall_threshold

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

import ccxt.pro as ccxtpro
import asyncio

@router.websocket("/ws/{exchange_id}/{symbol:path}")
async def websocket_market_depth(websocket: WebSocket, exchange_id: str, symbol: str):
    await websocket.accept()
    
    exchange_class = getattr(ccxtpro, exchange_id.lower(), None)
    if not exchange_class:
        await websocket.close(code=1008, reason="Exchange not supported")
        return
        
    exchange = exchange_class({'enableRateLimit': True})
    
    try:
        while True:
            try:
                # CCXT watch_order_book handles the WS connection gracefully behind the scenes
                orderbook = await exchange.watch_order_book(symbol.upper(), limit=50)
                
                bids = []
                bid_total = 0
                for bid in orderbook.get('bids', []):
                    price = float(bid[0])
                    size = float(bid[1])
                    bid_total += size
                    bids.append({"price": price, "size": size, "total": bid_total})
                    
                asks = []
                ask_total = 0
                for ask in orderbook.get('asks', []):
                    price = float(ask[0])
                    size = float(ask[1])
                    ask_total += size
                    asks.append({"price": price, "size": size, "total": ask_total})
                
                wall_threshold = calculate_dynamic_wall_threshold(bids, asks)
                
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
                break
            except RuntimeError as e:
                if "Cannot call" in str(e) and "send" in str(e):
                    print(f"Websocket already closed for {symbol}")
                    break
                print(f"RuntimeError on market depth stream for {symbol}: {e}")
                break
            except Exception as e:
                # Need to handle ccxt exceptions gracefully so it doesn't just crash on heartbeat or disconnect
                print(f"Error watching orderbook {symbol} on {exchange_id}: {e}")
                if "does not have market symbol" in str(e) or "bad symbol" in str(e).lower():
                    try:
                        await websocket.close(code=1008, reason="Invalid symbol")
                    except Exception:
                        pass
                    break
                await asyncio.sleep(1) # Backoff
                
    except WebSocketDisconnect:
        print(f"Client disconnected from market depth stream for {symbol}")
    except Exception as e:
        print(f"Error in market depth websocket setup: {e}")
    finally:
        try:
            await exchange.close()
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
