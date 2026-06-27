"""
Web App Backend - Main Entry Point

REST API for serving tool data and coordinating with the Data Ingestion Service.
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for shared module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from web_app.backend import config
from web_app.backend.tools.tool_registry import register_tool_routers, get_tool_metadata
from web_app.backend.tools.discord_bot.routes import set_data_service_url

# Create FastAPI app
app = FastAPI(
    title="Pokémon GO Web App Backend",
    description="REST API for web app tools",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set Data Service URL for tool proxies
set_data_service_url(config.DATA_SERVICE_URL)

# Register tool routers
register_tool_routers(app)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "web-app-backend",
        "data_service_url": config.DATA_SERVICE_URL,
    }


@app.get("/api/tools")
async def list_tools():
    """List all available tools"""
    tools = get_tool_metadata()
    return {
        "tools": tools,
    }


# Mount frontend static files
# Compute the path to the frontend directory relative to this file
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"Frontend mounted at {frontend_path}")
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")


if __name__ == "__main__":
    import uvicorn

    port = config.WEB_APP_PORT
    debug = config.DEBUG

    logger.info(f"Starting Web App Backend on port {port}")
    logger.info(f"Data Service URL: {config.DATA_SERVICE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=port, debug=debug)
