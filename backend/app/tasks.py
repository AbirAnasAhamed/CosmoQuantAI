from .celery_app import celery_app
from .database import SessionLocal
from .services.backtest_engine import BacktestEngine

# টাস্কটি ব্যাকগ্রাউন্ডে রান হবে
@celery_app.task(bind=True)
def run_backtest_task(self, symbol: str, timeframe: str, strategy_name: str, initial_cash: float, params: dict, start_date: str = None, end_date: str = None):
    # প্রতিটি টাস্কের জন্য নতুন ডিবি সেশন খুলতে হবে
    db = SessionLocal()
    engine = BacktestEngine()
    
    try:
        # ব্যাকটেস্ট ইঞ্জিন কল করা
        result = engine.run(
            db=db,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            initial_cash=initial_cash,
            params=params,
            start_date=start_date,
            end_date=end_date
        )
        return result
        
    except Exception as e:
        # এরর হলে সেটি রিটার্ন করা
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()
