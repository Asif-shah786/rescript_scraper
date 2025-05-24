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

3. Create a `.env` file in the project root (if needed for additional configuration)

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

## Deployment

The API can be deployed to:
- Render
- AWS Lambda + API Gateway
- Any other platform that supports Python applications

Make sure to set up the necessary environment variables and Firebase credentials in your deployment environment. 