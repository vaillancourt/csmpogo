"""
Discord Bot API Routes

Internal endpoints for controlling the Discord bot from other services.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from .bot import get_bot_manager
from .config_loader import get_loader

logger = logging.getLogger(__name__)

# Router for internal use only (should be at /internal/discord/...)
router = APIRouter(prefix="/internal/discord", tags=["discord_bot_internal"])


@router.get("/configs")
async def get_configs() -> Dict[str, Any]:
    """
    Reload and return all Discord bot configurations.
    
    Returns:
        {
            "zones": {...},
            "pois": {...},
            "channels": {...}
        }
    """
    try:
        configs = get_loader().reload_configs()
        return {
            "zones": configs["zones"],
            "pois": configs["pois"],
            "channels": configs["channels"],
        }
    except Exception as e:
        logger.error(f"Failed to load configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_bot(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start the Discord bot with specified zone, POI, and channel.
    
    Request body:
        {
            "zone": "zone_name",
            "poi": "poi_name",
            "channel_id": 123456789
        }
    
    Returns:
        Status dict
    """
    try:
        zone = request.get("zone")
        poi = request.get("poi")
        channel_id = request.get("channel_id")

        if not all([zone, poi, channel_id]):
            raise HTTPException(status_code=400, detail="Missing required fields: zone, poi, channel_id")

        if not isinstance(channel_id, int):
            raise HTTPException(status_code=400, detail="channel_id must be an integer")

        bot_manager = get_bot_manager()
        status = bot_manager.start_bot(zone, poi, channel_id)
        
        if status["state"] == "error":
            raise HTTPException(status_code=400, detail=status.get("error_msg"))

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_bot() -> Dict[str, Any]:
    """
    Stop the running Discord bot.
    
    Returns:
        Status dict
    """
    try:
        bot_manager = get_bot_manager()
        status = bot_manager.stop_bot()
        
        if status["state"] == "error":
            raise HTTPException(status_code=400, detail=status.get("error_msg"))

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get current Discord bot status.
    
    Returns:
        {
            "state": "idle|starting|running|stopping|error",
            "zone": "zone_name or null",
            "poi": "poi_name or null",
            "channel_id": 123456789 or null,
            "discord_connected": true|false,
            "error_msg": "error message or null",
            "s2_cells_loaded": 0
        }
    """
    try:
        bot_manager = get_bot_manager()
        return bot_manager.get_status()
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
