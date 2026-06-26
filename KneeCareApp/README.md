# 🦵 KneeCare — Mom's Knee-Replacement Tracker

A small, **free**, locally-hosted app for your Mac that tracks Mom's medicine and
exercises after her knee replacement, and pushes reminders to your phone.

No accounts, no fees, no cloud — it runs from this folder using the Python that
already ships with macOS, and sends notifications through a free Discord webhook.

---

## 1. Start the app
Double-click **`start.command`**.
A Terminal window opens and your browser opens to **http://localhost:8770**.
Keep that Terminal window open while you want reminders to run.

*(If macOS blocks it the first time: right-click `start.command` → Open → Open.)*

To stop: close the browser and press `Ctrl+C` in the Terminal window.

## 1b. Open it on the iPad (same WiFi — free)
1. Make sure the iPad and this Mac are on the **same WiFi network**.
2. Start the app on the Mac (step 1). The Terminal window now prints a line like:
   `On iPad/phone:  http://192.168.1.23:8770`
3. On the iPad, open **Safari** and type that exact address.
4. Tap the **Share** button → **Add to Home Screen** → *Add*. It now opens like a
   real app (full screen, own icon) and stays in sync with the Mac — ticking a
   medicine on the iPad shows on the Mac and vice versa (one shared database).

Notes:
- The Mac must be **on and running the app** for the iPad to reach it (the iPad is
  a window into the Mac, not a separate copy).
- If the address ever changes, just re-read the line the Terminal prints on startup.
  To make it permanent, reserve a fixed IP for the Mac in your router (optional).

## 2. Turn on phone notifications (Discord — 2 minutes, free)
1. On a computer, open Discord → your server → a channel (e.g. make one called `#mom-meds`).
2. **Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL.**
3. In the app, go to **Settings**, paste the URL into *Discord webhook URL*, **Save**, then **Send test**.
4. Install **Discord** on your phone and enable notifications for that channel.
   Reminders now buzz your phone at **07:00** (morning meds) and **19:00** (evening meds),
   plus exercise nudges at 10:00 and 15:00.

*Don't use Discord?* Settings also supports **Telegram**, **ntfy.sh**, and
**WhatsApp via CallMeBot** (free, sends to 066 233 4433). See `config.json`.

## 3. Daily use
The app has five pages (sidebar on desktop, top bar on phone):
- **Today** — dashboard with progress cards; tap each medicine and exercise to tick it off.
  Resets automatically every new day. "Take now" (every-day meds) is listed separately from "Only if she has pain".
- **Exercises** — each exercise with an **animated illustration** showing the movement, reps, and a Done button.
- **Medicines** — full reference per drug: purpose, how/when to take, warnings, and tags.
- **Wiki** — searchable knowledge base. Search by medicine name, ingredient, or purpose; click
  **tags** (e.g. "Blood thinner", "Opioid", "If pain") to filter; plus a schedule legend (S3–S6) and glossary.
- **Settings** — reminder times and notification setup.

---

## The medicines (read from the dispensary labels & verified)
| Medicine | Active ingredient | For | When |
|---|---|---|---|
| **Axolta 10 mg** ⚠️ | Rivaroxaban | Blood thinner (prevents clots) | Morning, with food — **never skip, complete the course** |
| **Belanex 75 mg** | Pregabalin | Nerve pain | Morning **and** evening |
| **Colcibra 200 mg** | Celecoxib (anti-inflammatory) | Pain & swelling | Once daily, morning, after food |
| **Xonoco XR 10/5 mg** | Oxycodone/Naloxone | Strong pain | Every 12h (morning/evening) after food, if needed |
| **Dynapayne** | Paracetamol+Codeine+Meprobamate+Caffeine | Breakthrough pain | After food if needed — **max 8 in 24h** |

⚠️ This app is a **reminder aid, not medical advice**. Always follow the doctor
and pharmacist. Don't double up paracetamol/codeine products (Dynapayne already
contains both).

## Editing content
All content lives in plain files you can open and edit:
- `meds.json` — medicines & cycles
- `exercises.json` — exercise checklist (some entries are the *standard* knee set —
  marked ⚠ — please confirm/adjust against the printed physio booklet)
- `config.json` — reminder times, port, notification channel

## Note on the exercises
The physio booklet's first exercise pages were readable (deep breaths, ankle pumps,
ankle rotations — included word-for-word). The later pages couldn't be read from the
synced PDF, so the remaining exercises are the **standard** total-knee-replacement set,
clearly marked ⚠ in the app. Edit `exercises.json` to match the booklet exactly.
