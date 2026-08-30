import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://cosmouser:your_secure_password@cosmoquant_db:5432/cosmoquant_db")
    cur = conn.cursor()
    cur.execute("SELECT explainability FROM model_versions WHERE model_id = 'forex_model_1788010326';")
    result = cur.fetchone()
    if result:
        print("Explainability Data:")
        print(json.dumps(result[0], indent=2))
    else:
        print("Not found.")
    
    cur.execute("SELECT accuracy FROM model_versions WHERE model_id = 'forex_model_1788010326';")
    print("Accuracy:", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("Error:", e)
