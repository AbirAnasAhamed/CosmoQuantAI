import sys
import os
sys.path.append(os.path.abspath('e:/CosmoQuantAI/backend'))
from app.db.session import SessionLocal
from app import models

db = SessionLocal()
job = db.query(models.ModelTrainingJob).filter_by(id="forex_train_1787836549104").first()
if job:
    print(f"Status: {job.status}")
    print(f"Error Message: {job.error_message}")
    print(f"Logs: {job.logs[-10:] if job.logs else 'No logs'}")
db.close()
