# core/tools.py
# Minimal implementation of the required tool.
# Replace the path or implementation if your project already provides this.
import os, json

BASE_DIR = os.path.dirname(__file__)
BOOKS_PATH = os.path.join(BASE_DIR, "book_summaries.json")

def get_summary_by_title(title: str) -> str:
    if not os.path.exists(BOOKS_PATH):
        return "(Nu am găsit book_summaries.json)"
    with open(BOOKS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for b in data:
        if b.get("title", "").strip().lower() == title.strip().lower():
            return b.get("summary", "(Fără rezumat)")
    return "(Nu am găsit această carte în baza de date)"
