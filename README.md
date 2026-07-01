# Pokémon GO Companion Tools

A small self-hosted web app for Pokémon GO mapping utilities, currently offering:

1. **Coordinates → GPX** — converts a pasted list of lat/lon pairs into a downloadable GPX route file.
2. **Discord Spawn Bot** — a web UI to start/stop a Discord bot that posts alerts when specific Pokémon spawn inside a configured zone.

The app is split into two services meant to run on the same private network:

- **Web App Backend** — serves the frontend and the public `/api/...` used by the browser.
- **Data Ingestion Service** — receives Golbat webhooks and hosts the Discord bot itself; only reachable internally.

## Project Structure

```
csmpogo/
├── data_service/                   # Internal service: Golbat webhooks + Discord bot
│   ├── main.py                     # FastAPI entry point
│   ├── config.py                   # Local config (gitignored — copy from config.py.example)
│   ├── config.py.example
│   ├── zones.json                  # Zone definitions (box or Koji-area)
│   ├── pois.json                   # Pokémon allowlists
│   ├── discord.json                # Bot token & channel IDs (gitignored — copy from discord.json.example)
│   ├── discord.json.example
│   ├── discord_bot/                # Bot state machine, zone/POI matching, config loading
│   ├── webhooks/                   # POST /webhook — Golbat event receiver
│   └── storage/                    # Placeholder for future DB writes
│
├── web_app/
│   ├── backend/                    # Public FastAPI app
│   │   ├── main.py                 # Entry point; also serves the frontend as static files
│   │   ├── config.py                # Local config (gitignored — copy from config.py.example)
│   │   ├── config.py.example
│   │   └── tools/                  # One package per tool (metadata + routes)
│   └── frontend/                   # Vanilla HTML/CSS/JS, no build step
│       ├── index.html              # App shell, sidebar navigation, tool loader
│       ├── css/
│       ├── js/tools/                # Per-tool client-side logic
│       └── views/                  # Per-tool HTML fragments
│
├── webhook_receiver.py             # Standalone Flask script for manually inspecting raw Golbat payloads (dev use only, not part of the running app)
├── requirements.txt
├── .env.example                    # Alternative to per-service config.py files
├── .gitignore
├── IMPLEMENTATION_SUMMARY.md        # Build log, API reference, and remaining work
└── README.md
```

## Setup & Installation

### Prerequisites

- Python 3.9+
- pip
- (Future) MySQL/MariaDB — database storage is not implemented yet, see [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the services

Each service reads settings from its own `config.py`, which can be overridden by environment variables. Copy the example files and adjust as needed:

```bash
cp data_service/config.py.example data_service/config.py
cp web_app/backend/config.py.example web_app/backend/config.py
cp .env.example .env
```

Key settings:

| Setting | Where | Purpose |
|---|---|---|
| `DATA_SERVICE_PORT` | `data_service/config.py` | Port the Data Ingestion Service listens on (default `5000`) |
| `KOJI_HOST` / `KOJI_PORT` / `KOJI_TIMEOUT` | `data_service/config.py` | Koji instance used to resolve `koji_area` zones to S2 cells |
| `DATABASE_URL` | `.env` | Reserved for future DB integration; not currently used |
| `DATA_SERVICE_URL` | `web_app/backend/config.py` | Where the Web App Backend reaches the Data Ingestion Service |
| `WEB_APP_PORT` | `web_app/backend/config.py` | Port the Web App Backend listens on (default `8000`) |
| `DEBUG` | either | Enables debug mode; keep `false` in production |

`config.py` and `.env` are gitignored — never commit real values.

### 3. Configure the Discord bot

1. Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications) and copy its token.
2. Note the Discord channel IDs you want alerts posted to.
3. Copy the template and fill it in:

```bash
cp data_service/discord.json.example data_service/discord.json
```

```json
{
  "token": "YOUR_BOT_TOKEN_HERE",
  "channels": {
    "alerts": 1513202613456338984,
    "gofestspawns": 1513229477801627658
  }
}
```

`discord.json` is gitignored — keep the token secret.

### 4. Configure zones & POIs

Edit `data_service/zones.json` and `data_service/pois.json`:

- **Zones** define the area to monitor. Two types are supported:
  - `"type": "box"` — a lat/lon bounding rectangle (`min`/`max`).
  - `"type": "koji_area"` — an area fetched from a Koji instance and converted to S2 cells at runtime.
- **POIs** define an allowlist of `{id, form}` Pokémon pairs to alert on.

Example entries are already present in both files.

## Running the Services

Both services need to be running for the app to be fully functional.

### Data Ingestion Service (internal)

```bash
python -m uvicorn data_service.main:app --port 5000 --reload
```

Health check: http://localhost:5000/health

### Web App Backend (public-facing)

```bash
python -m uvicorn web_app.backend.main:app --port 8000 --reload
```

Health check: http://localhost:8000/health

The Web App Backend also serves the frontend, so once it's running the app itself is available at http://localhost:8000/.

## Using the Tools

### Coordinates → GPX

1. Open the app and select **Coordinates to GPX**.
2. Enter a route name (e.g. "Community Day Route").
3. Paste coordinate pairs, one per line, as `latitude,longitude`:
   ```
   40.7128,-74.0060
   40.7138,-74.0050
   40.7148,-74.0040
   ```
4. Click **Download GPX** — a `{routeName}.gpx` file is downloaded, using the GPX route format (`<rte>/<rtept>`), compatible with navigation apps like ReactMap.

### Discord Spawn Bot

1. Open the app and select **Discord Spammer Bot**.
2. Click **Reload Configurations** to load the zones, POIs, and channels from `data_service`.
3. Select a **Zone**, a **POI** allowlist, and a **Discord Channel**.
4. Click **Start Bot**.
5. The status badge turns green once the bot has connected to Discord; it will then post an embed to the selected channel for each matching spawn.
6. Click **Stop Bot** to shut it down.

**Status indicators:**
- 🔴 Offline — bot idle, not running
- 🟡 Starting/Stopping — transition in progress
- 🟢 Running — connected and monitoring
- 🟠 Error — check the displayed error message

## Troubleshooting

**Discord bot won't connect**
- Check the token in `data_service/discord.json`.
- Verify the channel IDs are correct and the bot has permission to post in them.
- Check the Data Ingestion Service logs for connection errors.

**GPX file won't download**
- Check the browser console (F12) for JavaScript errors.
- Verify coordinates are `lat,lon` per line.
- Route name must not be empty.

**Web App Backend can't reach the Data Service**
- Confirm the Data Ingestion Service is running (http://localhost:5000/health).
- Check `DATA_SERVICE_URL` in `web_app/backend/config.py`.
- Check firewall rules if the two services run on different hosts.

## Security Notes

- `discord.json`, `config.py`, and `.env` contain secrets and must stay out of version control (already gitignored).
- `/internal/...` endpoints on the Data Ingestion Service are meant to be reachable only from the Web App Backend — keep that service off any public network.
- CORS currently allows all origins, for development convenience; restrict this before exposing the app beyond a private network.
- There is no authentication layer. This app is designed to run on a private/trusted network only.
