# Pokémon GO Mapping Web App - Implementation Guide

## Overview

This is the implementation of two web app tools as specified in `projectDescription.md`:
1. **Coordinates-to-GPX** — Converts user-entered coordinate pairs to a downloadable GPX file
2. **Discord Spammer Bot** — Web UI to control a Discord bot that sends alerts for Pokémon spawns

## Project Structure

```
project-root/
├── data-service/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration
│   ├── zones.json                 # Zone definitions (KEEP SECRET)
│   ├── pois.json                  # POI/allowlist definitions
│   ├── discord.json               # Discord bot token & channels (KEEP SECRET)
│   ├── discord_bot/
│   │   ├── __init__.py
│   │   ├── config_loader.py       # Loads & validates config files
│   │   ├── bot.py                 # Discord bot core logic
│   │   └── routes.py              # Internal API endpoints (/internal/discord/...)
│   ├── webhooks/
│   │   ├── __init__.py
│   │   └── handlers/
│   │       ├── __init__.py
│   │       └── pokemon.py         # (TODO) Pokémon event handler
│   └── storage/
│       └── __init__.py            # (TODO) Database writer
│
├── web-app/
│   ├── backend/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── config.py              # Backend configuration
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── tool_registry.py   # Tool discovery & registration
│   │       ├── coords_to_gpx/
│   │       │   ├── __init__.py
│   │       │   └── routes.py      # Tool metadata (no API endpoints)
│   │       └── discord_bot/
│   │           ├── __init__.py
│   │           └── routes.py      # Proxy to data service
│   └── frontend/
│       ├── index.html             # (TODO) Main HTML entry
│       ├── css/
│       │   └── forms.css          # Form styling
│       ├── js/
│       │   ├── app.js             # (TODO) Main app controller
│       │   └── tools/
│       │       ├── coords_to_gpx.js
│       │       └── discord_bot.js
│       └── views/
│           ├── coords_to_gpx.html
│           └── discord_bot.html
│
├── shared/                         # (TODO) Shared Python code
│   ├── __init__.py
│   ├── db.py                      # Database connection
│   ├── models.py                  # SQLAlchemy ORM models
│   └── config.py                  # Shared configuration
│
├── plan.md                         # Implementation plan
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

## Installation & Setup

### 1. Prerequisites

- Python 3.9+
- Pip (Python package manager)
- MySQL/MariaDB (for the shared database)

### 2. Install Dependencies

Add to `requirements.txt` at the project root:

```
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
httpx==0.25.0

# Discord Bot
discord.py==2.3.2

# Geolocation & S2 Geometry
s2sphere==0.2.13

# Database (when implemented)
sqlalchemy==2.0.0
pymysql==1.1.0

# Utilities
python-dotenv==1.0.0
```

Then install:

```bash
pip install -r requirements.txt
```

### 3. Configure Discord Bot

1. **Create a Discord bot** at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Copy the bot token** (keep it secret!)
3. **Create/note Discord channel IDs** where alerts should be sent
4. **Edit `data-service/discord.json`**:

```json
{
  "token": "YOUR_BOT_TOKEN_HERE",
  "channels": {
    "alerts": 1513202613456338984,
    "gofestspawns": 1513229477801627658
  }
}
```

**⚠️ IMPORTANT:** Add `discord.json` and `master-latest-raw.json` to `.gitignore` to avoid committing secrets.

### 4. Configure Zones & POIs

Edit `data-service/zones.json` and `data-service/pois.json` with your custom zones and Pokémon allowlists. Examples are provided.

### 5. Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Data Service
DATA_SERVICE_PORT=5000
DATA_SERVICE_URL=http://localhost:5000
DEBUG=False

# Web App Backend
WEB_APP_PORT=8000
DEBUG=False

# Database (when implemented)
DATABASE_URL=mysql+pymysql://user:password@localhost/pogo_db
KOJI_HOST=192.168.0.247
KOJI_PORT=8080
```

## Running the Services

### Start Data Ingestion Service

```bash
python -m uvicorn data_service.main:app --port 5000 --reload
```

Visit: http://localhost:5000/

### Start Web App Backend

```bash
python -m uvicorn web_app.backend.main:app --port 8000 --reload
```

Visit: http://localhost:8000/

### Health Checks

- Data Service: http://localhost:5000/health
- Web App: http://localhost:8000/health

## API Endpoints

### Web App Backend (`/api/tools/...`)

#### List All Tools
```
GET /api/tools
```

**Response:**
```json
{
  "tools": [
    {
      "id": "coords_to_gpx",
      "name": "Coordinates to GPX",
      "description": "...",
      "has_map": false,
      "icon": "download",
      "mobile_optimized": true
    },
    {
      "id": "discord_bot",
      "name": "Discord Spammer Bot",
      "description": "...",
      "has_map": false,
      "icon": "bell",
      "mobile_optimized": true
    }
  ]
}
```

#### Discord Bot - Get Configs
```
GET /api/tools/discord_bot/configs
```

**Response:**
```json
{
  "zones": {
    "steJulieDomaine": {...},
    "goFestChicago": {...}
  },
  "pois": {
    "current": {...},
    "goFestChicago": {...}
  },
  "channels": {
    "alerts": 1513202613456338984,
    "gofestspawns": 1513229477801627658
  }
}
```

#### Discord Bot - Start
```
POST /api/tools/discord_bot/start

{
  "zone": "goFestChicago",
  "poi": "current",
  "channel_id": 1513202613456338984
}
```

**Response:**
```json
{
  "state": "running",
  "zone": "goFestChicago",
  "poi": "current",
  "channel_id": 1513202613456338984,
  "discord_connected": true,
  "error_msg": null,
  "s2_cells_loaded": 0
}
```

#### Discord Bot - Stop
```
POST /api/tools/discord_bot/stop
```

#### Discord Bot - Get Status
```
GET /api/tools/discord_bot/status
```

### Data Ingestion Service (Internal Only)

**Note:** These endpoints are internal (`/internal/...`) and should not be exposed externally. They are accessed by the Web App Backend for proxying.

- `GET /internal/discord/configs`
- `POST /internal/discord/start`
- `POST /internal/discord/stop`
- `GET /internal/discord/status`

## Using the Tools

### Coordinates-to-GPX

1. Open the web app and navigate to the **Coordinates to GPX** tool
2. Enter a route name (e.g., "Community Day Route")
3. Paste coordinate pairs (one per line, `latitude,longitude`):
   ```
   40.7128,-74.0060
   40.7138,-74.0050
   40.7148,-74.0040
   ```
4. Click **Download GPX**
5. A `.gpx` file is downloaded with your route

**Format:** GPX route (`<rte>/<rtept>`) — compatible with navigation apps like ReactMap

### Discord Spammer Bot

1. Open the web app and navigate to the **Discord Spammer Bot** tool
2. Click **Reload Configurations** to load zones, POIs, and channels
3. Select a **Zone** (area to monitor)
4. Select a **POI** (Pokémon allowlist filter)
5. Select a **Discord Channel** (where alerts will be posted)
6. Click **Start Bot**
7. Status badge turns **green** when connected
8. Bot sends Discord embeds whenever a matching Pokémon is spotted
9. Click **Stop Bot** to shut down

**Status Indicators:**
- 🟢 **Running** — Bot is active and monitoring
- 🟡 **Starting/Stopping** — Transition in progress
- 🔴 **Offline** — Bot is not running
- 🟠 **Error** — Bot encountered an error (check error message)

## TODO & Future Work

### Phase 1 (Coordinates-to-GPX) — ✅ DONE
- [x] Backend tool registration
- [x] Frontend HTML & JS
- [x] GPX generation & download
- [x] Coordinate validation
- [x] LocalStorage persistence

### Phase 2A (Discord Bot - Data Service)
- [x] Config loader (zones, POIs, Discord)
- [x] Bot core logic (state machine, zone checking, Discord integration)
- [x] Internal API routes
- [ ] Webhook handler hook-up (integrate with pokemon.py handler)
- [ ] S2 geometry support (Koji area zones) — stubbed, needs implementation
- [ ] Pokémon name loader from master file

### Phase 2B (Discord Bot - Web Backend)
- [x] Proxy routes to Data Service
- [x] Tool registration

### Phase 2C (Discord Bot - Frontend)
- [x] HTML tool panel
- [x] JS UI controller
- [x] Config loading & dropdown population
- [x] Start/stop buttons
- [x] Status polling & badge
- [x] Error handling

### Common Next Steps

1. **Integrate with actual Golbat webhooks:**
   - Implement `data-service/webhooks/routes.py` (POST /webhook endpoint)
   - Implement `data-service/webhooks/handlers/pokemon.py`
   - Call `discord_bot.bot.check_and_notify()` from handler

2. **Set up database:**
   - Implement `shared/models.py` with SQLAlchemy ORM
   - Create database schema in `db/schema.sql`
   - Implement `data-service/storage/writer.py`

3. **Build main frontend:**
   - Create `web-app/frontend/index.html`
   - Implement `web-app/frontend/js/app.js` with:
     - Tool navigation (sidebar/hamburger menu)
     - Tool switching & display
     - Tool module loading

4. **Add more tools:**
   - **Show-in-ReactMap** (list areas from Koji, open in ReactMap)
   - **Showcase Map** (map of Pokémon showcase data)

5. **Mobile optimization:**
   - Test on actual mobile devices
   - Responsive CSS (already structured for mobile-first)
   - Touch gestures

6. **Optional: PWA & offline support**
   - Service Worker for caching
   - Manifest.json for install
   - Offline fallback

## Troubleshooting

### Discord Bot Won't Connect

1. **Check the bot token** in `discord.json` — is it correct?
2. **Verify channel IDs** — are they valid Discord channel IDs?
3. **Check Discord permissions** — does the bot have permission to send messages in those channels?
4. **Check logs** for error messages

### GPX File Won't Download

1. **Check browser console** (F12) for JavaScript errors
2. **Verify coordinates format** — should be `lat,lon` (comma-separated, decimals allowed)
3. **Check route name** — it must not be empty

### Web App Backend Can't Connect to Data Service

1. **Is the Data Service running?** Check http://localhost:5000/health
2. **Check `DATA_SERVICE_URL`** in `web-app/backend/config.py` — is it correct?
3. **Check firewall** — port 5000 must be accessible

## Security Notes

- **Secrets:** `discord.json`, `config files with DB credentials` must be in `.gitignore`
- **Internal Endpoints:** `/internal/...` endpoints should only be accessible from the Web App Backend (both services on private network per spec)
- **CORS:** Currently allows all origins for development. Restrict in production.
- **No authentication:** Per project spec, all services are on a private network. Add auth if exposed publicly.

## Performance Considerations

- **Discord Bot:** Runs in a daemon thread with its own asyncio event loop (proven pattern from reference)
- **Config Caching:** Configs are loaded once on bot start, not re-fetched per webhook
- **S2 Cells:** For `koji_area` zones, S2 cells are cached in memory to avoid API calls per event
- **Status Polling:** Frontend polls bot status every 10 seconds (configurable)

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Golbat Webhooks](https://github.com/UnownHash/Golbat/blob/main/webhooks.md)
- [S2 Geometry](https://github.com/sidewalklabs/s2geometry)
- [GPX File Format](https://www.topografix.com/GPX/1/1/)

---

**Last Updated:** 2026-06-26  
**Status:** Implementation Complete (Core Features)
