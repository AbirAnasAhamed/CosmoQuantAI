from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from typing import List
import shutil
import os
import backtrader as bt

from app import models, schemas
from app.api import deps
from app.constants import STANDARD_STRATEGY_PARAMS, STRATEGY_CATALOG
from app.services import ai_service
from app.strategy_parser import parse_strategy_params
from app.strategies import STRATEGY_MAP

router = APIRouter()

UPLOAD_DIR = "app/strategies/custom"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ যেসব প্যারামিটার ইউজারের দেখার দরকার নেই (System Internal)
HIDDEN_PARAMS = ['ind_name', 'verbose', 'plot', 'name']

def generate_param_config(key, default_val):
    if not isinstance(default_val, (int, float)) or isinstance(default_val, bool):
        return {
            "type": "text" if not isinstance(default_val, bool) else "boolean",
            "label": key.replace('_', ' ').title(),
            "default": default_val
        }

    is_int = isinstance(default_val, int)
    min_val = 0 if default_val >= 0 else default_val * 2
    
    if default_val > 0:
        min_val = 1 if is_int else 0.1
    
    max_val = default_val * 5 if default_val > 0 else 100
    if max_val == 0: max_val = 100
    
    step = 1 if is_int else round(default_val / 10, 3) or 0.01

    return {
        "type": "number",
        "label": key.replace('_', ' ').title(),
        "default": default_val,
        "min": min_val,
        "max": max_val,
        "step": step
    }

@router.post("/upload")
async def upload_strategy(file: UploadFile = File(...), current_user: models.User = Depends(deps.get_current_user)):
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are allowed")

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    return {"filename": file.filename, "message": "Strategy uploaded successfully."}

@router.get("/standard-params")
def get_standard_strategy_params():
    return STANDARD_STRATEGY_PARAMS

@router.get("/catalog")
def get_strategy_catalog(current_user: models.User = Depends(deps.get_current_user)):
    """
    Returns the categorized list of all available global strategies.
    """
    return STRATEGY_CATALOG

@router.get("/list")
def get_all_strategies(current_user: models.User = Depends(deps.get_current_user)):
    """
    Returns the combined list of 'Strategy Library' and 'Custom Strategies'.
    """
    try:
        # STRATEGY_MAP থেকে সব কী (Key) নিয়ে লিস্ট তৈরি করা
        # এতে __init__.py তে যোগ করা সব নতুন স্ট্র্যাটেজি অটোমেটিক চলে আসবে
        all_strategies = list(STRATEGY_MAP.keys())
        
        # বর্ণানুক্রমে সাজানো (Optional)
        return sorted(all_strategies)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source/{strategy_name}")
def get_strategy_source(strategy_name: str, current_user: models.User = Depends(deps.get_current_user)):
    try:
        filename = f"{strategy_name}.py" if not strategy_name.endswith(".py") else strategy_name
        file_path = f"{UPLOAD_DIR}/{filename}"
        
        # ১. স্ট্র্যাটেজি ম্যাপ থেকে লোড করা (Standard/Library Strategies)
        if not os.path.exists(file_path):
             if strategy_name in STRATEGY_MAP:
                 strategy_class = STRATEGY_MAP[strategy_name]
                 standard_params = {}

                 if hasattr(strategy_class, 'params'):
                     params_dict = {}
                     if hasattr(strategy_class.params, '_getpairs'):
                         params_dict = strategy_class.params._getpairs()
                     elif isinstance(strategy_class.params, dict):
                         params_dict = strategy_class.params
                     elif isinstance(strategy_class.params, tuple):
                         params_dict = dict(strategy_class.params)
                     
                     for key, val in params_dict.items():
                         # ✅ ফিল্টার: ইন্টারনাল প্যারামিটার বাদ দেওয়া হচ্ছে
                         if val is not None and key not in HIDDEN_PARAMS:
                             standard_params[key] = generate_param_config(key, val)

                 return {
                     "code": f"# Strategy Library: {strategy_name}\n# This is a built-in strategy.",
                     "inferred_params": standard_params
                 }
             
             raise HTTPException(status_code=404, detail="Strategy file not found")
            
        # ২. কাস্টম ফাইল লোড করা
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        extracted_params = {}
        try:
            raw_params_dict = parse_strategy_params(file_path)
            for key, default_val in raw_params_dict.items():
                if key not in HIDDEN_PARAMS: # কাস্টম ফাইলেও ফিল্টার অ্যাপ্লাই
                    extracted_params[key] = generate_param_config(key, default_val)
        except Exception as e:
            pass
            
        return {
            "code": code,
            "inferred_params": extracted_params
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File read error: {str(e)}")


from pydantic import BaseModel

# --- Request Model ---
class StrategyConfig(BaseModel):
    name: str
    type: str  # 'crossover', 'oscillator', 'signal'
    indicator: str  # 'SMA', 'RSI', 'EMA'
    params: dict  # {'period': 14, 'fast': 10, ...}

@router.post("/builder")
async def build_strategy(config: StrategyConfig, current_user: models.User = Depends(deps.get_current_user)):
    """
    Builds a strategy python file from frontend configuration
    """
    clean_name = config.name.replace(" ", "")
    filename = f"{clean_name}.py"
    file_path = f"{UPLOAD_DIR}/{filename}"
    
    # 1. কোড টেমপ্লেট জেনারেট করা
    code = f"""import backtrader as bt
from app.strategies.base_strategy import BaseStrategy

class {clean_name}(BaseStrategy):
    '''
    Auto-generated Strategy: {config.name}
    Type: {config.type.title()} | Indicator: {config.indicator}
    '''
    params = ("""
    
    # প্যারামস টিপল তৈরি
    for k, v in config.params.items():
        code += f"('{k}', {v}), "
    code += ")\\n\\n"

    # __init__ এবং next লজিক
    code += "    def __init__(self):\\n"
    code += "        super().__init__()\\n"
    
    if config.type == 'crossover':
        code += f"        self.fast = bt.indicators.{config.indicator}(self.data.close, period=self.params.fast)\\n"
        code += f"        self.slow = bt.indicators.{config.indicator}(self.data.close, period=self.params.slow)\\n"
        code += "        self.crossover = bt.indicators.CrossOver(self.fast, self.slow)\\n\\n"
        
        code += "    def next(self):\\n"
        code += "        if not self.position:\\n"
        code += "            if self.crossover > 0: self.buy()\\n"
        code += "        elif self.crossover < 0: self.close()\\n"

    elif config.type == 'oscillator':
        code += f"        self.ind = bt.indicators.{config.indicator}(self.data.close, period=self.params.period)\\n\\n"
        
        code += "    def next(self):\\n"
        code += "        if not self.position:\\n"
        code += "            if self.ind < self.params.lower: self.buy()\\n"
        code += "        elif self.ind > self.params.upper: self.close()\\n"
        
    elif config.type == 'signal':
        code += f"        self.ind = bt.indicators.{config.indicator}(self.data.close, period=self.params.period)\\n"
        code += "        self.crossover = bt.indicators.CrossOver(self.ind, 0.0)\\n\\n"
        
        code += "    def next(self):\\n"
        code += "        if not self.position:\\n"
        code += "            if self.crossover > 0: self.buy()\\n"
        code += "        elif self.crossover < 0: self.close()\\n"

    # 2. ফাইল সেভ করা
    try:
        with open(file_path, "w") as f:
            f.write(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save strategy: {str(e)}")

    return {"message": "Strategy created successfully!", "filename": filename}
