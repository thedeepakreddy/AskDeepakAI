import sqlite3
import os
import uuid
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "askdeepakai.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chats(id)
        )
    ''')
    conn.commit()
    conn.close()

def create_chat(title: str = "New Chat") -> str:
    conn = get_connection()
    c = conn.cursor()
    chat_id = str(uuid.uuid4())
    c.execute("INSERT INTO chats (id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()
    return chat_id

def list_chats() -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM chats ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]

def get_chat_messages(chat_id: str) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def add_message(chat_id: str, role: str, content: str):
    conn = get_connection()
    c = conn.cursor()
    msg_id = str(uuid.uuid4())
    c.execute("INSERT INTO messages (id, chat_id, role, content) VALUES (?, ?, ?, ?)", 
              (msg_id, chat_id, role, content))
    conn.commit()
    conn.close()
    
def update_chat_title(chat_id: str, title: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))
    conn.commit()
    conn.close()

def delete_chat(chat_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()

# Initialize on load
init_db()
