import time
import asyncio
import datetime
import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.services.websocket_manager import manager

from app import models, schemas
from app.api import deps
from app.db.session import get_db
# In the future, we will create and use `forex_train_model_task` from app.tasks
# from app.services.forex_ml_training_engine import forex_train_model_task
from app.services.notification import NotificationService
from pydantic import BaseModel

router = APIRouter()

@router.post("/train", response_model=schemas.TrainingJobResponse)
def start_forex_training_job(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
    job_in: schemas.TrainingJobCreate,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Start a new Forex Auto-ML training job.
    """
    job_id = f"forex_train_{int(time.time() * 1000)}"
    
    # Ensure market_type is forex
    job_in.market_type = "forex"

    job = models.ModelTrainingJob(
        id=job_id,
        user_id=current_user.id,
        symbol=job_in.symbol,
        timeframe=job_in.timeframe,
        algorithm=job_in.algorithm,
        config=job_in.config,
        status=models.TrainingStatus.PENDING,
        market_type="forex",
        progress=0.0,
        logs=["Forex Job queued for execution..."]
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # trigger celery background task
    from app.tasks import celery_forex_train_model_task
    celery_forex_train_model_task.apply_async(args=[job_id], task_id=job_id)
    
    return job

@router.get("/jobs", response_model=List[schemas.TrainingJobResponse])
def list_forex_training_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    List all Forex training jobs for the current user.
    """
    return db.query(models.ModelTrainingJob).filter(
        models.ModelTrainingJob.user_id == current_user.id,
        models.ModelTrainingJob.market_type == "forex"
    ).order_by(models.ModelTrainingJob.created_at.desc()).all()

@router.get("/jobs/{job_id}", response_model=schemas.TrainingJobResponse)
def get_forex_training_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the status and logs of a specific Forex training job.
    """
    job = db.query(models.ModelTrainingJob).filter(
        models.ModelTrainingJob.id == job_id,
        models.ModelTrainingJob.user_id == current_user.id,
        models.ModelTrainingJob.market_type == "forex"
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Forex training job not found")
    return job

@router.post("/jobs/{job_id}/cancel", response_model=schemas.TrainingJobResponse)
def cancel_forex_training_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Cancel an ongoing Forex training job.
    """
    job = db.query(models.ModelTrainingJob).filter(
        models.ModelTrainingJob.id == job_id,
        models.ModelTrainingJob.user_id == current_user.id,
        models.ModelTrainingJob.market_type == "forex"
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Forex training job not found")
        
    if job.status in [models.TrainingStatus.COMPLETED, models.TrainingStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Job is already finished")

    job.status = models.TrainingStatus.FAILED
    job.error_message = "Training cancelled by user."
    
    logs = list(job.logs) if job.logs else []
    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🛑 Forex Training cancelled by user.")
    job.logs = logs

    # Terminate the underlying Celery task to stop background execution
    from app.core.celery_app import celery_app
    try:
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
    except Exception as e:
        pass

    db.commit()
    db.refresh(job)
    return job

@router.post("/start-forex-collector", response_model=schemas.TrainingJobResponse)
def start_forex_collector(
    request: schemas.StartForexCollectorRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """
    Start the Forex Tick Data Collector script in the background.
    """
    import subprocess
    import os
    import uuid
    from datetime import datetime
    
    job_id = f"forex_job_{uuid.uuid4().hex[:8]}"
    new_job = models.ModelTrainingJob(
        id=job_id,
        user_id=current_user.id,
        symbol=request.symbol.upper(),
        timeframe="Tick",
        algorithm="Forex Data Collector",
        status=models.TrainingStatus.RUNNING,
        market_type="forex",
        progress=0.0,
        config={"target_rows": request.target_rows, "dataset_type": "forex_collector", "mode": request.mode},
        logs=[f"[{datetime.utcnow().strftime('%H:%M:%S')}] Started Forex Collector for {request.symbol} in {request.mode} mode"]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    script_name = "dukascopy_collector.py" if request.data_source == "dukascopy" else "forex_collector.py"
    script_path = os.path.join(os.getcwd(), "scripts", script_name)
    
    try:
        cmd = ["python", script_path, "--symbol", request.symbol.upper(), "--target", str(request.target_rows), "--job_id", job_id, "--mode", request.mode, "--timeframe", request.timeframe]
        if request.mode == 'date' and request.start_date and request.end_date:
            logger.info(f"🚀 Starting Forex Collector for {request.symbol} from {request.start_date} to {request.end_date}")
            cmd.extend(["--start_date", request.start_date, "--end_date", request.end_date])
        else:
            logger.info(f"🚀 Starting Forex Collector for {request.symbol} for {request.target_rows} rows")
            
        subprocess.Popen(cmd)
        return new_job
    except Exception as e:
        new_job.status = models.TrainingStatus.FAILED
        new_job.error_message = f"Failed to start forex collector subprocess: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start collector: {str(e)}")

@router.get("/forex-snapshots", response_model=List[str])
def list_forex_snapshots(
    current_user: models.User = Depends(deps.get_current_user),
):
    """
    List all downloaded forex snapshot .parquet files.
    """
    import os
    import glob
    
    data_dir = os.path.join(os.getcwd(), "data", "raw", "forex_snapshots")
    if not os.path.exists(data_dir):
        return []
        
    pattern = os.path.join(data_dir, "*.parquet")
    files = glob.glob(pattern)
    files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in files]

@router.delete("/forex-snapshots/{filename}")
def delete_forex_snapshot(
    filename: str,
    current_user: models.User = Depends(deps.get_current_user),
):
    """
    Delete a downloaded forex snapshot .parquet file.
    """
    import os
    
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    file_path = os.path.join(os.getcwd(), "data", "raw", "forex_snapshots", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/instruments")
def get_oanda_instruments(current_user: models.User = Depends(deps.get_current_user)):
    """
    Fetch all available trading instruments dynamically from OANDA API.
    """
    import os
    import requests
    
    account_id = os.getenv("OANDA_ACCOUNT_ID")
    api_key = os.getenv("OANDA_API_KEY")
    
    if not account_id or not api_key:
        # Fallback if API keys not present
        return [
            {"name": "EUR_USD", "display_name": "EUR/USD"},
            {"name": "GBP_USD", "display_name": "GBP/USD"},
            {"name": "USD_JPY", "display_name": "USD/JPY"},
        ]
        
    url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/instruments"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        instruments = []
        for inst in data.get("instruments", []):
            if inst.get("type") == "CURRENCY":
                instruments.append({
                    "name": inst["name"],
                    "display_name": inst["displayName"]
                })
        return instruments
    except Exception as e:
        print(f"OANDA API Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch instruments from OANDA")


@router.delete("/dataset/{symbol}")
def delete_forex_dataset(
    symbol: str, 
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Delete a stored CSV dataset for a given forex symbol to free up disk space.
    """
    import os
    
    # Sanitize symbol (e.g. replace / with _)
    clean_symbol = symbol.replace("/", "_")
    file_path = os.path.join(os.getcwd(), "data", "forex", f"{clean_symbol}_data.csv")
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return {"status": "success", "message": f"Dataset for {symbol} deleted."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
    else:
        raise HTTPException(status_code=404, detail="Dataset not found")


class CheckDataQualityRequest(BaseModel):
    symbol: str
    timeframe: str
    mode: str
    target_rows: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/check-data-quality")
def check_forex_data_quality(
    request: CheckDataQualityRequest,
    current_user: models.User = Depends(deps.get_current_user),
):
    """
    Check if the requested data range is valid and what limits might apply.
    """
    expected_rows = request.target_rows
    if request.mode == 'date' and request.start_date and request.end_date:
        try:
            start = datetime.datetime.strptime(request.start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(request.end_date, "%Y-%m-%d")
            days = (end - start).days
            
            if days < 0:
                return {"status": "error", "message": "End Date must be after Start Date."}
                
            rows_per_day = 24
            tf = request.timeframe.lower()
            if tf == '1m': rows_per_day = 1440
            elif tf == '5m': rows_per_day = 288
            elif tf == '15m': rows_per_day = 96
            elif tf == '30m': rows_per_day = 48
            elif tf == '1d': rows_per_day = 1
            
            # 5 days a week ~ 71% of days
            expected_rows = int(days * rows_per_day * 0.71)
            
            # Check YF 1m limit (7 days)
            if tf == '1m' and start < datetime.datetime.now() - datetime.timedelta(days=7):
                return {"status": "warning", "message": "Yahoo Finance only provides 1m data for the last 7 days. Ensure OANDA API keys are active for deep history."}
        except ValueError:
            return {"status": "error", "message": "Invalid date format."}
            
    if expected_rows > 500000:
        return {"status": "warning", "message": f"Extremely high density ({expected_rows:,} rows). May encounter API limits or timeouts."}
    elif expected_rows < 1000:
        return {"status": "error", "message": f"Too few rows ({expected_rows:,}). Not enough data to train a reliable model."}
        
    return {"status": "ok", "message": f"Data integrity check passed. Estimated ~{expected_rows:,} rows."}

