import pandas as pd
import numpy as np

def advanced_forex_data_cleaning(df: pd.DataFrame, missing_data_threshold: float, max_warmup_tolerance: float, naturally_zero_features: list, add_log: callable) -> pd.DataFrame:
    """
    Advanced data cleaning specifically designed for Forex ML training on datasets of all sizes.
    Handles 'indicator warmup' (initial NaNs) dynamically without deleting crucial features.
    
    1. Identifies the warmup period (consecutive NaNs from the start) for each feature.
    2. Drops features where the warmup period exceeds the max_warmup_tolerance (e.g., >30% of dataset).
    3. Trims the top N rows based on the maximum warmup period among the surviving features.
    4. Applies the standard missing data threshold filter on the remaining data.
    """
    if len(df) == 0:
        return df

    original_shape = df.shape
    total_rows = len(df)
    max_warmup_allowed = int(total_rows * max_warmup_tolerance)
    
    add_log(f"🧹 Starting Advanced Forex Data Cleaning. Total rows: {total_rows}. Max warmup tolerance: {max_warmup_tolerance*100}% ({max_warmup_allowed} rows).")
    
    warmup_periods = {}
    
    # 1. Warmup Detection
    for col in df.columns:
        if col in naturally_zero_features or col == 'target':
            continue
            
        # Count consecutive NaNs from the beginning of the series
        series = df[col].values
        warmup_len = 0
        for val in series:
            if pd.isna(val):
                warmup_len += 1
            else:
                break
        
        if warmup_len > 0:
            warmup_periods[col] = warmup_len
            
    # 2. Lagging Feature Removal
    features_to_drop = []
    for col, warmup in warmup_periods.items():
        if warmup > max_warmup_allowed:
            features_to_drop.append(col)
            
    if features_to_drop:
        df.drop(columns=features_to_drop, inplace=True)
        add_log(f"🗑️ Dropped {len(features_to_drop)} lagging features exceeding warmup tolerance (e.g., {features_to_drop[:3]}).")
        
    # Remove dropped features from warmup_periods dictionary
    for f in features_to_drop:
        del warmup_periods[f]
        
    # 3. Dynamic Trimming
    rows_to_trim = 0
    if warmup_periods:
        rows_to_trim = max(warmup_periods.values())
        
    if rows_to_trim > 0:
        df = df.iloc[rows_to_trim:].copy()
        add_log(f"✂️ Dynamically trimmed top {rows_to_trim} rows to handle indicator warmup. Remaining rows: {len(df)}.")
        
    # 4. Small Dataset Threshold Adjustment
    # Even after warmup trimming, small datasets shouldn't lose features too easily due to random missing data.
    final_threshold = missing_data_threshold
    if len(df) < 1000:
        final_threshold = max(0.85, missing_data_threshold)
        add_log(f"⚠️ Dataset is small ({len(df)} rows). Auto-adjusted missing_data_threshold from {missing_data_threshold} to {final_threshold} to prevent feature wipeout.")

    # 5. Standard Missing Data Filter
    from app.services.ml_utils import apply_missing_data_threshold
    
    df, _ = apply_missing_data_threshold(
        df=df,
        threshold=final_threshold,
        naturally_zero_features=naturally_zero_features,
        add_log=add_log
    )
    
    add_log(f"✅ Advanced Data Cleaning complete. Original shape: {original_shape}, Final shape: {df.shape}")
    return df
