# core/embeddings.py
import os
from typing import List
from openai import OpenAI

OPENAI_API_KEY = ""

_client = None
def get_openai():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("Set OPENAI_API_KEY in environment.")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    client = get_openai()

    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]
