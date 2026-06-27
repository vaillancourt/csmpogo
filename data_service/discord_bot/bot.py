"""
Discord Bot Core Logic

Manages the Discord bot thread, state machine, and notification logic.
Ported from C:\dev\pogo\dataquery\webhook_listener.py
"""

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import discord
from discord.ext import commands
from s2sphere import Cell, CellId, LatLng

from .config_loader import get_loader

logger = logging.getLogger(__name__)


class DiscordBotManager:
    """
    Manages Discord bot lifecycle: start, stop, status monitoring.
    
    The bot runs in a separate daemon thread with its own asyncio event loop.
    This matches the proven pattern from webhook_listener.py and avoids conflicts
    with FastAPI's event loop.
    """

    def __init__(self):
        """Initialize the bot manager."""
        self.state: str = "idle"  # idle, starting, running, stopping, error
        self.zone: Optional[str] = None
        self.poi: Optional[str] = None
        self.channel_id: Optional[int] = None
        self.error_msg: Optional[str] = None
        
        self.bot_thread: Optional[threading.Thread] = None
        self.bot_loop: Optional[asyncio.AbstractEventLoop] = None
        self.discord_client: Optional[discord.Client] = None
        self.discord_connected: bool = False
        
        # Cached configuration
        self.s2_cells: set = set()  # For koji_area zones
        self.pokemon_names: Dict[int, str] = {}  # ID -> name mapping
        self.zones: Dict[str, Dict] = {}
        self.pois: Dict[str, Dict] = {}
        self.channels_config: Dict[str, int] = {}

    def start_bot(self, zone: str, poi: str, channel_id: int) -> Dict[str, Any]:
        """
        Start the Discord bot with the given zone, POI, and channel.
        
        Args:
            zone: Zone name from zones.json
            poi: POI name from pois.json
            channel_id: Discord channel ID to post alerts to
            
        Returns:
            Status dict
        """
        if self.state == "running":
            self.error_msg = f"Bot already running on zone '{self.zone}' / POI '{self.poi}'"
            return self.get_status()

        if self.state == "starting":
            self.error_msg = "Bot is already starting"
            return self.get_status()

        try:
            self.state = "starting"
            self.zone = zone
            self.poi = poi
            self.channel_id = channel_id
            self.error_msg = None
            self.discord_connected = False

            # Load and validate configs
            configs = get_loader().reload_configs()
            self.zones = configs["zones"]
            self.pois = configs["pois"]
            self.channels_config = configs["channels"]

            # Validate zone and POI exist
            if zone not in self.zones:
                raise ValueError(f"Zone '{zone}' not found in zones.json")
            if poi not in self.pois:
                raise ValueError(f"POI '{poi}' not found in pois.json")

            zone_config = self.zones[zone]
            
            # For koji_area zones, fetch S2 cells
            if zone_config.get("type") == "koji_area":
                koji_instance = zone_config.get("koji_instance")
                self._fetch_s2_cells_from_koji(koji_instance)
                logger.info(f"Loaded {len(self.s2_cells)} S2 cells for zone '{zone}'")

            # Load Pokemon names (stub for now - would load from master file)
            self._load_pokemon_names()

            # Start bot thread
            self._start_bot_thread()

            logger.info(f"Discord bot starting for zone '{zone}' / POI '{poi}'")
            return self.get_status()

        except Exception as e:
            self.state = "error"
            self.error_msg = str(e)
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            return self.get_status()

    def stop_bot(self) -> Dict[str, Any]:
        """
        Stop the Discord bot gracefully.
        
        Returns:
            Status dict
        """
        if self.state == "idle":
            self.error_msg = "Bot is not running"
            return self.get_status()

        try:
            self.state = "stopping"
            self.error_msg = None

            if self.bot_loop and self.discord_client:
                # Close the Discord client gracefully
                asyncio.run_coroutine_threadsafe(
                    self.discord_client.close(),
                    self.bot_loop
                ).result(timeout=10)

            if self.bot_thread:
                self.bot_thread.join(timeout=5)
                self.bot_thread = None

            self.state = "idle"
            self.zone = None
            self.poi = None
            self.channel_id = None
            self.discord_connected = False
            self.s2_cells.clear()

            logger.info("Discord bot stopped")
            return self.get_status()

        except Exception as e:
            self.state = "error"
            self.error_msg = f"Failed to stop bot: {str(e)}"
            logger.error(self.error_msg, exc_info=True)
            return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Status dict with state, zone, POI, channel, connection status, etc.
        """
        return {
            "state": self.state,
            "zone": self.zone,
            "poi": self.poi,
            "channel_id": self.channel_id,
            "discord_connected": self.discord_connected,
            "error_msg": self.error_msg,
            "s2_cells_loaded": len(self.s2_cells),
        }

    def check_and_notify(self, pokemon_data: Dict[str, Any]) -> bool:
        """
        Check if a Pokemon spawn matches the active zone and POI.
        If it matches, send a Discord notification.
        
        Args:
            pokemon_data: Pokemon event data from webhook.
                         Must have: pokemon_id, form, latitude, longitude
                         
        Returns:
            True if notification was sent, False otherwise
        """
        if self.state != "running":
            return False

        if not self.discord_client or not self.discord_connected:
            logger.warning("Discord client not connected")
            return False

        try:
            # Extract data
            pokemon_id = pokemon_data.get("pokemon_id")
            form = pokemon_data.get("form", 0)
            latitude = pokemon_data.get("latitude")
            longitude = pokemon_data.get("longitude")

            if None in (pokemon_id, latitude, longitude):
                logger.warning(f"Incomplete pokemon data: {pokemon_data}")
                return False

            # Check if in zone
            if not self._is_point_in_zone(latitude, longitude):
                return False

            # Check if in allowlist
            if not self._is_pokemon_in_allowlist(pokemon_id, form):
                return False

            # Send Discord notification
            pokemon_name = self.pokemon_names.get(pokemon_id, f"Pokemon {pokemon_id}")
            message = self._format_discord_message(pokemon_name, latitude, longitude)
            self._send_to_discord(message)

            logger.info(
                f"Sent alert: {pokemon_name} (form {form}) at {latitude},{longitude} "
                f"in zone '{self.zone}' / POI '{self.poi}'"
            )
            return True

        except Exception as e:
            logger.error(f"Error in check_and_notify: {e}", exc_info=True)
            return False

    def _start_bot_thread(self) -> None:
        """Start the bot in a separate daemon thread."""
        self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self.bot_thread.start()

    def _run_bot(self) -> None:
        """
        Run the Discord bot in its own event loop (executed in bot thread).
        """
        try:
            # Create new event loop for this thread
            self.bot_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.bot_loop)

            # Create Discord client
            intents = discord.Intents.default()
            self.discord_client = discord.Client(intents=intents)

            @self.discord_client.event
            async def on_ready():
                self.discord_connected = True
                self.state = "running"
                logger.info(f"Discord bot connected as {self.discord_client.user}")

            # Start the client (blocks until disconnect)
            token = get_loader().reload_configs()["discord"]["token"]
            self.bot_loop.run_until_complete(self.discord_client.start(token))

        except Exception as e:
            self.state = "error"
            self.error_msg = f"Bot thread error: {str(e)}"
            logger.error(self.error_msg, exc_info=True)
        finally:
            self.discord_connected = False
            if self.bot_loop:
                self.bot_loop.close()

    def _is_point_in_zone(self, latitude: float, longitude: float) -> bool:
        """
        Check if a point is within the active zone.
        
        Supports both 'box' type (bounding rectangle) and 'koji_area' type (S2 cells).
        """
        if not self.zone or self.zone not in self.zones:
            return False

        zone_config = self.zones[self.zone]
        zone_type = zone_config.get("type")

        if zone_type == "box":
            return self._is_point_in_box(latitude, longitude, zone_config)
        elif zone_type == "koji_area":
            return self._is_point_in_s2_cells(latitude, longitude)

        return False

    def _is_point_in_box(
        self, latitude: float, longitude: float, zone_config: Dict[str, Any]
    ) -> bool:
        """Check if point is within a bounding box."""
        min_bounds = zone_config.get("min", {})
        max_bounds = zone_config.get("max", {})

        min_lat = min_bounds.get("latitude")
        max_lat = max_bounds.get("latitude")
        min_lon = min_bounds.get("longitude")
        max_lon = max_bounds.get("longitude")

        if None in (min_lat, max_lat, min_lon, max_lon):
            return False

        return (
            min_lat <= latitude <= max_lat
            and min_lon <= longitude <= max_lon
        )

    def _is_point_in_s2_cells(self, latitude: float, longitude: float) -> bool:
        """Check if point's S2 cell is in the cached set."""
        try:
            lat_lng = LatLng.from_degrees(latitude, longitude)
            cell = Cell(CellId.from_lat_lng(lat_lng).parent(15))  # Level 15
            return cell.id().id() in self.s2_cells
        except Exception as e:
            logger.error(f"Error checking S2 cell: {e}")
            return False

    def _is_pokemon_in_allowlist(self, pokemon_id: int, form: int) -> bool:
        """Check if Pokemon ID+form is in the POI allowlist."""
        if not self.poi or self.poi not in self.pois:
            return False

        poi_config = self.pois[self.poi]
        pokemon_list = poi_config.get("pokemon", [])

        for entry in pokemon_list:
            if entry.get("id") == pokemon_id and entry.get("form") == form:
                return True

        return False

    def _format_discord_message(self, pokemon_name: str, latitude: float, longitude: float) -> str:
        """
        Create a Discord embed for a Pokemon alert.
        
        Returns:
            JSON-serialized Discord embed dict
        """
        gmaps_url = f"https://maps.google.com/?q={latitude},{longitude}"

        embed = {
            "title": f"🔴 {pokemon_name} Spotted in {self.zone}",
            "color": 16711680,  # Red
            "fields": [
                {
                    "name": "Location",
                    "value": f"[{latitude:.4f}, {longitude:.4f}]({gmaps_url})",
                    "inline": False,
                }
            ],
            "timestamp": None,  # Will be set by Discord
        }

        return embed

    def _send_to_discord(self, embed_dict: Dict[str, Any]) -> bool:
        """
        Send an embed to Discord asynchronously.
        
        Args:
            embed_dict: Embed data dict
            
        Returns:
            True if sent successfully
        """
        if not self.bot_loop or not self.discord_client or not self.channel_id:
            return False

        async def send():
            try:
                channel = self.discord_client.get_channel(self.channel_id)
                if not channel:
                    logger.error(f"Channel {self.channel_id} not found")
                    return False

                embed = discord.Embed.from_dict(embed_dict)
                await channel.send(embed=embed)
                return True
            except Exception as e:
                logger.error(f"Failed to send Discord message: {e}")
                return False

        try:
            future = asyncio.run_coroutine_threadsafe(send(), self.bot_loop)
            return future.result(timeout=5)
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return False

    def _fetch_s2_cells_from_koji(self, koji_instance: str) -> None:
        """
        Fetch S2 cells from Koji API for a koji_area zone.
        
        TODO: Implement actual Koji API call.
        For now, this is a stub that can be called but does nothing.
        """
        logger.info(f"TODO: Fetch S2 cells from Koji instance '{koji_instance}'")
        # Would call Koji API and populate self.s2_cells
        pass

    def _load_pokemon_names(self) -> None:
        """
        Load Pokemon ID -> name mapping from master file.
        
        TODO: Implement actual master file loading.
        For now, this is a stub with a few common Pokemon.
        """
        # Stub: minimal Pokemon name mapping
        self.pokemon_names = {
            1: "Bulbasaur",
            4: "Charmander",
            7: "Squirtle",
            25: "Pikachu",
            26: "Raichu",
            147: "Dratini",
            149: "Dragonite",
            # Add more as needed or load from master file
        }


# Global bot manager instance
_bot_manager: Optional[DiscordBotManager] = None


def get_bot_manager() -> DiscordBotManager:
    """Get or create the bot manager singleton."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = DiscordBotManager()
    return _bot_manager
