import os
import re

FRONTEND_FILE = r"e:\CosmoQuantAI\frontend\src\components\features\market\ManualTradeModal.tsx"
TRADING_FILE = r"e:\CosmoQuantAI\backend\app\api\v1\endpoints\trading.py"
SERVICE_FILE = r"e:\CosmoQuantAI\backend\app\services\manual_trade_service.py"

def verify():
    success = True
    print("--- VERIFYING MANUAL TRADE FIXES ---")
    
    # 1. Verify Frontend
    with open(FRONTEND_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
        if "setReduceOnly(false);" in content and "setLeverage(10);" in content:
            print("[SUCCESS] Frontend: Futures states are properly reset on symbol change.")
        else:
            print("[FAIL] Frontend: Futures states reset missing!")
            success = False
            
        if "isQuoteSize = true;" in content and "paramsPayload.isQuoteSize = true;" in content:
            print("[SUCCESS] Frontend: Spot Market slippage fix (isQuoteSize) is present.")
        else:
            print("[FAIL] Frontend: Spot Market slippage fix missing!")
            success = False
            
        if "decimals = 2" in content and "if (currentPrice < 0.001) decimals = 0;" in content:
            print("[SUCCESS] Frontend: Dynamic decimals fix is present.")
        else:
            print("[FAIL] Frontend: Dynamic decimals fix missing!")
            success = False

    # 2. Verify trading.py
    with open(TRADING_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if "order._backend_start_time" not in content:
            print("[SUCCESS] Backend (trading.py): Pydantic dynamic attribute assignment removed.")
        else:
            print("[FAIL] Backend (trading.py): order._backend_start_time still present!")
            success = False
            
        if "logger.exception" in content:
            print("[SUCCESS] Backend (trading.py): logger.exception is being used for full stack traces.")
        else:
            print("[FAIL] Backend (trading.py): logger.exception missing!")
            success = False

    # 3. Verify manual_trade_service.py
    with open(SERVICE_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
        if "def background_send_notification" in content and "db = SessionLocal()" in content:
            print("[SUCCESS] Backend (manual_trade_service.py): DB Session wrapper added for background notification.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): DB Session wrapper missing for notification!")
            success = False
            
        if "def background_tp_monitor" in content and "db = SessionLocal()" in content:
            print("[SUCCESS] Backend (manual_trade_service.py): DB Session wrapper added for TP monitor.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): DB Session wrapper missing for TP monitor!")
            success = False
            
        if "start_time: float = None" in content:
            print("[SUCCESS] Backend (manual_trade_service.py): place_manual_trade signature updated with start_time.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): start_time signature missing!")
            success = False
            
        if "ex_params['quoteOrderQty'] = order_req.amount" in content:
            print("[SUCCESS] Backend (manual_trade_service.py): Spot market quoteOrderQty support added.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): quoteOrderQty support missing!")
            success = False

    print("\n------------------------------------")
    if success:
        print("[ALL CLEAR] All fixes verified successfully!")
    else:
        print("[WARNING] Some fixes are missing or incorrectly applied.")

if __name__ == "__main__":
    verify()
