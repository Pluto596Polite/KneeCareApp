# Run KneeCare 24/7 in the cloud (Mac can be off)

This hosts the web app **and** the Discord assistant on an always-on machine, so
the bot answers even when your Mac and home are off. The SQLite database lives on a
persistent volume, so logged entries survive deploys, restarts, and crashes.

Recommended host: **fly.io** (always-on machine + persistent volume, one card on
file, a tiny machine costs roughly $0–2/month). A truly $0 alternative (Oracle
Always Free VM) is at the bottom.

---

## fly.io — step by step

### 0. One-time install + login
```bash
brew install flyctl          # or: curl -L https://fly.io/install.sh | sh
fly auth signup              # or: fly auth login
```

### 1. Create the app (from this folder)
```bash
cd KneeCareApp
fly launch --no-deploy --copy-config --name kneecare-mom
```
- `--copy-config` uses the included `fly.toml`.
- Pick a **unique** app name (e.g. `kneecare-mom`) and your nearest region
  (`jnb` = Johannesburg). If it asks to set up Postgres/Redis, say **No**.

### 2. Create the persistent disk (same region as the app)
```bash
fly volumes create kneecare_data --size 1 --region jnb
```

### 3. Set the secrets (never commit these)
```bash
fly secrets set \
  DISCORD_BOT_TOKEN="your-discord-bot-token" \
  GOOGLE_API_KEY="your-gemini-key" \
  KNEECARE_PASSWORD="a-strong-web-password" \
  DISCORD_WEBHOOK_URL="your-discord-webhook-url"
```
(`KNEECARE_PASSWORD` protects the public web UI; `DISCORD_WEBHOOK_URL` is only for
the scheduled reminder posts. The channel ID stays in `config.json`.)

### 4. Deploy
```bash
fly deploy
```

### 5. Verify
```bash
fly logs
```
You should see `KneeCare is running` and
`[discord] bot online, polling channel … — natural-language (Gemini) mode`, and the
bot posts **🟢 KneeCare assistant is online** to your channel. Message the channel —
it replies. The web app is at `https://<your-app>.fly.dev` (log in with
`KNEECARE_PASSWORD`); this also works from your iPad anywhere, not just home WiFi.

### 6. (Optional) Move your existing log history to the cloud
Your current data is in `KneeCareApp/data/kneecare.db` on the Mac. To carry it over:
```bash
fly sftp shell
put data/kneecare.db /data/kneecare.db
exit
fly apps restart kneecare-mom
```
Skip this to just start fresh in the cloud.

---

## Day-to-day
- **Update content/code:** edit locally, then `fly deploy`.
- **Logs:** `fly logs`     **Restart:** `fly apps restart <app>`     **Stop:** `fly apps suspend <app>`
- **Cost guard:** the config runs **one** small always-on machine. Don't scale up.

## Timezone
Reminders fire in `TZ` (set to `Africa/Johannesburg` in `fly.toml` + `Dockerfile`).
Change both if you're elsewhere, then `fly deploy`.

## Security (do this)
You shared the bot token + Gemini key in chat, and `config.json` still holds the old
webhook URL + password. Once cloud is live, **rotate**: Discord → Reset Token; Gemini
→ new key (aistudio.google.com/apikey); set a fresh `KNEECARE_PASSWORD`. Secrets set
via `fly secrets` override anything in `config.json` and are never in the image.

---

## Truly $0 alternative — Oracle Cloud Always Free VM
1. Create an **Always Free** account, launch a small VM (Ampere/AMD micro), open
   port 8770 in the security list, SSH in.
2. Install Docker (`sudo apt install -y docker.io`), copy this folder up
   (`scp -r KneeCareApp ubuntu@<ip>:~`).
3. Run it always-on with a persistent volume and your secrets:
```bash
docker build -t kneecare ~/KneeCareApp
docker run -d --name kneecare --restart always -p 8770:8770 \
  -v kneecare_data:/data \
  -e DISCORD_BOT_TOKEN="..." -e GOOGLE_API_KEY="..." \
  -e KNEECARE_PASSWORD="..." -e DISCORD_WEBHOOK_URL="..." \
  -e TZ="Africa/Johannesburg" \
  kneecare
```
`--restart always` brings it back on reboot/crash. The named volume `kneecare_data`
persists the database. No recurring cost, data stays on a VM you control.
