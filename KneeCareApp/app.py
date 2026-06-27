#!/usr/bin/env python3
"""
KneeCare - local medicine & exercise tracker for Mom's knee replacement recovery.
"""
import json
import os
import sqlite3
import threading
import time
import urllib.request
import urllib.parse
import urllib.error
import base64
from contextlib import contextmanager
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.expanduser("~"), ".kneecare")
DB_PATH = os.path.join(DATA_DIR, "kneecare.db")
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(name, obj):
    path = os.path.join(BASE, name)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)

def get_config():
    return load_json("config.json")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS dose_log(
            day TEXT, cycle TEXT, med_id TEXT, taken INTEGER, ts TEXT,
            PRIMARY KEY(day, cycle, med_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS exercise_log(
            day TEXT, ex_id TEXT, done INTEGER, ts TEXT,
            PRIMARY KEY(day, ex_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sent_log(
            key TEXT PRIMARY KEY, ts TEXT)""")

def set_dose(day, cycle, med_id, taken):
    with get_db() as conn:
        conn.execute("""INSERT INTO dose_log(day,cycle,med_id,taken,ts)
            VALUES(?,?,?,?,?)
            ON CONFLICT(day,cycle,med_id) DO UPDATE SET taken=excluded.taken, ts=excluded.ts""",
            (day, cycle, med_id, 1 if taken else 0, datetime.now().isoformat(timespec="seconds")))

def set_exercise(day, ex_id, done):
    with get_db() as conn:
        conn.execute("""INSERT INTO exercise_log(day,ex_id,done,ts)
            VALUES(?,?,?,?)
            ON CONFLICT(day,ex_id) DO UPDATE SET done=excluded.done, ts=excluded.ts""",
            (day, ex_id, 1 if done else 0, datetime.now().isoformat(timespec="seconds")))

def day_state(day):
    with get_db() as conn:
        doses = {f"{r['cycle']}:{r['med_id']}": bool(r["taken"])
                 for r in conn.execute("SELECT * FROM dose_log WHERE day=?", (day,))}
        ex = {r["ex_id"]: bool(r["done"])
              for r in conn.execute("SELECT * FROM exercise_log WHERE day=?", (day,))}
    return {"doses": doses, "exercises": ex}

def already_sent(key):
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM sent_log WHERE key=?", (key,)).fetchone() is not None

def mark_sent(key):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO sent_log(key,ts) VALUES(?,?)",
                     (key, datetime.now().isoformat(timespec="seconds")))

def send_notification(text):
    cfg = get_config()["notify"]
    ch = cfg.get("channel", "discord")
    try:
        if ch == "discord":
            # Prefer Bot Token if available
            tok = cfg.get("discord_bot_token", "").strip()
            ch_id = cfg.get("discord_channel_id", "").strip()
            if tok and ch_id:
                url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
                data = json.dumps({"content": text}).encode()
                req = urllib.request.Request(url, data=data, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bot {tok}",
                    "User-Agent": "KneeCare/1.0"
                })
                urllib.request.urlopen(req, timeout=15)
                return True, "Sent via Discord Bot."
            
            url = cfg.get("discord_webhook_url", "").strip()
            if not url:
                return False, "No Discord webhook URL set (open Settings)."
            data = json.dumps({"content": text}).encode()
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "User-Agent": "KneeCare/1.0 (Macintosh; medicine reminder)"})
            urllib.request.urlopen(req, timeout=15)
            return True, "Sent via Discord Webhook."
        if ch == "telegram":
            tok = cfg.get("telegram_bot_token", "").strip()
            chat = cfg.get("telegram_chat_id", "").strip()
            if not tok or not chat: return False, "Telegram missing."
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
            return True, "Sent via Telegram."
        if ch == "ntfy":
            topic = cfg.get("ntfy_topic", "").strip()
            if not topic: return False, "ntfy topic missing."
            url = f"https://ntfy.sh/{topic}"
            req = urllib.request.Request(url, data=text.encode(), headers={"Title": "KneeCare reminder"})
            urllib.request.urlopen(req, timeout=15)
            return True, "Sent via ntfy."
        if ch == "whatsapp":
            phone = cfg.get("whatsapp_phone", "").strip()
            key = cfg.get("whatsapp_callmebot_apikey", "").strip()
            if not phone or not key: return False, "WhatsApp missing."
            intl = "27" + phone[1:] if phone.startswith("0") else phone
            intl = "".join(c for c in intl if c.isdigit())
            url = ("https://api.callmebot.com/whatsapp.php?phone=" + intl + "&text=" + urllib.parse.quote(text) + "&apikey=" + key)
            urllib.request.urlopen(url, timeout=20)
            return True, "Sent via WhatsApp."
        return False, f"Unknown channel '{ch}'."
    except Exception as e:
        return False, f"Send failed: {e}"

def build_cycle_message(cycle):
    meds = load_json("meds.json")["medicines"]
    
    def strength(m):
        try: return int(m.get("schedule_code", "S0").replace("S", ""))
        except: return 0
    
    cycle_meds = []
    for m in meds:
        for c in m["cycles"]:
            if c["cycle"] == cycle:
                cycle_meds.append((m, c))
    
    if not cycle_meds: return ""
    
    cycle_meds.sort(key=lambda x: strength(x[0]), reverse=True)
    
    with_food = []
    without_food = []
    
    for m, c in cycle_meds:
        line = f"{m['name']} — {c['qty']}"
        if m.get("critical"): line += " ⚠️"
        if not c.get("regular"): line += " (PRN / If pain)"
        if m.get("with_food"): with_food.append(line)
        else: without_food.append(line)

    label = "MORNING" if cycle == "morning" else "EVENING"
    lines = [f"💊 {label} medicine for Mom ({datetime.now():%a %d %b})", ""]
    
    if with_food:
        lines.append("Take WITH FOOD:")
        for line in with_food: lines.append(f"  • {line}")
    if without_food:
        lines.append("")
        lines.append("Take WITHOUT FOOD:")
        for line in without_food: lines.append(f"  • {line}")
            
    lines.append("")
    lines.append("Open the app and tick off each one. ✅")
    return "\n".join(lines)

def build_exercise_message():
    return ("🦵 Exercise reminder for Mom — time for a set of knee exercises "
            "(aim 20–30 min, 2–3× a day). Open the app for the checklist.")

def scheduler_loop():
    sent_memory = set()
    while True:
        try:
            cfg = get_config()
            now = datetime.now()
            hm = now.strftime("%H:%M")
            today = date.today().isoformat()
            
            jobs = [
                (cfg.get("morning_time", "07:00"), f"med:morning:{today}", lambda: build_cycle_message("morning")),
                (cfg.get("evening_time", "19:00"), f"med:evening:{today}", lambda: build_cycle_message("evening")),
            ]
            for t in cfg.get("exercise_reminder_times", []):
                jobs.append((t, f"ex:{t}:{today}", build_exercise_message))
                
            messages_to_send = []
            keys_to_mark = []
            
            for t, key, builder in jobs:
                if hm == t and key not in sent_memory and not already_sent(key):
                    sent_memory.add(key)
                    messages_to_send.append(builder())
                    keys_to_mark.append(key)
            
            if messages_to_send:
                combined_msg = "\n\n---\n\n".join(messages_to_send)
                ok, msg = send_notification(combined_msg)
                if ok:
                    for k in keys_to_mark:
                        mark_sent(k)
                else:
                    for k in keys_to_mark:
                        sent_memory.discard(k)
                print(f"[scheduler] {keys_to_mark}: {msg}")
        except Exception as e:
            print("[scheduler] error:", e)
        time.sleep(20)

def discord_chatbot_loop():
    last_msg_id = None
    while True:
        try:
            cfg = get_config().get("notify", {})
            tok = cfg.get("discord_bot_token", "").strip()
            ch_id = cfg.get("discord_channel_id", "").strip()
            if not tok or not ch_id:
                time.sleep(10)
                continue
                
            url = f"https://discord.com/api/v10/channels/{ch_id}/messages?limit=5"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bot {tok}",
                "User-Agent": "KneeCare/1.0"
            })
            res = urllib.request.urlopen(req, timeout=10)
            msgs = json.loads(res.read())
            
            if msgs and not last_msg_id:
                last_msg_id = msgs[0]["id"]
            
            msgs.reverse()
            for msg in msgs:
                if msg["id"] <= last_msg_id: continue
                last_msg_id = msg["id"]
                
                if msg.get("author", {}).get("bot"): continue
                
                content = msg.get("content", "").lower()
                reply = ""
                
                if "what" in content and "cycle" in content:
                    hour = datetime.now().hour
                    cycle = "evening" if hour >= 14 else "morning"
                    reply = build_cycle_message(cycle)
                elif "strongest" in content or "rank" in content:
                    meds = load_json("meds.json")["medicines"]
                    def strength(m):
                        try: return int(m.get("schedule_code", "S0").replace("S", ""))
                        except: return 0
                    meds.sort(key=strength, reverse=True)
                    reply = "Strongest painkillers:\n" + "\n".join([f"- {m['name']} ({m['schedule_code']})" for m in meds])
                elif "used for what" in content or "what is" in content:
                    meds = load_json("meds.json")["medicines"]
                    found = False
                    for m in meds:
                        if m["name"].split()[0].lower() in content:
                            reply = f"{m['name']} is used for: {m['purpose']}"
                            found = True
                            break
                    if not found:
                        reply = "I didn't recognize that medication. Try asking about Axolta, Belanex, Colcibra, Xonoco, or Dynapayne."
                elif "help" in content or "hello" in content or "hi" in content:
                    reply = "Hello! You can ask me:\n- 'what is the following medication cycle'\n- 'which is strongest'\n- 'what is [medication name] used for'."
                
                if reply:
                    post_url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
                    data = json.dumps({"content": reply}).encode()
                    req_post = urllib.request.Request(post_url, data=data, headers={
                        "Authorization": f"Bot {tok}",
                        "Content-Type": "application/json",
                        "User-Agent": "KneeCare/1.0"
                    })
                    urllib.request.urlopen(req_post, timeout=10)
        except Exception as e:
            pass
        time.sleep(5)

class Handler(BaseHTTPRequestHandler):
    def do_AUTH(self):
        pwd = get_config().get("password", "")
        if not pwd: return True
        auth = self.headers.get("Authorization")
        if not auth:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="KneeCare"')
            self.end_headers()
            return False
        try:
            kind, encoded = auth.split(" ", 1)
            if kind.lower() == "basic":
                decoded = base64.b64decode(encoded).decode("utf-8")
                user, p = decoded.split(":", 1)
                if p == pwd: return True
        except: pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="KneeCare"')
        self.end_headers()
        return False

    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)): body = json.dumps(body).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.do_AUTH(): return
        p = urllib.parse.urlparse(self.path)
        if p.path in ("/", "/index.html"):
            with open(os.path.join(BASE, "web", "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if p.path != "/" and "." in p.path:
            name = urllib.parse.unquote(p.path.lstrip("/"))
            types = {".js": "application/javascript", ".css": "text/css",
                     ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json"}
            ext = os.path.splitext(name)[1]
            fpath = os.path.abspath(os.path.join(BASE, "web", name))
            web_dir = os.path.abspath(os.path.join(BASE, "web"))
            if fpath.startswith(web_dir) and ext in types and os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    return self._send(200, f.read(), types[ext] + "; charset=utf-8")
        if p.path == "/api/data":
            try:
                day = urllib.parse.parse_qs(p.query).get("day", [date.today().isoformat()])[0]
                return self._send(200, {
                    "meds": load_json("meds.json"),
                    "exercises": load_json("exercises.json"),
                    "wiki": load_json("wiki.json"),
                    "config": get_config(),
                    "day": day,
                    "state": day_state(day),
                })
            except Exception as e:
                return self._send(500, {"error": str(e)})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.do_AUTH(): return
        p = urllib.parse.urlparse(self.path)
        try: length = int(self.headers.get("Content-Length", 0))
        except ValueError: length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try: payload = json.loads(raw or b"{}")
        except Exception: payload = {}
        
        if p.path == "/api/dose":
            set_dose(payload["day"], payload["cycle"], payload["med_id"], payload["taken"])
            return self._send(200, {"ok": True})
        if p.path == "/api/exercise":
            set_exercise(payload["day"], payload["ex_id"], payload["done"])
            return self._send(200, {"ok": True})
        if p.path == "/api/config":
            cfg = get_config()
            for k in ("morning_time", "evening_time", "password"):
                if k in payload: cfg[k] = payload[k]
            if "notify" in payload: cfg["notify"].update(payload["notify"])
            if "exercise_reminder_times" in payload: cfg["exercise_reminder_times"] = payload["exercise_reminder_times"]
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
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except: return None
    finally: s.close()

def main():
    init_db()
    port = get_config().get("port", 8770)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=discord_chatbot_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    lan_ip = get_lan_ip()
    print(f"\n  KneeCare is running.")
    print(f"  On this Mac:        http://localhost:{port}")
    if lan_ip:
        print(f"  On iPad/phone:      http://{lan_ip}:{port}")
    print("\n  Press Ctrl+C to stop.\n")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Stopped.")

if __name__ == "__main__":
    main()
