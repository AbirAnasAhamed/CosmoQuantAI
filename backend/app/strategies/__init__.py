import backtrader as bt
import os
import importlib
import inspect
import pkgutil
from .base_strategy import BaseStrategy

# -----------------------------------------------------------
# ১. ডায়নামিক লোডিং ফাংশন (Dynamic Loader)
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
                # Ensure we don't load BaseStrategy itself or imports, only actual strategies defined in the file
                if issubclass(cls, bt.Strategy) and cls is not BaseStrategy and cls.__module__ == full_module_name:
                    display_name = f"{module_name} ({name})"
                    # Use a cleaner name if possible, or key by class name
                    custom_strategies[display_name] = cls
                    print(f"✅ Loaded Custom Strategy: {display_name}")
        except Exception as e:
            print(f"⚠️ Failed to load custom strategy module '{module_name}': {e}")
            continue

    return custom_strategies

# -----------------------------------------------------------
# ২. স্ট্র্যাটেজি ম্যাপ
# -----------------------------------------------------------

STRATEGY_MAP = {}

try:
    custom_map = load_custom_strategies()
    STRATEGY_MAP.update(custom_map)
except Exception as e:
    print(f"Error initializing custom strategies: {e}")