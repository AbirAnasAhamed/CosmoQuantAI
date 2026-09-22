import importlib
import inspect

# c01_smc_ict_tick_verified module initialization
from .base_feature import BaseTickVerifiedFeature

from .m01_ob_breaker import *
from .m02_fvg_imbalance import *
from .m03_liquidity_stophunt import *
from .m04_market_structure import *
from .m05_time_macro import *
from .m06_order_flow import *
from .m07_micro_structure import *
from .m08_advanced_dynamics import *
from .m09_ai_ml_specific import *

# Dynamically populate __all__ with all classes that inherit from BaseTickVerifiedFeature
__all__ = ['BaseTickVerifiedFeature']

_modules = [
    'm01_ob_breaker', 'm02_fvg_imbalance', 'm03_liquidity_stophunt',
    'm04_market_structure', 'm05_time_macro', 'm06_order_flow',
    'm07_micro_structure', 'm08_advanced_dynamics', 'm09_ai_ml_specific'
]

import sys
for _mod_name in _modules:
    _full_mod_name = f"{__name__}.{_mod_name}"
    if _full_mod_name in sys.modules:
        _mod = sys.modules[_full_mod_name]
        for _name, _obj in inspect.getmembers(_mod, inspect.isclass):
            if issubclass(_obj, BaseTickVerifiedFeature) and _obj is not BaseTickVerifiedFeature:
                if _name not in __all__:
                    __all__.append(_name)
