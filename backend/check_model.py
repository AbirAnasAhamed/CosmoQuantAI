import sys
import os

from app.db.session import SessionLocal
from app.models.model_training import ModelTrainingJob
import json

try:
    db = SessionLocal()
    job = db.query(ModelTrainingJob).filter(ModelTrainingJob.id.like("%1788078468012%")).first()

    if job:
        print("Job ID:", job.id)
        d = job.__dict__
        d.pop('_sa_instance_state', None)
        print("Attributes:", list(d.keys()))
        print("Algorithm:", job.algorithm)
        if 'config' in d:
            print("Config:", json.dumps(job.config, indent=2) if isinstance(job.config, dict) else job.config)
        if hasattr(job, 'logs') and job.logs:
            print("Logs:")
            for log in job.logs: 
                print(log)
        else:
            print("No logs.")
    else:
        print("Job not found in database.")
except Exception as e:
    print("Error:", e)
