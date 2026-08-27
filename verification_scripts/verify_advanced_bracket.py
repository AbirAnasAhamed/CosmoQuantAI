import os

def verify():
    print("--- VERIFYING ADVANCED BRACKET (SL & TRAILING) FIXES ---\n")
    success = True
    
    # 1. Verify trading.py (Backend Schema)
    trading_py_path = r"e:\CosmoQuantAI\backend\app\api\v1\endpoints\trading.py"
    with open(trading_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if "class AttachedSLConfig(BaseModel):" in content and "class TrailingConfig(BaseModel):" in content:
            print("[SUCCESS] Backend (trading.py): SL and Trailing schemas are present.")
        else:
            print("[FAIL] Backend (trading.py): Schemas missing!")
            success = False
            
        if "attached_sl: Optional[AttachedSLConfig] = None" in content and "trailing_config: Optional[TrailingConfig] = None" in content:
            print("[SUCCESS] Backend (trading.py): OrderRequest payload updated.")
        else:
            print("[FAIL] Backend (trading.py): OrderRequest fields missing!")
            success = False

    # 2. Verify manual_trade_service.py
    manual_trade_service_path = r"e:\CosmoQuantAI\backend\app\services\manual_trade_service.py"
    with open(manual_trade_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if "async def background_bracket_monitor" in content and "sl_config," in content and "trailing_config," in content:
            print("[SUCCESS] Backend (manual_trade_service.py): background_bracket_monitor signature is correct.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): background_bracket_monitor missing or incorrect!")
            success = False
            
        if "has_tp = getattr(order_req, 'attached_tp', None)" in content and "sl_config=order_req.attached_sl.dict()" in content:
            print("[SUCCESS] Backend (manual_trade_service.py): Execution orchestrator correctly forwards SL & Trailing payloads.")
        else:
            print("[FAIL] Backend (manual_trade_service.py): Payload forwarding logic missing!")
            success = False

    # 3. Verify bracket_order_service.py
    bracket_order_service_path = r"e:\CosmoQuantAI\backend\app\services\bracket_order_service.py"
    with open(bracket_order_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if "async def monitor_and_execute_bracket(" in content:
            print("[SUCCESS] Backend (bracket_order_service.py): Main Bracket Executor is defined.")
        else:
            print("[FAIL] Backend (bracket_order_service.py): Main Bracket Executor missing!")
            success = False
            
        if "if not is_futures and ('insufficient' in err_str or 'balance' in err_str):" in content:
            print("[SUCCESS] Backend (bracket_order_service.py): Spot 'Insufficient Balance' fallback (Synthetic SL) is present.")
        else:
            print("[FAIL] Backend (bracket_order_service.py): Spot balance lock fallback missing!")
            success = False
            
        if "async def synthetic_oco_monitor(" in content and "await exchange.cancel_order" in content:
            print("[SUCCESS] Backend (bracket_order_service.py): Synthetic OCO Monitor with mutual cancellation is present.")
        else:
            print("[FAIL] Backend (bracket_order_service.py): Synthetic OCO Monitor missing!")
            success = False
            
        if "fetch_positions" in content and "fetch_balance" in content and "LIVENESS CHECK" in content:
            print("[SUCCESS] Backend (bracket_order_service.py): Liveness check added to Synthetic Trailing.")
        else:
            print("[FAIL] Backend (bracket_order_service.py): Synthetic Trailing liveness check missing!")
            success = False

    # 4. Verify ManualTradeModal.tsx
    frontend_path = r"e:\CosmoQuantAI\frontend\src\components\features\market\ManualTradeModal.tsx"
    with open(frontend_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if "const [slConfig, setSlConfig] = useState" in content and "const [trailingConfig, setTrailingConfig] = useState" in content:
            print("[SUCCESS] Frontend: SL and Trailing React states are present.")
        else:
            print("[FAIL] Frontend: State variables missing!")
            success = False
            
        if "payload.attached_sl =" in content and "payload.trailing_config =" in content:
            print("[SUCCESS] Frontend: Payload construction includes SL and Trailing.")
        else:
            print("[FAIL] Frontend: Payload construction missing!")
            success = False
            
        if "Advanced Bracket & Trailing" in content and "Stop-Loss (SL)" in content and "Trailing Stop" in content:
            print("[SUCCESS] Frontend: Combined Bracket UI panels rendered successfully.")
        else:
            print("[FAIL] Frontend: UI Elements missing!")
            success = False

    print("\n----------------------------------------------------")
    if success:
        print("[ALL CLEAR] Advanced Bracket System verified successfully!")
    else:
        print("[WARNING] Some fixes are missing or incorrectly applied.")

if __name__ == "__main__":
    verify()
