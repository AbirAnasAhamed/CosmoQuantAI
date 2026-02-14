from fastapi import APIRouter, HTTPException, Query
from typing import Any
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
