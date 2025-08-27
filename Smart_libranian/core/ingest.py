# core/ingest.py
import os, json
import chromadb
from chromadb.config import Settings
from core.embeddings import embed_texts
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

BASE_DIR = os.path.dirname(__file__)
BOOKS_PATH = os.path.join(BASE_DIR, "book_summaries.json")
CHROMA_DIR = os.path.join(BASE_DIR, ".chroma_store")
COLLECTION_NAME = "books"

def get_client():
    return chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))

def recreate_collection():
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

def run_ingest():
    if not os.path.exists(BOOKS_PATH):
        raise FileNotFoundError(f"Missing {BOOKS_PATH}. Place your JSON summaries file there.")
    with open(BOOKS_PATH, "r", encoding="utf-8") as f:
        books = json.load(f)

    coll = recreate_collection()

    docs, metadatas, ids = [], [], []
    for i, b in enumerate(books):
        title = b.get("title", f"Unknown {i}")
        themes = ", ".join(b.get("themes", []))
        summary = b.get("summary", "")
        text = f"Title: {title}\nThemes: {themes}\nSummary: {summary}"
        docs.append(text)
        metadatas.append({"title": title})
        ids.append(f"book-{i}")

    vectors = embed_texts(docs)  # list[list[float]]
    coll.add(ids=ids, embeddings=vectors, metadatas=metadatas, documents=docs)
    print(f"[INGEST DONE] {len(ids)} books -> {CHROMA_DIR}")

if __name__ == "__main__":
    run_ingest()
