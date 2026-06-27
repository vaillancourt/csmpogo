"""
Coordinates-to-GPX tool registration and metadata.

This tool is purely frontend-based and requires no backend API endpoints.
It handles coordinate input, GPX generation, and file download entirely in the browser.
"""

from fastapi import APIRouter

# Tool metadata for registration
TOOL_METADATA = {
    "id": "coords_to_gpx",
    "name": "Coordinates to GPX",
    "description": "Convert a list of coordinate pairs to a downloadable GPX file (route format)",
    "has_map": False,
    "icon": "download",
    "mobile_optimized": True,
}

# Create router (no actual endpoints needed)
router = APIRouter(prefix="/api/tools/coords_to_gpx", tags=["coords_to_gpx"])

# No endpoints required for this tool - all work done on frontend
