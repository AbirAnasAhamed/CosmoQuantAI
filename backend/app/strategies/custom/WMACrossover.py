import backtrader as bt
from app.strategies.base_strategy import BaseStrategy

class WMACrossover(BaseStrategy):
    '''
    Auto-generated Strategy: WMA Crossover
    Type: Crossover | Indicator: WMA
    '''
    params = (('fast', 10), ('slow', 30), )\n\n    def __init__(self):\n        super().__init__()\n        self.fast = bt.indicators.WMA(self.data.close, period=self.params.fast)\n        self.slow = bt.indicators.WMA(self.data.close, period=self.params.slow)\n        self.crossover = bt.indicators.CrossOver(self.fast, self.slow)\n\n    def next(self):\n        if not self.position:\n            if self.crossover > 0: self.buy()\n        elif self.crossover < 0: self.close()\n