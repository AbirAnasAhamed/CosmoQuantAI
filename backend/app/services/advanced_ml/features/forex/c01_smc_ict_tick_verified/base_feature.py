from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

class BaseTickVerifiedFeature(ABC):
    """
    Abstract base class for all Tick-Verified SMC & ICT metrics.
    Ensures a standardized, dynamic, and modular interface for feature calculation.
    Designed for high-frequency tick data combined with standard OHLCV.
    """

    @abstractmethod
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Calculates the advanced metric.
        
        Args:
            df_ohlcv (pd.DataFrame): Standard OHLCV data.
            df_tick (pd.DataFrame): High-frequency L1 tick data.
            **kwargs: Dynamic parameters for the specific metric.
            
        Returns:
            pd.DataFrame: A DataFrame containing the calculated feature(s), aligned with df_ohlcv index.
        """
        pass

    def _validate_inputs(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame):
        """
        Basic validation to ensure required columns exist and data is not empty.
        """
        if df_ohlcv.empty or df_tick.empty:
            raise ValueError(f"{self.__class__.__name__}: Input DataFrames cannot be empty.")
            
        required_ohlcv = {'open', 'high', 'low', 'close', 'volume'}
        if not required_ohlcv.issubset(set(df_ohlcv.columns)):
            raise ValueError(f"{self.__class__.__name__}: df_ohlcv missing required columns.")
            
        required_tick = {'bid', 'ask', 'volume'} # L1 Tick Data
        if not required_tick.issubset(set(df_tick.columns)):
            # Warning or fallback based on provider
            pass
