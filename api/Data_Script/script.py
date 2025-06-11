import json
import requests
import csv
from collections import defaultdict
import time
from pprint import pprint
from drugbank import get_drugbank_info


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
rxnav_base_url = "https://rxnav.nlm.nih.gov/REST"


def make_request(url, max_retries=3, delay=1):
    """Make a request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {str(e)}")
            time.sleep(delay)
    return None


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
                }
            )

    return patent_data, exclusivity_data, products_data


# Load Orange Book data
patent_data, exclusivity_data, products_data = load_orange_book_data()

# Dictionary to store results
medication_data = {}

for medication in MEDICATIONS:
    print(f"\nProcessing {medication}...")

    # Get RxNorm data
    rxcui = get_rxcui(medication)
    if rxcui:
        print(f"Found RxCUI: {rxcui}")
        classes = get_drug_classes(rxcui)
    else:
        print(f"Could not find RxCUI for {medication}")
        classes = {"broad_class": [], "narrow_class": [], "pharmacologic_class": []}

    # Get DrugBank data
    drugbank_info = get_drugbank_info(medication)

    # Get FDA data
    search_url = f"{openfda_base_url}?search=openfda.brand_name:{medication}"

    try:
        response = requests.get(search_url)
        response.raise_for_status()

        data = response.json()

        if data.get("results"):
            result = data["results"][0]

            # Extract the required fields
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

            # Get product info (use first entry if available)
            product_details = product_info[0] if product_info else {}

            medication_data[medication] = {
                "application_number": openfda.get("application_number", ["N/A"])[0],
                "brand_name": openfda.get("brand_name", ["N/A"])[0],
                "generic_name": openfda.get("generic_name", ["N/A"])[0],
                "manufacturer_name": openfda.get("manufacturer_name", ["N/A"])[0],
                # Not needed as per client
                # "route": openfda.get("route", ["N/A"])[0],
                # "product_type": openfda.get("product_type", ["N/A"])[0],
                # "dosage_form": (
                #     products[0].get("dosage_form", "N/A") if products else "N/A"
                # ),
                "patent_expiry_date": latest_patent.get("expiration_date", "N/A"),
                "patent_number": latest_patent.get("patent_number", "N/A"),
                "exclusivity_expiry_date": latest_exclusivity.get(
                    "expiration_date", "N/A"
                ),
                "exclusivity_code": latest_exclusivity.get("exclusivity_code", "N/A"),
                "current_patent_owner": product_details.get(
                    "applicant_full_name", "N/A"
                ),
                "broad_therapeutic_class": classes["broad_class"],
                "narrow_pharmacological_class": classes["pharmacologic_class"],
                "pharmacologic_class": classes["narrow_class"],
                "metabolism": drugbank_info["metabolism"],
                "route_of_elimination": drugbank_info["route_of_elimination"],
            }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching FDA data for {medication}: {e}")
    except (KeyError, IndexError) as e:
        print(f"Error processing FDA data for {medication}: {e}")

    # Be nice to the APIs
    time.sleep(1)

# Print the results
print("\nFinal Results:")
for med, data in medication_data.items():
    print(f"\nMedication: {med}")
    for key, value in data.items():
        print(f"{key}: {value}")

# Save to a file
with open("medication_data.json", "w") as f:
    json.dump(medication_data, f, indent=2)
print("\nResults saved to medication_data.json")
