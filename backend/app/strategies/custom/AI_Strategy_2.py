# @params
# {
#   "period": { "type": "number", "label": "RSI Period", "default": 14, "min": 2, "max": 100, "step": 1 },
#   "oversold": { "type": "number", "label": "RSI Oversold Threshold", "default": 30, "min": 10, "max": 50, "step": 1 },
#   "overbought": { "type": "number", "label": "RSI Overbought Threshold", "default": 70, "min": 50, "max": 90, "step": 1 }
# }
# @params_end
import backtrader as bt

class RSIStrategy(bt.Strategy):
    params = (
        ('period', 14),
        ('oversold', 30),
        ('overbought', 70),
    )

    def __init__(self):
        self.trade_history = []
        self.dataclose = self.datas[0].close # Keep a reference to the close price line
        self.order = None  # To keep track of pending orders

        # Add an RSI indicator
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.period)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            is_buy = order.isbuy()
            self.trade_history.append({
                "type": "buy" if is_buy else "sell",
                "price": order.executed.price,
                "size": order.executed.size,
                "time": int(bt.num2date(order.executed.dt).timestamp())
            })
            self.order = None # IMPORTANT: Reset order to allow new orders after completion
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # If the order was canceled, rejected, or margin call, clear the pending order
            self.order = None 

    def next(self):
        # If an order is pending, do nothing to avoid sending multiple orders
        if self.order:
            return

        # Check if we are not in the market
        if not self.position:  # self.position.size == 0 implies no open position
            # If RSI is below the oversold threshold, buy
            if self.rsi[0] < self.p.oversold:
                self.order = self.buy()
        else:  # We are in the market (holding a long position)
            # If RSI is above the overbought threshold, sell (close position)
            if self.rsi[0] > self.p.overbought:
                self.order = self.close() # Close the current long position