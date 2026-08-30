import os
import sys
import json
sys.path.append("/app")

from app.database import SessionLocal
from app.models import ModelVersion

db = SessionLocal()
version = db.query(ModelVersion).filter(ModelVersion.model_id == "forex_model_1788010326").first()
if version:
    print(f"Accuracy: {version.accuracy}")
    print(f"Explainability: {json.dumps(version.explainability, indent=2)}")
else:
    print("Model version not found.")
db.close()
