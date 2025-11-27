# @params
# {
#   "period": { "type": "number", "label": "RSI Period", "default": 14, "min": 2, "max": 50, "step": 1 },
#   "oversold_level": { "type": "number", "label": "RSI Oversold Level", "default": 30, "min": 0, "max": 50, "step": 1 },
#   "overbought_level": { "type": "number", "label": "RSI Overbought Level", "default": 70, "min": 50, "max": 100, "step": 1 }
# }
# @params_end
import backtrader as bt

class RSIStrategy(bt.Strategy):
    params = (
        ('period', 14),
        ('oversold_level', 30),
        ('overbought_level', 70),
    )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and avoid multiple buys/sells
        self.order = None

        # Add an RSI indicator
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.params.period)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Reset orders
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

    def next(self):
        # Simply log the closing price of the current bar
        self.log(f'Close: {self.dataclose[0]:.2f}')

        # Check if an order is pending. If yes, we cannot send another one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:  # Not in the market
            # If RSI is oversold, BUY
            if self.rsi[0] < self.params.oversold_level:
                self.log(f'BUY CREATE, {self.dataclose[0]:.2f}, RSI: {self.rsi[0]:.2f}')
                # Keep track of the created order to avoid a second one
                self.order = self.buy()
        else:  # Already in the market
            # If RSI is overbought, SELL
            if self.rsi[0] > self.params.overbought_level:
                self.log(f'SELL CREATE, {self.dataclose[0]:.2f}, RSI: {self.rsi[0]:.2f}')
                # Keep track of the created order to avoid a second one
                self.order = self.sell()