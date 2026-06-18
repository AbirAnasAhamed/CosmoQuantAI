import pandas as pd
import numpy as np

def generate_advanced_setup_targets(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """
    Generates MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion) 
    as ideal Take Profit (TP) and Stop Loss (SL) targets for a given forecast horizon.
    
    This function calculates the maximum positive excursion and maximum negative excursion
    relative to the 'Close' price over the next `horizon` rows.
    
    Args:
        df (pd.DataFrame): The historical market data containing 'Close', 'High', 'Low'.
                           If only 'Close' exists (e.g. tick data), it falls back to 'Close'.
        horizon (int): The forward-looking window size (e.g., 5 candles/ticks).
        
    Returns:
        pd.DataFrame: The dataframe with 'Target_Direction', 'Target_SL', 'Target_TP' appended.
    """
    # Defensive check
    if 'Close' not in df.columns:
        raise ValueError("DataFrame must contain a 'Close' column to calculate advanced setup targets.")

    # Determine which columns to use for Excursion
    # Tick data usually lacks High/Low, whereas OHLCV has them.
    high_col = 'High' if 'High' in df.columns else 'Close'
    low_col = 'Low' if 'Low' in df.columns else 'Close'

    # Calculate rolling maximum and minimum over the future horizon window
    # We reverse the dataframe, apply rolling window, then reverse back to simulate "looking forward"
    future_highs = df[high_col].iloc[::-1].rolling(window=horizon, min_periods=1).max().iloc[::-1]
    future_lows = df[low_col].iloc[::-1].rolling(window=horizon, min_periods=1).min().iloc[::-1]

    # Calculate exact future close for Direction
    future_close = df['Close'].shift(-horizon)
    future_return = future_close - df['Close']

    # Target 1: Direction (1 for Up, 0 for Down)
    df['Target_Direction'] = (future_return > 0).astype(float)

    # Target 2 & 3: TP (MFE) and SL (MAE) distances
    # MFE = Highest High in horizon - Current Close (for Longs)
    # MAE = Current Close - Lowest Low in horizon (for Longs)
    
    # We represent these as positive distances from the current price.
    # A model predicting this will learn the "Expected Volatility Bounds" for the upcoming horizon.
    df['Target_TP'] = (future_highs - df['Close']).clip(lower=0.0)
    df['Target_SL'] = (df['Close'] - future_lows).clip(lower=0.0)

    # Prevent look-ahead bias at the very end of the dataframe by masking NaN future returns
    # where the horizon goes out of bounds.
    mask = future_close.isna()
    df.loc[mask, 'Target_Direction'] = np.nan
    df.loc[mask, 'Target_TP'] = np.nan
    df.loc[mask, 'Target_SL'] = np.nan

    return df
