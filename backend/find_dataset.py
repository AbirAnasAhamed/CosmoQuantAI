import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://cosmouser:your_secure_password@cosmoquant_db:5432/cosmoquant_db")
    cur = conn.cursor()
    cur.execute("SELECT dataset_path FROM model_versions WHERE model_id = 'forex_model_1788010326';")
    result = cur.fetchone()
    if result:
        print("Dataset Path:", result[0])
    else:
        print("Not found in model_versions.")
        
    cur.execute("SELECT config FROM model_training_jobs WHERE id = 'forex_train_1788009559292';")
    job = cur.fetchone()
    if job:
        print("Dataset Path from Job:", job[0].get("dataset_path"))
    else:
        print("Job not found.")
    conn.close()
except Exception as e:
    print("Error:", e)
