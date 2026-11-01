"""SQLite storage for saved stories."""

import json
import os
import sqlite3
from contextlib import closing

DB_PATH = os.environ.get("STORY_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stories.db"))


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stories (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               created_at TEXT DEFAULT CURRENT_TIMESTAMP,
               title TEXT, topic TEXT, level TEXT, data TEXT
           )"""
    )
    return conn


def save_story(story):
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO stories (title, topic, level, data) VALUES (?, ?, ?, ?)",
            (story["title"], story["topic"], story["level"], json.dumps(story)),
        )
        return cur.lastrowid


def list_stories():
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, created_at, title, topic, level FROM stories ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_story(story_id):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT id, data FROM stories WHERE id = ?", (story_id,)).fetchone()
    if not row:
        return None
    story = json.loads(row["data"])
    story["id"] = row["id"]
    return story


def delete_story(story_id):
    with closing(_connect()) as conn, conn:
        cur = conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
        return cur.rowcount > 0
