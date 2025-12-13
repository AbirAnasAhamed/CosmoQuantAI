import backtrader as bt
import os
import importlib
import inspect
import pkgutil
from .base_strategy import BaseStrategy

# -----------------------------------------------------------
# 1. GENERIC STRATEGY TEMPLATES (The Factory Engines)
# -----------------------------------------------------------

class GenericOscillatorStrategy(BaseStrategy):
    """
    Template for Oscillator Strategies (RSI, Stochastic, CCI, WilliamsR, etc.)
    Logic: Buy < Lower Band (Oversold), Sell > Upper Band (Overbought)
    """
    params = (('period', 14), ('lower', 30), ('upper', 70), ('ind_name', 'RSI'))

    def __init__(self):
        super().__init__()
        # Dynamic Indicator Loading
        ind_cls = getattr(bt.indicators, self.params.ind_name, None)
        if not ind_cls:
            raise ValueError(f"Indicator {self.params.ind_name} not found in Backtrader")
        
        self.ind = ind_cls(self.data.close, period=self.params.period)

    def next(self):
        if not self.position:
            if self.ind < self.params.lower:
                self.buy()
        elif self.ind > self.params.upper:
            self.close()

class GenericCrossoverStrategy(BaseStrategy):
    """
    Template for Moving Average Crossovers (SMA, EMA, WMA, KAMA, etc.)
    Logic: Fast MA crosses above Slow MA -> Buy
    """
    params = (('fast_period', 10), ('slow_period', 30), ('ind_name', 'SMA'))

    def __init__(self):
        super().__init__()
        ind_cls = getattr(bt.indicators, self.params.ind_name, None)
        if not ind_cls:
            raise ValueError(f"Indicator {self.params.ind_name} not found")

        self.fast_ma = ind_cls(self.data.close, period=self.params.fast_period)
        self.slow_ma = ind_cls(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0:
            self.close()

class GenericSignalStrategy(BaseStrategy):
    """
    Template for Zero-Line Cross Strategies (MACD, ROC, Momentum)
    Logic: Value crosses above 0 -> Buy
    """
    params = (('period', 12), ('ind_name', 'Momentum'))

    def __init__(self):
        super().__init__()
        ind_cls = getattr(bt.indicators, self.params.ind_name, None)
        self.ind = ind_cls(self.data.close, period=self.params.period)
        self.crossover = bt.indicators.CrossOver(self.ind, 0.0)

    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0:
            self.close()

# -----------------------------------------------------------
# 2. STRATEGY CONFIGURATION (The "1000 Strategy" List)
# -----------------------------------------------------------
# আপনি এখানে যত খুশি ইন্ডিকেটর যোগ করতে পারেন, কোড অটোমেটিক স্ট্র্যাটেজি বানাবে।

INDICATOR_CONFIG = [
    # --- Moving Averages (Crossover Logic) ---
    {"name": "SMA Cross", "type": "crossover", "ind": "SMA", "fast": 10, "slow": 30},
    {"name": "EMA Cross", "type": "crossover", "ind": "EMA", "fast": 9, "slow": 21},
    {"name": "WMA Cross", "type": "crossover", "ind": "WMA", "fast": 10, "slow": 30},
    {"name": "DEMA Cross", "type": "crossover", "ind": "DEMA", "fast": 10, "slow": 30},
    {"name": "TEMA Cross", "type": "crossover", "ind": "TEMA", "fast": 10, "slow": 30},
    {"name": "KAMA Cross", "type": "crossover", "ind": "KAMA", "fast": 10, "slow": 30},
    {"name": "T3 Cross", "type": "crossover", "ind": "T3", "fast": 5, "slow": 10},
    
    # --- Oscillators (Reversion Logic) ---
    {"name": "RSI Strategy", "type": "oscillator", "ind": "RSI", "period": 14, "lower": 30, "upper": 70},
    {"name": "Stochastic", "type": "oscillator", "ind": "Stochastic", "period": 14, "lower": 20, "upper": 80},
    {"name": "CCI Strategy", "type": "oscillator", "ind": "CCI", "period": 20, "lower": -100, "upper": 100},
    {"name": "Williams %R", "type": "oscillator", "ind": "WilliamsR", "period": 14, "lower": -80, "upper": -20},
    {"name": "Ultimate Osc", "type": "oscillator", "ind": "UltimateOscillator", "period": 20, "lower": 30, "upper": 70},
    {"name": "MFI Strategy", "type": "oscillator", "ind": "MFI", "period": 14, "lower": 20, "upper": 80},
    
    # --- Momentum/Trend (Signal Logic) ---
    {"name": "Momentum", "type": "signal", "ind": "Momentum", "period": 12},
    {"name": "ROC Strategy", "type": "signal", "ind": "ROC", "period": 12},
    {"name": "TRIX Strategy", "type": "signal", "ind": "Trix", "period": 15},
    {"name": "CMO Strategy", "type": "oscillator", "ind": "CMO", "period": 14, "lower": -50, "upper": 50}, # Chande Momentum
    
    # --- Special / Complex Strategies (Pre-built) ---
    {"name": "Bollinger Bands", "type": "custom", "cls": "BollingerBandsStrategy"},
    {"name": "MACD Trend", "type": "custom", "cls": "MacdStrategy"},
    {"name": "Parabolic SAR", "type": "custom", "cls": "ParabolicSarStrategy"},
    {"name": "ADX Trend", "type": "custom", "cls": "AdxStrategy"},
    {"name": "ATR Breakout", "type": "custom", "cls": "AtrBreakout"},
]

# -----------------------------------------------------------
# 3. CUSTOM CLASSES (Complex Logic)
# -----------------------------------------------------------

class MacdStrategy(BaseStrategy):
    params = (('fast_period', 12), ('slow_period', 26), ('signal_period', 9))
    def __init__(self):
        super().__init__()
        self.macd = bt.indicators.MACD(
            period_me1=self.params.fast_period, 
            period_me2=self.params.slow_period, 
            period_signal=self.params.signal_period
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0: self.close()

class BollingerBandsStrategy(BaseStrategy):
    params = (('period', 20), ('devfactor', 2.0))
    def __init__(self):
        super().__init__()
        self.bb = bt.indicators.BollingerBands(period=self.params.period, devfactor=self.params.devfactor)
    def next(self):
        if not self.position:
            if self.data.close < self.bb.lines.bot: self.buy()
        elif self.data.close > self.bb.lines.mid: self.close()

class AtrBreakout(BaseStrategy):
    params = (('period', 14), ('multiplier', 3.0))
    def __init__(self):
        super().__init__()
        self.atr = bt.indicators.ATR(period=self.params.period)
        self.sma = bt.indicators.SMA(period=20)
    def next(self):
        if not self.position:
            if self.data.close > (self.sma + self.atr * self.params.multiplier): self.buy()
        elif self.data.close < self.sma:
            self.close()

class ParabolicSarStrategy(BaseStrategy):
    params = (('af', 0.02), ('afmax', 0.2))
    def __init__(self):
        super().__init__()
        self.psar = bt.indicators.ParabolicSAR(af=self.params.af, afmax=self.params.afmax)
    def next(self):
        if not self.position:
            if self.data.close > self.psar: self.buy()
        elif self.data.close < self.psar: self.close()

class AdxStrategy(BaseStrategy):
    params = (('period', 14), ('threshold', 25))

    def __init__(self):
        super().__init__()
        # ✅ ১. SMA ইন্ডিকেটরটি এখানে তৈরি করতে হবে (আগে এটি next() এর ভেতরে ছিল)
        self.adx = bt.indicators.ADX(period=self.params.period)
        self.sma = bt.indicators.SMA(self.data.close, period=20)

    def next(self):
        if not self.position:
            # ✅ ২. এখানে self.sma ব্যবহার করুন (নতুন করে তৈরি করবেন না)
            if self.adx > self.params.threshold and self.data.close > self.sma:
                 self.buy()
        elif self.adx < self.params.threshold:
            self.close()

# -----------------------------------------------------------
# 4. STRATEGY FACTORY (Dynamic Class Generation)
# -----------------------------------------------------------

STRATEGY_MAP = {}

# Load Custom / Complex first
STRATEGY_MAP["MACD Trend"] = MacdStrategy
STRATEGY_MAP["Bollinger Bands"] = BollingerBandsStrategy
STRATEGY_MAP["ATR Breakout"] = AtrBreakout
STRATEGY_MAP["Parabolic SAR"] = ParabolicSarStrategy
STRATEGY_MAP["ADX Trend"] = AdxStrategy

# Generate Generic Strategies dynamically
for config in INDICATOR_CONFIG:
    name = config['name']
    
    if config['type'] == 'custom':
        continue # Already loaded manually above
        
    elif config['type'] == 'crossover':
        # Create a new class dynamically inheriting from GenericCrossoverStrategy
        new_class = type(
            name.replace(" ", ""), 
            (GenericCrossoverStrategy,), 
            {'params': (('fast_period', config['fast']), ('slow_period', config['slow']), ('ind_name', config['ind']))}
        )
        STRATEGY_MAP[name] = new_class
        
    elif config['type'] == 'oscillator':
        new_class = type(
            name.replace(" ", ""), 
            (GenericOscillatorStrategy,), 
            {'params': (('period', config['period']), ('lower', config['lower']), ('upper', config['upper']), ('ind_name', config['ind']))}
        )
        STRATEGY_MAP[name] = new_class

    elif config['type'] == 'signal':
        new_class = type(
            name.replace(" ", ""), 
            (GenericSignalStrategy,), 
            {'params': (('period', config['period']), ('ind_name', config['ind']))}
        )
        STRATEGY_MAP[name] = new_class

# -----------------------------------------------------------
# 5. Load User Uploaded Custom Strategies
# -----------------------------------------------------------
def load_custom_strategies():
    custom_strategies = {}
    current_dir = os.path.dirname(__file__)
    custom_dir = os.path.join(current_dir, 'custom')

    if not os.path.exists(custom_dir):
        return custom_strategies

    for _, module_name, _ in pkgutil.iter_modules([custom_dir]):
        try:
            full_module_name = f"app.strategies.custom.{module_name}"
            module = importlib.import_module(full_module_name)
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, bt.Strategy) and cls is not BaseStrategy and cls.__module__ == full_module_name:
                    custom_strategies[module_name] = cls
        except Exception as e:
            print(f"⚠️ Failed to load custom strategy '{module_name}': {e}")
            continue
    return custom_strategies

try:
    custom_map = load_custom_strategies()
    STRATEGY_MAP.update(custom_map)
except Exception as e:
    print(f"Error initializing strategies: {e}")