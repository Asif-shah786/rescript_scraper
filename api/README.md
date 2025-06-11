# Medication Scraper API

This FastAPI application integrates a medication scraper with Firebase Firestore for data storage.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Firebase:
   - Create a Firebase project at https://console.firebase.google.com/
   - Go to Project Settings > Service Accounts
   - Generate a new private key
   - Save the JSON file as `firebase-credentials.json` in the project root

3. Create a `.env` file in the project root with the following variables:
```
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_X509_CERT_URL=your_client_x509_cert_url
FIREBASE_TYPE=service_account
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
```

## Running the API

Start the API server:
```bash
cd api
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /scrape-medications
Scrapes medication data and stores it in Firebase.

Request body:
```json
{
    "medications": ["medication1", "medication2", ...]
}
```

### GET /
Health check endpoint

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Local Development

For local development:
1. Make sure you have Chrome installed
2. Install Python dependencies
3. Set up your Firebase credentials
4. Run the server locally

The API will be accessible at `http://localhost:8000` and can be used with your local development environment. 