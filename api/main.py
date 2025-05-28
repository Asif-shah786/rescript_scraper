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

# Add CORS middleware import
from fastapi.middleware.cors import CORSMiddleware

# Add import for running synchronous code in background thread
from starlette.concurrency import run_in_threadpool

# Add the parent directory to sys.path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Script.working import (
    scrape_medications,
)

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rescriptapp.web.app",  # Allow your deployed Flutter app origin
        "http://localhost:XXXX",  # Optional: Add your local Flutter web dev origin for testing
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (POST, GET, OPTIONS)
    allow_headers=["*"],  # Allow all headers
)


class MedicationRequest(BaseModel):
    medications: List[str]
    run_id: Optional[str] = None  # Optional run ID for tracking multiple scraping runs


# Use api_route to explicitly allow POST and OPTIONS methods
@app.api_route("/scrape-medications", methods=["POST", "OPTIONS"])
async def scrape_and_store_medications(request: MedicationRequest):
    # This check is usually not needed when CORS is properly configured with OPTIONS allowed
    # but we can keep it for robustness if needed.
    # if request.method == "OPTIONS":
    #    return {"message": "OK"}

    try:
        print(f"\nReceived request to scrape medications: {request.medications}")

        # Generate a unique run ID if not provided
        run_id = request.run_id or str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Run the synchronous scraper in a background thread
        print("Starting scraper in background thread...")
        results = await run_in_threadpool(scrape_medications, request.medications)
        print(f"Scraper completed. Got {len(results)} results.")

        if not results:
            raise HTTPException(status_code=500, detail="No data was scraped")

        # Filter out any results that have errors
        valid_results = [r for r in results if "error" not in r]

        if not valid_results:
            raise HTTPException(
                status_code=500, detail="All medication scraping attempts failed"
            )

        # Store results in Firestore
        print("Storing results in Firestore...")
        batch = db.batch()

        # Create a run metadata document
        run_metadata = {
            "run_id": run_id,
            "timestamp": timestamp,
            "medications_requested": request.medications,
            "medications_scraped": len(valid_results),
            "medications_failed": len(results) - len(valid_results),
            "status": "completed",
        }
        run_doc_ref = db.collection("scraping_runs").document(run_id)
        batch.set(run_doc_ref, run_metadata)

        for medication_data in valid_results:
            # Add metadata to each medication record
            medication_data.update(
                {"scraped_at": timestamp, "run_id": run_id, "source": "admin_portal"}
            )

            # Use an auto-generated document reference for draft_medications
            doc_ref = db.collection("draft_medications").document()
            # Ensure name field exists for querying and identification
            medication_data["name"] = medication_data.get("name", "Unknown Medication")
            batch.set(doc_ref, medication_data)
            print(
                f"Added medication with ID {doc_ref.id} (Name: {medication_data['name']}) to batch"
            )

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
            "message": f"Successfully scraped and stored {len(valid_results)} medications",
            "run_id": run_id,
            "timestamp": timestamp.isoformat(),
            "medications": valid_results,
        }
    except Exception as e:
        print(f"Error in scrape_and_store_medications: {str(e)}")
        # Catch specific exceptions for better error messages if needed
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Medication Scraper API is running"}


# IMPORTANT: You still need to implement the /scrape-medications/status/{run_id} endpoint
# for your Flutter app to be able to poll for scraping progress.

if __name__ == "__main__":
    import uvicorn

    # Use host="0.0.0.0" and port from environment variable if running on Render
    # For local development, you might use host="127.0.0.1" and a fixed port
    # Example for Render:
    # port = int(os.environ.get("PORT", 8000))
    # uvicorn.run(app, host="0.0.0.0", port=port)
    uvicorn.run(
        app, host="0.0.0.0", port=8001
    )  # Assuming port 8001 is configured on Render
