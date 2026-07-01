"""
Data Ingestion Service - Main Entry Point

Receives Golbat webhook events, processes them, and writes to the shared database.
Also hosts internal Discord bot control endpoints.
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for shared module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from data_service import config
from data_service.discord_bot.routes import router as discord_bot_router
from data_service.webhooks.routes import router as webhook_router

# Create FastAPI app
app = FastAPI(
    title="Pokémon GO Data Ingestion Service",
    description="Receives Golbat webhooks and manages Discord bot",
    version="0.1.0",
)

# Add CORS middleware (since we're on a private network, allow all)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Discord bot internal routes
app.include_router(discord_bot_router)

# Include Golbat webhook receiver
app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-ingestion",
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Pokémon GO Data Ingestion Service",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "discord_bot": "/internal/discord/...",
            "webhook": "/webhook",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("DATA_SERVICE_PORT", "5000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    logger.info(f"Starting Data Ingestion Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, debug=debug)
