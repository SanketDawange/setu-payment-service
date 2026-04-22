import json
import requests
import sys
import os

# Base URL of the service (can be set via environment variable)
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def ingest_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        events = json.load(f)

    print(f"Total events to ingest: {len(events)}")
    
    success_count = 0
    error_count = 0
    
    # Using a session for better performance
    session = requests.Session()
    
    for i, event in enumerate(events):
        try:
            response = session.post(f"{BASE_URL}/events", json=event)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Error at index {i}: {response.status_code} - {response.text}")
                error_count += 1
        except Exception as e:
            print(f"Exception at index {i}: {e}")
            error_count += 1
            
        if (i + 1) % 500 == 0:
            print(f"Processed {i + 1} events...")

    print(f"Ingestion completed.")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")

if __name__ == "__main__":
    sample_file = "../sample_events.json"
    ingest_file(sample_file)
