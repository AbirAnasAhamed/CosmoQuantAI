from typing import List, Dict, Any
import random
from datetime import datetime, timedelta

class DarkPoolService:
    """
    Service to track "Smart Money" activity via Large Block Trades and OTC proxies.
    Since direct Dark Pool data is proprietary, this simulates "Institutional Flow"
    using algorthmic detection of large volume blocks.
    """

    def get_institutional_flow(self, symbol: str) -> Dict[str, Any]:
        """
        Generates simulated Dark Pool / OTC data for a given symbol.
        """
        # 1. Simulate recent large trades
        block_trades = self._simulate_block_trades(symbol)

        # 2. Calculate Sentiment
        buy_vol = sum(t['volume'] for t in block_trades if t['side'] == 'BUY')
        sell_vol = sum(t['volume'] for t in block_trades if t['side'] == 'SELL')
        total_vol = buy_vol + sell_vol

        sentiment_score = 0.0
        if total_vol > 0:
            # Range -1 (Bearish) to +1 (Bullish)
            sentiment_score = (buy_vol - sell_vol) / total_vol

        # 3. Calculate Net Flow
        net_flow = buy_vol - sell_vol

        return {
            "symbol": symbol,
            "sentiment_score": round(sentiment_score, 2),
            "net_flow": round(net_flow, 2),
            "large_buy_volume": round(buy_vol, 2),
            "large_sell_volume": round(sell_vol, 2),
            "block_trades": block_trades,
            "timestamp": datetime.now().isoformat()
        }

    def _simulate_block_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Simulates a list of recent large block trades.
        In production, this would query exchange websocket feeds for orders > $100k.
        """
        trades = []
        # Generate 5-10 recent large trades
        num_trades = random.randint(5, 10)
        
        # Base price simulation
        base_price = 45000 if symbol == "BTC" else 3000 if symbol == "ETH" else 100

        for _ in range(num_trades):
            # 60% chance of following the "trend" (random bias)
            bias = random.choice(['BUY', 'SELL']) 
            
            # Volume: 10 to 100 BTC (or equivalent)
            volume = random.uniform(10, 100) 
            
            # Slight price variation
            price = base_price * random.uniform(0.99, 1.01)
            
            # OTC / Dark Pool flags
            is_otc = random.choice([True, False])
            source = "OTC Desk" if is_otc else "Dark Pool"

            trades.append({
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
                "volume": round(volume, 2),
                "price": round(price, 2),
                "value_usd": round(volume * price, 2),
                "side": bias,
                "source": source
            })
            
        # Sort by latest
        trades.sort(key=lambda x: x['timestamp'], reverse=True)
        return trades

dark_pool_service = DarkPoolService()
