import requests
import json

# Base URL
BASE_URL = "https://rescript-scraper.onrender.com"

# Test root endpoint
print("Testing root endpoint...")
response = requests.get(f"{BASE_URL}/")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test scraping endpoint
print("Testing scraping endpoint...")
data = {
    "medications": [
        "Abilify",
        "Adderall",
        "Aimovig",
    ]
}
response = requests.post(f"{BASE_URL}/scrape-medications", json=data)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}\n")

# If we got a run_id, test progress endpoint
if response.status_code == 200:
    run_id = response.json().get("run_id")
    if run_id:
        print(f"Testing progress endpoint for run_id: {run_id}")
        progress_response = requests.get(f"{BASE_URL}/scraping-progress/{run_id}")
        print(f"Status: {progress_response.status_code}")
        print(f"Response: {json.dumps(progress_response.json(), indent=2)}")
