import os
import shutil
import time
import asyncio
from typing import List, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()

UPLOAD_DIR = "uploads/models"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def simulate_processing(db: Session, version_id: str):
    """Background task to simulate model processing"""
    # Wait for a few seconds
    await asyncio.sleep(5)
    
    # Update status to Ready
    version = db.query(models.ModelVersion).filter(models.ModelVersion.id == version_id).first()
    if version and version.status == models.ModelStatus.PROCESSING:
        version.status = models.ModelStatus.READY
        db.commit()

@router.get("", response_model=List[schemas.CustomMLModelResponse])
def get_custom_models(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve all custom models for the current user.
    """
    models_list = db.query(models.CustomMLModel).filter(models.CustomMLModel.user_id == current_user.id).order_by(models.CustomMLModel.created_at.desc()).all()
    return models_list

@router.post("", response_model=schemas.CustomMLModelResponse)
async def create_custom_model(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    model_type: str = Form(...),
    version: float = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new custom ML model and upload its first version.
    """
    timestamp = int(time.time() * 1000)
    model_id = f"model_{timestamp}"
    version_id = f"v{version}-{timestamp}"
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{version_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create model entry
    db_model = models.CustomMLModel(
        id=model_id,
        name=name,
        model_type=model_type,
        user_id=current_user.id,
        active_version_id=version_id
    )
    db.add(db_model)
    db.commit()

    # Create version entry
    db_version = models.ModelVersion(
        id=version_id,
        model_id=model_id,
        version=version,
        description=description,
        file_path=file_path,
        status=models.ModelStatus.PROCESSING
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_model)
    
    # Trigger background processing
    background_tasks.add_task(simulate_processing, db, version_id)

    return db_model

@router.post("/{model_id}/versions", response_model=schemas.CustomMLModelResponse)
async def upload_new_version(
    model_id: str,
    background_tasks: BackgroundTasks,
    version: float = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload a new version for an existing model.
    """
    db_model = db.query(models.CustomMLModel).filter(models.CustomMLModel.id == model_id, models.CustomMLModel.user_id == current_user.id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    timestamp = int(time.time() * 1000)
    version_id = f"v{version}-{timestamp}"
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{version_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create version entry
    db_version = models.ModelVersion(
        id=version_id,
        model_id=model_id,
        version=version,
        description=description,
        file_path=file_path,
        status=models.ModelStatus.PROCESSING
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_model)

    # Trigger background processing
    background_tasks.add_task(simulate_processing, db, version_id)

    return db_model

@router.put("/{model_id}/active-version", response_model=schemas.CustomMLModelResponse)
def set_active_version(
    model_id: str,
    update_data: schemas.CustomMLModelUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Set the active version for a model.
    """
    db_model = db.query(models.CustomMLModel).filter(models.CustomMLModel.id == model_id, models.CustomMLModel.user_id == current_user.id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Verify version exists and belongs to this model
    db_version = db.query(models.ModelVersion).filter(models.ModelVersion.id == update_data.active_version_id, models.ModelVersion.model_id == model_id).first()
    if not db_version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    if db_version.status != models.ModelStatus.READY:
        raise HTTPException(status_code=400, detail="Cannot activate a version that is not Ready")

    db_model.active_version_id = update_data.active_version_id
    db.commit()
    db.refresh(db_model)

    return db_model

@router.delete("/{model_id}")
def delete_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a custom ML model and its files.
    """
    db_model = db.query(models.CustomMLModel).filter(models.CustomMLModel.id == model_id, models.CustomMLModel.user_id == current_user.id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete physical files
    for version in db_model.versions:
        if os.path.exists(version.file_path):
            try:
                os.remove(version.file_path)
            except Exception as e:
                print(f"Error removing file {version.file_path}: {e}")

    db.delete(db_model)
    db.commit()

    return {"status": "success"}
