import json
import requests
import csv
from collections import defaultdict
import time
from pprint import pprint
from .drugbank import get_drugbank_info
from typing import Dict, List

MEDICATIONS = [
    "Abilify",
    "Adderall",
    "Aimovig",
    "Ambien",
    "Atorvastatin",
    "Austedo",
    "Avastin",
    "Benlysta",
    "Biktarvy",
    "Botox",
]

openfda_base_url = "https://api.fda.gov/drug/drugsfda.json"
openfda_label_url = "https://api.fda.gov/drug/label.json"
rxnav_base_url = "https://rxnav.nlm.nih.gov/REST"


def make_request(url, params=None, max_retries=3, delay=1):
    """Make a request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {str(e)}")
            time.sleep(delay)
    return None


def fetch_fda_label_data(brand_name: str, generic_name: str) -> Dict:
    """Fetch medication label data from OpenFDA API."""
    search_query = f'openfda.generic_name:"{generic_name}"'
    print(f"Trying search query: {search_query}")

    data = make_request(openfda_label_url, params={"search": search_query, "limit": 1})

    if not data or not data.get("results"):
        print(f"No label data found for {brand_name}")
        return {
            "brand_name": brand_name,
            "generic_name": generic_name,
            "error": "No data found",
        }

    result = data["results"][0]

    print("result", result)

    # Extract relevant fields
    return {
        "indications_and_usage": (
            result.get("indications_and_usage", ["N/A"])[0]
            if result.get("indications_and_usage")
            else "N/A"
        ),
        "dosage_and_administration": (
            result.get("dosage_and_administration", ["N/A"])[0]
            if result.get("dosage_and_administration")
            else "N/A"
        ),
        "mechanism_of_action": (
            result.get("mechanism_of_action", ["N/A"])[0]
            if result.get("mechanism_of_action")
            else "N/A"
        ),
        "boxed_warning": (
            result.get("boxed_warning", ["N/A"])[0]
            if result.get("boxed_warning")
            else "N/A"
        ),
        "warnings_and_cautions": (
            result.get("warnings_and_cautions", ["N/A"])[0]
            if result.get("warnings_and_cautions")
            else "N/A"
        ),
        "adverse_reactions": (
            result.get("adverse_reactions", ["N/A"])[0]
            if result.get("adverse_reactions")
            else "N/A"
        ),
        "abuse": (result.get("abuse", ["N/A"])[0] if result.get("abuse") else "N/A"),
        "dependence": (
            result.get("dependence", ["N/A"])[0] if result.get("dependence") else "N/A"
        ),
        "spl_medguide": (
            result.get("spl_medguide", ["N/A"])[0]
            if result.get("spl_medguide")
            else "N/A"
        ),
        "information_for_patients": (
            result.get("information_for_patients", ["N/A"])[0]
            if result.get("information_for_patients")
            else "N/A"
        ),
        "drug_interactions": (
            result.get("drug_interactions", ["N/A"])[0]
            if result.get("drug_interactions")
            else "N/A"
        ),
        "contraindications": (
            result.get("contraindications", ["N/A"])[0]
            if result.get("contraindications")
            else "N/A"
        ),
        "pregnancy": (
            result.get("pregnancy", ["N/A"])[0] if result.get("pregnancy") else "N/A"
        ),
        "pediatric_use": (
            result.get("pediatric_use", ["N/A"])[0]
            if result.get("pediatric_use")
            else "N/A"
        ),
        "geriatric_use": (
            result.get("geriatric_use", ["N/A"])[0]
            if result.get("geriatric_use")
            else "N/A"
        ),
        "controlled_substance": (
            result.get("controlled_substance", ["N/A"])[0]
            if result.get("controlled_substance")
            else "N/A"
        ),
    }


def get_rxcui(drug_name):
    """Get RxCUI for a drug name"""
    print(f"Getting RxCUI for {drug_name}...")
    url = f"{rxnav_base_url}/rxcui.json?name={drug_name}"
    data = make_request(url)
    if data and "idGroup" in data and "rxnormId" in data["idGroup"]:
        return data["idGroup"]["rxnormId"][0]
    return None


def get_drug_classes(rxcui):
    """Get therapeutic and pharmacological classes"""
    print(f"Getting drug classes for RxCUI {rxcui}...")
    url = f"{rxnav_base_url}/rxclass/class/byRxcui.json?rxcui={rxcui}"
    data = make_request(url)
    classes = {
        "broad_class": set(),  # VA Class
        "narrow_class": set(),  # ATC Class
        "pharmacologic_class": set(),  # EPC
    }

    if data and "rxclassDrugInfoList" in data:
        for item in data["rxclassDrugInfoList"]["rxclassDrugInfo"]:
            class_info = item["rxclassMinConceptItem"]
            class_type = class_info["classType"]

            if class_type == "VA":
                classes["broad_class"].add(class_info["className"])
            elif class_type == "ATC1-4":
                classes["narrow_class"].add(class_info["className"])
            elif class_type == "EPC":
                classes["pharmacologic_class"].add(class_info["className"])

    return {k: list(v) for k, v in classes.items()}


def load_orange_book_data():
    print("Loading Orange Book data...")
    # Load patent data
    patent_data = defaultdict(list)
    with open("Orange_Data/patent.txt", "r") as f:
        reader = csv.DictReader(f, delimiter="~")
        for row in reader:
            app_no = row["Appl_No"]
            patent_data[app_no].append(
                {
                    "patent_number": row["Patent_No"],
                    "expiration_date": row["Patent_Expire_Date_Text"],
                }
            )

    # Load exclusivity data
    exclusivity_data = defaultdict(list)
    with open("Orange_Data/exclusivity.txt", "r") as f:
        reader = csv.DictReader(f, delimiter="~")
        for row in reader:
            app_no = row["Appl_No"]
            exclusivity_data[app_no].append(
                {
                    "exclusivity_code": row["Exclusivity_Code"],
                    "expiration_date": row["Exclusivity_Date"],
                }
            )

    # Load products data
    products_data = defaultdict(list)
    with open("Orange_Data/products.txt", "r") as f:
        reader = csv.DictReader(f, delimiter="~")
        for row in reader:
            app_no = row["Appl_No"]
            products_data[app_no].append(
                {
                    "applicant_full_name": row["Applicant_Full_Name"],
                    "drug_manufacturer": row["Applicant_Full_Name"],
                }
            )

    return patent_data, exclusivity_data, products_data


def scrape_medications(medications: List[str]) -> List[Dict]:
    """
    Scrape medication data from various sources and return a list of dictionaries.
    Each dictionary contains detailed information about a medication.
    """
    print(f"\nStarting to scrape data for medications: {medications}")

    try:
        # Load Orange Book data
        print("Loading Orange Book data...")
        patent_data, exclusivity_data, products_data = load_orange_book_data()
        print("Orange Book data loaded successfully")
    except Exception as e:
        print(f"Error loading Orange Book data: {e}")
        patent_data, exclusivity_data, products_data = {}, {}, {}

    # Dictionary to store results
    medication_data = {}

    for medication in medications:
        print(f"\nProcessing {medication}...")
        try:
            # Get RxNorm data
            rxcui = get_rxcui(medication)
            if rxcui:
                print(f"Found RxCUI: {rxcui}")
                classes = get_drug_classes(rxcui)
            else:
                print(f"Could not find RxCUI for {medication}")
                classes = {
                    "broad_class": [],
                    "narrow_class": [],
                    "pharmacologic_class": [],
                }

            # Get DrugBank data
            print(f"Getting DrugBank data for {medication}...")
            drugbank_info = get_drugbank_info(medication)
            print(f"DrugBank data retrieved: {drugbank_info}")

            # Get FDA data
            print(f"Getting FDA data for {medication}...")
            try:
                search_url = (
                    f"{openfda_base_url}?search=openfda.brand_name:{medication}"
                )
                response = requests.get(search_url)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"Medication {medication} not found in FDA database")
                    medication_data[medication] = {
                        "name": medication,
                        "error": f"Medication not found in FDA database: {str(e)}",
                        "error_type": "FDA_NOT_FOUND",
                    }
                    continue
                else:
                    raise

            if data.get("results"):
                result = data["results"][0]
                openfda = result.get("openfda", {})
                products = result.get("products", [])

                # Get application number without 'NDA' prefix
                app_number = openfda.get("application_number", ["N/A"])[0]
                if app_number != "N/A":
                    app_number = app_number.replace("NDA", "")

                # Get Orange Book data
                patent_info = patent_data.get(app_number, [])
                exclusivity_info = exclusivity_data.get(app_number, [])
                product_info = products_data.get(app_number, [])

                # Get latest patent and exclusivity dates
                latest_patent = (
                    max(patent_info, key=lambda x: x["expiration_date"])
                    if patent_info
                    else {}
                )
                latest_exclusivity = (
                    max(exclusivity_info, key=lambda x: x["expiration_date"])
                    if exclusivity_info
                    else {}
                )
                product_details = product_info[0] if product_info else {}

                # Get FDA label data
                generic_name = openfda.get("generic_name", ["N/A"])[0]
                label_data = fetch_fda_label_data(medication, generic_name)

                # Combine all data
                medication_data[medication] = {
                    "name": medication,
                    "application_number": openfda.get("application_number", ["N/A"])[0],
                    "brand_name": openfda.get("brand_name", ["N/A"])[0],
                    "generic_name": generic_name,
                    "manufacturer_name": openfda.get("manufacturer_name", ["N/A"])[0],
                    "patent_expiry_date": latest_patent.get("expiration_date", "N/A"),
                    "patent_number": latest_patent.get("patent_number", "N/A"),
                    "exclusivity_expiry_date": latest_exclusivity.get(
                        "expiration_date", "N/A"
                    ),
                    "exclusivity_code": latest_exclusivity.get(
                        "exclusivity_code", "N/A"
                    ),
                    "current_patent_owner": product_details.get(
                        "applicant_full_name", "N/A"
                    ),
                    "drug_manufacturer": product_details.get(
                        "drug_manufacturer", "N/A"
                    ),
                    "therapeutic_class": classes["broad_class"],
                    "broad_pharmacological_class": classes["narrow_class"],
                    "narrow_pharmacologic_class": classes["pharmacologic_class"],
                    "metabolism": drugbank_info["metabolism"],
                    "route_of_elimination": drugbank_info["route_of_elimination"],
                    **label_data,  # Include all FDA label data
                }
                print(f"Successfully processed {medication}")
            else:
                print(f"No FDA data found for {medication}")
                medication_data[medication] = {
                    "name": medication,
                    "error": "No FDA data found",
                }

        except Exception as e:
            print(f"Error processing {medication}: {e}")
            medication_data[medication] = {
                "name": medication,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_source": "scraper",
            }

        # Be nice to the APIs
        time.sleep(1)

    print(f"\nScraping complete. Processed {len(medication_data)} medications.")
    return list(medication_data.values())


def main():
    # Use the predefined list of medications
    results = scrape_medications(MEDICATIONS)

    # Save to a file
    with open("medication_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to medication_data.json")


if __name__ == "__main__":
    main()
