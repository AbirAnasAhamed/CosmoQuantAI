import backtrader as bt
import pandas as pd
import quantstats as qs
import json
import numpy as np
from sqlalchemy.orm import Session
from app.services.market_service import MarketService
from app.strategies import STRATEGY_MAP

# QuantStats setup
qs.extend_pandas()

market_service = MarketService()

class BacktestEngine:
    
    def run(self, db: Session, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None):
        
        # 1. Fetch data from DB
        candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
        
        if not candles or len(candles) < 20:
            return {"error": "Insufficient Data"}

        # 2. Convert to Pandas DataFrame
        df = pd.DataFrame([{
            'datetime': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        df.set_index('datetime', inplace=True)

        # 3. Clean parameters
        clean_params = {}
        for k, v in params.items():
            try:
                clean_params[k] = int(v)
            except:
                try: clean_params[k] = float(v)
                except: clean_params[k] = v

        # 4. Backtrader setup
        cerebro = bt.Cerebro()
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed)

        strategy_class = STRATEGY_MAP.get(strategy_name)
        if not strategy_class: return {"error": "Strategy not found"}
        
        cerebro.addstrategy(strategy_class, **clean_params)
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.001) 
        cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

        # 5. Run backtest
        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        first_strat = results[0]
        end_value = cerebro.broker.getvalue()

        # 6. Calculate Advanced Metrics with QuantStats
        portfolio_stats = first_strat.analyzers.getbyname('pyfolio')
        returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
        
        # Fix timezone issue for QuantStats
        returns.index = returns.index.tz_localize(None)

        # --- Advanced Metrics Calculation ---
        qs_metrics = {
            "sharpe": qs.stats.sharpe(returns),
            "sortino": qs.stats.sortino(returns),
            "calmar": qs.stats.calmar(returns),
            "max_drawdown": qs.stats.max_drawdown(returns) * 100, # Percentage
            "volatility": qs.stats.volatility(returns),
            "win_rate": qs.stats.win_rate(returns) * 100,
            "profit_factor": qs.stats.profit_factor(returns),
            "expectancy": qs.stats.expected_return(returns) * 100, # Avg return per trade approx
            "cagr": qs.stats.cagr(returns) * 100
        }

        # --- Visual Data Generation ---
        # 1. Monthly Heatmap Data
        monthly_returns = qs.stats.monthly_returns(returns)
        heatmap_data = []
        for index, value in monthly_returns.items():
             if isinstance(index, tuple):
                 heatmap_data.append({"year": index[0], "month": index[1], "value": round(value * 100, 2)})
             elif hasattr(index, 'year') and hasattr(index, 'month'):
                 heatmap_data.append({"year": index.year, "month": index.month, "value": round(value * 100, 2)})
             else:
                 try:
                     idx_ts = pd.to_datetime(index)
                     heatmap_data.append({"year": idx_ts.year, "month": idx_ts.month, "value": round(value * 100, 2)})
                 except:
                     pass

        # 2. Underwater Plot Data
        drawdown_series = qs.stats.to_drawdown_series(returns)
        underwater_data = [{"time": int(t.timestamp()), "value": round(v * 100, 2)} for t, v in drawdown_series.items()]

        # 3. Returns Distribution (Histogram)
        histogram_data = []
        try:
            # Drop NaN values
            clean_returns = returns.dropna()
            
            if not clean_returns.empty:
                # Multiply by 100 to convert to percentage
                hist_values, bin_edges = np.histogram(clean_returns * 100, bins=20)
                
                for i in range(len(hist_values)):
                    if hist_values[i] > 0:
                        # Range label formatting
                        range_label = f"{round(bin_edges[i], 1)}% to {round(bin_edges[i+1], 1)}%"
                        histogram_data.append({
                            "range": range_label,
                            "frequency": int(hist_values[i])
                        })
        except Exception as e:
            print(f"Histogram Generation Error: {e}")
            histogram_data = []

        trade_analysis = first_strat.analyzers.trades.get_analysis()
        total_closed = trade_analysis.get('total', {}).get('closed', 0)
        
        # Trade logs and candles for chart
        executed_trades = getattr(first_strat, 'trade_history', [])
        chart_candles = []
        for index, row in df.iterrows():
            chart_candles.append({
                "time": int(index.timestamp()), 
                "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'],
            })

        return {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy_name,
            "initial_cash": initial_cash,
            "final_value": round(end_value, 2),
            "profit_percent": round((end_value - start_value) / start_value * 100, 2),
            "total_trades": total_closed,
            
            # Advanced Metrics
            "advanced_metrics": {k: (round(v, 2) if isinstance(v, (int, float)) else 0) for k, v in qs_metrics.items()},
            "heatmap_data": heatmap_data,
            "underwater_data": underwater_data,
            "histogram_data": histogram_data,

            
            # Chart Data
            "trades_log": executed_trades, 
            "candle_data": chart_candles 
        }