# LLM-RAG-Smart-Libranian
## Overview
RINA Smart Librarian is an **AI chatbot** that recommends books based on a user’s interests using **RAG (Retrieval-Augmented Generation)** with a **ChromaDB** vector store. After recommending a title, it enriches the answer with a **full book summary** via the tools.  
Interaction is **text-only** (in both romanian and english): a Flask web UI talks to a FastAPI backend.
<img width="958" height="477" alt="Screenshot 2025-08-22 180701" src="https://github.com/user-attachments/assets/56303d5d-91de-413f-9a73-2f8ad4d95b72" />


## Architecture
- **core/** — data & logic
  - `book_summaries.json` – local corpus (**12 books**) with title, themes, and summary.
  - `ingest.py` – builds the ChromaDB store from `book_summaries.json` using OpenAI embeddings.
  - `vector_store.py` – semantic search & RAG helper (`answer_book_question`, `search_books`).
  - `tools.py` – `get_summary_by_title(title)` returns the exact book’s detailed summary.
  - `embeddings.py` – embeddings helper (OpenAI).
  - `database.py` – SQLite for users, sessions, and messages (`rina.sqlite3`).
  - `language_filter.py` – polite blocking/censoring of offensive inputs (RO/EN).
  - `.chroma_store/` – the persistent vector store.
- **backend/** — FastAPI service
  - `api.py` – `/ping` and `/chat` endpoints; orchestrates RAG + tool calling and LLM completion.
- **frontend/** — Flask web app
  - `app.py` – routes for login/register/chat/history; calls FastAPI at `http://127.0.0.1:8000`.
  - `templates/` – `login.html`, `register.html`, `chat.html`, `conversations.html`.
- Project root
  - `run.py` – Orchestrator: runs `core.ingest` on first launch, then starts FastAPI and Flask.
  - `requirements.txt`

---

## Project Structure
```
tema_rina_chatbot_rag/
├─ requirements.txt
├─ run.py
├─ backend/
│  └─ api.py                         # FastAPI: /ping, /chat
├─ core/
│  ├─ book_summaries.json            # 12+ curated book entries (title, themes, summary)
│  ├─ database.py                    # SQLite schema & helpers (users/sessions/messages)
│  ├─ embeddings.py                  # OpenAI embeddings helper
│  ├─ ingest.py                      # Seed Chroma from book_summaries.json
│  ├─ language_filter.py             # Profanity filter (RO/EN): block or censor
│  ├─ tools.py                       # get_summary_by_title(title)
│  ├─ vector_store.py                # RAG search + final answer assembly
│  ├─ rina.sqlite3                   # SQLite DB (created/used at runtime)
│  └─ .chroma_store/                 # ChromaDB persistence
└─ frontend/
   ├─ app.py                         # Flask UI (text-only, ChatGPT-style)
   └─ templates/
      ├─ chat.html
      ├─ conversations.html
      ├─ login.html
      └─ register.html
```

---

## Features (Assignment Alignment)
- **RAG + vector store (ChromaDB)** with OpenAI embeddings.
- **Tool calling**: `get_summary_by_title(title)` provides the detailed summary.
- **Text-only UI** (Flask) with **multi-user auth** and **saved conversation history**.
- **Offensive-language filter** (block or censor mode in romanian and english).
  <img width="818" height="317" alt="Screenshot 2025-08-22 180528" src="https://github.com/user-attachments/assets/ad081c78-ee5c-413b-8075-df9a651358f9" />
  <img width="814" height="325" alt="Screenshot 2025-08-22 180549" src="https://github.com/user-attachments/assets/6c013411-69e1-47bf-8c6f-8d436ccb8df7" />

- **Example prompts** (see below).  

---

## Quickstart

### Prerequisites
- **Python 3.10+** (3.11 recommended)
- macOS/Linux/WSL/Windows
- A valid **OpenAI API key** for embeddings & chat

### 1) Install dependencies
```bash
cd Smart_libranian
python -m venv .venv && source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure API keys
The current code expects a value in two files:
- `core/embeddings.py` → `OPENAI_API_KEY = ""`
- `backend/api.py`     → `OPENAI_API_KEY = ""`

**Option A (quick & minimal changes):**
Open both files and set:
```python
OPENAI_API_KEY = "sk-...your-openai-key..."
```

**Option B (recommended patch – use environment variables):**
Replace the above line in both files with:
```python
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
```
Then export your key:
```bash
export OPENAI_API_KEY="sk-...your-openai-key..."   # PowerShell: setx OPENAI_API_KEY "sk-..."
```

### 3) First run (auto-ingest)
Just run the orchestrator (it will build the vector store on first launch):
```bash
python run.py
```
- **Backend (FastAPI):** http://127.0.0.1:8000  
- **Frontend (Flask):**  http://127.0.0.1:5000  

If you prefer manual ingestion:
```bash
python -m core.ingest
```

---

## Using the App

### Web UI
Open **http://127.0.0.1:5000**, register/login, then chat. A sidebar shows your past conversations.

### API (FastAPI)
- **Ping**
  ```bash
  curl http://127.0.0.1:8000/ping
  ```
- **Chat**
  ```bash
  curl -X POST http://127.0.0.1:8000/chat \
       -H "Content-Type: application/json" \
       -d '{"user_id":"demo","question":"I want a book about friendship and magic"}'
  ```

Response:
```json
{"response": "… final assistant message …"}
```

> Logic: the backend filters language → tries an **exact title** match from the local set → if found, assembles a prompt to the LLM with the **local full summary**; otherwise it asks the LLM to suggest a **relevant alternative** with a short summary.

---

## Example Queries
- “I want a book about friendship and magic.”  
- “What do you recommend for someone who loves war stories?”  
- “Suggest a book about freedom and social control.”  
- “What is *1984*?”

---

## Configuration & Tips

### Language moderation
- Backend uses `LANGUAGE_FILTER_MODE = "block"` (polite refusal) or `"censor"` (mask profanities and continue).
- Frontend mirrors this behavior (`LANGUAGE_FILTER_MODE_FRONTEND`).
- Implementation: `core/language_filter.py` (works for RO/EN).

### Switching to Google Gemini (optional)
If you prefer Gemini for **generation** (keeping OpenAI for **embeddings** is fine):
1. Install:
   ```bash
   pip install google-generativeai
   export GEMINI_API_KEY="..."
   ```
2. In `backend/api.py`, swap the chat completion helper to use Gemini (e.g., `gemini-1.5-pro`).  
   Minimal example:
   ```python
   import google.generativeai as genai
   genai.configure(api_key=os.getenv("GEMINI_API_KEY",""))
   model = genai.GenerativeModel("gemini-1.5-pro")

   def chat_completion(prompt: str, temperature: float = 0.4) -> str:
       resp = model.generate_content(prompt, generation_config={"temperature": temperature})
       return resp.text.strip()
   ```
3. Keep `core/embeddings.py` as-is (OpenAI) to avoid reworking the ingest pipeline.

### Resetting the vector store
Delete `core/.chroma_store/` and re-run ingest:
```bash
rm -rf core/.chroma_store
python -m core.ingest
```

### Troubleshooting
- **Auth/UI issues**: clear browser cookies or restart Flask (`Ctrl+C` then `python run.py`).
- **“Set OPENAI_API_KEY” error**: make sure both `backend/api.py` and `core/embeddings.py` see your key (Option A or B above).
- **Ports busy**: change ports in `run.py` (FastAPI 8000, Flask 5000) or stop other services.
- **No results**: ensure `book_summaries.json` exists and ingest completed.





## License
Educational / demo use. Replace or add a proper license if you publish publicly.


          Sidebar to view previous conversations.

          Offensive language filter (polite response, no forwarding to LLM).

          Modular architecture with FastAPI + threading/async.

          User-friendly interface.




