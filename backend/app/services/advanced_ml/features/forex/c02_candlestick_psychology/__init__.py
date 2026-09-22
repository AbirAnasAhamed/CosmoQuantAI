import importlib
import inspect
import sys

# c02_candlestick_psychology module initialization
from .base_feature import BaseCandlePsychologyFeature

from .m01_wick_anatomy import *
from .m02_body_momentum import *
from .m03_tick_verified_patterns import *
from .m04_intra_candle_trapping import *
from .m05_time_and_velocity import *
from .m06_vpa_wyckoff_signatures import *
from .m07_intra_candle_auction import *
from .m08_liquidity_voids import *

# Dynamically populate __all__ with all classes that inherit from BaseCandlePsychologyFeature
__all__ = ['BaseCandlePsychologyFeature']

_modules = [
    'm01_wick_anatomy', 'm02_body_momentum', 'm03_tick_verified_patterns',
    'm04_intra_candle_trapping', 'm05_time_and_velocity', 'm06_vpa_wyckoff_signatures',
    'm07_intra_candle_auction', 'm08_liquidity_voids'
]

for _mod_name in _modules:
    _full_mod_name = f"{__name__}.{_mod_name}"
    if _full_mod_name in sys.modules:
        _mod = sys.modules[_full_mod_name]
        for _name, _obj in inspect.getmembers(_mod, inspect.isclass):
            if issubclass(_obj, BaseCandlePsychologyFeature) and _obj is not BaseCandlePsychologyFeature:
                if _name not in __all__:
                    __all__.append(_name)
