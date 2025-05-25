from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from dotenv import load_dotenv
import sys
import os
from datetime import datetime
import uuid

# Add the parent directory to sys.path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Script.working import (
    scrape_medications,
)  # Note: The actual directory has a space, but Python module names can't have spaces

# Load environment variables
load_dotenv()

# Initialize Firebase Admin
try:
    # Try to use environment variables first
    required_env_vars = [
        "FIREBASE_PROJECT_ID",
        "FIREBASE_PRIVATE_KEY_ID",
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_CLIENT_ID",
        "FIREBASE_CLIENT_X509_CERT_URL",
        "FIREBASE_TYPE",
        "FIREBASE_AUTH_URI",
        "FIREBASE_TOKEN_URI",
        "FIREBASE_AUTH_PROVIDER_X509_CERT_URL",
    ]

    # Check if all required environment variables are present
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your Render environment settings")
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    cred_dict = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv(
            "FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
        ),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    }

    # Add universe_domain if it exists
    if os.getenv("FIREBASE_UNIVERSE_DOMAIN"):
        cred_dict["universe_domain"] = os.getenv("FIREBASE_UNIVERSE_DOMAIN")

    print("Initializing Firebase with credentials...")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully with environment variables")

except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    print(
        "Please make sure all required environment variables are set in your Render environment settings"
    )
    raise

app = FastAPI(title="Medication Scraper API")


class MedicationRequest(BaseModel):
    medications: List[str]
    run_id: Optional[str] = None  # Optional run ID for tracking multiple scraping runs


@app.post("/scrape-medications")
async def scrape_and_store_medications(request: MedicationRequest):
    try:
        print(f"\nReceived request to scrape medications: {request.medications}")

        # Generate a unique run ID if not provided
        run_id = request.run_id or str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Run the scraper with the provided medications
        print("Starting scraper...")
        results = scrape_medications(request.medications)
        print(f"Scraper completed. Got {len(results)} results.")

        if not results:
            raise HTTPException(status_code=500, detail="No data was scraped")

        # Store results in Firestore
        print("Storing results in Firestore...")
        batch = db.batch()

        # Create a run metadata document
        run_metadata = {
            "run_id": run_id,
            "timestamp": timestamp,
            "medications_requested": request.medications,
            "medications_scraped": len(results),
            "status": "completed",
        }
        run_doc_ref = db.collection("scraping_runs").document(run_id)
        batch.set(run_doc_ref, run_metadata)

        for medication_data in results:
            # Add metadata to each medication record
            medication_data.update(
                {"scraped_at": timestamp, "run_id": run_id, "source": "admin_portal"}
            )

            # Create a document reference with the medication name as ID
            doc_ref = db.collection("draft_medications").document(
                medication_data["name"]
            )
            batch.set(doc_ref, medication_data)
            print(f"Added {medication_data['name']} to batch")

        # Commit the batch
        print("Committing batch to Firestore...")
        batch.commit()
        print("Batch committed successfully")

        # # Save results locally to a JSON file
        # print("Saving results locally...")
        # with open("medication_data.json", "w") as f:
        #     json.dump(results, f, indent=2)
        # print("Results saved locally")

        return {
            "status": "success",
            "message": f"Successfully scraped and stored {len(results)} medications",
            "run_id": run_id,
            "timestamp": timestamp.isoformat(),
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
