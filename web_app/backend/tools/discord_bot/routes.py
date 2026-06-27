"""
Discord Bot Tool - Web App Backend Proxy

Proxies requests from the frontend to the Data Ingestion Service's internal Discord bot API.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
import httpx

logger = logging.getLogger(__name__)

# Tool metadata for registration
TOOL_METADATA = {
    "id": "discord_bot",
    "name": "Discord Spammer Bot",
    "description": "Control a Discord bot to send alerts for Pokemon spawns in specific zones",
    "has_map": False,
    "icon": "bell",
    "mobile_optimized": True,
}

# Create router
router = APIRouter(prefix="/api/tools/discord_bot", tags=["discord_bot"])

# Data Ingestion Service URL (will be set by main.py)
DATA_SERVICE_URL: str = "http://localhost:5000"


def set_data_service_url(url: str) -> None:
    """Set the Data Ingestion Service base URL."""
    global DATA_SERVICE_URL
    DATA_SERVICE_URL = url


async def _proxy_request(
    method: str,
    endpoint: str,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Proxy a request to the Data Ingestion Service.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Endpoint path (e.g., "configs", "start", "stop", "status")
        body: Request body for POST requests
        
    Returns:
        Response JSON
        
    Raises:
        HTTPException: If the request fails
    """
    url = f"{DATA_SERVICE_URL}/internal/discord/{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url, json=body)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Data Service returned {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Data Service error: {e.response.text}"
        )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Data Service at {url}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Data Ingestion Service unavailable at {url}"
        )
    except Exception as e:
        logger.error(f"Proxy request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Proxy error: {str(e)}"
        )


@router.get("/configs")
async def get_configs() -> Dict[str, Any]:
    """
    Get available zones, POIs, and Discord channels.
    
    Returns:
        {
            "zones": {"zone_name": {...}, ...},
            "pois": {"poi_name": {...}, ...},
            "channels": {"channel_name": channel_id, ...}
        }
    """
    return await _proxy_request("GET", "configs")


@router.post("/start")
async def start_bot(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start the Discord bot.
    
    Request body:
        {
            "zone": "zone_name",
            "poi": "poi_name",
            "channel_id": 123456789
        }
    
    Returns:
        Status dict
    """
    return await _proxy_request("POST", "start", request)


@router.post("/stop")
async def stop_bot() -> Dict[str, Any]:
    """
    Stop the Discord bot.
    
    Returns:
        Status dict
    """
    return await _proxy_request("POST", "stop")


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get Discord bot status.
    
    Returns:
        Status dict
    """
    return await _proxy_request("GET", "status")
