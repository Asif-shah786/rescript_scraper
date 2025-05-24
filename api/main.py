from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from dotenv import load_dotenv
import sys
import os

# Add the parent directory to sys.path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Script.working import (
    scrape_medications,
)  # Note: The actual directory has a space, but Python module names can't have spaces

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
private_key = os.getenv("FIREBASE_PRIVATE_KEY")
if private_key:
    private_key = private_key.replace("\\n", "\n")

cred = credentials.Certificate(
    {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": private_key,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv(
            "FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
        ),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    }
)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI(title="Medication Scraper API")


class MedicationRequest(BaseModel):
    medications: List[str]


@app.post("/scrape-medications")
async def scrape_and_store_medications(request: MedicationRequest):
    try:
        print(f"\nReceived request to scrape medications: {request.medications}")

        # Run the scraper with the provided medications
        print("Starting scraper...")
        results = scrape_medications(request.medications)
        print(f"Scraper completed. Got {len(results)} results.")

        if not results:
            raise HTTPException(status_code=500, detail="No data was scraped")

        # Store results in Firestore
        print("Storing results in Firestore...")
        batch = db.batch()
        for medication_data in results:
            # Create a document reference with the medication name as ID
            doc_ref = db.collection("medications").document(medication_data["name"])
            batch.set(doc_ref, medication_data)
            print(f"Added {medication_data['name']} to batch")

        # Commit the batch
        print("Committing batch to Firestore...")
        batch.commit()
        print("Batch committed successfully")

        # Save results locally to a JSON file
        print("Saving results locally...")
        with open("medication_data.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Results saved locally")

        return {
            "status": "success",
            "message": f"Successfully scraped and stored {len(results)} medications",
            "medications": results,
        }
    except Exception as e:
        print(f"Error in scrape_and_store_medications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Medication Scraper API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
