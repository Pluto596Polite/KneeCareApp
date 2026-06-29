#!/usr/bin/env python3
"""
Natural-language KneeCare assistant built on Google's Agent Development Kit (ADK).

It reads a free-form Discord message, lets Gemini work out what you actually want
(no fixed command list), and answers about Mom's medicines — their uses, strength,
how/when to take them, the morning/evening dose schedule, and what she has logged.

Cost / setup:
  • Uses the FREE Gemini tier (Google AI Studio). Set GOOGLE_API_KEY (or
    GEMINI_API_KEY). No billing account is required for the free tier.
  • `pip install google-adk`  (only needed for this assistant; the core app still
    runs on the standard library alone).

Safety net: if the key or the package is missing — or anything goes wrong — every
public function returns None so the Discord bot falls back to its built-in keyword
replies. The app therefore keeps working, offline and free, with the agent off.
"""
import os
import json
import sqlite3
import traceback
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "kneecare.db")

# Force the free AI-Studio path (a personal API key), never Vertex AI (billing).
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


def _load(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
#  Tools the agent may call. Plain functions with type hints + docstrings —
#  ADK turns each into a tool and Gemini decides when to use it. They read the
#  live JSON / SQLite files, so edits to meds.json show up without code changes.
# --------------------------------------------------------------------------- #
def get_medicines() -> list:
    """List every medicine with its use/purpose, strength code (S-number; higher
    means stronger / more tightly controlled), whether it is taken with food,
    whether it is critical (never skip), its tags, and its morning/evening dose
    cycles. Use this to answer what a medicine is for, how strong it is, or how
    and when to take it."""
    meds = _load("meds.json")["medicines"]
    return [{
        "name": m.get("name"),
        "use": m.get("purpose"),
        "schedule_code": m.get("schedule_code"),
        "with_food": m.get("with_food", False),
        "critical": m.get("critical", False),
        "tags": m.get("tags", []),
        "cycles": m.get("cycles", []),
        "notes": m.get("notes", ""),
    } for m in meds]


def get_dose_schedule(cycle: str = "") -> dict:
    """Return the dose schedule. `cycle` may be 'morning', 'evening', or '' for
    both. For each cycle it lists the medicines to take, the quantity, the food
    rule, and whether each is a regular daily dose or only-if-pain (PRN)."""
    meds = _load("meds.json")["medicines"]
    wanted = [cycle] if cycle in ("morning", "evening") else ["morning", "evening"]
    sched = {}
    for cy in wanted:
        items = []
        for m in meds:
            for c in m.get("cycles", []):
                if c.get("cycle") == cy:
                    items.append({
                        "name": m.get("name"),
                        "qty": c.get("qty"),
                        "with_food": m.get("with_food", False),
                        "regular": c.get("regular", True),
                        "critical": m.get("critical", False),
                    })
        sched[cy] = items
    return sched


def get_log(day: str = "") -> list:
    """Return the medicines logged as taken on a day. `day` is 'YYYY-MM-DD',
    'today', 'yesterday', or '' (= today). Use this when asked what Mom has
    taken or for her history."""
    try:
        if not day or day.lower() == "today":
            day = datetime.now().strftime("%Y-%m-%d")
        elif day.lower() == "yesterday":
            day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        names = {m["id"]: m["name"] for m in _load("meds.json")["medicines"]}
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM dose_events WHERE day=? ORDER BY ts DESC", (day,)
            ).fetchall()
        finally:
            conn.close()
        return [{
            "time": r["ts"].split("T")[1][:5] if r["ts"] and "T" in r["ts"] else "",
            "medicine": names.get(r["med_id"], r["med_id"]),
            "qty": (dict(r).get("qty") or 1),
        } for r in rows]
    except Exception:
        return []


_INSTRUCTION = (
    "You are KneeCare, a warm, concise assistant helping a family manage their "
    "mother's recovery after a total knee replacement. Answer in natural language, "
    "working out what the person wants from however they phrase it. You help with: "
    "what each medicine is for, how strong it is, how and when to take it "
    "(with/without food, morning/evening, regular vs only-if-pain), the daily dose "
    "schedule, and what she has logged.\n\n"
    "Always get facts from the tools — never invent a medicine, dose, schedule, or "
    "log entry. For 'strongest painkiller' questions, compare schedule_code (a higher "
    "S-number is stronger / more tightly controlled). Keep replies short and friendly "
    "for Discord — a few lines; simple bullets are fine. When you give any dosing or "
    "safety guidance, end with a short reminder that this is a reminder aid, not "
    "medical advice — follow the doctor and pharmacist — and never suggest exceeding a "
    "stated maximum."
)


def available() -> bool:
    """True only if a Gemini key and the google-adk package are both present."""
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        return False
    try:
        import google.adk  # noqa: F401
        return True
    except Exception:
        return False


_runner = None
_session_service = None
_sessions = set()
_USER = "discord"


def _build_runner():
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    # google-genai accepts GEMINI_API_KEY too; ADK reads GOOGLE_API_KEY — bridge it.
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("KNEECARE_MODEL", "gemini-2.5-flash")
    agent = Agent(
        name="kneecare",
        model=model,
        instruction=_INSTRUCTION,
        tools=[get_medicines, get_dose_schedule, get_log],
    )
    svc = InMemorySessionService()
    runner = Runner(agent=agent, app_name="kneecare", session_service=svc)
    return runner, svc


def _ensure_session(sid):
    # Create each session once so the conversation keeps its memory across
    # messages (don't recreate per message — that would wipe the history).
    if sid in _sessions:
        return
    import asyncio
    try:
        res = _session_service.create_session(
            app_name="kneecare", user_id=_USER, session_id=sid)
        if asyncio.iscoroutine(res):
            asyncio.run(res)
    except Exception:
        pass  # already exists, or a no-op on this ADK version
    _sessions.add(sid)


def answer(message: str, session_id: str = "discord-main"):
    """Run the agent on one message and return its reply text, or None if the
    agent isn't set up / hits an error (caller then falls back to keyword replies)."""
    if not message or not available():
        return None
    try:
        from google.genai import types
        global _runner, _session_service
        if _runner is None:
            _runner, _session_service = _build_runner()
        _ensure_session(session_id)
        content = types.Content(role="user", parts=[types.Part(text=message)])
        final = None
        for event in _runner.run(
                user_id=_USER, session_id=session_id, new_message=content):
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts)
        return final or None
    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Quick manual check:  GOOGLE_API_KEY=... python3 kneecare_agent.py "what is the strongest painkiller?"
    import sys
    q = " ".join(sys.argv[1:]) or "what should mom take this evening and what is each for?"
    print("available:", available())
    print(answer(q) or "(agent unavailable — Discord bot would use keyword fallback)")
