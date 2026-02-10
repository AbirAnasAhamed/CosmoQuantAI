import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint
from typing import Dict, Union, Tuple, List

def calculate_correlation_matrix(price_data: pd.DataFrame) -> Dict:
    """
    Calculate the Pearson correlation matrix of asset returns.
    
    Args:
        price_data (pd.DataFrame): DataFrame with asset symbols as columns and timestamps as rows.
                                   Values should be numeric prices.

    Returns:
        Dict: A dictionary representation of the correlation matrix.
              NaNs are replaced with 0.
    """
    # Calculate percentage change to get returns
    returns = price_data.pct_change()
    
    # Calculate correlation matrix
    correlation_matrix = returns.corr(method='pearson')
    
    # Replace NaNs with 0 (e.g., if a column has constant values or not enough data)
    correlation_matrix = correlation_matrix.fillna(0)
    
    # Convert to dictionary
    return correlation_matrix.to_dict()

def calculate_cointegration(series_a: Union[pd.Series, np.ndarray], series_b: Union[pd.Series, np.ndarray]) -> Dict:
    """
    Perform the Engle-Granger two-step cointegration test.
    
    Args:
        series_a: First time series (price data).
        series_b: Second time series (price data).

    Returns:
        Dict: A dictionary containing:
              - score (float): The t-statistic of the unit-root test on residuals.
              - p_value (float): MacKinnon's approximate p-value.
              - is_cointegrated (bool): True if p_value < 0.05, else False.
    """
    # Ensure inputs are valid 1D arrays/series and drop NaNs if aligned
    # Check for length match, etc. handled by statsmodels largely, but let's be safe
    # If using pandas, we might want to align indices, but the prompt implies simple series input
    # calculating cointegration requires aligned data usually.
    
    # Run cointegration test
    # coint returns: t-stat, p-value, crit_values
    score, p_value, _ = coint(series_a, series_b)
    
    return {
        "score": float(score),
        "p_value": float(p_value),
        "is_cointegrated": bool(p_value < 0.05)
    }

def calculate_z_score(spread: pd.Series, window: int = 20) -> float:
    """
    Calculate the rolling Z-Score of the spread.
    
    Args:
        spread (pd.Series): The spread time series (e.g., Asset A - Asset B * HedgeRatio).
        window (int): The rolling window size. Default is 20.

    Returns:
        float: The latest Z-Score value. 
               Returns 0.0 if not enough data.
    """
    if len(spread) < window:
        return 0.0

    rolling_mean = spread.rolling(window=window).mean()
    rolling_std = spread.rolling(window=window).std()
    
    z_score = (spread - rolling_mean) / rolling_std
    
    # Get the latest value. Handle potential NaNs at the start or if std is 0
    latest_z = z_score.iloc[-1]
    
    
    if pd.isna(latest_z) or np.isinf(latest_z):
        return 0.0
        
    return float(latest_z)

def calculate_rolling_correlation(series_a: pd.Series, series_b: pd.Series, window: int = 30) -> List[Dict[str, float]]:
    """
    Calculate the rolling correlation between two time series.

    Args:
        series_a (pd.Series): First time series.
        series_b (pd.Series): Second time series.
        window (int): Rolling window size.

    Returns:
        List[Dict[str, float]]: A list of dictionaries containing time and correlation value.
                                [{'time': timestamp, 'value': correlation}, ...]
    """
    # Ensure they are aligned
    df = pd.DataFrame({'a': series_a, 'b': series_b}).dropna()

    if len(df) < window:
        return []

    # Calculate rolling correlation
    rolling_corr = df['a'].rolling(window=window).corr(df['b'])

    # Convert to list of dicts
    result = []
    for date, value in rolling_corr.items():
        if pd.notna(value):
             time_val = date.isoformat() if hasattr(date, 'isoformat') else str(date)
             result.append({"time": time_val, "value": value})
             
    return result
