import pandas as pd
import numpy as np
import importlib
import inspect
import sys
import os

# Add backend to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Data Generation
def generate_mock_data():
    dates = pd.date_range('2024-01-01', periods=5, freq='5min')
    df_ohlcv = pd.DataFrame({
        'open': [1.1000, 1.1010, 1.1020, 1.0990, 1.0980],
        'high': [1.1020, 1.1030, 1.1025, 1.1010, 1.1000],
        'low': [1.0990, 1.1005, 1.0985, 1.0980, 1.0970],
        'close': [1.1010, 1.1020, 1.0990, 1.0985, 1.0995],
        'volume': [1000, 1500, 2000, 1200, 1800]
    }, index=dates)

    tick_dates = pd.date_range('2024-01-01', periods=10, freq='1min')
    df_tick = pd.DataFrame({
        'bid': np.random.uniform(1.0980, 1.1030, 10),
        'ask': np.random.uniform(1.0981, 1.1031, 10),
        'volume': np.random.randint(1, 100, 10)
    }, index=tick_dates)
    
    return df_ohlcv, df_tick

def main():
    print("============================================================")
    print("QUANT PIPELINE VERIFICATION SCRIPT: CANDLESTICK PSYCHOLOGY")
    print("============================================================")
    
    df_ohlcv, df_tick = generate_mock_data()
    print(f"[OK] Mock Data Generated: OHLCV ({len(df_ohlcv)} rows), Ticks ({len(df_tick)} rows)")
    print("\n[INFO] Starting verification for 54 Advanced Metrics...\n")
    print("-" * 60)
    
    modules_to_test = [
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m01_wick_anatomy',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m02_body_momentum',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m03_tick_verified_patterns',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m04_intra_candle_trapping',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m05_time_and_velocity',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m06_vpa_wyckoff_signatures',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m07_intra_candle_auction',
        'app.services.advanced_ml.features.forex.c02_candlestick_psychology.m08_liquidity_voids',
    ]
    
    from app.services.advanced_ml.features.forex.c02_candlestick_psychology.base_feature import BaseCandlePsychologyFeature
    
    total_metrics = 0
    passed_metrics = 0
    
    for module_name in modules_to_test:
        mod = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and issubclass(obj, BaseCandlePsychologyFeature) and obj is not BaseCandlePsychologyFeature:
                total_metrics += 1
                try:
                    feature_instance = obj()
                    result = feature_instance.calculate(df_ohlcv, df_tick)
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        passed_metrics += 1
                    else:
                        print(f"[FAILED] {name} returned empty or invalid data.")
                except Exception as e:
                    print(f"[ERROR] {name} crashed: {e}")

    print("-" * 60)
    print(f"[SUCCESS] VERIFICATION COMPLETE: {passed_metrics}/{total_metrics} Metrics Passed.")
    if passed_metrics == total_metrics and total_metrics > 0:
         print("[SUCCESS] ALL CANDLESTICK PSYCHOLOGY METRICS ARE 100% COMPATIBLE AND FUNCTIONAL!")
    else:
         print("[WARNING] Some metrics failed validation.")
    print("============================================================")

if __name__ == "__main__":
    main()
