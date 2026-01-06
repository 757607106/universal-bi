
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_chat():
    # 1. List Datasets
    print("Listing datasets...")
    resp = requests.get(f"{BASE_URL}/datasets/")
    if resp.status_code != 200:
        print(f"Failed to list datasets: {resp.text}")
        return

    datasets = resp.json()
    target_ds = None
    
    # Prefer dataset 7 if exists, else any trained one
    for ds in datasets:
        if ds['id'] == 7:
            target_ds = ds
            break
    
    if not target_ds and datasets:
        target_ds = datasets[0]
        
    if not target_ds:
        print("No datasets found. Cannot verify chat.")
        return

    print(f"Using Dataset ID: {target_ds['id']} (Status: {target_ds.get('training_status')})")
    
    # 2. Send Chat Request
    # question = "按城市统计用户数量" # This failed because users table missing
    question = "统计商品数量" # Try querying products
    
    payload = {
        "dataset_id": target_ds['id'],
        "question": question
    }
    
    print(f"Sending Chat Request: {payload}")
    resp = requests.post(f"{BASE_URL}/chat/", json=payload)
    
    if resp.status_code == 200:
        print("Chat Request Successful!")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Chat Request Failed: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    test_chat()
