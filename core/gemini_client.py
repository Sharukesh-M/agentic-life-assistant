import os
from google import genai
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

client = genai.Client(
    api_key=os.getenv("gemini_api_key")
)

MODEL = "gemini-2.5-flash"


def ask_gemini(prompt: str) -> str:

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text