import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_summary(text: str, max_length: int = 300) -> Optional[str]:
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
