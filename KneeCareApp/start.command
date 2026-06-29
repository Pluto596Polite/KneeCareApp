#!/bin/bash
# Double-click this file to start KneeCare. Keep the window that opens running.
cd "$(dirname "$0")"
# Load the optional Gemini key for the Discord assistant, if present (free tier).
[ -f agent.env ] && . ./agent.env
PORT=$(python3 -c "import json;print(json.load(open('config.json')).get('port',8770))" 2>/dev/null || echo 8770)
# open the browser shortly after the server starts
( sleep 2; open "http://localhost:$PORT" ) &
# show the address to use on the iPad (same WiFi)
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "Starting KneeCare..."
if [ -n "$LAN_IP" ]; then
  echo "On your iPad (same WiFi), open:  http://$LAN_IP:$PORT"
fi
python3 app.py
