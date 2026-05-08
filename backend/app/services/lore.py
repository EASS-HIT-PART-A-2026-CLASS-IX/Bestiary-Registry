import os

from google import genai
from fastapi import HTTPException, status

_MODEL = "gemini-2.5-flash"

_PROMPT_TEMPLATE = (
    "Write a short, atmospheric lore description (2-3 sentences) for a creature called {name}. "
    "It originates from {mythology} mythology and is classified as a {creature_type}. "
    "Focus on its mystical qualities and role in legend. Be vivid and concise."
)


def generate_lore(name: str, mythology: str, creature_type: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured",
        )
    client = genai.Client(api_key=api_key)
    prompt = _PROMPT_TEMPLATE.format(
        name=name, mythology=mythology, creature_type=creature_type
    )
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    return response.text
