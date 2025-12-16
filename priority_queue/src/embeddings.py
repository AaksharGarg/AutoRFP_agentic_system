# embeddings.py

"""
Embedding adapter used by the Priority Queue system.
Supports:
- OpenAI embeddings if OPENAI_API_KEY is set and EMBED_PROVIDER=openai
- Local embeddings via sentence-transformers (all-MiniLM-L6-v2) as fallback
"""

import os
from functools import lru_cache

# Attempt OpenAI
USE_OPENAI = os.getenv("EMBED_PROVIDER", "local").lower() == "openai"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load OpenAI if allowed
if USE_OPENAI and OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        USE_OPENAI = True
    except Exception:
        USE_OPENAI = False
else:
    USE_OPENAI = False

# Load local model
@lru_cache(maxsize=1)
def load_local_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding(text: str):
    """Return embedding for text using OpenAI or local model.
    Returns a list[float].
    """
    text = text or ""

    # Try OpenAI first
    if USE_OPENAI:
        try:
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return resp.data[0].embedding
        except Exception:
            pass

    # Local model fallback
    model = load_local_model()
    vec = model.encode(text)
    return vec.tolist()
