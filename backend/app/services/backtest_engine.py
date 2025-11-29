import os
import sys
import importlib.util
import inspect
import backtrader as bt
import pandas as pd
import quantstats as qs
import json
import numpy as np
from sqlalchemy.orm import Session
from app.services.market_service import MarketService
from app.strategies import STRATEGY_MAP
import random
from deap import base, creator, tools, algorithms

# QuantStats setup
qs.extend_pandas()

market_service = MarketService()

# ✅ ১. এই ক্লাসটি ফাইলের উপরের দিকে (imports এর পরে) যোগ করুন
class FractionalPercentSizer(bt.Sizer):
    params = (
        ('percents', 90),
    )
    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # বর্তমান ক্যাশ ভ্যালুর ৯০% দিয়ে কতটুকু কেনা যায় তা বের করা (দশমিক সহ)
            size = self.broker.get_value() * (self.params.percents / 100) / data.close[0]
            return size
        # সেল করার সময় পজিশনের সবটুকু বিক্রি করা
        position = self.broker.getposition(data)
        if not position.size:
            return 0
        return position.size

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

        # 4. Strategy Loading (Dynamic + Static)
        strategy_class = STRATEGY_MAP.get(strategy_name)

        # If not found in map, check custom folder
        if not strategy_class:
            try:
                # Add .py extension if missing
                file_name = f"{strategy_name}.py" if not strategy_name.endswith(".py") else strategy_name
                file_path = f"app/strategies/custom/{file_name}"

                if os.path.exists(file_path):
                    # Dynamically import file
                    spec = importlib.util.spec_from_file_location("custom_strategy", file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Register module in sys.modules so pickle/backtrader can find it
                    sys.modules[file_name.replace('.py', '')] = module
                    sys.modules["custom_strategy"] = module

                    # Find class inheriting from bt.Strategy
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                            strategy_class = obj
                            break
            except Exception as e:
                print(f"Error loading custom strategy: {e}")

        # If still not found, return error
        if not strategy_class:
            return {"error": f"Strategy '{strategy_name}' not found via Map or File."}
        
        # Pass dynamic parameters
        # Filter parameters to only include those accepted by the strategy
        valid_params = {}
        if hasattr(strategy_class, 'params') and hasattr(strategy_class.params, '_getkeys'):
            allowed_keys = strategy_class.params._getkeys()
            for k, v in clean_params.items():
                if k in allowed_keys:
                    valid_params[k] = v
        else:
            # Fallback if introspection fails
            valid_params = clean_params

        cerebro.addstrategy(strategy_class, **valid_params)

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
        qs_metrics = {
            "sharpe": 0, "sortino": 0, "calmar": 0, "max_drawdown": 0,
            "volatility": 0, "win_rate": 0, "profit_factor": 0, "expectancy": 0, "cagr": 0
        }
        heatmap_data = []
        underwater_data = []
        histogram_data = []

        try:
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

            # --- Visual Data Generation (Debug Version) ---
            
            # ১. Monthly Heatmap Data
            heatmap_data = []
            try:
                # ডেটা আছে কি না চেক করা
                if returns.empty:
                    print("Warning: Returns series is empty. No heatmap data.")
                else:
                    # মান্থলি রিটার্ন ক্যালকুলেশন
                    monthly_ret_series = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
                    
                    for timestamp, value in monthly_ret_series.items():
                        # ভ্যালু NaN বা 0 হলে ইগনোর করব না, কারণ 0% রিটার্নও ডেটা
                        if pd.notna(value):
                            heatmap_data.append({
                                "year": timestamp.year,
                                "month": timestamp.month,
                                "value": round(value * 100, 2)
                            })
                    
                    print(f"Heatmap Data Generated: {len(heatmap_data)} points") # ডিবাগ লগ

            except Exception as e:
                print(f"CRITICAL HEATMAP ERROR: {e}")
                # ফলব্যাক: এরর হলে অন্তত খালি লিস্ট যাবে, ক্র্যাশ করবে না
                heatmap_data = []

            # 2. Underwater Plot Data
            drawdown_series = qs.stats.to_drawdown_series(returns)
            underwater_data = [{"time": int(t.timestamp()), "value": round(v * 100, 2)} for t, v in drawdown_series.items()]

            # 3. Returns Distribution (Histogram)
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
            print(f"QuantStats Error: {e}")

        trade_analysis = first_strat.analyzers.trades.get_analysis()
        total_closed = trade_analysis.get('total', {}).get('closed', 0)
        
        # --- Optimization: iterrows() এর পরিবর্তে to_dict ব্যবহার ---
        # এটি অনেক দ্রুত চার্ট ডেটা তৈরি করবে
        
        # প্রথমে টাইমস্ট্যাম্প কলামটি তৈরি করে নিই (ইন্টিজার হিসেবে)
        df['time'] = df.index.astype('int64') // 10**9 
        
        # সরাসরি ডিকশনারিতে কনভার্ট (লুপ ছাড়া)
        chart_candles = df[['time', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')

        # ট্রেড লগ এবং ক্যান্ডেল রিটার্ন করা
        executed_trades = getattr(first_strat, 'trade_history', [])

        return {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy_name,
            "initial_cash": initial_cash,
            "final_value": round(end_value, 2),
            "profit_percent": round((end_value - start_value) / start_value * 100, 2),
            "total_trades": total_closed,
            
            # মেট্রিক্স
            "advanced_metrics": {k: (round(v, 2) if isinstance(v, (int, float)) else 0) for k, v in qs_metrics.items()},
            "heatmap_data": heatmap_data,
            "underwater_data": underwater_data,
            "histogram_data": histogram_data,
            
            # চার্ট ডেটা
            "trades_log": executed_trades, 
            "candle_data": chart_candles 
        }

    def optimize(self, db: Session, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None, method: str = "grid", population_size: int = 50, generations: int = 10, progress_callback=None, abort_callback=None):
        import itertools
        import random
        from deap import base, creator, tools
        import numpy as np
        import json # Added for unique results check

        # 1. Fetch data from DB
        candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
        if not candles or len(candles) < 20:
            return {"error": "Insufficient Data"}

        df = pd.DataFrame([{
            'datetime': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        df.set_index('datetime', inplace=True)

        # 2. প্যারামিটার কম্বিনেশন তৈরি করা (Robust Logic)
        keys = []
        values_ranges = []
        fixed_params = {}
        
        # জেনেটিক অ্যালগরিদমের জন্য বাউন্ডারি
        param_bounds = [] 

        for key, val in params.items():
            # চেক করি এটি অপটিমাইজেশন প্যারামিটার কিনা
            if isinstance(val, dict) and 'start' in val and 'end' in val:
                start = float(val['start'])
                end = float(val['end'])
                step = float(val.get('step', 1))
                
                keys.append(key)
                param_bounds.append((start, end, step))

                # 🛠️ ফিক্স: ফ্লোট বনাম ইন্টিজার হ্যান্ডলিং
                # যদি কোনো ভ্যালুতে দশমিক থাকে (যেমন 0.5), তবে ফ্লোট লজিক চলবে
                # আর যদি সব পূর্ণসংখ্যা হয় (যেমন 10.0), তবে int এ কনভার্ট করে range() ব্যবহার হবে
                is_float = (start % 1 != 0) or (end % 1 != 0) or (step % 1 != 0)

                if is_float:
                    # ফ্লোট রেঞ্জ জেনারেশন
                    # np.arange বা ম্যানুয়াল লুপ ব্যবহার করছি প্রিসিশন ঠিক রাখার জন্য
                    vals = []
                    curr = start
                    # সামান্য বাফার যোগ করা হয়েছে যাতে শেষ ভ্যালুটি মিস না হয়
                    while curr <= (end + step/10000): 
                        vals.append(round(curr, 4)) # ৪ ঘর পর্যন্ত রাউন্ড করা
                        curr += step
                    values_ranges.append(vals)
                else:
                    # ইন্টিজার রেঞ্জ জেনারেশন
                    # int() দিয়ে কাস্ট করা জরুরি কারণ range() ফ্লোট নেয় না
                    values_ranges.append(list(range(int(start), int(end) + 1, int(step))))
            else:
                fixed_params[key] = val

        # স্ট্র্যাটেজি ক্লাস লোড
        strategy_class = STRATEGY_MAP.get(strategy_name)
        if not strategy_class:
            # কাস্টম স্ট্র্যাটেজি লোডিং লজিক (আপনার আগের কোড অনুযায়ী)
            try:
                file_name = f"{strategy_name}.py" if not strategy_name.endswith(".py") else strategy_name
                file_path = f"app/strategies/custom/{file_name}"
                if os.path.exists(file_path):
                    spec = importlib.util.spec_from_file_location("custom_strategy", file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    sys.modules[file_name.replace('.py', '')] = module
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                            strategy_class = obj
                            break
            except Exception as e:
                print(f"Error loading custom strategy: {e}")

        if not strategy_class:
            return {"error": f"Strategy '{strategy_name}' not found."}

        # --- Helper: Evaluate Strategy ---
        def evaluate_strategy(individual):
            run_params = fixed_params.copy()
            for i, key in enumerate(keys):
                val = individual[i]
                # যদি স্ট্র্যাটেজি ইন্টিজার আশা করে কিন্তু আমরা ফ্লোট পেয়েছি (GA এর ক্ষেত্রে হতে পারে)
                # তবে এটি হ্যান্ডেল করার দরকার নেই কারণ আমরা values_ranges থেকে ভ্যালু নিচ্ছি না GA তে
                # কিন্তু GA তে আমরা বাউন্ডারি থেকে ভ্যালু জেনারেট করি
                run_params[key] = val

            cerebro = bt.Cerebro()
            data_feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data_feed)
            
            # প্যারামিটার পাস করা
            cerebro.addstrategy(strategy_class, **run_params)
            
            cerebro.broker.setcash(initial_cash)
            cerebro.broker.setcommission(commission=0.001)
            # আপনার কাস্টম সাইজার ক্লাসটি ব্যবহার করুন (যদি আগের ধাপে যোগ করে থাকেন)
            # এখানে ধরে নিচ্ছি FractionalPercentSizer বা ডিফল্ট Sizer আছে
            cerebro.addsizer(bt.sizers.PercentSizer, percents=90) 

            cerebro.run()
            value = cerebro.broker.get_value()
            profit_pct = ((value - initial_cash) / initial_cash) * 100
            return (profit_pct,)

        # ==========================================
        # 1. GENETIC ALGORITHM LOGIC
        # ==========================================
        if method == "genetic":
            if not param_bounds:
                return {"error": "No optimizable parameters found."}

            print(f"🧬 Starting Genetic Algorithm with {generations} gens, pop {population_size}")
            
            # DEAP Setup (Local scope to avoid global pollution)
            if not hasattr(creator, "FitnessMax"):
                creator.create("FitnessMax", base.Fitness, weights=(1.0,))
            if not hasattr(creator, "Individual"):
                creator.create("Individual", list, fitness=creator.FitnessMax)

            toolbox = base.Toolbox()

            # অ্যাট্রিবিউট জেনারেটর (ফ্লোট বা ইন্টিজার হ্যান্ডলিং সহ)
            def generate_attr(i):
                min_v, max_v, step = param_bounds[i]
                val = random.uniform(min_v, max_v)
                # স্টেপ অনুযায়ী রাউন্ড করা
                steps = round((val - min_v) / step)
                final_val = min_v + (steps * step)
                # যদি অরিজিনাল ইনপুট ইন্টিজার হয়, তবে ইন্টিজারে কাস্ট করা
                if min_v % 1 == 0 and step % 1 == 0:
                    return int(final_val)
                return round(final_val, 4)

            toolbox.register("individual", tools.initCycle, creator.Individual, 
                             [lambda i=i: generate_attr(i) for i in range(len(keys))], n=1)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            
            toolbox.register("evaluate", evaluate_strategy)
            toolbox.register("mate", tools.cxBlend, alpha=0.5)
            toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
            toolbox.register("select", tools.selTournament, tournsize=3)

            pop = toolbox.population(n=population_size)
            
            # Evolution Loop
            # প্রথম জেনারেশন ইভালুয়েশন
            fitnesses = list(map(toolbox.evaluate, pop))
            for ind, fit in zip(pop, fitnesses):
                ind.fitness.values = fit
            
            for gen in range(generations):
                # ✅ Cancellation Check
                if abort_callback and abort_callback():
                    print("🛑 Optimization Cancelled (Genetic)", flush=True)
                    break # লুপ ভেঙে বেরিয়ে যাবে

                if progress_callback:
                    progress_callback(gen + 1, generations)
                
                offspring = toolbox.select(pop, len(pop))
                offspring = list(map(toolbox.clone, offspring))

                for child1, child2 in zip(offspring[::2], offspring[1::2]):
                    if random.random() < 0.5:
                        toolbox.mate(child1, child2)
                        del child1.fitness.values
                        del child2.fitness.values

                for mutant in offspring:
                    if random.random() < 0.2:
                        toolbox.mutate(mutant)
                        del mutant.fitness.values
                
                # মিউটেটেড বা নতুন চাইল্ডদের প্যারামিটার ভ্যালিড (Step অনুযায়ী) করা
                for ind in offspring:
                    if not ind.fitness.valid:
                        for i in range(len(ind)):
                            min_v, max_v, step = param_bounds[i]
                            # বাউন্ডারির মধ্যে রাখা
                            val = max(min_v, min(max_v, ind[i]))
                            # স্টেপ স্ন্যাপ করা
                            steps = round((val - min_v) / step)
                            final_val = min_v + (steps * step)
                            if min_v % 1 == 0 and step % 1 == 0:
                                ind[i] = int(final_val)
                            else:
                                ind[i] = round(final_val, 4)

                invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
                fitnesses = map(toolbox.evaluate, invalid_ind)
                for ind, fit in zip(invalid_ind, fitnesses):
                    ind.fitness.values = fit

                pop[:] = offspring

            # সেরা ১০টি ইউনিক রেজাল্ট
            top_individuals = tools.selBest(pop, k=population_size) # সব নিয়ে ইউনিক বের করব
            unique_results = []
            seen_params = set()

            for ind in top_individuals:
                # প্যারামিটার ডিকশনারি তৈরি
                p_values = {k: ind[i] for i, k in enumerate(keys)}
                # ডুপ্লিকেট চেক (JSON স্ট্রিং করে)
                param_str = json.dumps(p_values, sort_keys=True)
                
                if param_str not in seen_params:
                    seen_params.add(param_str)
                    unique_results.append({
                        "params": p_values,
                        "profitPercent": round(ind.fitness.values[0], 2),
                        "maxDrawdown": 0, # GA তে স্পিডের জন্য বাদ দেওয়া হয়েছে
                        "sharpeRatio": 0,
                        "finalValue": 0
                    })
                    if len(unique_results) >= 10:
                        break
            
            return unique_results

        # ==========================================
        # 2. GRID SEARCH LOGIC (Fallback)
        # ==========================================
        else: 
            # Grid Search এর জন্য সব কম্বিনেশন
            combinations = list(itertools.product(*values_ranges))
            total_combos = len(combinations)
            final_results = []

            for idx, combo in enumerate(combinations):
                
                # ✅ ১. ফোর্স স্টপ চেক: লুপের শুরুতেই চেক করা
                if abort_callback and abort_callback():
                    print("🛑 Optimization process aborted by user.")
                    break # লুপ ভেঙে বেরিয়ে যাবে

                run_params = fixed_params.copy()
                for i, key in enumerate(keys):
                    run_params[key] = combo[i]

                # Evaluate (একই কোড যা GA তে ব্যবহার করেছি, কিন্তু এখানে ম্যানুয়ালি)
                cerebro = bt.Cerebro()
                data_feed = bt.feeds.PandasData(dataname=df)
                cerebro.adddata(data_feed)
                cerebro.addstrategy(strategy_class, **run_params)
                cerebro.broker.setcash(initial_cash)
                cerebro.broker.setcommission(commission=0.001)
                cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
                
                # Grid Search এ আমরা ড্রডাউনও ক্যালকুলেট করতে পারি কারণ এখানে কম্বিনেশন কম হয় সাধারণত
                cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

                results = cerebro.run()
                strat = results[0]
                
                value = strat.broker.get_value()
                profit_pct = ((value - initial_cash) / initial_cash) * 100
                drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)

                final_results.append({
                    "params": run_params,
                    "profitPercent": round(profit_pct, 2),
                    "maxDrawdown": round(drawdown, 2),
                    "sharpeRatio": 0, # আপাতত ০
                    "finalValue": round(value, 2)
                })

                if progress_callback:
                    progress_callback(idx + 1, total_combos)

            return sorted(final_results, key=lambda x: x['profitPercent'], reverse=True)[:10]