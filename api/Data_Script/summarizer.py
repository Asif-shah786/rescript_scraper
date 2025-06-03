import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def generate_summary_openrouter(text: str, max_length: int = 300) -> Optional[str]:
    """
    Generate a summary of the given text using OpenRouter's Mixtral model.
    The summary will be concise but informative, suitable for a mobile screen.

    Args:
        text (str): The text to summarize
        max_length (int): Maximum length of the summary in characters

    Returns:
        str: The generated summary or None if there was an error
    """
    if not text or text == "N/A":
        return "N/A"

    try:
        # Prepare the prompt
        prompt = f"""Create a clear and concise summary of the following text. 
        Focus on the key points and main information.
        Keep the summary under {max_length} characters.

        Text to summarize:
        {text}"""

        # Make the API request
        response = requests.post(
            url=OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,  # Limit response length
                "temperature": 0.3,  # Lower temperature for more focused summaries
            },
        )

        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"].strip()
            return summary
        else:
            print(
                f"Error from OpenRouter API: {response.status_code} - {response.text}"
            )
            return None

    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return None


def generate_summary_gemini(text: str, max_length: int = 300) -> Optional[str]:
    """
    Generate a summary of the given text using Google's Gemini API.
    The summary will be concise but informative, suitable for a mobile screen.

    Args:
        text (str): The text to summarize
        max_length (int): Maximum length of the summary in characters

    Returns:
        str: The generated summary or None if there was an error
    """
    if not text or text == "N/A":
        return "N/A"

    try:
        # Prepare the prompt
        prompt = f"""Create a clear and concise summary of the following text. 
        Focus on the key points and main information.
        Keep the summary under {max_length} characters.

        Text to summarize:
        {text}"""

        # Initialize the Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Generate content using the official client
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )

        # Extract the summary from the response
        summary = response.text.strip() if response.text is not None else None
        return summary

    except Exception as e:
        print(f"Error generating summary with Gemini: {str(e)}")
        return None


# Default to using Gemini API
def generate_summary(text: str, max_length: int = 300) -> Optional[str]:
    """
    Default summary generation function that uses Gemini API.
    Falls back to OpenRouter if Gemini fails.
    """
    # Try Gemini first
    summary = generate_summary_gemini(text, max_length)
    if summary is None:
        # Fall back to OpenRouter if Gemini fails
        print("Falling back to OpenRouter API...")
        summary = generate_summary_openrouter(text, max_length)
    return summary
