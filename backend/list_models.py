"""Prints every model this API key can call. Run once, then delete."""

from google import genai
from app.config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if not actions or "generateContent" in actions:
        print(m.name)