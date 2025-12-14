import inspect
import math
import backtrader as bt
import pandas as pd
import quantstats as qs
import json
import numpy as np
from sqlalchemy.orm import Session
from app.services.market_service import MarketService
from app.strategies import STRATEGY_MAP
import random
import itertools
import os
import importlib
import importlib.util
import sys
import asyncio
import time
from asgiref.sync import async_to_sync

import warnings

# QuantStats setup
qs.extend_pandas()

# Suppress QuantStats RuntimeWarnings (e.g. invalid value in scalar power)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="quantstats")

market_service = MarketService()

import logging

# ✅ SAFE LOGGING CONFIGURATION
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('backtrader').setLevel(logging.WARNING)

# ✅ 1. Progress Observer (Backtrader internal for 'run' method)
# এটি সরাসরি টার্মিনালে প্রিন্ট না করে কলব্যাক ফাংশন ব্যবহার করবে
class ProgressObserver(bt.Observer):
    lines = ('progress',)
    params = (
        ('total_len', 0),
        ('callback', None),
    )

    def next(self):
        current_idx = len(self)
        total = self.params.total_len

        if total > 0 and self.params.callback:
            # কম্প্রেশন বা রিস্যাম্পলিং থাকলে ইনডেক্স এডজাস্ট করা হতে পারে
            # আমরা সহজভাবে পার্সেন্টেজ পাঠাচ্ছি
            percent = int((current_idx / total) * 100)
            if percent > 100: percent = 100
            
            # প্রতি ১% পর পর আপডেট পাঠাবে
            if percent % 1 == 0: 
                # Call callback with percentage
                self.params.callback(percent)

# ✅ NEW: Custom Analyzer for accurate Equity Curve (TradingView Style)
class EquityAnalyzer(bt.Analyzer):
    def __init__(self):
        self.equity_data = []

    def start(self):
        self.equity_data = []

    def next(self):
        # Save correct time and cash value after each candle process
        # self.datas[0] is primary data feed
        try:
            current_time = self.datas[0].datetime.datetime(0)
            current_equity = self.strategy.broker.getvalue()
            
            self.equity_data.append({
                "time": int(current_time.timestamp()), # Unix Timestamp for Frontend
                "value": round(current_equity, 2)
            })
        except Exception:
            pass

    def get_analysis(self):
        return self.equity_data

class FractionalPercentSizer(bt.Sizer):
    params = (
        ('percents', 90),
    )
    def _getsizing(self, comminfo, cash, data, isbuy):
        position = self.broker.getposition(data)
        if position.size == 0:
            size = self.broker.get_value() * (self.params.percents / 100) / data.close[0]
            return size
        return position.size

class BacktestEngine:
    
    def run(self, db: Session, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, 
            start_date: str = None, end_date: str = None, custom_data_file: str = None, progress_callback=None, 
            commission: float = 0.001, slippage: float = 0.0, leverage: float = 1.0,  # 👈 leverage added
            secondary_timeframe: str = None,  # ✅ Secondary Timeframe (Trend)
            stop_loss: float = 0.0, take_profit: float = 0.0, trailing_stop: float = 0.0): # ✅ Risk Management
        
        resample_compression = 1
        base_timeframe = timeframe
        df = None
        strategy_class = None

        # 1. Load Data (CSV or DB)
        if custom_data_file:
            file_path = f"app/data_feeds/{custom_data_file}"
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    df.columns = [c.lower().strip() for c in df.columns]
                    
                    if 'datetime' in df.columns:
                        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce') 
                        if df['datetime'].isnull().all():
                            return {"error": "CSV Date format invalid. Use YYYY-MM-DD HH:MM:SS format."}
                        df.dropna(subset=['datetime'], inplace=True)
                        df.set_index('datetime', inplace=True)
                    elif 'date' in df.columns:
                        df['datetime'] = pd.to_datetime(df['date'], errors='coerce')
                        if df['datetime'].isnull().all():
                            return {"error": "CSV Date format invalid."}
                        df.dropna(subset=['datetime'], inplace=True)
                        df.set_index('datetime', inplace=True)
                        
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if not all(col in df.columns for col in required_cols):
                         return {"error": f"CSV file must contain columns: {required_cols}"}
                    
                    df = df[required_cols]
                except Exception as e:
                    return {"error": f"Error reading CSV file: {str(e)}"}
            else:
                return {"error": "Custom data file not found on server."}

        if df is None:
            candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)

            if not candles or len(candles) < 20:
                print(f"📉 Data missing for {symbol} {timeframe}. Auto-syncing from Exchange...")
                if progress_callback: progress_callback(5)
                try:
                    async_to_sync(market_service.fetch_and_store_candles)(
                        db=db, symbol=symbol, timeframe=timeframe, start_date=start_date, end_date=end_date, limit=1000
                    )
                    candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
                except Exception as e:
                    print(f"❌ Auto-sync failed: {e}")
            
            if not candles or len(candles) < 20:
                if timeframe == '45m':
                    base_timeframe = '15m'
                    resample_compression = 3
                    candles = market_service.get_candles_from_db(db, symbol, '15m', start_date, end_date)
                elif timeframe == '2h':
                    base_timeframe = '1h'
                    resample_compression = 2
                    candles = market_service.get_candles_from_db(db, symbol, '1h', start_date, end_date)

            if not candles or len(candles) < 20:
                 return {"error": "Insufficient Data in Database."}

            df = pd.DataFrame(candles, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index('datetime', inplace=True)



        # ✅ NEW: Calculate total candles
        total_candles = len(df) if df is not None else 0

        clean_params = {}
        for k, v in params.items():
            try: clean_params[k] = int(v)
            except:
                try: clean_params[k] = float(v)
                except: clean_params[k] = v

        # ✅ FIX: Risk Management Params Injection (Handle NoneType Error)
        # এখানে আমরা নিশ্চিত করছি যে ভ্যালুগুলো None হলে যেন 0.0 হয়ে যায়।
        stop_loss = float(stop_loss) if stop_loss is not None else 0.0
        take_profit = float(take_profit) if take_profit is not None else 0.0
        trailing_stop = float(trailing_stop) if trailing_stop is not None else 0.0

        if stop_loss > 0: clean_params['stop_loss'] = stop_loss
        if take_profit > 0: clean_params['take_profit'] = take_profit
        if trailing_stop > 0: clean_params['trailing_stop'] = trailing_stop

        cerebro = bt.Cerebro()
        data_feed = bt.feeds.PandasData(dataname=df)
        
        # Add Primary Data
        if resample_compression > 1:
            tf_mapping = {
                'm': bt.TimeFrame.Minutes,
                'h': bt.TimeFrame.Hours,
                'd': bt.TimeFrame.Days
            }
            unit_char = base_timeframe[-1] 
            bt_timeframe = tf_mapping.get(unit_char, bt.TimeFrame.Minutes)
            cerebro.resampledata(data_feed, timeframe=bt_timeframe, compression=resample_compression)
        else:
            cerebro.adddata(data_feed)

        # ✅ Secondary Timeframe Logic
        if secondary_timeframe:
            tf_map = {
                "1m": (bt.TimeFrame.Minutes, 1), "5m": (bt.TimeFrame.Minutes, 5),
                "15m": (bt.TimeFrame.Minutes, 15), "30m": (bt.TimeFrame.Minutes, 30),
                "1h": (bt.TimeFrame.Minutes, 60), "4h": (bt.TimeFrame.Minutes, 240),
                "1d": (bt.TimeFrame.Days, 1), "1w": (bt.TimeFrame.Weeks, 1)
            }
            if secondary_timeframe in tf_map:
                bt_tf, compression = tf_map[secondary_timeframe]
                cerebro.resampledata(data_feed, timeframe=bt_tf, compression=compression, name=f"TF_{secondary_timeframe}")
            else:
                print(f"⚠️ Warning: Unsupported secondary timeframe {secondary_timeframe}")

        if progress_callback:
            total_candles = len(df)
            if resample_compression > 1:
                total_candles = total_candles // resample_compression
            cerebro.addobserver(ProgressObserver, total_len=total_candles, callback=progress_callback)

        strategy_class = self._load_strategy_class(strategy_name)
        if not strategy_class:
            return {"error": f"Strategy '{strategy_name}' not found via Map or File."}
        
        valid_params = self._smart_filter_params(strategy_class, clean_params)
        
        # Risk Management Params (SL/TP) যদি ফিল্টারে বাদ পড়ে যায়, তবুও জোর করে অ্যাড করা
        # কারণ BaseStrategy তে এগুলো থাকে, কিন্তু মাঝে মাঝে ডিটেক্ট হয় না।
        if 'stop_loss' in clean_params: valid_params['stop_loss'] = clean_params['stop_loss']
        if 'take_profit' in clean_params: valid_params['take_profit'] = clean_params['take_profit']
        if 'trailing_stop' in clean_params: valid_params['trailing_stop'] = clean_params['trailing_stop']

        try:
            cerebro.addstrategy(strategy_class, **valid_params)
        except Exception as e:
            return {"error": f"Failed to initialize strategy parameters: {str(e)}"}

        cerebro.broker.setcash(initial_cash)
        
        # Leveage / Futures Logic
        is_futures = leverage > 1.0
        
        cerebro.broker.setcommission(
            commission=commission, 
            commtype=bt.CommInfoBase.COMM_PERC, 
            leverage=leverage, 
            stocklike=not is_futures
        )

        if slippage > 0:
            cerebro.broker.set_slippage_perc(perc=slippage)
        
        cerebro.addsizer(FractionalPercentSizer, percents=90)
        
        cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Transactions, _name="transactions")
        
        # ✅ NEW: Adding Custom Equity Analyzer
        cerebro.addanalyzer(EquityAnalyzer, _name='equity_curve')

        start_value = cerebro.broker.getvalue()
        try:
            results = cerebro.run() 
            first_strat = results[0]
        except IndexError as e:
            # ✅ বিশেষ লজিক: ইনডেক্স এরর ধরলে ইউজারকে গাইড করা
            error_msg = str(e)
            print(f"❌ Backtest Critical Error: {error_msg}")
            return {
                "status": "error",
                "message": "Critical Error: 'Array Index Out of Range'. This usually happens if you define Indicators (like SMA, RSI) inside the next() method. Please move them to __init__()."
            }
        except Exception as e:
            # ✅ সাধারণ এরর হ্যান্ডলিং
            import traceback
            trace_str = traceback.format_exc()
            print(f"❌ Backtest Runtime Error: {e}\n{trace_str}")
            
            # যদি এরর মেসেজে ইনডেক্স এরর থাকে
            if "array index out of range" in str(e).lower() or "list index out of range" in str(e).lower():
                 return {
                    "status": "error",
                    "message": "Critical Error: 'Index Out of Range'. You likely instantiated an Indicator inside the next() method. Please move it to __init__()."
                }

            return {"status": "error", "message": f"Backtest execution failed: {str(e)}"}

        end_value = cerebro.broker.getvalue()

        # ✅ FIX: ভেরিয়েবলগুলো প্রিন্ট করার আগেই ডিফাইন করা হলো
        total_candles = len(df) if df is not None else 0
        profit_value = end_value - start_value
        profit_percent = round((profit_value / start_value) * 100, 2)

        qs_metrics = self._calculate_metrics(first_strat, start_value, end_value)
        detailed_trade_analysis = self._format_trade_analysis(first_strat)
        
        executed_trades = getattr(first_strat, 'trade_history', [])
        
        if not executed_trades:
            trans_anal = first_strat.analyzers.transactions.get_analysis()
            for dt, trans_list in trans_anal.items():
                for trans in trans_list:
                    size = trans[0]
                    price = trans[1]
                    executed_trades.append({
                        "type": "buy" if size > 0 else "sell",
                        "price": price,
                        "size": abs(size),
                        "time": int(dt.timestamp())
                    })
            executed_trades.sort(key=lambda x: x['time'])
        
        df['time'] = df.index.astype('int64') // 10**9 
        # Format: [time, open, high, low, close, volume]
        chart_candles = df[['time', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
        
        # Extract Equity Curve
        # ---------------------------------------------------------
        # 👇 2. Equity Curve Extraction: Using Custom Analyzer
        # ---------------------------------------------------------
        equity_curve = []
        try:
            # Get data directly from custom Analyzer
            equity_curve = first_strat.analyzers.equity_curve.get_analysis()
            
            # Safety check: if data empty, add initial cash
            if not equity_curve:
                equity_curve = [{"time": int(df.index[0].timestamp()), "value": initial_cash}]
                
        except Exception as e:
            print(f"⚠️ Error extracting equity curve: {e}")
            equity_curve = []

        # ✅ PRINT: with Leverage Info
        print(f"\n📊 Backtest Result for {symbol} ({timeframe}) | Lev: {leverage}x")
        print(f"------------------------------------------------")
        print(f"🕯️  Total Candles : {total_candles}")
        print(f"💰 Final Value   : {round(end_value, 2)}")
        print(f"📈 Profit        : {profit_percent}%")
        print(f"📉 Max Drawdown  : {qs_metrics['metrics'].get('max_drawdown', 0)}%")
        print(f"------------------------------------------------\n")

        return {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy_name,
            "initial_cash": initial_cash,
            "leverage": leverage,
            "final_value": round(end_value, 2),
            "profit_percent": profit_percent,
            "total_candles": total_candles,
            "total_trades": detailed_trade_analysis.get('total_closed', 0),
            "advanced_metrics": qs_metrics["metrics"],
            "heatmap_data": qs_metrics["heatmap"],
            "underwater_data": qs_metrics["underwater"],
            "histogram_data": qs_metrics["histogram"],
            "trades_log": executed_trades, 
            "candle_data": chart_candles,
            "trade_analysis": detailed_trade_analysis,
            "equity_curve": equity_curve
        }

    def _format_trade_analysis(self, strategy):
        try:
            analysis = strategy.analyzers.trades.get_analysis()
            def get(d, keys, default=0):
                for k in keys:
                    if isinstance(d, dict): d = d.get(k, default)
                    else: return default
                return d

            total = analysis.get('total', {})
            won = analysis.get('won', {})
            lost = analysis.get('lost', {})
            pnl = analysis.get('pnl', {})
            long_t = analysis.get('long', {})
            short_t = analysis.get('short', {})

            total_closed = total.get('closed', 0)
            total_open = total.get('open', 0)
            total_won = won.get('total', 0)
            total_lost = lost.get('total', 0)
            win_rate = (total_won / total_closed * 100) if total_closed > 0 else 0
            
            gross_pnl = get(pnl, ['gross', 'total'])
            net_pnl = get(pnl, ['net', 'total'])
            avg_pnl = get(pnl, ['net', 'average'])
            avg_win_trade = get(won, ['pnl', 'average'])
            avg_loss_trade = get(lost, ['pnl', 'average'])
            ratio_avg_win_loss = abs(avg_win_trade / avg_loss_trade) if avg_loss_trade != 0 else 0
            largest_win_value = get(won, ['pnl', 'max'])
            largest_loss_value = get(lost, ['pnl', 'max'])

            largest_win_percent = 0
            largest_loss_percent = 0
            if hasattr(strategy, '_trades'):
                all_trades = []
                for feed in strategy._trades:
                    all_trades.extend(strategy._trades[feed][0]) 
                for t in all_trades:
                    investment = t.price * t.size
                    if investment != 0:
                        roi = (t.pnl / abs(investment)) * 100
                        if roi > largest_win_percent: largest_win_percent = roi
                        if roi < largest_loss_percent: largest_loss_percent = roi

            return {
                "total_closed": total_closed,
                "total_open": total_open,
                "total_won": total_won,
                "total_lost": total_lost,
                "win_rate": round(win_rate, 2),
                "long_trades_total": long_t.get('total', 0),
                "long_trades_won": get(long_t, ['won', 'total']),
                "short_trades_total": short_t.get('total', 0),
                "short_trades_won": get(short_t, ['won', 'total']),
                "gross_profit": round(gross_pnl, 2),
                "net_profit": round(net_pnl, 2),
                "avg_pnl": round(avg_pnl, 2),
                "avg_win": round(avg_win_trade, 2),
                "avg_loss": round(avg_loss_trade, 2),
                "ratio_avg_win_loss": round(ratio_avg_win_loss, 2),
                "largest_win_value": round(largest_win_value, 2),
                "largest_loss_value": round(largest_loss_value, 2),
                "largest_win_percent": round(largest_win_percent, 2),
                "largest_loss_percent": round(largest_loss_percent, 2),
            }
        except Exception as e:
            return {}

    def optimize(self, db: Session, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, 
                 start_date: str = None, end_date: str = None, custom_data_file: str = None,  # ✅ Added custom_data_file
                 method="grid", population_size=50, generations=10, progress_callback=None, abort_callback=None,
                 commission: float = 0.001, slippage: float = 0.0, leverage: float = 1.0):
        
        df = None

        # ✅ 1. OPTIMIZATION: Load Data ONCE (CSV or DB) before the loop
        if custom_data_file:
            file_path = f"app/data_feeds/{custom_data_file}"
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    df.columns = [c.lower().strip() for c in df.columns]
                    
                    if 'datetime' in df.columns:
                        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce') 
                        df.dropna(subset=['datetime'], inplace=True)
                        df.set_index('datetime', inplace=True)
                    elif 'date' in df.columns:
                        df['datetime'] = pd.to_datetime(df['date'], errors='coerce')
                        df.dropna(subset=['datetime'], inplace=True)
                        df.set_index('datetime', inplace=True)
                        
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if not all(col in df.columns for col in required_cols):
                         return {"error": f"CSV file must contain columns: {required_cols}"}
                    
                    df = df[required_cols]
                except Exception as e:
                    return {"error": f"Error reading CSV file: {str(e)}"}
            else:
                return {"error": "Custom data file not found on server."}

        # If CSV not used or failed, try DB
        if df is None:
            candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
            if not candles or len(candles) < 20:
                print(f"Data missing for {symbol} {timeframe}. Auto-syncing...")
                if progress_callback: progress_callback(0, meta={"status": "Syncing Data..."})
                try:
                    async_to_sync(market_service.fetch_and_store_candles)(
                        db=db, symbol=symbol, timeframe=timeframe, start_date=start_date, end_date=end_date, limit=1000
                    )
                    candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
                except Exception as e:
                    print(f"Auto-sync failed: {e}")

            if not candles or len(candles) < 20:
                return {"error": f"Insufficient Data for {symbol}."}

            df = pd.DataFrame(candles, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index('datetime', inplace=True)
        
        # ✅ 2. OPTIMIZATION: Load Strategy Class ONCE before the loop
        # This prevents disk I/O (file check/import) in every iteration
        strategy_class = self._load_strategy_class(strategy_name)
        if not strategy_class:
            return {"error": f"Strategy '{strategy_name}' not found."}

        # Parameter processing logic...
        param_ranges = {} 
        fixed_params = {}
        for k, v in params.items():
            if isinstance(v, dict) and 'start' in v and 'end' in v:
                start, end = float(v['start']), float(v['end'])
                step = float(v.get('step', 1)) if float(v.get('step', 1)) != 0 else 1
                vals = []
                curr = start
                while curr <= end + (step/1000): 
                    vals.append(curr)
                    curr += step
                vals = [int(x) if int(start)==start and int(step)==step else round(x, 4) for x in vals]
                param_ranges[k] = vals
            else:
                fixed_params[k] = v

        results = []
        best_profit_so_far = -float('inf')

        # Grid Search
        if method == "grid":
            param_names = list(param_ranges.keys())
            param_values = list(param_ranges.values())
            combinations = list(itertools.product(*param_values))
            total = len(combinations)
            
            for i, combo in enumerate(combinations):
                if abort_callback and abort_callback(): 
                    break
                instance_params = dict(zip(param_names, combo))
                
                # ✅ Pass the pre-loaded 'strategy_class' instead of 'strategy_name'
                metrics = self._run_single_backtest(df, strategy_class, initial_cash, instance_params, fixed_params, commission, slippage, leverage)
                
                metrics['params'] = instance_params
                results.append(metrics)
                
                if metrics['profitPercent'] > best_profit_so_far:
                    best_profit_so_far = metrics['profitPercent']

                if progress_callback:
                    percent = int(((i + 1) / total) * 100)
                    progress_callback(
                        percent, 
                        meta={
                            "current": i + 1,
                            "total": total,
                            "best_profit": round(best_profit_so_far, 2),
                            "last_profit": metrics['profitPercent']
                        }
                    )

        # Genetic Algorithm
        elif method == "genetic" or method == "geneticAlgorithm":
            # Pass strategy_class to GA method as well
            results = self._run_genetic_algorithm(
                df, strategy_class, initial_cash, param_ranges, fixed_params, 
                pop_size=population_size, generations=generations, 
                progress_callback=progress_callback, abort_callback=abort_callback,
                commission=commission, slippage=slippage, leverage=leverage
            )

        results.sort(key=lambda x: x['profitPercent'], reverse=True)
        return results

    def _run_genetic_algorithm(self, df, strategy_class, initial_cash, param_ranges, fixed_params, pop_size=50, generations=10, progress_callback=None, abort_callback=None, commission=0.001, slippage=0.0, leverage=1.0):
        # ... (Genetic setup same as before) ...
        param_keys = list(param_ranges.keys())
        population = []
        for _ in range(pop_size):
            population.append({k: random.choice(v) for k, v in param_ranges.items()})

        best_results = []
        history_cache = {} 
        total_steps = generations * pop_size
        best_profit_so_far = -float('inf')

        for gen in range(generations):
            if abort_callback and abort_callback(): 
                break
            
            evaluated_pop = []
            
            for i, individual in enumerate(population):
                param_signature = json.dumps(individual, sort_keys=True)
                
                if param_signature in history_cache:
                    metrics = history_cache[param_signature]
                else:
                    # ✅ Pass pre-loaded strategy_class
                    metrics = self._run_single_backtest(df, strategy_class, initial_cash, individual, fixed_params, commission, slippage, leverage)
                    metrics['params'] = individual
                    history_cache[param_signature] = metrics
                
                evaluated_pop.append(metrics)
                
                if metrics['profitPercent'] > best_profit_so_far:
                    best_profit_so_far = metrics['profitPercent']

                current_step = (gen * pop_size) + (i + 1)
                
                if progress_callback:
                    percent = int((current_step / total_steps) * 100)
                    progress_callback(
                        percent,
                        meta={
                            "current": current_step,
                            "total": total_steps,
                            "generation": gen + 1,
                            "best_profit": round(best_profit_so_far, 2)
                        }
                    )
            
            evaluated_pop.sort(key=lambda x: x['profitPercent'], reverse=True)
            best_results.extend(evaluated_pop[:5]) 
            
            elite_count = int(pop_size * 0.2)
            next_generation = [item['params'] for item in evaluated_pop[:elite_count]]
            
            while len(next_generation) < pop_size:
                parent1 = random.choice(evaluated_pop[:int(pop_size/2)])['params']
                parent2 = random.choice(evaluated_pop[:int(pop_size/2)])['params']
                child = parent1.copy()
                for k in param_keys:
                    if random.random() > 0.5: child[k] = parent2[k]
                if random.random() < 0.2: 
                    mutate_key = random.choice(param_keys)
                    child[mutate_key] = random.choice(param_ranges[mutate_key])
                next_generation.append(child)
            
            population = next_generation

        unique_results = {json.dumps(r['params'], sort_keys=True): r for r in best_results}
        return list(unique_results.values())

    # ✅ UPDATED: Accepts strategy_class object instead of name string
    def _run_single_backtest(self, df, strategy_class, initial_cash, variable_params, fixed_params, commission=0.001, slippage=0.0, leverage=1.0):
        full_params = {**fixed_params, **variable_params}
        clean_params = {}
        for k, v in full_params.items():
            try: clean_params[k] = int(v)
            except: 
                try: clean_params[k] = float(v)
                except: clean_params[k] = v

        cerebro = bt.Cerebro(stdstats=False) 
        
        # ✅ Data is already loaded in memory (df), so this is fast
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed)
        
        # ✅ Removed _load_strategy_class call from here to avoid repetitive Disk I/O
        
        valid_params = self._smart_filter_params(strategy_class, clean_params)
        
        if 'stop_loss' in clean_params: valid_params['stop_loss'] = clean_params['stop_loss']
        if 'take_profit' in clean_params: valid_params['take_profit'] = clean_params['take_profit']

        cerebro.addstrategy(strategy_class, **valid_params)
        
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=commission, commtype=bt.CommInfoBase.COMM_PERC, margin=None, mult=1.0, stocklike=True)
        
        # ✅ Leveage / Futures Logic
        is_futures = leverage > 1.0
        cerebro.broker.setcommission(
            commission=commission, 
            commtype=bt.CommInfoBase.COMM_PERC, 
            leverage=leverage, 
            stocklike=not is_futures
        )

        if slippage > 0: cerebro.broker.set_slippage_perc(perc=slippage)
            
        cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.0)
        
        try:
            results = cerebro.run()
            strat = results[0]
            end_value = cerebro.broker.getvalue()
            profit_percent = ((end_value - initial_cash) / initial_cash) * 100
            
            dd = strat.analyzers.drawdown.get_analysis()
            max_drawdown = dd.get('max', {}).get('drawdown', 0)
            
            sharpe = strat.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe.get('sharperatio', 0) or 0

            trade_analysis = strat.analyzers.trades.get_analysis()
            total_closed = trade_analysis.get('total', {}).get('closed', 0)
            won_trades = trade_analysis.get('won', {}).get('total', 0)
            win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0
            
            return {
                "profitPercent": round(profit_percent, 2),
                "maxDrawdown": round(max_drawdown, 2),
                "sharpeRatio": round(sharpe_ratio, 2),
                "total_trades": total_closed,
                "winRate": round(win_rate, 2),
                "final_value": round(end_value, 2),
                "initial_cash": initial_cash,
                "total_candles": len(df)
            }
        except Exception:
            return {
                "profitPercent": 0, 
                "maxDrawdown": 0, 
                "sharpeRatio": 0, 
                "total_trades": 0, 
                "winRate": 0, 
                "final_value": initial_cash, 
                "initial_cash": initial_cash,
                "total_candles": len(df) if df is not None else 0
            }

    # ... (বাকি মেথডগুলো অপরিবর্তিত রাখুন) ...
    def _load_strategy_class(self, strategy_name):
        # ১. ম্যাপ থেকে চেক করা (স্ট্যান্ডার্ড স্ট্র্যাটেজি)
        strategy_class = STRATEGY_MAP.get(strategy_name)
        
        # ২. ফাইল থেকে লোড করা (কাস্টম স্ট্র্যাটেজি)
        if not strategy_class:
            try:
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                custom_strategies_dir = os.path.join(current_file_dir, '..', 'strategies', 'custom')
                custom_strategies_dir = os.path.normpath(custom_strategies_dir)
                
                file_name = f"{strategy_name}.py" if not strategy_name.endswith(".py") else strategy_name
                file_path = os.path.join(custom_strategies_dir, file_name)
                
                if os.path.exists(file_path):
                    module_name = file_name.replace('.py', '')
                    
                    # পুরোনো মডিউল ক্যাশ থেকে সরানো (রিলোড নিশ্চিত করতে)
                    if module_name in sys.modules: 
                        del sys.modules[module_name]
                        
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                    else: 
                        return None
                    
                    # ✅ ফিক্স: শুধু এই মডিউলে ডিফাইন করা ক্লাসটিই রিটার্ন করবে
                    # এটি ইম্পোর্ট করা অন্য ক্লাস (যেমন BaseStrategy) ইগনোর করবে
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                            # 🔴 গুরুত্বপূর্ণ চেক: ক্লাসটি কি এই ফাইলেই ডিফাইন করা হয়েছে?
                            if obj.__module__ == module_name:
                                return obj
                                
            except Exception as e: 
                print(f"❌ Exception loading custom strategy '{strategy_name}': {e}")
                
        return strategy_class

    # ✅ অপটিমাইজড প্যারামিটার ফিল্টার (Smart Matcher)
    def _smart_filter_params(self, strategy_class, params):
        valid_params = {}
        
        # ১. স্ট্র্যাটেজির নিজস্ব প্যারামিটার লিস্ট বের করা
        if hasattr(strategy_class, 'params'):
            # Backtrader এর params dict বা tuple হতে পারে
            if hasattr(strategy_class.params, '_getkeys'):
                allowed_keys = strategy_class.params._getkeys()
            elif isinstance(strategy_class.params, dict):
                allowed_keys = strategy_class.params.keys()
            else:
                # Fallback for tuple based params
                allowed_keys = dict(strategy_class.params).keys()

            # ২. নরমাল এবং লোয়ারকেস ম্যাপ তৈরি (Case Insensitive Matching)
            # এটি fast_period, fastPeriod, FastPeriod সব কিছুকে একই ধরবে
            key_map = {k.lower().replace('_', ''): k for k in allowed_keys}
            
            # ৩. ইউজার ইনপুট চেক করা
            for k, v in params.items():
                # সরাসরি ম্যাচ করলে
                if k in allowed_keys:
                    valid_params[k] = v
                else:
                    # যদি নাম হুবহু না মিলে, তবে লোয়ারকেস চেক করা
                    clean_k = k.lower().replace('_', '')
                    if clean_k in key_map:
                        real_key = key_map[clean_k]
                        valid_params[real_key] = v
                        # print(f"🔧 Param Fixed: '{k}' -> '{real_key}'") # Debugging log
                    else:
                        # যদি তাও না মিলে, ইগনোর করবে (Risk params বাদে)
                        pass 

        return valid_params

    def _calculate_metrics(self, first_strat, start_value, end_value):
        qs_metrics = {
            "sharpe": 0, "sortino": 0, "max_drawdown": 0, "win_rate": 0, 
            "profit_factor": 0, "cagr": 0, "volatility": 0, "calmar": 0, 
            "recovery_factor": 0, "expected_return": 0
        }
        heatmap_data = []
        underwater_data = []
        histogram_data = []
        
        try:
            portfolio_stats = first_strat.analyzers.getbyname('pyfolio')
            returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
            returns.index = returns.index.tz_localize(None)
            
            sharpe_val = 0
            if not returns.empty and len(returns) > 5:
                try: sharpe_val = qs.stats.sharpe(returns)
                except: sharpe_val = 0
            
            # --- মেট্রিক্স ক্যালকুলেশন ---
            qs_metrics = {
                "sharpe": sharpe_val,
                "sortino": qs.stats.sortino(returns) if not returns.empty else 0,
                "max_drawdown": qs.stats.max_drawdown(returns) * 100 if not returns.empty else 0,
                "win_rate": qs.stats.win_rate(returns) * 100 if not returns.empty else 0,
                "profit_factor": qs.stats.profit_factor(returns) if not returns.empty else 0,
                "cagr": qs.stats.cagr(returns) * 100 if not returns.empty else 0,
                "volatility": qs.stats.volatility(returns) * 100 if not returns.empty else 0,
                "calmar": qs.stats.calmar(returns) if not returns.empty else 0,
                "recovery_factor": qs.stats.recovery_factor(returns) if not returns.empty else 0,
                "expected_return": qs.stats.expected_return(returns) * 100 if not returns.empty else 0
            }

            # --- Heatmap Data ---
            if not returns.empty:
                monthly_ret_series = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
                for timestamp, value in monthly_ret_series.items():
                    val = value * 100
                    # NaN বা Inf চেক
                    if isinstance(val, (int, float)) and not (math.isnan(val) or math.isinf(val)):
                        heatmap_data.append({"year": timestamp.year, "month": timestamp.month, "value": round(val, 2)})
            
            # --- Underwater Data ---
            drawdown_series = qs.stats.to_drawdown_series(returns)
            for t, v in drawdown_series.items():
                val = v * 100
                if isinstance(val, (int, float)) and not (math.isnan(val) or math.isinf(val)):
                    underwater_data.append({"time": int(t.timestamp()), "value": round(val, 2)})
            
            # --- Histogram Data ---
            clean_returns = returns.dropna()
            if not clean_returns.empty:
                hist_values, bin_edges = np.histogram(clean_returns * 100, bins=20)
                for i in range(len(hist_values)):
                    if hist_values[i] > 0: 
                        histogram_data.append({"range": f"{round(bin_edges[i], 1)}% to {round(bin_edges[i+1], 1)}%", "frequency": int(hist_values[i])})
                        
        except Exception as e: 
            print(f"⚠️ Metrics Calculation Error: {e}")
            pass

        # ✅ ফাইনাল স্যানিটাইজেশন (NaN/Inf কে 0 তে কনভার্ট করা)
        sanitized_metrics = {}
        for k, v in qs_metrics.items():
            if isinstance(v, (int, float)):
                if math.isnan(v) or math.isinf(v):
                    sanitized_metrics[k] = 0.0
                else:
                    sanitized_metrics[k] = round(v, 2)
            else:
                sanitized_metrics[k] = 0.0

        return {
            "metrics": sanitized_metrics, 
            "heatmap": heatmap_data, 
            "underwater": underwater_data, 
            "histogram": histogram_data
        }

    # Helper method already added in previous step
    def _format_trade_analysis(self, strategy):
        # ... (keep this method as provided in previous response) ...
        try:
            analysis = strategy.analyzers.trades.get_analysis()
            def get(d, keys, default=0):
                for k in keys:
                    if isinstance(d, dict): d = d.get(k, default)
                    else: return default
                return d
            total = analysis.get('total', {})
            won = analysis.get('won', {})
            lost = analysis.get('lost', {})
            pnl = analysis.get('pnl', {})
            long_t = analysis.get('long', {})
            short_t = analysis.get('short', {})
            total_closed = total.get('closed', 0)
            total_open = total.get('open', 0)
            total_won = won.get('total', 0)
            total_lost = lost.get('total', 0)
            win_rate = (total_won / total_closed * 100) if total_closed > 0 else 0
            gross_pnl = get(pnl, ['gross', 'total'])
            net_pnl = get(pnl, ['net', 'total'])
            avg_pnl = get(pnl, ['net', 'average'])
            avg_win_trade = get(won, ['pnl', 'average'])
            avg_loss_trade = get(lost, ['pnl', 'average'])
            ratio_avg_win_loss = abs(avg_win_trade / avg_loss_trade) if avg_loss_trade != 0 else 0
            largest_win_value = get(won, ['pnl', 'max'])
            largest_loss_value = get(lost, ['pnl', 'max'])
            largest_win_percent = 0
            largest_loss_percent = 0
            if hasattr(strategy, '_trades'):
                all_trades = []
                for feed in strategy._trades:
                    all_trades.extend(strategy._trades[feed][0]) 
                for t in all_trades:
                    investment = t.price * t.size
                    if investment != 0:
                        roi = (t.pnl / abs(investment)) * 100
                        if roi > largest_win_percent: largest_win_percent = roi
                        if roi < largest_loss_percent: largest_loss_percent = roi
            return {
                "total_closed": total_closed,
                "total_open": total_open,
                "total_won": total_won,
                "total_lost": total_lost,
                "win_rate": round(win_rate, 2),
                "long_trades_total": long_t.get('total', 0),
                "long_trades_won": get(long_t, ['won', 'total']),
                "short_trades_total": short_t.get('total', 0),
                "short_trades_won": get(short_t, ['won', 'total']),
                "gross_profit": round(gross_pnl, 2),
                "net_profit": round(net_pnl, 2),
                "avg_pnl": round(avg_pnl, 2),
                "avg_win": round(avg_win_trade, 2),
                "avg_loss": round(avg_loss_trade, 2),
                "ratio_avg_win_loss": round(ratio_avg_win_loss, 2),
                "largest_win_value": round(largest_win_value, 2),
                "largest_loss_value": round(largest_loss_value, 2),
                "largest_win_percent": round(largest_win_percent, 2),
                "largest_loss_percent": round(largest_loss_percent, 2),
            }
        except Exception as e:
            return {}