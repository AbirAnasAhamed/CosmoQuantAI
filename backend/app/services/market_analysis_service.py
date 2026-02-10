import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.services.quant_engine import calculate_correlation_matrix, calculate_cointegration, calculate_z_score

class MarketAnalysisService:
    def get_correlation_data(self, symbols: List[str], timeframe: str) -> Dict[str, Any]:
        """
        Get correlation matrix and cointegration analysis for a list of symbols.
        
        Args:
            symbols (List[str]): List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT']).
            timeframe (str): Timeframe (e.g., '1h', '1d').

        Returns:
            Dict[str, Any]: Dictionary containing 'matrix' and 'cointegrated_pairs'.
        """
        # 1. Fetch OHLCV Data (Mocked for now as per instructions)
        # Using a fixed seed for consistency during dev/test
        np.random.seed(42)  
        
        # Simulate fetching 100 periods of data
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=timeframe)
        
        data = {}
        # Generate some correlated random walks
        base_series = np.cumsum(np.random.randn(periods))
        
        for symbol in symbols:
            # Create some variety: some highly correlated to base, some noise
            noise = np.random.randn(periods) * 0.5
            # Just a simple mock: symbol price is base + specific trend + noise
            # randomize trend direction slightly so not all are identical
            trend = np.linspace(0, np.random.randint(-10, 10), periods)
            price_series = base_series + trend + noise + 1000 # Add base price
            data[symbol] = price_series
            
        df = pd.DataFrame(data, index=dates)
        
        # 2. Calculate Correlation Matrix
        correlation_matrix = calculate_correlation_matrix(df)
        
        # 3. Find Cointegrated Pairs & Calculate Z-Scores
        cointegrated_pairs = []
        
        # Iterate through unique pairs
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                sym_a = symbols[i]
                sym_b = symbols[j]
                
                series_a = df[sym_a]
                series_b = df[sym_b]
                
                # Cointegration Test
                coint_res = calculate_cointegration(series_a, series_b)
                
                if coint_res['is_cointegrated']:
                    # Calculate Spread and Z-Score for this pair
                    # Basic spread: A - B (in reality, requires hedge ratio)
                    # For this mock, we'll assume spread = A - B
                    spread = series_a - series_b
                    z_score = calculate_z_score(spread)
                    
                    cointegrated_pairs.append({
                        "asset_a": sym_a,
                        "asset_b": sym_b,
                        "score": coint_res['score'],
                        "p_value": coint_res['p_value'],
                        "is_cointegrated": coint_res['is_cointegrated'],
                        "z_score": z_score
                    })
                    
        return {
            "matrix": correlation_matrix,
            "cointegrated_pairs": cointegrated_pairs
        }


    def get_rolling_correlation(self, symbol_a: str, symbol_b: str, timeframe: str = "1h", window: int = 30) -> List[Dict[str, Any]]:
        """
        Get rolling correlation history for two assets.
        """
        # Mock data generation (consistent with get_correlation_data)
        np.random.seed(42)
        periods = 200 # More history for rolling
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=timeframe)
        
        # Base series
        base_series = np.cumsum(np.random.randn(periods))
        
        # Symbol A (base + noise)
        series_a = base_series + np.random.randn(periods) * 0.5 + 1000
        
        # Symbol B (correlated or not based on random choice? Let's make them correlated for demo)
        # Or even better, let's make correlation change over time
        # First half correlated, second half less correlated
        noise_b = np.random.randn(periods)
        series_b = base_series.copy()
        
        # Introduce regime change in correlation
        split = periods // 2
        series_b[split:] = series_b[split:] * -1 # Flip correlation in second half
        
        series_b = series_b + noise_b * 0.5 + 2000
        
        # Create DataFrames
        df_a = pd.Series(series_a, index=dates)
        df_b = pd.Series(series_b, index=dates)
        
        from app.services.quant_engine import calculate_rolling_correlation
        return calculate_rolling_correlation(df_a, df_b, window=window)

market_analysis_service = MarketAnalysisService()

