import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple
import config

def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table for managing Multi-Key Pool (Gemini, Groq, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL, -- 'gemini' or 'groq'
                key_value TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active', -- 'active', 'rate_limited', 'invalid'
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for User Active PDF Metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_documents (
                user_id INTEGER PRIMARY KEY,
                doc_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table for User Reviews & Feature Suggestions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                rating INTEGER,
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table for User MCQ Quiz Stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_quiz_stats (
                user_id INTEGER PRIMARY KEY,
                mcqs_played INTEGER DEFAULT 0,
                reviewed INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()

# --- API KEY MANAGEMENT ---

def add_api_key(provider: str, key_value: str) -> Tuple[bool, str]:
    provider = provider.lower().strip()
    if provider not in ['gemini', 'groq']:
        return False, "Provider must be 'gemini' or 'groq'."
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO api_keys (provider, key_value) VALUES (?, ?)",
                (provider, key_value.strip())
            )
            conn.commit()
            return True, f"✅ API Key successfully added for {provider.upper()}!"
    except sqlite3.IntegrityError:
        return False, "⚠️ This API key already exists in the database."
    except Exception as e:
        return False, f"Error adding API key: {str(e)}"

def remove_api_key(key_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_api_keys() -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys ORDER BY provider, id ASC")
        return [dict(row) for row in cursor.fetchall()]

def get_active_keys(provider: Optional[str] = None) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if provider:
            cursor.execute(
                "SELECT * FROM api_keys WHERE provider = ? AND status = 'active' ORDER BY usage_count ASC",
                (provider.lower(),)
            )
        else:
            cursor.execute("SELECT * FROM api_keys WHERE status = 'active' ORDER BY usage_count ASC")
        return [dict(row) for row in cursor.fetchall()]

def update_key_usage(key_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "UPDATE api_keys SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
            (now, key_id)
        )
        conn.commit()

def mark_key_status(key_id: int, status: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE api_keys SET status = ? WHERE id = ?", (status, key_id))
        conn.commit()

def reset_rate_limited_keys():
    """Resets keys marked as rate_limited back to active."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE api_keys SET status = 'active' WHERE status = 'rate_limited'")
        conn.commit()

# --- USER MANAGEMENT ---

def register_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active = excluded.last_active
        ''', (user_id, username, first_name, now))
        conn.commit()

def get_user_count() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def get_all_user_ids() -> List[int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

# --- DOCUMENT MANAGEMENT ---

def set_user_document(user_id: int, doc_id: str, file_name: str, chunk_count: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO user_documents (user_id, doc_id, file_name, chunk_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                doc_id = excluded.doc_id,
                file_name = excluded.file_name,
                chunk_count = excluded.chunk_count,
                uploaded_at = excluded.uploaded_at
        ''', (user_id, doc_id, file_name, chunk_count, now))
        conn.commit()

def get_user_document(user_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_documents WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_user_document(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_documents WHERE user_id = ?", (user_id,))
        conn.commit()

def get_inactive_user_ids(max_inactive_hours: int = 2) -> List[int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=max_inactive_hours)).isoformat()
        cursor.execute('''
            SELECT d.user_id FROM user_documents d
            LEFT JOIN users u ON d.user_id = u.user_id
            WHERE u.last_active < ? OR d.uploaded_at < ?
        ''', (cutoff, cutoff))
        return [row[0] for row in cursor.fetchall()]

def increment_user_mcq(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_quiz_stats (user_id, mcqs_played, reviewed)
            VALUES (?, 1, 0)
            ON CONFLICT(user_id) DO UPDATE SET mcqs_played = mcqs_played + 1
        ''', (user_id,))
        conn.commit()
        
        cursor.execute("SELECT mcqs_played FROM user_quiz_stats WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

def get_user_mcq_stats(user_id: int) -> Dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quiz_stats WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else {"mcqs_played": 0, "reviewed": 0}

def mark_user_reviewed(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_quiz_stats SET reviewed = 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def save_user_review(user_id: int, username: Optional[str], rating: int, feedback_text: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO user_reviews (user_id, username, rating, feedback_text, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, rating, feedback_text, now))
        conn.commit()

def get_all_reviews() -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_reviews ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

# Initialize DB when module is loaded
init_db()
