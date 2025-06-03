import os
import json
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from summarizer import generate_summary

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
        print("Please set these variables in your .env file")
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

    print("Initializing Firebase with credentials...")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully")

except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    print(
        "Please make sure all required environment variables are set in your .env file"
    )
    raise


def update_summaries():
    try:
        # Get all medications from Firebase
        print("\nFetching medications from Firebase...")
        medications_ref = db.collection("draft_medications")
        medications = medications_ref.stream()

        # Convert to list for easier processing
        medications_list = []
        for med in medications:
            medications_list.append(med.to_dict())

        print(f"Found {len(medications_list)} medications")

        # Fields that need summaries
        summary_fields = [
            "indications_and_usage",
            "dosage_and_administration",
            "mechanism_of_action",
            "adverse_reactions",
            "drug_interactions",
            "contraindications",
            "pregnancy",
            "pediatric_use",
            "geriatric_use",
            "metabolism",
            "route_of_elimination",
            "information_for_patients",
            "boxed_warning",
            "warnings_and_cautions",
            "abuse",
            "dependence",
            "spl_medguide",
            "controlled_substance",
        ]

        # Process each medication
        updated_medications = []
        for med in medications_list:
            print(f"\nProcessing {med.get('name', 'Unknown')}...")

            # Generate new summaries for each field
            for field in summary_fields:
                original_text = med.get(field, "")
                if original_text and original_text != "N/A":
                    print(f"Generating summary for {field}...")
                    new_summary = generate_summary(original_text)
                    if new_summary:
                        med[f"{field}_summary"] = new_summary
                        print(f"Updated {field} summary")

            updated_medications.append(med)

        # Update Firebase
        print("\nUpdating Firebase...")
        batch = db.batch()
        for med in updated_medications:
            doc_ref = medications_ref.document(med.get("id", ""))
            batch.set(doc_ref, med, merge=True)
        batch.commit()
        print("Firebase updated successfully")

        # Update the existing local JSON file
        local_file_path = "/Users/syedasif/dev/rescript_scraper/api/runs/medication_data_2025-06-03_12-45.json"
        print(f"\nUpdating local file at {local_file_path}")

        # Read existing file
        with open(local_file_path, "r") as f:
            existing_data = json.load(f)

        # Update summaries in existing data
        for existing_med in existing_data:
            med_name = existing_med.get("name")
            # Find matching medication in updated data
            updated_med = next(
                (m for m in updated_medications if m.get("name") == med_name), None
            )
            if updated_med:
                # Update summaries
                for field in summary_fields:
                    summary_field = f"{field}_summary"
                    if summary_field in updated_med:
                        existing_med[summary_field] = updated_med[summary_field]

        # Write back to the same file
        with open(local_file_path, "w") as f:
            json.dump(existing_data, f, indent=2, default=str)
        print("Local file updated successfully")

        print(f"\nSuccessfully updated {len(updated_medications)} medications")

    except Exception as e:
        print(f"Error updating summaries: {str(e)}")
        raise


if __name__ == "__main__":
    update_summaries()
