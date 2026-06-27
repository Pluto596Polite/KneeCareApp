import sqlite3, os
DB_PATH = "test.db"
def db():
    conn = sqlite3.connect(DB_PATH)
    return conn
def mark_sent(key):
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sent_log(key TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO sent_log(key) VALUES(?)", (key,))
def already_sent(key):
    with db() as conn:
        return conn.execute("SELECT 1 FROM sent_log WHERE key=?", (key,)).fetchone() is not None

mark_sent("test1")
print(already_sent("test1"))
