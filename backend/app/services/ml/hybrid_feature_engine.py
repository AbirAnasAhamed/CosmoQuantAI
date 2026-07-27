import pandas as pd
import numpy as np
import pandas_ta as ta

def generate_hybrid_features(df: pd.DataFrame, selected_features: list[str]) -> pd.DataFrame:
    """
    Dynamically generates advanced Hybrid (OHLCV + Tick) features.
    This runs at the model training stage on the merged hybrid dataset.
    """
    if df.empty or not selected_features:
        return df
        
    df.columns = [str(c).lower() for c in df.columns]
    
    # Identify tick-related columns
    tick_vol = df['tick_net_volume'] if 'tick_net_volume' in df.columns else df.get('tick_count', df.get('volume', pd.Series(1, index=df.index)))
    tick_ofi = df['tick_volume_imbalance'] if 'tick_volume_imbalance' in df.columns else pd.Series(0, index=df.index)
    
    # 3. Time, Speed & Session-based Features
    if 'tick_velocity' in selected_features:
        df['tick_velocity'] = df['tick_count'] / 5.0 # Assuming 5s aggregation base
    if 'volume_velocity' in selected_features:
        df['volume_velocity'] = tick_vol / 5.0
        
    # 4. Hybrid Price Action (Wyckoff & VSA)
    if 'hybrid_vwap' in selected_features:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['hybrid_vwap'] = (typical_price * tick_vol).cumsum() / (tick_vol.cumsum() + 1e-8)
        
    if 'hybrid_effective_spread' in selected_features and 'tick_spread' in df.columns:
        hl_range = df['high'] - df['low']
        df['hybrid_effective_spread'] = np.where(hl_range == 0, 0, df['tick_spread'] / hl_range)
        
    if 'hybrid_candle_body_ratio' in selected_features:
        body = abs(df['open'] - df['close'])
        df['hybrid_candle_body_ratio'] = body / (tick_vol + 1e-8)
        
    if 'hybrid_fractal_dimension' in selected_features and 'tick_path_variation' in df.columns:
        hl_range = df['high'] - df['low']
        df['hybrid_fractal_dimension'] = np.log(df['tick_path_variation'] + 1e-8) / np.log(hl_range + 1e-8)
        
    # 5. Liquidity & Risk Metrics
    if 'amihud_illiquidity' in selected_features:
        ret = abs(df['close'].pct_change().fillna(0))
        df['amihud_illiquidity'] = ret / (tick_vol + 1e-8)
        
    if 'tick_volume_to_range' in selected_features:
        hl_range = df['high'] - df['low']
        df['tick_volume_to_range'] = tick_vol / (hl_range + 1e-8)
        
    # 6. Order Flow Imbalance (OFI) Momentum & Divergence
    if 'ofi_sma' in selected_features:
        df['ofi_sma'] = tick_ofi.rolling(14).mean()
    if 'ofi_ema' in selected_features:
        df['ofi_ema'] = tick_ofi.ewm(span=14).mean()
    if 'ofi_rsi' in selected_features:
        delta = tick_ofi.diff()
        up = delta.where(delta > 0, 0).rolling(14).mean()
        down = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = up / (down + 1e-8)
        df['ofi_rsi'] = 100 - (100 / (1 + rs))
        
    if 'ofi_zscore' in selected_features:
        roll_mean = tick_ofi.rolling(14).mean()
        roll_std = tick_ofi.rolling(14).std()
        df['ofi_zscore'] = (tick_ofi - roll_mean) / (roll_std + 1e-8)
        
    if 'cumulative_ofi' in selected_features:
        df['cumulative_ofi'] = tick_ofi.cumsum()
        
    if 'ofi_acceleration' in selected_features:
        df['ofi_acceleration'] = tick_ofi.diff().diff()
        
    if 'ofi_divergence' in selected_features:
        price_roc = df['close'].pct_change()
        ofi_roc = tick_ofi.diff()
        # 1 if price up but OFI down, -1 if price down but OFI up, else 0
        df['ofi_divergence'] = np.where((price_roc > 0) & (ofi_roc < 0), -1, 
                               np.where((price_roc < 0) & (ofi_roc > 0), 1, 0))
                               
    # 7. ML Specific
    if 'tick_entropy' in selected_features:
        # Simple Shannon entropy of tick returns histogram in a rolling window
        pass # placeholder for complex calculation
        
    return df
