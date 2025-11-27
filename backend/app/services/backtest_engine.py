import backtrader as bt
import pandas as pd
from sqlalchemy.orm import Session
from app.services.market_service import MarketService
from app.strategies import STRATEGY_MAP

market_service = MarketService()

class BacktestEngine:
    
    def run(self, db: Session, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None):
        
        # ১. ডাটাবেস থেকে ডেটা আনা
        candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date, end_date)
        
        # DEBUG LOG: কনসোলে প্রিন্ট হবে
        print(f"--- BACKTEST DEBUG ---")
        print(f"Request: {symbol} [{timeframe}] | Date: {start_date} to {end_date}")
        print(f"Found Candles in DB: {len(candles)}")
        
        # VALIDATION
        min_required_candles = 20 # অন্তত ২০টি ক্যান্ডেল না থাকলে রান হবে না
        
        if not candles or len(candles) < min_required_candles:
            error_msg = (
                f"Insufficient Data! Found only {len(candles)} candles for {symbol} ({timeframe}). "
                f"Strategy requires more data to calculate indicators. "
                f"Please go to 'Sync Market Data' and fetching at least 500+ candles."
            )
            return {"error": error_msg}

        # ২. ডাটা পান্ডাস ডাটাফ্রেম এ কনভার্ট করা (Backtrader এর জন্য)
        df = pd.DataFrame([{
            'datetime': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        
        df.set_index('datetime', inplace=True)

        # 🔴 NEW FIX: Convert string params to numbers safely
        clean_params = {}
        for k, v in params.items():
            try:
                # প্রথমে ইনটিজার করার চেষ্টা
                clean_params[k] = int(v)
            except (ValueError, TypeError):
                try:
                    # ইনটিজার না হলে ফ্লোট
                    clean_params[k] = float(v)
                except (ValueError, TypeError):
                    # তাও না হলে যা আছে তাই (string)
                    clean_params[k] = v

        # ৩. ব্রেন (Cerebro) সেটআপ
        cerebro = bt.Cerebro()
        
        # ফিড যোগ করা
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed)

        # ৪. স্ট্র্যাটেজি যোগ করা
        strategy_class = STRATEGY_MAP.get(strategy_name)
        if not strategy_class:
            return {"error": f"Strategy '{strategy_name}' not found."}
        
        # ডাইনামিক প্যারামিটার পাস করা
        cerebro.addstrategy(strategy_class, **clean_params)

        # ৫. ক্যাশ সেটআপ
        cerebro.broker.setcash(initial_cash)

        # 🔴 নতুন কোড: কমিশন এবং সাইজার সেটআপ
        # ০.১% কমিশন সেট করা
        cerebro.broker.setcommission(commission=0.001) 
        
        # স্ট্র্যাটেজিকে বলা যে প্রতি ট্রেডে একাউন্টের ৯০% টাকা দিয়ে কিনবে
        cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
        
        # ৬. অ্যানালাইজার (Analyzers) যোগ করা (ফলাফল বের করার জন্য)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")

        # রান করার আগের ভ্যালু
        start_value = cerebro.broker.getvalue()

        # ৭. ব্যাকটেস্ট চালানো!
        results = cerebro.run()
        first_strat = results[0]

        # ৮. ফলাফল প্রসেসিং
        end_value = cerebro.broker.getvalue()
        total_return = end_value - start_value
        profit_percent = (total_return / start_value) * 100
        
        # Analyzers থেকে ডেটা বের করা
        trade_analysis = first_strat.analyzers.trades.get_analysis()
        drawdown_analysis = first_strat.analyzers.drawdown.get_analysis()
        sharpe_analysis = first_strat.analyzers.sharpe.get_analysis()

        # Win Rate ক্যালকুলেশন
        total_closed = trade_analysis.get('total', {}).get('closed', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0

        # 🟢 নতুন অংশ: ট্রেড হিস্ট্রি এবং ক্যান্ডেল ডেটা প্রিপেয়ার করা
        executed_trades = getattr(first_strat, 'trade_history', [])
        
        # চার্টের জন্য ক্যান্ডেল ডেটা JSON সিরিয়ালাইজেবল করা
        chart_candles = []
        for index, row in df.iterrows():
            # Pandas timestamp থেকে স্ট্রিং বা UNIX time
            chart_candles.append({
                "time": index.timestamp(), # UNIX timestamp for Lightweight Charts
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
            })

        return {
            "status": "success",
            "symbol": symbol,
            "strategy": strategy_name,
            "initial_cash": initial_cash,
            "final_value": round(end_value, 2),
            "profit_percent": round(profit_percent, 2),
            "max_drawdown": round(drawdown_analysis.get('max', {}).get('drawdown', 0), 2),
            "win_rate": round(win_rate, 2),
            "sharpe_ratio": round(sharpe_analysis.get('sharperatio', 0) or 0, 2),
            "total_trades": total_closed,
            "date_range": f"{start_date} to {end_date}",
            # নতুন ফিল্ড:
            "trades_log": executed_trades, 
            "candle_data": chart_candles 
        }