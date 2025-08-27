# core/vector_store.py
import os
import chromadb
from chromadb.config import Settings
from core.embeddings import embed_texts
from core.tools import get_summary_by_title

BASE_DIR = os.path.dirname(__file__)
CHROMA_DIR = os.path.join(BASE_DIR, ".chroma_store")
COLLECTION_NAME = "books"

def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
    return client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

def search_books(query: str, k: int = 3):
    coll = _get_collection()
    qvec = embed_texts([query])[0]
    res = coll.query(query_embeddings=[qvec], n_results=k, include=["documents", "metadatas", "distances"]) or {}
    hits = []
    if res.get("metadatas") and res["metadatas"]:
        for meta, doc, dist in zip(res["metadatas"][0], res["documents"][0], res["distances"][0]):
            hits.append({"title": meta.get("title"), "doc": doc, "score": 1.0 - float(dist)})
    return hits

def answer_book_question(user_prompt: str) -> str | None:
    hits = search_books(user_prompt, k=3)
    if not hits:
        return None
    best = hits[0]
    title = best["title"]
    summary_full = get_summary_by_title(title)
    lines = [
        f"Îți recomand: <b>{title}</b>.",
        "",
        "Rezumat detaliat:",
        summary_full,
    ]
    return "\n".join(lines)
