import sys
import os
import requests
import time
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_flow():
    # 0. Setup: Ensure we have the absolute path to the DB
    cwd = os.getcwd()
    db_path = os.path.join(cwd, "backend", "sql_app.db")
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    print(f"Using database at: {db_path}")

    # 1. Create DataSource (SQLite)
    print("\n1. Creating/Checking DataSource...")
    try:
        # List first to see if exists
        response = requests.get(f"{BASE_URL}/datasources/")
        if response.status_code != 200:
            print(f"Failed to list datasources. Is backend running? {response.text}")
            return
            
        datasources = response.json()
        ds_id = None
        
        # Check if our test datasource exists
        for ds in datasources:
            if ds["name"] == "Local Self-Test DB":
                ds_id = ds["id"]
                print(f"Found existing DataSource ID: {ds_id}")
                break
                
        if not ds_id:
            print("Creating new DataSource...")
            data = {
                "name": "Local Self-Test DB",
                "type": "sqlite",
                "host": db_path, # We use host field for file path in our hacked DBInspector
                "port": 0,
                "username": "",
                "password": "",
                "database_name": ""
            }
            resp = requests.post(f"{BASE_URL}/datasources/", json=data)
            if resp.status_code != 200:
                print(f"Failed to create datasource: {resp.text}")
                return
            ds_id = resp.json()["id"]
            print(f"Created DataSource ID: {ds_id}")

        # 2. Check Tables
        print(f"\n2. Fetching tables for DataSource {ds_id}...")
        resp = requests.get(f"{BASE_URL}/datasources/{ds_id}/tables")
        if resp.status_code != 200:
            print(f"Failed to get tables: {resp.text}")
            return
        tables = resp.json()
        print(f"Found tables: {tables}")
        
        if "datasources" not in tables:
            print("Error: Expected 'datasources' table not found.")
            # return # Proceed anyway to see what happens

        # 3. Create Dataset
        print("\n3. Creating Dataset...")
        dataset_name = f"Self-Reflection Dataset {int(time.time())}"
        data = {
            "name": dataset_name,
            "datasource_id": ds_id
        }
        resp = requests.post(f"{BASE_URL}/datasets/", json=data)
        if resp.status_code != 200:
            print(f"Failed to create dataset: {resp.text}")
            return
        dataset_id = resp.json()["id"]
        print(f"Created Dataset ID: {dataset_id}")

        # 4. Update Schema (Select tables)
        print("\n4. Updating Dataset Schema...")
        # Let's train on 'datasources' and 'datasets' tables
        selected_tables = [t for t in tables if t in ["datasources", "datasets"]]
        if not selected_tables:
             selected_tables = [tables[0]] if tables else []
             
        print(f"Selected tables: {selected_tables}")
        
        if not selected_tables:
            print("No tables available to select.")
            return

        resp = requests.put(f"{BASE_URL}/datasets/{dataset_id}/tables", json={"schema_config": selected_tables})
        if resp.status_code != 200:
            print(f"Failed to update tables: {resp.text}")
            return

        # 5. Train
        print("\n5. Triggering Training...")
        resp = requests.post(f"{BASE_URL}/datasets/{dataset_id}/train")
        if resp.status_code != 200:
            print(f"Failed to trigger training: {resp.text}")
            return
        print("Training triggered.")

        # 6. Poll Status
        print("\n6. Polling for completion...")
        max_retries = 30
        for i in range(max_retries):
            resp = requests.get(f"{BASE_URL}/datasets/")
            datasets = resp.json()
            target_ds = next((d for d in datasets if d["id"] == dataset_id), None)
            
            if target_ds:
                status = target_ds["training_status"]
                print(f"[{i+1}/{max_retries}] Status: {status}")
                
                if status == "completed":
                    print("\nSUCCESS: Training completed!")
                    return
                if status == "failed":
                    print("\nFAILURE: Training failed!")
                    return
            
            time.sleep(2)

        print("\nTIMEOUT: Training took too long.")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to backend. Is it running on port 8000?")

if __name__ == "__main__":
    test_flow()
