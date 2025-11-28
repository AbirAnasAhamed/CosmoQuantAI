# FILE: bot_worker/strategies/advanced_scalping_strategy.py (সম্পূর্ণ আপডেটেড)

# --- প্রয়োজনীয় লাইব্রেরি ---
import pandas as pd
import numpy as np
import pandas_ta as ta

# ==========================================================
#                      পরিবর্তন ১
#  Base Strategy এখন রিলেটিভ পাথ থেকে ইম্পোর্ট করা হচ্ছে
# ==========================================================
from .base_strategy import BaseStrategy


# =============================================================================
# ইন্ডিকেটর ফাংশন (আপনার দেওয়া কোড - অপরিবর্তিত)
# =============================================================================
def calculate_scalping_indicators(df: pd.DataFrame, bb_length: int, bb_stddev: float, sr_lookback: int, atr_length: int, squeeze_threshold: float, use_candle_confirm: bool, buffer_percent: float):
    data = df.copy()
    data.columns = [col.lower() for col in data.columns]
    
    data.ta.bbands(length=bb_length, std=bb_stddev, append=True)
    data.ta.atr(length=atr_length, append=True)
    
    bb_upper_col = f'bbu_{bb_length}_{bb_stddev}'.lower()
    bb_middle_col = f'bbm_{bb_length}_{bb_stddev}'.lower()
    bb_lower_col = f'bbl_{bb_length}_{bb_stddev}'.lower()

    if not all(col in data.columns for col in [bb_upper_col, bb_middle_col, bb_lower_col]):
        print(f"Warning: Bollinger Bands columns not found for length={bb_length}, stddev={bb_stddev}. Skipping signals.")
        data['bounce_buy_signal'] = False
        data['squeeze_buy_signal'] = False
        data['bounce_sell_signal'] = False
        data['squeeze_sell_signal'] = False
        return data

    data['bbw'] = (data[bb_upper_col] - data[bb_lower_col]) / data[bb_middle_col]
    data['is_squeeze'] = data['bbw'] < squeeze_threshold

    def get_activity_zones(window, num_bins=50):
        highest_high = window['high'].max()
        lowest_low = window['low'].min()
        price_range = highest_high - lowest_low
        if price_range <= 0: return (np.nan, np.nan)
        bin_size = price_range / num_bins
        histogram = np.zeros(num_bins)
        for _, row in window.iterrows():
            start_bin = int(np.floor((row['low'] - lowest_low) / bin_size)) if bin_size > 0 else 0
            end_bin = int(np.floor((row['high'] - lowest_low) / bin_size)) if bin_size > 0 else 0
            for j in range(start_bin, end_bin + 1):
                if 0 <= j < num_bins: histogram[j] += 1
        current_close = window['close'].iloc[-1]
        support_bins = [i for i, price in enumerate(lowest_low + np.arange(num_bins) * bin_size) if price < current_close]
        resistance_bins = [i for i in range(num_bins) if i not in support_bins]
        s_lvl, r_lvl = np.nan, np.nan
        if support_bins:
            max_sp_cnt, sp_idx = -1, -1
            for idx in support_bins:
                if histogram[idx] >= max_sp_cnt: max_sp_cnt, sp_idx = histogram[idx], idx
            if sp_idx != -1: s_lvl = lowest_low + (sp_idx * bin_size)
        if resistance_bins:
            max_rp_cnt, rp_idx = -1, -1
            for idx in resistance_bins:
                if histogram[idx] >= max_rp_cnt: max_rp_cnt, rp_idx = histogram[idx], idx
            if rp_idx != -1: r_lvl = lowest_low + (rp_idx * bin_size)
        return (s_lvl, r_lvl)
        
    sr_levels = data.rolling(window=sr_lookback).apply(get_activity_zones, raw=False)
    if not sr_levels.empty:
        data[['support_level', 'resistance_level']] = pd.DataFrame(sr_levels.tolist(), index=data.index)
    else:
        data['support_level'], data['resistance_level'] = np.nan, np.nan

    data['persistent_support'] = data['support_level'].ffill()
    data['persistent_resistance'] = data['resistance_level'].ffill()

    data['upper_trigger'] = data[bb_middle_col] + (data[bb_upper_col] - data[bb_middle_col]) * (buffer_percent / 100)
    data['lower_trigger'] = data[bb_middle_col] - (data[bb_middle_col] - data[bb_lower_col]) * (buffer_percent / 100)
    
    near_upper = data['high'] >= data['upper_trigger']
    near_lower = data['low'] <= data['lower_trigger']
    at_res = data['high'] >= data['persistent_resistance'].shift(1)
    at_sup = data['low'] <= data['persistent_support'].shift(1)
    
    is_bearish = data['close'] < data['open']
    is_bullish = data['close'] > data['open']
    
    data['bounce_sell_signal'] = near_upper & at_res & (is_bearish if use_candle_confirm else True)
    data['bounce_buy_signal'] = near_lower & at_sup & (is_bullish if use_candle_confirm else True)
    
    breakout_up = (data['close'] > data[bb_upper_col]) & (data['close'].shift(1) <= data[bb_upper_col].shift(1))
    breakout_down = (data['close'] < data[bb_lower_col]) & (data['close'].shift(1) >= data[bb_lower_col].shift(1))
    
    data['squeeze_buy_signal'] = data['is_squeeze'].shift(1) & breakout_up
    data['squeeze_sell_signal'] = data['is_squeeze'].shift(1) & breakout_down
    
    return data

# =============================================================================
# Zenith Bot-এর জন্য স্ট্র্যাটেজি ক্লাস (আপগ্রেডেড)
# =============================================================================

class AdvancedScalpingStrategy(BaseStrategy):

    def __init__(self, params: dict):
        # ==========================================================
        #                      পরিবর্তন ২
        #  Base class-এর __init__ কে কল করা হচ্ছে
        # ==========================================================
        super().__init__(params)

        self.bb_length = int(params.get('bb_length', 20))
        self.bb_stddev = float(params.get('bb_stddev', 2.0))
        self.sr_lookback = int(params.get('sr_lookback', 30))
        self.use_candle_confirm = bool(params.get('use_candle_confirm', True))
        self.squeeze_threshold = 0.015
        self.atr_length = 14
        self.buffer_percent = 90.0

    @staticmethod
    def get_params_definition():
        """UI-তে ডাইনামিক ফর্ম তৈরির জন্য প্যারামিটারগুলো সংজ্ঞায়িত করে।"""
        return [
            {"name": "bb_length", "type": "integer", "default": 20, "label": "Bollinger Band Length"},
            {"name": "bb_stddev", "type": "float", "default": 2.0, "label": "BB Standard Deviation"},
            {"name": "sr_lookback", "type": "integer", "default": 30, "label": "S/R Lookback Period"},
        ]

    # আপনার generate_signals মেথডটি পূর্বে generate_signals নামে ছিল, 
    # আমি এখানে কোনো পরিবর্তন না করে generate_signals ই রাখছি।
    # এটি BaseStrategy-এর অ্যাবস্ট্রাক্ট মেথডকে ইমপ্লিমেন্ট করে।
    def generate_signal(self, df: pd.DataFrame) -> str:
        """মূল সিগন্যাল জেনারেট করে: 'BUY', 'SELL', or 'HOLD'."""
        
        if len(df) < max(self.bb_length, self.sr_lookback):
            return 'HOLD'

        indicators_df = calculate_scalping_indicators(
            df,
            bb_length=self.bb_length,
            bb_stddev=self.bb_stddev,
            sr_lookback=self.sr_lookback,
            squeeze_threshold=self.squeeze_threshold,
            atr_length=self.atr_length,
            buffer_percent=self.buffer_percent,
            use_candle_confirm=self.use_candle_confirm
        )

        latest_signals = indicators_df.iloc[-1]
        
        if latest_signals.get('bounce_buy_signal') or latest_signals.get('squeeze_buy_signal'):
            return 'BUY'
        elif latest_signals.get('bounce_sell_signal') or latest_signals.get('squeeze_sell_signal'):
            return 'SELL'
        else:
            return 'HOLD'