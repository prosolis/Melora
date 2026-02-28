# Melora

A webhook receiver that listens for media import events from Radarr, Sonarr, and Lidarr and announces new arrivals to a Matrix room via a bot. Each media type posts into its own persistent thread, keeping the room tidy.

## Architecture

```
Radarr ─┐
Sonarr ──┼─→ POST webhook → Melora (FastAPI) → Matrix room (threaded)
Lidarr ─┘
```

No polling. All three *arr instances push events to Melora via their built-in webhook/Connect system.

## Requirements

- Python 3.12+
- A Matrix homeserver with an unencrypted room and a bot account
- Radarr, Sonarr, and/or Lidarr instances configured to send webhooks

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/prosolis/Melora.git
cd Melora
cp .env.example .env
```

Edit `.env` with your actual values (see [Environment Variables](#environment-variables) below).

### 2. Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Run with Docker

```bash
docker build -t melora .
docker run -d \
  --name melora \
  --env-file .env \
  -p 8000:8000 \
  -v melora-data:/app \
  melora
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MATRIX_HOMESERVER_URL` | Yes | — | Base URL of your Matrix homeserver |
| `MATRIX_BOT_USER_ID` | Yes | — | Bot's Matrix user ID (e.g. `@melora-bot:example.com`) |
| `MATRIX_BOT_ACCESS_TOKEN` | Yes | — | Pre-authenticated access token for the bot |
| `MATRIX_ARRIVALS_ROOM_ID` | Yes | — | Room ID for arrival announcements (e.g. `!abc123:example.com`) |
| `WEBHOOK_SECRET` | Yes | — | Shared secret for *arr webhook authentication |
| `DATABASE_PATH` | No | `melora.db` | Path to the SQLite database file |

## *arr Configuration

In each *arr instance, go to **Settings → Connect → Add → Webhook** and configure:

- **URL**: `http://melora-host:8000/webhook/radarr` (or `/sonarr`, `/lidarr`)
- **Method**: `POST`
- **Events**: Enable **On Import** (and **On Upgrade** if desired)
- **Tags**: Leave blank to capture all imports
- **Headers**: Add `X-Arr-Webhook-Secret` with the same value as `WEBHOOK_SECRET`

## Webhook Endpoints

```
POST /webhook/radarr
POST /webhook/sonarr
POST /webhook/lidarr
GET  /health
```

Each webhook endpoint validates the `X-Arr-Webhook-Secret` header, processes only `Download` events, and posts to the appropriate Matrix thread.

## Matrix Room Structure

On first startup, Melora creates three thread root messages in the configured room. All subsequent announcements reply into the appropriate thread.

```
#new-arrivals:your.domain
  ├── 🎬 Movies    ← Radarr imports
  ├── 📺 Shows     ← Sonarr imports
  └── 🎵 Music     ← Lidarr imports
```

Thread root `event_id` values are stored in SQLite, so threads persist across restarts.

## Message Format

Messages include both plain text and HTML (Matrix-flavored Markdown). New additions and quality upgrades are distinguished:

**New movie:**
```
🎬 The Substance (2024)
  ✅ New addition
  🎞️ Quality: Bluray-1080p
```

**Quality upgrade:**
```
🎬 The Substance (2024)
  ⬆️ Quality upgrade
  🎞️ Quality: Bluray-2160p
```

## Project Structure

```
Melora/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan, startup
│   ├── config.py        # Environment variable loading
│   ├── database.py      # Async SQLite for thread roots and dedup
│   ├── matrix.py        # matrix-nio posting and thread management
│   ├── formatters.py    # Message formatting for each media type
│   └── webhooks.py      # Webhook route handlers
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Error Handling

- Unknown or malformed payloads return 200 (prevents *arr retry storms)
- Parsing and Matrix posting errors are logged but don't crash the service
- Missing thread roots on startup halt with a clear error

## License

See repository for license details.
