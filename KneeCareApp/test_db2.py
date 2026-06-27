import sqlite3, os
DB_PATH = os.path.join(os.path.expanduser("~"), ".kneecare", "kneecare.db")
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def already_sent(key):
    with db() as conn:
        return conn.execute("SELECT 1 FROM sent_log WHERE key=?", (key,)).fetchone() is not None

def mark_sent(key):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO sent_log(key,ts) VALUES(?,?)",
                     (key, "now"))

print(already_sent("test_dup"))
mark_sent("test_dup")
print(already_sent("test_dup"))
