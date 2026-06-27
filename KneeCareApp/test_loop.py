import time
from datetime import datetime, date
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE sent_log(key TEXT PRIMARY KEY)")

def already_sent(key):
    return conn.execute("SELECT 1 FROM sent_log WHERE key=?", (key,)).fetchone() is not None

def mark_sent(key):
    with conn:
        conn.execute("INSERT OR REPLACE INTO sent_log(key) VALUES(?)", (key,))

def send_notification():
    print("Sent!")
    return True, "ok"

today = date.today().isoformat()
t = datetime.now().strftime("%H:%M")

for _ in range(3):
    hm = datetime.now().strftime("%H:%M")
    key = f"med:morning:{today}"
    if hm == t and not already_sent(key):
        ok, msg = send_notification()
        if ok:
            mark_sent(key)
    else:
        print("Skipped")
    time.sleep(1)
