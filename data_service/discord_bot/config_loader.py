"""
Discord Bot Configuration Loader

Loads and validates zones, POIs, and Discord credentials from JSON config files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates Discord bot configuration from JSON files."""

    def __init__(self, config_dir: Path = None):
        """
        Initialize config loader.
        
        Args:
            config_dir: Path to directory containing config files.
                       Defaults to the data_service directory.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent
        self.config_dir = Path(config_dir)

    def reload_configs(self) -> Dict[str, Any]:
        """
        Reload all configuration files from disk.
        
        Returns:
            Dict with keys: zones, pois, discord, channels
            
        Raises:
            FileNotFoundError: If required config files are missing
            ValueError: If config validation fails
        """
        zones = self._load_zones()
        pois = self._load_pois()
        discord_config = self._load_discord_config()

        # Extract channels dict for easy access
        channels = discord_config.get("channels", {})

        return {
            "zones": zones,
            "pois": pois,
            "discord": discord_config,
            "channels": channels,
        }

    def _load_zones(self) -> Dict[str, Dict[str, Any]]:
        """
        Load zones.json configuration.
        
        Expected format:
        {
          "zone_name": {
            "type": "box" or "koji_area",
            "min": {"latitude": ..., "longitude": ...},  // for box type
            "max": {"latitude": ..., "longitude": ...},  // for box type
            "koji_instance": "..."  // for koji_area type
          }
        }
        
        Returns:
            Dict of zone configurations
            
        Raises:
            FileNotFoundError: If zones.json is missing
            ValueError: If validation fails
        """
        zones_file = self.config_dir / "zones.json"
        
        if not zones_file.exists():
            raise FileNotFoundError(f"zones.json not found at {zones_file}")

        try:
            with open(zones_file, "r") as f:
                zones = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"zones.json is invalid JSON: {e}")

        # Validate zones
        for zone_name, zone_config in zones.items():
            self._validate_zone(zone_name, zone_config)

        logger.info(f"Loaded {len(zones)} zone(s)")
        return zones

    def _validate_zone(self, zone_name: str, zone_config: Dict[str, Any]) -> None:
        """Validate a single zone configuration."""
        zone_type = zone_config.get("type")

        if zone_type not in ("box", "koji_area"):
            raise ValueError(f"Zone '{zone_name}': invalid type '{zone_type}' (must be 'box' or 'koji_area')")

        if zone_type == "box":
            if "min" not in zone_config or "max" not in zone_config:
                raise ValueError(f"Zone '{zone_name}': box type requires 'min' and 'max' keys")

            for key in ("min", "max"):
                bounds = zone_config[key]
                if not isinstance(bounds, dict) or "latitude" not in bounds or "longitude" not in bounds:
                    raise ValueError(f"Zone '{zone_name}': {key} must have 'latitude' and 'longitude' keys")

                lat = bounds["latitude"]
                lon = bounds["longitude"]
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                    raise ValueError(f"Zone '{zone_name}': {key} coordinates must be numeric")

                if lat < -90 or lat > 90:
                    raise ValueError(f"Zone '{zone_name}': {key} latitude {lat} out of range [-90, 90]")
                if lon < -180 or lon > 180:
                    raise ValueError(f"Zone '{zone_name}': {key} longitude {lon} out of range [-180, 180]")

        elif zone_type == "koji_area":
            if "koji_instance" not in zone_config:
                raise ValueError(f"Zone '{zone_name}': koji_area type requires 'koji_instance' key")

    def _load_pois(self) -> Dict[str, Dict[str, Any]]:
        """
        Load pois.json configuration.
        
        Expected format:
        {
          "poi_name": {
            "pokemon": [
              {"id": 147, "form": 190},
              ...
            ]
          }
        }
        
        Returns:
            Dict of POI configurations
            
        Raises:
            FileNotFoundError: If pois.json is missing
            ValueError: If validation fails
        """
        pois_file = self.config_dir / "pois.json"
        
        if not pois_file.exists():
            raise FileNotFoundError(f"pois.json not found at {pois_file}")

        try:
            with open(pois_file, "r") as f:
                pois = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"pois.json is invalid JSON: {e}")

        # Validate POIs
        for poi_name, poi_config in pois.items():
            self._validate_poi(poi_name, poi_config)

        logger.info(f"Loaded {len(pois)} POI set(s)")
        return pois

    def _validate_poi(self, poi_name: str, poi_config: Dict[str, Any]) -> None:
        """Validate a single POI configuration."""
        if "pokemon" not in poi_config:
            raise ValueError(f"POI '{poi_name}': missing 'pokemon' array")

        pokemon_list = poi_config["pokemon"]
        if not isinstance(pokemon_list, list):
            raise ValueError(f"POI '{poi_name}': 'pokemon' must be an array")

        for i, entry in enumerate(pokemon_list):
            if not isinstance(entry, dict):
                raise ValueError(f"POI '{poi_name}': pokemon[{i}] must be an object")

            if "id" not in entry or "form" not in entry:
                raise ValueError(
                    f"POI '{poi_name}': pokemon[{i}] must have 'id' and 'form' keys"
                )

            pok_id = entry["id"]
            form = entry["form"]
            if not isinstance(pok_id, int) or not isinstance(form, int):
                raise ValueError(
                    f"POI '{poi_name}': pokemon[{i}] id={pok_id} and form={form} must be integers"
                )

    def _load_discord_config(self) -> Dict[str, Any]:
        """
        Load discord.json configuration.
        
        Expected format:
        {
          "token": "your_bot_token",
          "channels": {
            "channel_name": "123456789",
            ...
          }
        }
        
        Returns:
            Dict with token and channels
            
        Raises:
            FileNotFoundError: If discord.json is missing
            ValueError: If validation fails
        """
        discord_file = self.config_dir / "discord.json"
        
        if not discord_file.exists():
            raise FileNotFoundError(f"discord.json not found at {discord_file}")

        try:
            with open(discord_file, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"discord.json is invalid JSON: {e}")

        # Validate
        if "token" not in config:
            raise ValueError("discord.json: missing 'token' key")

        if "channels" not in config:
            raise ValueError("discord.json: missing 'channels' dict")

        channels = config["channels"]
        if not isinstance(channels, dict):
            raise ValueError("discord.json: 'channels' must be a dict")

        #for channel_name, channel_id in channels.items():
        #    if not isinstance(channel_id, int):
        #        raise ValueError(
        #            f"discord.json: channels.{channel_name} must be an integer channel ID"
        #        )

        logger.info("Loaded Discord config with %s channel(s)", len(channels))
        return config


# Singleton instance
_loader = None


def get_loader(config_dir: Path = None) -> ConfigLoader:
    """Get or create the config loader singleton."""
    global _loader
    if _loader is None:
        _loader = ConfigLoader(config_dir)
    return _loader


def reload_configs() -> Dict[str, Any]:
    """Reload all configurations from disk."""
    return get_loader().reload_configs()
