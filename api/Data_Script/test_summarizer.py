from summarizer import generate_summary
import json
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct path to medication_data.json (one level up from current directory)
medication_data_path = os.path.join(
    os.path.dirname(current_dir), "medication_data.json"
)

# Load real medication data
with open(medication_data_path, "r") as f:
    medications = json.load(f)

# Select a medication for testing (using Adderall as an example)
medication = medications[0]  # First medication in the list

# Sample medication data
sample_texts = {
    "indications_and_usage": medication["indications_and_usage"],
    "adverse_reactions": medication["adverse_reactions"],
    "drug_interactions": medication["drug_interactions"],
    "contraindications": medication["contraindications"],
    "pregnancy": medication["pregnancy"],
    "pediatric_use": medication["pediatric_use"],
    "geriatric_use": medication["geriatric_use"],
    "information_for_patients": medication["information_for_patients"],
}


def test_summaries():
    print(f"Testing summarizer with real medication data for {medication['name']}...\n")

    for field, text in sample_texts.items():
        if text and text != "N/A":  # Only process non-empty fields
            print(f"\nOriginal {field}:")
            print("-" * 50)
            print(text)
            print("\nSummary:")
            print("-" * 50)
            summary = generate_summary(text)
            print(summary)
            print("\n" + "=" * 80)


if __name__ == "__main__":
    test_summaries()
