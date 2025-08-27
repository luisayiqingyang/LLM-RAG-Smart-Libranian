
# core/database.py
import os, sqlite3, time
from typing import List, Tuple, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "rina.sqlite3")

class ConversationDB:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._init_db()

    def _execute(self, sql: str, params: tuple = (), fetch: bool = False, many: bool = False):
        con = sqlite3.connect(self.path)
        try:
            cur = con.cursor()
            if many and isinstance(params, list):
                cur.executemany(sql, params)
            else:
                cur.execute(sql, params)
            con.commit()
            if fetch:
                return cur.fetchall()
            return None
        finally:
            con.close()

    def _init_db(self):
        self._execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s','now'))
        );""")
        self._execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );""")
        self._execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            question TEXT,
            answer TEXT,
            created_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );""")

    # --- Users ---
    def create_user(self, username: str, password: str) -> tuple[bool, Optional[str]]:
        try:
            self._execute("INSERT INTO users(username,password) VALUES(?,?)", (username, password))
            return True, None
        except Exception as e:
            return False, str(e)

    def validate_user(self, username: str, password: str) -> Optional[int]:
        rows = self._execute("SELECT id FROM users WHERE username=? AND password=?", (username, password), fetch=True)
        if rows:
            return rows[0][0]
        return None

    # --- Sessions ---
    def create_session(self, user_id: int, title: str = None) -> int:
        title = title or f"Chat {int(time.time())}"
        self._execute("INSERT INTO sessions(user_id,title) VALUES(?,?)", (user_id, title))
        rows = self._execute("SELECT last_insert_rowid()", fetch=True)
        return int(rows[0][0])

    def get_latest_session(self, user_id: int) -> Optional[int]:
        rows = self._execute("SELECT id FROM sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,), fetch=True)
        return rows[0][0] if rows else None

    def get_sessions(self, user_id: int) -> List[tuple]:
        return self._execute("SELECT id, title FROM sessions WHERE user_id=? ORDER BY created_at DESC", (user_id,), fetch=True) or []

    def rename_session(self, session_id: int, new_title: str):
        self._execute("UPDATE sessions SET title=? WHERE id=?", (new_title, session_id))

    def delete_session(self, session_id: int):
        self._execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self._execute("DELETE FROM sessions WHERE id=?", (session_id,))

    # --- Messages ---
    def save(self, user_id: int, question: str, answer: str, session_id: int):
        self._execute(
            "INSERT INTO messages(user_id, session_id, question, answer) VALUES(?,?,?,?)",
            (user_id, session_id, question, answer)
        )

    def get_conversation_by_session(self, session_id: int) -> List[tuple]:
        # Return as list of (question, answer, created_at)
        return self._execute(
            "SELECT question, answer, created_at FROM messages WHERE session_id=? ORDER BY id ASC",
            (session_id,), fetch=True
        ) or []
