# KneeCare — web app + scheduler + natural-language Discord assistant.
# Builds an always-on image for a free cloud host (fly.io, a VM, etc.).
FROM python:3.12-slim

WORKDIR /app

# tzdata so scheduled reminders fire in local time (see TZ below), and google-adk
# for the assistant. The core app itself is pure standard library.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir google-adk

# App code + content (NOT secrets, NOT the local DB — those come from env/volume).
COPY app.py kneecare_agent.py config.json meds.json exercises.json wiki.json ./
COPY web/ ./web/
COPY Assets/ ./Assets/

# Persistent data lives on a mounted volume, never inside the image.
ENV KNEECARE_DATA_DIR=/data \
    PORT=8770 \
    GOOGLE_GENAI_USE_VERTEXAI=FALSE \
    TZ=Africa/Johannesburg
VOLUME ["/data"]
EXPOSE 8770

CMD ["python", "app.py"]
