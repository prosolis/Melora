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

### 2. Set up a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Verify your configuration

```bash
python -m app --check
```

This validates that all required environment variables are set, the Matrix homeserver is reachable, the bot token is valid, the bot has joined the announcements room, and the database path is writable. Fix any failing checks before starting the server.

### 4. Run locally

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Run with Docker

```bash
docker build -t melora .

# Verify configuration first
docker run --rm --env-file .env melora python -m app --check

# Start the service
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

Melora receives push notifications from each *arr app via their built-in **Connect / Webhook** system. The setup is nearly identical across Radarr, Sonarr, and Lidarr — only the webhook URL path differs.

> **Prerequisite:** Before configuring any *arr instance, make sure Melora is running and reachable from the machine that hosts your *arr apps. You can verify by hitting the health endpoint:
> ```bash
> curl http://melora-host:8000/health
> # Expected: {"status":"ok"}
> ```

---

### Radarr (Movies)

1. Open Radarr → **Settings** → **Connect**
2. Click **+** to add a new connection and select **Webhook**
3. Fill in the following fields:

| Field | Value |
|-------|-------|
| **Name** | `Melora` (or any label you like) |
| **On Grab** | Off |
| **On Import** | **On** |
| **On Upgrade** | **On** (if you want upgrade notifications) |
| **On Rename** | Off |
| **On Movie Added** | Off |
| **On Movie Delete** | Off |
| **On Movie File Delete** | Off |
| **On Health Issue** | Off |
| **Tags** | Leave blank (all movies) or choose specific tags |
| **URL** | `http://melora-host:8000/webhook/radarr` |
| **Method** | `POST` |
| **Username** | _(leave blank)_ |
| **Password** | _(leave blank)_ |

4. Under **Request Headers**, add a header:
   - **Key:** `X-Arr-Webhook-Secret`
   - **Value:** The same value you set for `WEBHOOK_SECRET` in your `.env`
5. Click **Test** — you should see a green check. Then click **Save**.

---

### Sonarr (TV Shows)

1. Open Sonarr → **Settings** → **Connect**
2. Click **+** to add a new connection and select **Webhook**
3. Fill in the following fields:

| Field | Value |
|-------|-------|
| **Name** | `Melora` |
| **On Grab** | Off |
| **On Import** | **On** |
| **On Upgrade** | **On** (if you want upgrade notifications) |
| **On Rename** | Off |
| **On Series Add** | Off |
| **On Series Delete** | Off |
| **On Episode File Delete** | Off |
| **On Health Issue** | Off |
| **Tags** | Leave blank (all series) or choose specific tags |
| **URL** | `http://melora-host:8000/webhook/sonarr` |
| **Method** | `POST` |
| **Username** | _(leave blank)_ |
| **Password** | _(leave blank)_ |

4. Under **Request Headers**, add a header:
   - **Key:** `X-Arr-Webhook-Secret`
   - **Value:** The same value you set for `WEBHOOK_SECRET` in your `.env`
5. Click **Test** — you should see a green check. Then click **Save**.

---

### Lidarr (Music)

1. Open Lidarr → **Settings** → **Connect**
2. Click **+** to add a new connection and select **Webhook**
3. Fill in the following fields:

| Field | Value |
|-------|-------|
| **Name** | `Melora` |
| **On Grab** | Off |
| **On Import** | **On** |
| **On Upgrade** | **On** (if you want upgrade notifications) |
| **On Rename** | Off |
| **On Album Delete** | Off |
| **On Artist Delete** | Off |
| **On Health Issue** | Off |
| **Tags** | Leave blank (all artists) or choose specific tags |
| **URL** | `http://melora-host:8000/webhook/lidarr` |
| **Method** | `POST` |
| **Username** | _(leave blank)_ |
| **Password** | _(leave blank)_ |

4. Under **Request Headers**, add a header:
   - **Key:** `X-Arr-Webhook-Secret`
   - **Value:** The same value you set for `WEBHOOK_SECRET` in your `.env`
5. Click **Test** — you should see a green check. Then click **Save**.

---

### Troubleshooting *arr Webhooks

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Test button shows red X | Melora is unreachable from the *arr host | Verify the URL, port, and any firewall rules between the hosts |
| Test passes but no Matrix messages appear | The Test event type is `Test`, not `Download` — Melora ignores it by design | Import a real file or trigger a manual import to generate a `Download` event |
| 401 Unauthorized in Melora logs | Secret mismatch | Ensure `X-Arr-Webhook-Secret` header value exactly matches the `WEBHOOK_SECRET` in Melora's `.env` |
| Duplicate notifications | Same media re-imported | Melora deduplicates by media ID — duplicates are silently ignored. If you see duplicates, check if the media has a different internal ID |

> **Note:** Melora only processes events with `eventType: "Download"`. This is the event type that Radarr/Sonarr/Lidarr send when a file is actually imported (not when it is grabbed from an indexer). All other event types are acknowledged with a `200 OK` but silently ignored.

## Webhook Endpoints

```
POST /webhook/radarr   — receives Radarr movie import events
POST /webhook/sonarr   — receives Sonarr episode import events
POST /webhook/lidarr   — receives Lidarr album import events
GET  /health           — returns {"status": "ok"} when the service is running
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
│   ├── __main__.py      # CLI entry point (--check flag)
│   ├── main.py          # FastAPI app, lifespan, startup
│   ├── check.py         # Configuration and connectivity checker
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

## Securing Webhooks

By default, webhook traffic (including the `X-Arr-Webhook-Secret` header) is sent over plain HTTP. Anyone who can observe network traffic between your \*arr instances and Melora can read the secret. The two recommended mitigations are a TLS reverse proxy and IP allowlisting — ideally both.

### 1. TLS via Caddy reverse proxy

[Caddy](https://caddyserver.com/) is the simplest option because it provisions and renews Let's Encrypt certificates automatically. Any reverse proxy that terminates TLS will work (nginx, Traefik, etc.) — Caddy just requires the least configuration.

#### Install Caddy

```bash
# Debian / Ubuntu
sudo apt install -y caddy

# Or with Docker
docker pull caddy:latest
```

#### Configure

Create (or edit) `/etc/caddy/Caddyfile`:

```
melora.example.com {
    reverse_proxy localhost:8000
}
```

Replace `melora.example.com` with your actual domain. Caddy will automatically obtain a TLS certificate and redirect HTTP to HTTPS.

```bash
sudo systemctl restart caddy
```

#### Update your \*arr webhook URLs

In each \*arr instance, change the webhook URL from:

```
http://melora-host:8000/webhook/radarr
```

to:

```
https://melora.example.com/webhook/radarr
```

The `X-Arr-Webhook-Secret` header is now encrypted in transit.

### 2. IP allowlisting

Restrict the webhook endpoints so only your \*arr server(s) can reach them. This works regardless of whether you use TLS, and is a good defense-in-depth layer.

#### Option A: At the reverse proxy (Caddy)

Add a `remote_ip` matcher to your Caddyfile:

```
melora.example.com {
    @allowed remote_ip 192.168.1.50 192.168.1.51
    handle @allowed {
        reverse_proxy localhost:8000
    }
    respond 403
}
```

Replace the IPs with the actual addresses of your Radarr/Sonarr/Lidarr hosts. If everything runs on the same machine, use `127.0.0.1`.

#### Option B: With a firewall (iptables / nftables)

If you aren't using a reverse proxy, restrict at the OS level:

```bash
# Allow only 192.168.1.50 to reach Melora on port 8000
sudo iptables -A INPUT -p tcp --dport 8000 -s 192.168.1.50 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
```

To persist across reboots:

```bash
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

### Recommended setup

| Layer | What it does |
|-------|-------------|
| **Caddy (TLS)** | Encrypts all traffic, including the webhook secret header |
| **IP allowlist** | Ensures only your \*arr hosts can reach the endpoint at all |
| **Webhook secret** | Authenticates requests in case the IP filter is misconfigured |

All three layers together give defense in depth — any single layer failing still leaves the other two in place.

## License

See repository for license details.
