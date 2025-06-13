import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from dotenv import load_dotenv
import sys
from datetime import datetime, timezone
import uuid
import argparse
from google.cloud.firestore_v1.base_query import FieldFilter

# Add the parent directory to sys.path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Data_Script.working import scrape_medications

# Load environment variables
load_dotenv()

# Create runs directory if it doesn't exist
runs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
os.makedirs(runs_dir, exist_ok=True)

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


def process_medications(medications):
    try:
        print(f"\nProcessing {len(medications)} medications...")
        print("Medications:", medications)

        # Generate a unique run ID and timestamp
        run_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Run the scraper
        print("\nStarting scraper...")
        results = scrape_medications(medications)
        print(f"Scraper completed. Got {len(results)} results.")

        if not results:
            print("Error: No data was scraped")
            return

        # Filter out any results that have errors
        valid_results = [r for r in results if "error" not in r]
        failed_results = [r for r in results if "error" in r]

        if not valid_results:
            print("Error: All medication scraping attempts failed")
            print("Failed results:", failed_results)
            return

        # Store results in Firestore
        print("\nStoring results in Firestore...")
        batch = db.batch()

        # Create a run metadata document
        run_metadata = {
            "run_id": run_id,
            "timestamp": timestamp,
            "medications_requested": medications,
            "medications_scraped": len(valid_results),
            "medications_failed": len(results) - len(valid_results),
            "status": "completed",
        }
        run_doc_ref = db.collection("scraping_runs").document(run_id)
        batch.set(run_doc_ref, run_metadata)

        # Process and store valid results in Firestore
        for medication_data in valid_results:
            # Add metadata to the medication record
            medication_data.update(
                {
                    "scraped_at": timestamp.isoformat(),
                    "run_id": run_id,
                    "source": "local_script",
                }
            )

            # Get name and generic name for uniqueness check
            name = medication_data.get("name", "").lower().strip()
            generic_name = medication_data.get("generic_name", "").lower().strip()
            # Store lowercase versions in the data
            medication_data["name"] = name
            medication_data["generic_name"] = generic_name

            print(f"\nDebug - Checking medication:")
            print(f"Name: '{name}'")
            print(f"Generic Name: '{generic_name}'")

            if not name or not generic_name:
                print(
                    f"Warning: Missing name or generic_name for medication {medication_data.get('name', 'Unknown')}"
                )
                # Create new document for medications without required fields
                doc_ref = db.collection("draft_medications").document()
                batch.set(doc_ref, medication_data)
                print(
                    f"Added new medication without complete identification: {medication_data.get('name', 'Unknown')}"
                )
                continue

            # Query for existing medication with same name and generic name
            existing_docs = (
                db.collection("draft_medications")
                .where(filter=FieldFilter("name", "==", name))
                .where(filter=FieldFilter("generic_name", "==", generic_name))
                .limit(1)
                .get()
            )

            print(f"Debug - Found {len(existing_docs)} existing documents")

            if existing_docs:
                # Update existing document
                existing_doc = existing_docs[0]
                existing_data = existing_doc.to_dict() or {}
                print(f"Debug - Existing document data:")
                print(f"Name: '{existing_data.get('name', '')}'")
                print(f"Generic Name: '{existing_data.get('generic_name', '')}'")

                # Get existing update history or initialize new one
                update_history = existing_data.get("update_history", [])
                update_history.append(timestamp.isoformat())

                # Add update history to medication data
                medication_data["update_history"] = update_history

                batch.set(existing_doc.reference, medication_data, merge=True)
                print(f"Updated existing medication: {name} (Generic: {generic_name})")
            else:
                # Create new document with initial update history
                medication_data["update_history"] = [timestamp.isoformat()]
                doc_ref = db.collection("draft_medications").document()
                batch.set(doc_ref, medication_data)
                print(f"Added new medication: {name} (Generic: {generic_name})")

        # Add metadata to failed results (for local JSON only)
        for medication_data in failed_results:
            medication_data.update(
                {
                    "scraped_at": timestamp.isoformat(),
                    "run_id": run_id,
                    "source": "local_script",
                }
            )

        # Commit the batch
        print("\nCommitting batch to Firestore...")
        batch.commit()
        print("Batch committed successfully")

        # Save all results (both valid and failed) locally to a JSON file
        print("\nSaving results locally...")
        # Format: YYYY-MM-DD_HH-MM
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_file = os.path.join(runs_dir, f"medication_data_{timestamp_str}.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved locally to {output_file}")

        print(f"\nSuccessfully processed {len(valid_results)} medications")
        print(f"Run ID: {run_id}")
        print(f"Timestamp: {timestamp.isoformat()}")
        if failed_results:
            print(
                f"\nFailed medications: {[r.get('name', 'Unknown') for r in failed_results]}"
            )

    except Exception as e:
        print(f"Error processing medications: {str(e)}")


if __name__ == "__main__":
    # Process only batch 1 for now
    print("Starting with Batch 0...")
    batch0 = [
        "Abilify",
        "Atorvastatin",
        # "Metformin",
        # "Lisinopril",
        # "Levothyroxine",
        # "Amlodipine",
        # "Metoprolol",
        # "Albuterol",
        # "Losartan",
        # "Omeprazole",
    ]

    # Split medications into batches of 50
    batch1 = [
        "Gabapentin",
        "Hydrochlorothiazide",
        "Amoxicillin",
        "Simvastatin",
        "Prednisone",
        "Sertraline",
        "Furosemide",
        "Acetaminophen",
        "Tamsulosin",
        "Escitalopram",
        "Rosuvastatin",
        "Clopidogrel",
        "Montelukast",
        "Fluoxetine",
        "Warfarin",
        "Bupropion",
        "Propranolol",
        "Doxycycline",
        "Meloxicam",
        "Citalopram",
        "Pantoprazole",
        "Allopurinol",
        "Venlafaxine",
        "Ranitidine",
        "Atenolol",
        "Cyclobenzaprine",
        "Pravastatin",
        "Loratadine",
        "Tramadol",
        "Azithromycin",
        "Cephalexin",
        "Trazodone",
        "Methylprednisolone",
        "Diltiazem",
        "Buspirone",
        "Spironolactone",
        "Naproxen",
        "Diazepam",
        "Amitriptyline",
        "Lorazepam",
        "Carvedilol",
    ]

    batch2 = [
        "Clonazepam",
        "Topiramate",
        "Lamotrigine",
        "Levofloxacin",
        "Latanoprost",
        "Aripiprazole",
        "Quetiapine",
        "Risperidone",
        "Olanzapine",
        "Ziprasidone",
        "Haloperidol",
        "Lithium",
        "Valproic Acid",
        "Carbamazepine",
        "Phenytoin",
        "Phenobarbital",
        "Ethosuximide",
        "Pregabalin",
        "Levetiracetam",
        "Oxcarbazepine",
        "Tiagabine",
        "Zonisamide",
        "Felbamate",
        "Vigabatrin",
        "Rufinamide",
        "Lacosamide",
        "Ezogabine",
        "Perampanel",
        "Brivaracetam",
        "Eslicarbazepine",
        "Cannabidiol",
        "Stiripentol",
        "Clobazam",
        "Methotrexate",
        "Hydroxychloroquine",
        "Sulfasalazine",
        "Leflunomide",
        "Azathioprine",
        "Cyclophosphamide",
        "Mycophenolate Mofetil",
        "Cyclosporine",
        "Tacrolimus",
        "Sirolimus",
        "Everolimus",
        "Belimumab",
        "Rituximab",
        "Infliximab",
        "Adalimumab",
        "Etanercept",
        "Golimumab",
    ]

    batch3 = [
        "Certolizumab",
        "Tocilizumab",
        "Anakinra",
        "Abatacept",
        "Ustekinumab",
        "Secukinumab",
        "Ixekizumab",
        "Brodalumab",
        "Guselkumab",
        "Tildrakizumab",
        "Risankizumab",
        "Apremilast",
        "Dimethyl Fumarate",
        "Fingolimod",
        "Teriflunomide",
        "Alemtuzumab",
        "Ocrelizumab",
        "Natalizumab",
        "Cladribine",
        "Siponimod",
        "Ozanimod",
        "Ponesimod",
        "Erenumab",
        "Fremanezumab",
        "Galcanezumab",
        "Eptinezumab",
        "Rimegepant",
        "Ubrogepant",
        "Lasmiditan",
        "Sumatriptan",
        "Rizatriptan",
        "Zolmitriptan",
        "Naratriptan",
        "Almotriptan",
        "Frovatriptan",
        "Eletriptan",
        "Dihydroergotamine",
        "Ergotamine",
        "Methysergide",
        "Verapamil",
        "Doxepin",
        "Protriptyline",
        "Clomipramine",
        "Imipramine",
        "Desipramine",
        "Trimipramine",
        "Maprotiline",
        "Amoxapine",
        "Mirtazapine",
        "Nefazodone",
    ]

    batch4 = [
        "Vilazodone",
        "Vortioxetine",
        "Desvenlafaxine",
        "Duloxetine",
        "Levomilnacipran",
        "Milnacipran",
        "Reboxetine",
        "Atomoxetine",
        "Modafinil",
        "Armodafinil",
        "Methylphenidate",
        "Dexmethylphenidate",
        "Amphetamine",
        "Dextroamphetamine",
        "Lisdexamfetamine",
        "Guanfacine",
        "Clonidine",
        "Naltrexone",
        "Acamprosate",
        "Disulfiram",
        "Methadone",
        "Buprenorphine",
        "Naloxone",
        "Varenicline",
        "Nicotine",
        "Nortriptyline",
        "Aspirin",
        "Lansoprazole",
        "Ramipril",
        "Bisoprolol",
        "Paracetamol",
        "Beclometasone",
        "Co-codamol",
        "Folic acid",
        "Salbutamol",
        "Apixaban",
        "Candesartan",
        "Colecalciferol",
        "Doxazosin",
        "Macrogol",
        "Prednisolone",
        "Bendroflumethiazide",
        "Gliclazide",
        "Indapamide",
        "Fexofenadine",
        "Fostair",
        "Codeine",
        "Alendronic acid",
        "Dapagliflozin",
        "Zopiclone",
        "Rivaroxaban",
    ]

    # Process only batch 1 for now
    print("Starting with Batch 0...")
    process_medications(batch0)
