import sys
import os
import time
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import re
from datetime import timedelta


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.database import ConversationDB


from core.language_filter import filter_prompt

app = Flask(__name__)
app.secret_key = "rina123"  
app.permanent_session_lifetime = timedelta(hours=4)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",  
    SESSION_COOKIE_SECURE=False,    
    SESSION_COOKIE_HTTPONLY=True,
)


LANGUAGE_FILTER_MODE_FRONTEND = "block"

@app.before_request
def _keep_session_alive():
    session.permanent = True

db = ConversationDB()

FASTAPI_URL = "http://127.0.0.1:8000/chat"
PING_URL     = "http://127.0.0.1:8000/ping"
SESSION_TIMEOUT = 180  # secunde

def clean_latex(text):
    return (
        re.sub(r"\$\\boxed{(.+?)}\$", r"\1", text)
        .replace("$$", "")
        .replace("\\(", "").replace("\\)", "")
        .replace("\\boxed", "").replace("$", "")
    )

def check_backend_status():
    try:
        res = requests.get(PING_URL, timeout=3)
        return res.json().get("status") == "ok"
    except Exception:
        return False

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user_id = db.validate_user(username, password)
        if user_id:
            session["user_id"] = user_id
            session["username"] = username
            session["pending"] = None
            session["last_active"] = time.time()

            
            session_id = db.get_latest_session(user_id)
            if session_id is None:
                session_id = db.create_session(user_id)
            session["session_id"] = session_id

            
            if session_id:
                history = db.get_conversation_by_session(session_id)
                session["messages"] = [
                    ("You", q) if i % 2 == 0 else ("RINA", a)
                    for i, (q, a, _) in enumerate(history)
                ]
            else:
                session["messages"] = []

            return redirect(url_for("chat_view"))
        else:
            return render_template("login.html", error="Invalid credentials.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        ok, err = db.create_user(username, password)
        if ok:
            return redirect(url_for("login"))
        return render_template("register.html", error=err)
    return render_template("register.html")

@app.route("/chat", methods=["GET", "POST"])
def chat_view():
    
    if request.method == "POST" and request.form.get("rate") in ("good", "bad") and (
        "user_id" not in session or session.get("user_id") is None
    ):
        try:
            uid = request.form.get("user_id")
            sid = request.form.get("session_id")
            if uid:
                session["user_id"] = int(uid)
            if sid:
                session["session_id"] = int(sid)
                hist = db.get_conversation_by_session(int(sid))
                session["messages"] = [("You", q) if i % 2 == 0 else ("RINA", a)
                                       for i, (q, a, _) in enumerate(hist)]
            session["last_active"] = time.time()
        except Exception as e:
            print("[WARN] Rehydrate failed:", e)

    
    if "user_id" not in session or session.get("user_id") is None:
        
        if request.method == "POST" and request.form.get("rate") in ("good", "bad"):
            session["pending"] = None
            return redirect(url_for("chat_view"))
        return redirect(url_for("login"))

    
    if time.time() - session.get("last_active", 0) > SESSION_TIMEOUT:
        session.clear()
        return redirect(url_for("login"))
    session["last_active"] = time.time()

    user_id = session.get("user_id")
    session_id = session.get("session_id")

    
    if not session_id:
        latest = db.get_latest_session(user_id)
        if latest is not None:
            session_id = latest
            session["session_id"] = session_id
            history = db.get_conversation_by_session(session_id)
            session["messages"] = [("You", q) if i % 2 == 0 else ("RINA", a)
                                   for i, (q, a, _) in enumerate(history)]
        else:
            session["messages"] = []

    messages = session.get("messages", [])
    pending  = session.get("pending")

    if request.method == "POST":
        rate_value = request.form.get("rate")

        
        if rate_value == "good" and pending:
            uid = session.get("user_id") or request.form.get("user_id")
            sid = session.get("session_id") or request.form.get("session_id")
            if not uid or not sid:
                print("[WARN] Missing user/session on rate=good; dropping pending and staying.")
                session["pending"] = None
                return redirect(url_for("chat_view"))

            messages.append(("You",  pending[0]))
            messages.append(("RINA", pending[1]))
            db.save(int(uid), pending[0], pending[1], int(sid))
            session["pending"] = None
            session["messages"] = messages
            return redirect(url_for("chat_view"))

        
        if rate_value == "bad":
            session["pending"] = None
            return redirect(url_for("chat_view"))

        
        if "message" in request.form:
            user_msg_original = request.form["message"].strip()
            if not user_msg_original:
                return redirect(url_for("chat_view"))

            
            if session.get("messages") and session["messages"][-1][0] == "You" and session["messages"][-1][1] == user_msg_original:
                return redirect(url_for("chat_view"))

            if not user_id:
                return redirect(url_for("login"))

            
            ok, maybe_censored = filter_prompt(user_msg_original, mode=LANGUAGE_FILTER_MODE_FRONTEND)

            
            if not ok:
                bot_reply = maybe_censored
                session["pending"] = (user_msg_original, bot_reply)
                return redirect(url_for("chat_view"))

            
            user_msg_to_send = maybe_censored

            try:
                r = requests.post(
                    FASTAPI_URL,
                    json={"user_id": str(user_id), "question": user_msg_to_send},
                    timeout=20,
                )
                r.raise_for_status()
                bot_reply = clean_latex(r.json().get("response", "[No response]"))
            except Exception as e:
                bot_reply = f"[Error contacting backend: {e}]"

            
            session["pending"] = (user_msg_original, bot_reply)
            return redirect(url_for("chat_view"))

    gemini_ok = check_backend_status()  
    sessions = db.get_sessions(user_id)
    return render_template("chat.html", messages=messages, pending=pending,
                           gemini_ok=gemini_ok, sessions=sessions)

@app.route("/book_recommendation", methods=["POST"])
def book_recommendation():
    data = request.get_json() or {}
    user_input_original = data.get("question", "").strip()
    if not user_input_original:
        return jsonify({"response": "Te rog să scrii o întrebare."})

  
    ok, maybe_censored = filter_prompt(user_input_original, mode=LANGUAGE_FILTER_MODE_FRONTEND)
    if not ok:
        return jsonify({"response": maybe_censored})

    user_input_to_send = maybe_censored

    try:
        r = requests.post(
            FASTAPI_URL,
            json={"user_id": str(session.get("user_id", "anonim")), "question": user_input_to_send},
            timeout=20,
        )
        r.raise_for_status()
        return jsonify({"response": r.json().get("response", "[Eroare: răspuns lipsă]")})
    except Exception as e:
        return jsonify({"response": f"Eroare API backend: {str(e)}"}), 500

@app.route("/new_chat")
def new_chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    session_id = db.create_session(session["user_id"])
    session["session_id"] = session_id
    session["messages"] = []
    session["pending"] = None
    return redirect(url_for("chat_view"))

@app.route("/session/<int:session_id>")
def load_session(session_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    session["session_id"] = session_id
    history = db.get_conversation_by_session(session_id)
    session["messages"] = [
        ("You", q) if i % 2 == 0 else ("RINA", a)
        for i, (q, a, _) in enumerate(history)
    ]
    return redirect(url_for("chat_view"))

@app.route("/rename_session/<int:session_id>", methods=["POST"])
def rename_session(session_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    new_title = request.form.get("new_title", "").strip()
    if new_title:
        db.rename_session(session_id, new_title)
    return redirect(url_for("chat_view"))

@app.route("/delete_session/<int:session_id>", methods=["POST"])
def delete_session(session_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db.delete_session(session_id)
    if session.get("session_id") == session_id:
        session["session_id"] = None
        session["messages"] = []
    return redirect(url_for("chat_view"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    # rulează Flask pe 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
