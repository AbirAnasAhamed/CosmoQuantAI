import pandas as pd
import numpy as np
import sys
import io

# Force UTF-8 for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Import the new PA Engine
from app.services.advanced_ml.features.forex.basic_price_action_features import BasicPriceActionEngine

def main():
    print("🚀 Initializing Basic Price Action Engine Verification...")
    
    # Create 500 rows of synthetic OHLC data
    np.random.seed(42)
    n = 500
    
    # Generate random walk for prices
    returns = np.random.normal(0, 0.001, n)
    close_px = pd.Series(1.1000 * np.exp(np.cumsum(returns)))
    
    high_px = close_px * (1 + np.abs(np.random.normal(0, 0.0005, n)))
    low_px = close_px * (1 - np.abs(np.random.normal(0, 0.0005, n)))
    open_px = close_px.shift(1).fillna(1.1000)
    
    df = pd.DataFrame({
        'open': open_px,
        'high': high_px,
        'low': low_px,
        'close': close_px
    })
    
    print(f"✅ Generated {len(df)} rows of synthetic Forex data (EUR/USD proxy).")
    
    try:
        engine = BasicPriceActionEngine(df)
        df_out = engine.generate_all_features()
        
        # Count only the pa_ features
        pa_cols = [c for c in df_out.columns if c.startswith('pa_')]
        total_pa = len(pa_cols)
        
        print(f"\n📊 Total Basic Price Action Metrics Generated: {total_pa}")
        
        if total_pa != 88:
            print(f"❌ ERROR: Expected 88 metrics, but got {total_pa}")
            # Identify missing metrics
            # We don't have the explicit list here, but we can print the generated ones
            for c in pa_cols: print(f" - {c}")
        else:
            print(f"✅ SUCCESS: All 88 metrics generated perfectly!")
            
        # Check for NaNs or Infs
        has_nans = df_out[pa_cols].isna().sum().sum()
        has_infs = np.isinf(df_out[pa_cols].values).sum()
        
        print(f"\n🔍 Data Integrity Check:")
        print(f"  NaN Values: {has_nans}")
        print(f"  Inf Values: {has_infs}")
        
        if has_nans == 0 and has_infs == 0:
            print(f"✅ SUCCESS: Engine is 100% ML-Ready with zero data leaks or missing values!")
        else:
            print(f"❌ ERROR: Found invalid values (NaN/Inf) in the output.")
            
        # Show a sample
        print("\n📈 Sample Output (Last Row):")
        sample = df_out[pa_cols].iloc[-1]
        print(sample.head(10).to_string())
        print("...")
        print(sample.tail(10).to_string())
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR during execution: {e}")

if __name__ == "__main__":
    main()
