# backend/api.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Union, List, Dict, Tuple
import os, json, re
from openai import OpenAI
from unidecode import unidecode

# filtrul local de limbaj
from core.language_filter import filter_prompt

from core.tools import get_summary_by_title

app = FastAPI(title="RINA Bot - OpenAI + ChromaDB")

# ==== OpenAI config ====
OPENAI_API_KEY = ""
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


LANGUAGE_FILTER_MODE = "block"


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BOOKS_PATH = os.path.join(BASE_DIR, "core", "book_summaries.json")

def load_books() -> List[Dict]:
    try:
        with open(BOOKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

BOOKS = load_books()

def strip_diacritics(s: str) -> str:
    return unidecode(s or "").lower().strip()

def chat_completion(prompt: str, temperature: float = 0.4) -> str:
    msgs = [
        {"role": "system", "content": "You are a helpful, concise assistant."},
        {"role": "user", "content": prompt}
    ]
    resp = client.chat.completions.create(model=MODEL_NAME, messages=msgs, temperature=temperature)
    return resp.choices[0].message.content

def detect_lang_and_to_ro(text: str) -> Tuple[str, str]:
    prompt = (
        "Detectează limba următorului text și traduce-l în română. "
        "Răspunde STRICT în JSON cu cheile: lang, ro.\n\n"
        f"Text: ```{text}```"
    )
    raw = chat_completion(prompt, temperature=0.0)
    lang, ro = "ro", text
    try:
        data = json.loads(raw)
        lang = (data.get("lang") or "ro").lower()
        ro = data.get("ro") or text
    except Exception:
        pass
    return lang, ro

# ---------- API ----------
class ChatIn(BaseModel):
    user_id: Union[str, int]
    question: str

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: ChatIn):
    original_question = (payload.question or "").strip()

    
    ok, filtered_or_reply = filter_prompt(original_question, mode=LANGUAGE_FILTER_MODE)
    if not ok:
        return {"response": filtered_or_reply, "moderated": True}

  
    user_lang, q_ro = detect_lang_and_to_ro(filtered_or_reply)

    
    title = None
    for b in BOOKS:
        t_norm = strip_diacritics(b.get("title", ""))
        if t_norm and t_norm in strip_diacritics(q_ro):
            title = b.get("title")
            break

    if title:
        summary_local = get_summary_by_title(title)
        prompt = (
            f"Cartea: {title}\n"
            f"Rezumat:\n{summary_local}\n\n"
            f"Rescrie într-un răspuns scurt, conversațional, în limba {user_lang.upper()}."
        )
        reply = chat_completion(prompt)
        return {"response": reply}

    
    prompt_alt = (
        f"User language: {user_lang}\n"
        f"User asked: {q_ro}\n"
        "Nu am găsit cartea în baza locală. Recomandă o ALTĂ carte relevantă și un rezumat scurt (2–4 fraze)."
    )
    reply_alt = chat_completion(prompt_alt)
    return {"response": reply_alt}
