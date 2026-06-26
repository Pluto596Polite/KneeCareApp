#!/usr/bin/env python3
"""
KneeCare - local medicine & exercise tracker for Mom's knee replacement recovery.

Pure Python standard library (no installs, no cost). Runs a small web app on
this Mac and sends reminder push notifications to your phone via a free channel
(Discord by default; Telegram / ntfy / WhatsApp-CallMeBot also supported).
"""
import json
import os
import sqlite3
import threading
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
# The database lives OUTSIDE this folder, in the user's home, because SQLite
# cannot reliably lock files inside cloud-synced folders (Google Drive/iCloud).
DATA_DIR = os.path.join(os.path.expanduser("~"), ".kneecare")
DB_PATH = os.path.join(DATA_DIR, "kneecare.db")
os.makedirs(DATA_DIR, exist_ok=True)

# ----------------------------- config / content -----------------------------

def load_json(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(name, obj):
    with open(os.path.join(BASE, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def get_config():
    return load_json("config.json")

# ----------------------------- database -------------------------------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS dose_log(
            day TEXT, cycle TEXT, med_id TEXT, taken INTEGER, ts TEXT,
            PRIMARY KEY(day, cycle, med_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS exercise_log(
            day TEXT, ex_id TEXT, done INTEGER, ts TEXT,
            PRIMARY KEY(day, ex_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sent_log(
            key TEXT PRIMARY KEY, ts TEXT)""")

def set_dose(day, cycle, med_id, taken):
    with db() as conn:
        conn.execute("""INSERT INTO dose_log(day,cycle,med_id,taken,ts)
            VALUES(?,?,?,?,?)
            ON CONFLICT(day,cycle,med_id) DO UPDATE SET taken=excluded.taken, ts=excluded.ts""",
            (day, cycle, med_id, 1 if taken else 0, datetime.now().isoformat(timespec="seconds")))

def set_exercise(day, ex_id, done):
    with db() as conn:
        conn.execute("""INSERT INTO exercise_log(day,ex_id,done,ts)
            VALUES(?,?,?,?)
            ON CONFLICT(day,ex_id) DO UPDATE SET done=excluded.done, ts=excluded.ts""",
            (day, ex_id, 1 if done else 0, datetime.now().isoformat(timespec="seconds")))

def day_state(day):
    with db() as conn:
        doses = {f"{r['cycle']}:{r['med_id']}": bool(r["taken"])
                 for r in conn.execute("SELECT * FROM dose_log WHERE day=?", (day,))}
        ex = {r["ex_id"]: bool(r["done"])
              for r in conn.execute("SELECT * FROM exercise_log WHERE day=?", (day,))}
    return {"doses": doses, "exercises": ex}

def already_sent(key):
    with db() as conn:
        return conn.execute("SELECT 1 FROM sent_log WHERE key=?", (key,)).fetchone() is not None

def mark_sent(key):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO sent_log(key,ts) VALUES(?,?)",
                     (key, datetime.now().isoformat(timespec="seconds")))

# ----------------------------- notifications --------------------------------

def send_notification(text):
    """Send 'text' through the configured free channel. Returns (ok, message)."""
    cfg = get_config()["notify"]
    ch = cfg.get("channel", "discord")
    try:
        if ch == "discord":
            url = cfg.get("discord_webhook_url", "").strip()
            if not url:
                return False, "No Discord webhook URL set (open Settings)."
            data = json.dumps({"content": text}).encode()
            # A real User-Agent is REQUIRED: Discord sits behind Cloudflare, which
            # rejects Python's default urllib agent with HTTP 403 Forbidden.
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "User-Agent": "KneeCare/1.0 (Macintosh; medicine reminder)"})
            urllib.request.urlopen(req, timeout=15)
            return True, "Sent via Discord."
        if ch == "telegram":
            tok = cfg.get("telegram_bot_token", "").strip()
            chat = cfg.get("telegram_chat_id", "").strip()
            if not tok or not chat:
                return False, "Telegram bot token / chat id missing."
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
            return True, "Sent via Telegram."
        if ch == "ntfy":
            topic = cfg.get("ntfy_topic", "").strip()
            if not topic:
                return False, "ntfy topic missing."
            url = f"https://ntfy.sh/{topic}"
            req = urllib.request.Request(url, data=text.encode(),
                                         headers={"Title": "KneeCare reminder"})
            urllib.request.urlopen(req, timeout=15)
            return True, "Sent via ntfy."
        if ch == "whatsapp":
            phone = cfg.get("whatsapp_phone", "").strip()
            key = cfg.get("whatsapp_callmebot_apikey", "").strip()
            if not phone or not key:
                return False, "WhatsApp phone / CallMeBot api key missing."
            # CallMeBot expects an international number, no leading 0. ZA: 0XXXXXXXXX -> 27XXXXXXXXX
            intl = phone
            if intl.startswith("0"):
                intl = "27" + intl[1:]
            intl = "".join(c for c in intl if c.isdigit())
            url = ("https://api.callmebot.com/whatsapp.php?phone=" + intl +
                   "&text=" + urllib.parse.quote(text) + "&apikey=" + key)
            urllib.request.urlopen(url, timeout=20)
            return True, "Sent via WhatsApp (CallMeBot)."
        return False, f"Unknown channel '{ch}'."
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")[:200]
        except Exception:
            pass
        hint = ""
        if e.code == 401 or e.code == 404:
            hint = " (webhook URL looks wrong or was deleted — recopy it from Discord)"
        elif e.code == 429:
            hint = " (rate limited — wait a moment and retry)"
        return False, f"Send failed: HTTP {e.code} {e.reason}{hint} {body}".strip()
    except Exception as e:
        return False, f"Send failed: {e}"

def build_cycle_message(cycle):
    meds = load_json("meds.json")["medicines"]
    must, prn = [], []
    for m in meds:
        for c in m["cycles"]:
            if c["cycle"] != cycle:
                continue
            line = f"{m['name']} — {c['qty']}"
            (must if c.get("regular") else prn).append((line, m))
    label = "MORNING" if cycle == "morning" else "EVENING"
    lines = [f"💊 {label} medicine for Mom ({datetime.now():%a %d %b})", ""]
    if must:
        lines.append("Take now (with food):")
        for line, m in must:
            star = " ⚠️" if m.get("critical") else ""
            lines.append(f"  • {line}{star}")
    if prn:
        lines.append("")
        lines.append("Only if she has pain:")
        for line, m in prn:
            lines.append(f"  • {line}")
    lines.append("")
    lines.append("Open the app and tick off each one. ✅")
    return "\n".join(lines)

def build_exercise_message():
    return ("🦵 Exercise reminder for Mom — time for a set of knee exercises "
            "(aim 20–30 min, 2–3× a day). Open the app for the checklist.")

# ----------------------------- scheduler ------------------------------------

def scheduler_loop():
    while True:
        try:
            cfg = get_config()
            now = datetime.now()
            hm = now.strftime("%H:%M")
            today = date.today().isoformat()
            jobs = [
                (cfg.get("morning_time", "07:00"), f"med:morning:{today}",
                 lambda: build_cycle_message("morning")),
                (cfg.get("evening_time", "19:00"), f"med:evening:{today}",
                 lambda: build_cycle_message("evening")),
            ]
            for t in cfg.get("exercise_reminder_times", []):
                jobs.append((t, f"ex:{t}:{today}", build_exercise_message))
            for t, key, builder in jobs:
                if hm == t and not already_sent(key):
                    ok, msg = send_notification(builder())
                    if ok:
                        mark_sent(key)
                    print(f"[scheduler] {key}: {msg}")
        except Exception as e:
            print("[scheduler] error:", e)
        time.sleep(20)

# ----------------------------- web server -----------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path in ("/", "/index.html"):
            with open(os.path.join(BASE, "web", "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        # static files from web/ (js, css, images) – safe, no path traversal
        if p.path != "/" and "/" not in p.path.strip("/") and "." in p.path:
            name = p.path.lstrip("/")
            types = {".js": "application/javascript", ".css": "text/css",
                     ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json"}
            ext = os.path.splitext(name)[1]
            fpath = os.path.join(BASE, "web", name)
            if ext in types and os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    return self._send(200, f.read(), types[ext] + "; charset=utf-8")
        if p.path == "/api/data":
            day = urllib.parse.parse_qs(p.query).get("day", [date.today().isoformat()])[0]
            return self._send(200, {
                "meds": load_json("meds.json"),
                "exercises": load_json("exercises.json"),
                "wiki": load_json("wiki.json"),
                "config": get_config(),
                "day": day,
                "state": day_state(day),
            })
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}
        if p.path == "/api/dose":
            set_dose(payload["day"], payload["cycle"], payload["med_id"], payload["taken"])
            return self._send(200, {"ok": True})
        if p.path == "/api/exercise":
            set_exercise(payload["day"], payload["ex_id"], payload["done"])
            return self._send(200, {"ok": True})
        if p.path == "/api/config":
            cfg = get_config()
            for k in ("morning_time", "evening_time"):
                if k in payload:
                    cfg[k] = payload[k]
            if "notify" in payload:
                cfg["notify"].update(payload["notify"])
            if "exercise_reminder_times" in payload:
                cfg["exercise_reminder_times"] = payload["exercise_reminder_times"]
            save_json("config.json", cfg)
            return self._send(200, {"ok": True})
        if p.path == "/api/test":
            ok, msg = send_notification("✅ KneeCare test message — notifications are working!")
            return self._send(200, {"ok": ok, "message": msg})
        if p.path == "/api/notify_cycle":
            ok, msg = send_notification(build_cycle_message(payload.get("cycle", "morning")))
            return self._send(200, {"ok": ok, "message": msg})
        return self._send(404, {"error": "not found"})

def get_lan_ip():
    """Best-effort local network IP (the address the iPad should use)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are sent; this just selects the outbound interface.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()

def main():
    init_db()
    port = get_config().get("port", 8770)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    # Bind to 0.0.0.0 so other devices on the same WiFi (e.g. the iPad) can connect.
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    lan_ip = get_lan_ip()
    print(f"\n  KneeCare is running.")
    print(f"  On this Mac:        http://localhost:{port}")
    if lan_ip:
        print(f"  On iPad/phone:      http://{lan_ip}:{port}   (same WiFi)")
    print("\n  Keep this window open. Press Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

if __name__ == "__main__":
    main()
