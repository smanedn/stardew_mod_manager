"""Configuration management for Stardew Valley Mod Manager."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

DEFAULT_GAME_PATH = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley"
)

DEFAULT_CONFIG: dict[str, Any] = {
    "game_path": DEFAULT_GAME_PATH,
    "active_profile": "Default",
    "profiles": {
        "Default": {
            "name": "Default",
            "enabled_mods": [],
        }
    },
}


class ConfigManager:
    """Loads, validates, and persists SVMM configuration in JSON format."""

    def __init__(self, config_path: str | Path = Path("SVMM_Data") / "config.json") -> None:
        self.config_path = Path(config_path)
        self.data: dict[str, Any] = self.load()

    def load(self) -> dict[str, Any]:
        """Load configuration from disk, creating defaults if missing or invalid."""
        if not self.config_path.exists():
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.data

        try:
            raw_text = self.config_path.read_text(encoding="utf-8")
            loaded = json.loads(raw_text)
            if not isinstance(loaded, dict):
                raise ValueError("Configuration root must be a JSON object.")
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.data

        self.data = self._normalize_config(loaded)
        return self.data

    def save(self) -> None:
        """Persist the current configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _normalize_config(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Ensure required top-level keys and at least one valid profile exist."""
        normalized = copy.deepcopy(DEFAULT_CONFIG)

        if isinstance(raw.get("game_path"), str):
            normalized["game_path"] = raw["game_path"]

        raw_profiles = raw.get("profiles")
        if isinstance(raw_profiles, dict) and raw_profiles:
            profiles: dict[str, dict[str, Any]] = {}
            for profile_id, profile_data in raw_profiles.items():
                if not isinstance(profile_id, str) or not isinstance(profile_data, dict):
                    continue
                name = profile_data.get("name")
                enabled_mods = profile_data.get("enabled_mods")
                profiles[profile_id] = {
                    "name": name if isinstance(name, str) and name.strip() else profile_id,
                    "enabled_mods": [
                        m for m in enabled_mods if isinstance(m, str)
                    ]
                    if isinstance(enabled_mods, list)
                    else [],
                }
            if profiles:
                normalized["profiles"] = profiles

        active_profile = raw.get("active_profile")
        if isinstance(active_profile, str) and active_profile in normalized["profiles"]:
            normalized["active_profile"] = active_profile
        else:
            normalized["active_profile"] = next(iter(normalized["profiles"]))

        return normalized

    @property
    def game_path(self) -> str:
        """Return the configured Stardew Valley installation path."""
        return str(self.data.get("game_path", DEFAULT_GAME_PATH))

    @game_path.setter
    def game_path(self, path: str | Path) -> None:
        self.data["game_path"] = str(path)
        self.save()

    @property
    def active_profile(self) -> str:
        """Return the active profile ID."""
        return str(self.data["active_profile"])

    @active_profile.setter
    def active_profile(self, profile_id: str) -> None:
        if profile_id not in self.data["profiles"]:
            raise KeyError(f"Profile '{profile_id}' does not exist.")
        self.data["active_profile"] = profile_id
        self.save()

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        """Return the mapping of profile IDs to profile data."""
        return self.data["profiles"]

    def get_enabled_mods(self, profile_id: str | None = None) -> list[str]:
        """Return enabled mod folder names for the given or active profile."""
        pid = profile_id or self.active_profile
        profile = self.profiles.get(pid)
        if profile is None:
            return []
        return list(profile.get("enabled_mods", []))

    def set_enabled_mods(self, mods: list[str], profile_id: str | None = None) -> None:
        """Update enabled mod folder names for the given or active profile."""
        pid = profile_id or self.active_profile
        if pid not in self.profiles:
            raise KeyError(f"Profile '{pid}' does not exist.")
        self.profiles[pid]["enabled_mods"] = list(dict.fromkeys(mods))
        self.save()

    def create_profile(self, profile_id: str, display_name: str | None = None) -> None:
        """Create a new profile and save the configuration."""
        clean_id = profile_id.strip()
        if not clean_id:
            raise ValueError("Profile ID cannot be empty.")
        if clean_id in self.profiles:
            raise ValueError(f"Profile '{clean_id}' already exists.")
        self.profiles[clean_id] = {
            "name": display_name.strip() if display_name and display_name.strip() else clean_id,
            "enabled_mods": [],
        }
        self.save()

    def delete_profile(self, profile_id: str) -> None:
        """Delete a profile, ensuring at least one profile always remains."""
        if profile_id not in self.profiles:
            raise KeyError(f"Profile '{profile_id}' does not exist.")
        if len(self.profiles) <= 1:
            raise ValueError("Cannot delete the last remaining profile.")
        del self.profiles[profile_id]
        if self.active_profile == profile_id:
            self.data["active_profile"] = next(iter(self.profiles))
        self.save()
