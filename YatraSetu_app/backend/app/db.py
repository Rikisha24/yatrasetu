"""SQLite storage: one saved profile, plus a small event log used for the in-app metrics."""
import json
import os
import sqlite3
import threading

DB_PATH = os.environ.get("YATRASETU_DB", os.path.join(os.path.dirname(__file__), "..", "yatrasetu.db"))
_lock = threading.Lock()


def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)")
        c.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP,
            session TEXT NOT NULL,
            kind TEXT NOT NULL,          -- search | recovery | fallback
            scenario TEXT,
            evaluated INTEGER DEFAULT 0,
            removed INTEGER DEFAULT 0,
            secs REAL,
            delta INTEGER,
            top_accepted INTEGER DEFAULT 0)""")


def get_profile():
    with _lock, conn() as c:
        row = c.execute("SELECT data FROM profile WHERE id = 1").fetchone()
    return json.loads(row["data"]) if row else {}


def save_profile(data):
    with _lock, conn() as c:
        c.execute("INSERT INTO profile (id, data) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                  (json.dumps(data),))


def delete_profile():
    with _lock, conn() as c:
        c.execute("DELETE FROM profile")


def log_event(session, kind, scenario=None, evaluated=0, removed=0, secs=None, delta=None, top_accepted=False):
    with _lock, conn() as c:
        c.execute("INSERT INTO events (session, kind, scenario, evaluated, removed, secs, delta, top_accepted) "
                  "VALUES (?,?,?,?,?,?,?,?)", (session, kind, scenario, evaluated, removed, secs, delta,
                                               1 if top_accepted else 0))


def metrics(session):
    with _lock, conn() as c:
        ev = c.execute("SELECT * FROM events WHERE session = ? ORDER BY id", (session,)).fetchall()
    rec = [e for e in ev if e["kind"] == "recovery"]
    secs = [e["secs"] for e in rec if e["secs"] is not None]
    return {
        "recoveries": len(rec),
        "lastSecs": secs[-1] if secs else None,
        "avgSecs": sum(secs) / len(secs) if secs else None,
        "lastDelta": rec[-1]["delta"] if rec else None,
        "evaluated": sum(e["evaluated"] for e in ev if e["kind"] == "search"),
        "removed": sum(e["removed"] for e in ev if e["kind"] == "search"),
        "topAccepted": sum(e["top_accepted"] for e in rec),
        "fallbacks": sum(1 for e in ev if e["kind"] == "fallback"),
    }


def clear_events(session):
    with _lock, conn() as c:
        c.execute("DELETE FROM events WHERE session = ?", (session,))
