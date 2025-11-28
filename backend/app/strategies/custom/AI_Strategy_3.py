# @params
# {
#   "period": { "type": "number", "label": "Bollinger Period", "default": 20, "min": 5, "max": 50, "step": 1 },
#   "devfactor": { "type": "number", "label": "Std Dev Factor", "default": 2.0, "min": 1.0, "max": 3.0, "step": 0.1 }
# }
# @params_end
import backtrader as bt

class BollingerBandsMeanReversion(bt.Strategy):
    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )

    def __init__(self):
        self.trade_history = []
        self.order = None  # To keep track of pending orders

        # Bollinger Bands Indicator
        # The 'self.data.close' refers to the close price of the first data feed
        self.bband = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.period,
            devfactor=self.p.devfactor
        )

        # Alias for easier access to lines
        # These lines are dynamically created by the BollingerBands indicator
        self.upper_band = self.bband.lines.top
        self.lower_band = self.bband.lines.bot
        self.middle_band = self.bband.lines.mid

        # Keep a reference to the close price line for easier access
        self.dataclose = self.data.close

    def notify_order(self, order):
        # This method is called exactly as specified by the requirements
        if order.status in [order.Completed]:
            is_buy = order.isbuy()
            self.trade_history.append({
                "type": "buy" if is_buy else "sell",
                "price": order.executed.price,
                "size": order.executed.size,
                "time": int(bt.num2date(order.executed.dt).timestamp())
            })
            # Clear the pending order reference once it's completed
            self.order = None
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            # If the order was not completed (e.g., canceled, rejected, or margin call),
            # clear the pending order reference to allow new orders.
            self.order = None

    def next(self):
        # If an order is already pending, do not place another one
        if self.order:
            return

        # Check if we are not currently in the market (no open position)
        if not self.position:
            # Buy Signal: Close price crosses below the Lower Band (Oversold condition)
            # This indicates a potential mean reversion upswing.
            if self.dataclose[0] < self.lower_band[0]:
                # Place a buy order
                self.order = self.buy()
        else:
            # If we have an open position (we are long), look for a sell signal
            # Sell Signal: Close price crosses above the Upper Band (Overbought condition)
            # This indicates a potential mean reversion downswing, so we close our long position.
            if self.dataclose[0] > self.upper_band[0]:
                # Place a sell order (which will close the existing long position)
                self.order = self.sell()