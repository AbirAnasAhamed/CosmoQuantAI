import pandas as pd
import numpy as np
import logging

class BasicPriceActionFeatures:
    """
    100% Modular, Vectorised, Hedge-Fund Grade Feature Engineering.
    Focus: Category 1 - Basic Price Action (Forex Layer Only).
    
    Contains 24 Matrices: 
    - 4 Legacy (Support, Resistance, Swing H/L, Price Rejection)
    - 20 Advanced (Frac Diff, CPR, Z-Score, Fractal Dim, etc.)
    """
    
    @staticmethod
    def calculate_all(df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Main entry point. Takes raw OHLCV and returns DataFrame with 24 new columns.
        Safeguarded against NaNs and specifically targeted for Forex data.
        """
        if df_raw.empty:
            return df_raw
            
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df_raw.columns:
                logging.warning(f"Missing column '{col}' for Basic Price Action features.")
                return df_raw
                
        df = df_raw.copy()
        
        # Helper variables
        close = df['close']
        high = df['high']
        low = df['low']
        open_p = df['open']
        
        try:
            # ==========================================
            # PHASE 1: Foundation & Stationarity (Math)
            # ==========================================
            
            # 1. Log Returns
            df['pa_log_returns'] = np.log(close / close.shift(1)).fillna(0)
            
            # 2. Price Acceleration (Momentum of returns)
            df['pa_price_acceleration'] = df['pa_log_returns'].diff().fillna(0)
            
            # 3. Fractional Differencing (Simplified proxy for fast vectorised HFT)
            # True frac diff requires expanding window math, which is slow for live ticks.
            # Here we use an institutional proxy: weighted blend of Return and Price Z-score
            z_price = (close - close.rolling(20, min_periods=1).mean()) / close.rolling(20, min_periods=1).std().clip(lower=1e-9)
            df['pa_frac_diff_proxy'] = (0.5 * df['pa_log_returns']) + (0.5 * z_price.diff().fillna(0))
            
            # ==========================================
            # PHASE 2: Micro-Structure & Geometry
            # ==========================================
            
            candle_range = (high - low).clip(lower=1e-9)
            
            # 4. Close Position in Range (CPR)
            df['pa_cpr'] = (close - low) / candle_range
            
            # 5. Upper Wick Ratio
            df['pa_upper_wick_ratio'] = (high - np.maximum(open_p, close)) / candle_range
            
            # 6. Lower Wick Ratio
            df['pa_lower_wick_ratio'] = (np.minimum(open_p, close) - low) / candle_range
            
            # 7. Body to Range Ratio
            df['pa_body_ratio'] = np.abs(close - open_p) / candle_range
            
            # 8. Session Gap (Close to Open)
            df['pa_session_gap'] = (open_p - close.shift(1)) / close.shift(1).clip(lower=1e-9)
            df['pa_session_gap'] = df['pa_session_gap'].fillna(0)
            
            # 9. True Range
            df['pa_true_range'] = np.maximum(high - low, 
                                  np.maximum(np.abs(high - close.shift(1)), 
                                             np.abs(low - close.shift(1))))
            
            # ==========================================
            # PHASE 3: Rolling Windows & Volatility
            # ==========================================
            
            # 10. Rolling Z-Score (Over-extension)
            df['pa_rolling_z_score'] = z_price.fillna(0)
            
            # 11. Historical Volatility (20-period StdDev of Log Returns)
            df['pa_hist_volatility'] = df['pa_log_returns'].rolling(20, min_periods=1).std().fillna(0)
            
            # 12. Consecutive Runs (Directional)
            trade_dir = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
            trade_dir_series = pd.Series(trade_dir, index=df.index)
            run_blocks = (trade_dir_series != trade_dir_series.shift()).cumsum()
            # Must multiply by trade_dir to know if the run is bullish (+3) or bearish (-3)
            df['pa_consecutive_runs'] = (trade_dir_series.groupby(run_blocks).cumcount() + 1) * trade_dir_series
            
            # 13. Inside / Outside Bar State
            is_inside = (high <= high.shift(1)) & (low >= low.shift(1))
            is_outside = (high > high.shift(1)) & (low < low.shift(1))
            df['pa_inside_outside'] = np.where(is_outside, 1, np.where(is_inside, -1, 0))
            
            # 14. Price vs N-Period Median
            median_20 = close.rolling(20, min_periods=1).median()
            df['pa_price_vs_median'] = (close - median_20) / median_20.clip(lower=1e-9)
            
            # ==========================================
            # PHASE 4: Legacy Upgrades & Market Dynamics
            # ==========================================
            
            # Calculate rolling pivots/swings for the legacy variables
            rolling_high_20 = high.rolling(20, min_periods=1).max()
            rolling_low_20 = low.rolling(20, min_periods=1).min()
            
            # 15. Legacy 1 Upgrade: Distance to Nearest Support (Dynamic)
            df['pa_dist_to_support'] = (close - rolling_low_20) / close.clip(lower=1e-9)
            
            # 16. Legacy 2 Upgrade: Distance to Nearest Resistance (Dynamic)
            df['pa_dist_to_resistance'] = (rolling_high_20 - close) / close.clip(lower=1e-9)
            
            # Find exact bars of swing highs/lows without LOOKAHEAD BIAS (Data Leakage)
            # A 5-bar swing high requires 2 lower bars before and 2 lower bars after.
            # We can only confirm it 2 bars AFTER it happens.
            swing_h_cond = (high.shift(2) > high.shift(3)) & (high.shift(2) > high.shift(4)) & (high.shift(2) > high.shift(1)) & (high.shift(2) > high)
            swing_l_cond = (low.shift(2) < low.shift(3)) & (low.shift(2) < low.shift(4)) & (low.shift(2) < low.shift(1)) & (low.shift(2) < low)
            
            df['is_swing_high'] = swing_h_cond.astype(int)
            df['is_swing_low'] = swing_l_cond.astype(int)
            
            # Distance to last swing high/low (Time & Price)
            # When swing is detected at time T, the actual swing price was at T-2
            df['swing_h_price'] = np.where(df['is_swing_high'] == 1, high.shift(2), np.nan)
            df['swing_l_price'] = np.where(df['is_swing_low'] == 1, low.shift(2), np.nan)
            
            last_swing_h_price = df['swing_h_price'].ffill()
            last_swing_l_price = df['swing_l_price'].ffill()
            
            # 17. Legacy 3 Upgrade A: Swing High Price Distance
            df['pa_swing_high_dist'] = (last_swing_h_price - close) / close.clip(lower=1e-9)
            df['pa_swing_high_dist'] = df['pa_swing_high_dist'].fillna(0)
            
            # 18. Legacy 3 Upgrade B: Swing Low Price Distance
            df['pa_swing_low_dist'] = (close - last_swing_l_price) / close.clip(lower=1e-9)
            df['pa_swing_low_dist'] = df['pa_swing_low_dist'].fillna(0)
            
            # 19. Legacy 4 Upgrade: Price Rejection Magnitude
            # Aggregation of wick ratio and volatility to define a 'rejection' score
            df['pa_price_rejection_score'] = (df['pa_upper_wick_ratio'] - df['pa_lower_wick_ratio']) * df['pa_true_range']
            
            # Time dynamics
            # 20. Bars Since Last Swing High
            # Swing confirmation has a 2-bar lag. So at confirmation, it's already been 2 bars.
            blocks_h = df['is_swing_high'].cumsum()
            df['pa_bars_since_swing_h'] = df.groupby(blocks_h).cumcount() + 2
            
            # 21. Bars Since Last Swing Low
            blocks_l = df['is_swing_low'].cumsum()
            df['pa_bars_since_swing_l'] = df.groupby(blocks_l).cumcount() + 2
            
            # 22. Daily Anchor / Midnight Open Distance (Robust logic)
            # Find the time column for daily grouping
            time_col = None
            if pd.api.types.is_datetime64_any_dtype(df.index):
                time_col = pd.Series(df.index.date, index=df.index)
            elif 'timestamp' in df.columns:
                time_col = pd.to_datetime(df['timestamp']).dt.date
            elif 'time' in df.columns:
                time_col = pd.to_datetime(df['time']).dt.date
            elif 'datetime' in df.columns:
                time_col = pd.to_datetime(df['datetime']).dt.date
                
            if time_col is not None:
                proxy_open = df.groupby(time_col)['open'].transform('first')
            else:
                # 288 bars = 24 hours of 5-min candles. Fallback for non-datetime index.
                proxy_open = open_p.shift(288).ffill().fillna(open_p)
                
            df['pa_dist_to_anchor'] = (close - proxy_open) / proxy_open.clip(lower=1e-9)
            
            # 23. Fractal Dimension (Scale-Independent Choppiness formulation)
            # The previous raw log(path) / log(net) is scale-dependent (fails across JPY vs USD).
            # This Choppiness Index formulation scales beautifully between 0 and 100 for any asset.
            sum_tr = df['pa_true_range'].rolling(20, min_periods=1).sum()
            net_range = rolling_high_20 - rolling_low_20
            # log10(sum_tr / net_range) / log10(20)
            df['pa_fractal_dimension'] = np.log10(sum_tr / net_range.clip(lower=1e-9)) / np.log10(20)
            df['pa_fractal_dimension'] = df['pa_fractal_dimension'].replace([np.inf, -np.inf], 0)
            df['pa_fractal_dimension'] = df['pa_fractal_dimension'].fillna(0)
            
            # 24. Donchian Channel Position
            df['pa_donchian_pos'] = (close - rolling_low_20) / np.maximum(rolling_high_20 - rolling_low_20, 1e-9)
            
        except Exception as e:
            logging.error(f"Error calculating Advanced Basic Price Action features: {e}")
            
        # Clean up temporary columns
        cleanup_cols = ['is_swing_high', 'is_swing_low', 'swing_h_price', 'swing_l_price']
        df = df.drop(columns=[c for c in cleanup_cols if c in df.columns])
        
        # Final NaN/Inf safeguard for ML models
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill()
        df = df.fillna(0)
        
        return df
