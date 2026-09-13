import os
from dotenv import load_dotenv

load_dotenv()

# Standard model configuration (Groq LLaMA 3.3 70B Versatile for high-speed, factual inference)
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def get_groq_api_key(explicit_key: str = None) -> str:
    """
    Returns the Groq API key:
    1. Explicit key passed from request (if non-empty)
    2. Standard environment variable GROQ_API_KEY
    3. Legacy fallback environment variable groq_api_key
    Does NOT mutate os.environ to avoid race conditions.
    """
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    return os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key") or ""