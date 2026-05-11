import pandas as pd
import numpy as np
import os
import pandas_ta as ta

def process_historical_trades(file_path: str, bar_type: str = "time", bar_size: str = "1m", volume_threshold: float = 10.0, apply_indicators: list = None, add_log_func=print) -> pd.DataFrame:
    """
    Process raw trade tick data from CSV into ML-ready features.
    Supports both Time Bars and Volume Bars.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Trade file not found at {file_path}")
        
    add_log_func(f"Loading raw trades from {os.path.basename(file_path)}...")
    
    # Read the necessary columns. The downloader uses: ['id', 'timestamp', 'datetime', 'symbol', 'side', 'price', 'amount', 'cost']
    try:
        df = pd.read_csv(file_path, usecols=['datetime', 'price', 'amount', 'side'])
    except ValueError:
        # Fallback if 'side' is missing in some older formats
        df = pd.read_csv(file_path, usecols=['datetime', 'price', 'amount'])
        
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['price'] = df['price'].astype(float)
    df['amount'] = df['amount'].astype(float)
    
    # Estimate or use trade direction (1 for Buy, -1 for Sell)
    if 'side' in df.columns:
        df['trade_dir'] = df['side'].map({'buy': 1, 'sell': -1}).fillna(0)
    else:
        # Tick rule fallback
        df['price_change'] = df['price'].diff()
        df['trade_dir'] = np.where(df['price_change'] > 0, 1, np.where(df['price_change'] < 0, -1, 0))
        df['trade_dir'] = df['trade_dir'].replace(0, np.nan).ffill().fillna(0)
        
    df['signed_volume'] = df['amount'] * df['trade_dir']
    df['trade_count'] = 1
    
    add_log_func(f"Loaded {len(df)} raw trades. Generating {bar_type.upper()} bars...")
    
    if bar_type == "time":
        df.set_index('datetime', inplace=True)
        
        # Mapping timeframe string
        tf_map = {'1s': '1S', '5s': '5S', '1m': '1min', '5m': '5min', '15m': '15min', '1h': '1h', '4h': '4h', '1d': '1D'}
        pandas_tf = tf_map.get(bar_size.lower(), '1min')
        
        # Open, High, Low, Close, Volume
        bars = pd.DataFrame()
        bars['open'] = df['price'].resample(pandas_tf).first()
        bars['high'] = df['price'].resample(pandas_tf).max()
        bars['low'] = df['price'].resample(pandas_tf).min()
        bars['close'] = df['price'].resample(pandas_tf).last()
        bars['volume'] = df['amount'].resample(pandas_tf).sum()
        
        # Trade specific features
        buy_vol = df.loc[df['trade_dir'] == 1, 'amount'].resample(pandas_tf).sum()
        sell_vol = df.loc[df['trade_dir'] == -1, 'amount'].resample(pandas_tf).sum()
        bars['buy_volume'] = buy_vol.fillna(0)
        bars['sell_volume'] = sell_vol.fillna(0)
        
        bars['cvd'] = (bars['buy_volume'] - bars['sell_volume']).cumsum()
        bars['trade_count'] = df['trade_count'].resample(pandas_tf).sum()
        
        # FFill missing candles
        bars['close'] = bars['close'].ffill()
        bars['open'] = bars['open'].fillna(bars['close'])
        bars['high'] = bars['high'].fillna(bars['close'])
        bars['low'] = bars['low'].fillna(bars['close'])
        bars['volume'] = bars['volume'].fillna(0)
        bars['trade_count'] = bars['trade_count'].fillna(0)
        
    elif bar_type == "volume":
        df['cum_vol'] = df['amount'].cumsum()
        df['bar_id'] = (df['cum_vol'] // volume_threshold).astype(int)
        
        bars = df.groupby('bar_id').agg(
            datetime=('datetime', 'last'),
            open=('price', 'first'),
            high=('price', 'max'),
            low=('price', 'min'),
            close=('price', 'last'),
            volume=('amount', 'sum'),
            net_volume=('signed_volume', 'sum'),
            trade_count=('trade_count', 'sum')
        )
        bars.set_index('datetime', inplace=True)
        bars['cvd'] = bars['net_volume'].cumsum()
        bars['buy_volume'] = (bars['volume'] + bars['net_volume']) / 2
        bars['sell_volume'] = (bars['volume'] - bars['net_volume']) / 2
    else:
        raise ValueError("bar_type must be either 'time' or 'volume'")
        
    bars = bars.dropna()
    
    # Capitalize columns for consistency with rest of the engine
    bars.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    
    add_log_func(f"Generated {len(bars)} bars. Calculating requested indicators...")

    return bars
