"""
Tool Registry

Dynamically discovers and registers all available tools.
Each tool module must export a TOOL_METADATA dict with tool metadata.
"""

from typing import Dict, List, Any
from fastapi import APIRouter

# Import tool metadata
from .coords_to_gpx.routes import TOOL_METADATA as COORDS_TO_GPX_METADATA
from .discord_bot.routes import TOOL_METADATA as DISCORD_BOT_METADATA

# Tool registry: maps tool_id to metadata and router
TOOLS: Dict[str, Dict[str, Any]] = {
    "coords_to_gpx": COORDS_TO_GPX_METADATA,
    "discord_bot": DISCORD_BOT_METADATA,
}

def get_tool_metadata() -> List[Dict[str, Any]]:
    """
    Return list of all registered tool metadata for API response.
    """
    return [
        {
            "id": metadata["id"],
            "name": metadata["name"],
            "description": metadata["description"],
            "has_map": metadata.get("has_map", False),
            "icon": metadata.get("icon", "puzzle"),
            "mobile_optimized": metadata.get("mobile_optimized", False),
        }
        for metadata in TOOLS.values()
    ]


def register_tool_routers(app) -> None:
    """
    Register all tool routers with the FastAPI app.
    
    This should be called during app initialization.
    """
    from .coords_to_gpx.routes import router as coords_router
    from .discord_bot.routes import router as discord_router
    
    app.include_router(coords_router)
    app.include_router(discord_router)
