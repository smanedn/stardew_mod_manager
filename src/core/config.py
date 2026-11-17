"""Configuration management for Stardew Valley Mod Manager."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

DEFAULT_GAME_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley"

_INVALID_PROFILE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ProfileData(TypedDict):
    """Schema for a single modpack profile entry."""

    name: str
    enabled_mods: list[str]


class AppConfig(TypedDict):
    """Schema for the root SVMM configuration file."""

    game_path: str
    active_profile: str
    appearance_mode: str
    profiles: dict[str, ProfileData]


DEFAULT_CONFIG: AppConfig = {
    "game_path": DEFAULT_GAME_PATH,
    "active_profile": "Default",
    "appearance_mode": "dark",
    "profiles": {
        "Default": {
            "name": "Default",
            "enabled_mods": [],
        }
    },
}


def detect_game_path() -> str:
    """Return the first existing common Stardew Valley install path, or default."""
    if sys.platform == "win32":
        candidates = [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley"),
            Path(r"C:\Program Files\Steam\steamapps\common\Stardew Valley"),
            Path(r"D:\Steam\steamapps\common\Stardew Valley"),
            Path(r"D:\SteamLibrary\steamapps\common\Stardew Valley"),
            Path(r"C:\Program Files (x86)\GOG Galaxy\Games\Stardew Valley"),
        ]
    elif sys.platform == "darwin":
        home = Path.home()
        candidates = [
            home
            / "Library/Application Support/Steam/steamapps/common"
            / "Stardew Valley/Contents/MacOS",
        ]
    else:
        home = Path.home()
        candidates = [
            home / ".steam/steam/steamapps/common/Stardew Valley",
            home / ".local/share/Steam/steamapps/common/Stardew Valley",
        ]

    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return DEFAULT_GAME_PATH


def validate_profile_name(name: str) -> str:
    """Validate and normalize a profile name for safe use as a folder name."""
    clean = name.strip()
    if not clean:
        raise ValueError("Profile name cannot be empty.")
    if clean in (".", "..") or clean.endswith((".", " ")):
        raise ValueError("Profile name cannot end with a dot or space.")
    if _INVALID_PROFILE_CHARS_RE.search(clean):
        raise ValueError('Profile name contains invalid characters (< > : " / \\ | ? *).')
    return clean


class ConfigManager:
    """Loads, validates, and persists SVMM configuration in JSON format."""

    def __init__(self, config_path: str | Path = Path("SVMM_Data") / "config.json") -> None:
        self.config_path = Path(config_path)
        self.data: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Load configuration from disk, creating defaults if missing or invalid."""
        if not self.config_path.exists():
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.data["game_path"] = detect_game_path()
            self.save()
            return self.data

        try:
            raw_text = self.config_path.read_text(encoding="utf-8")
            loaded = json.loads(raw_text)
            if not isinstance(loaded, dict):
                raise ValueError("Configuration root must be a JSON object.")
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.data["game_path"] = detect_game_path()
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

    def _normalize_config(self, raw: dict[str, Any]) -> AppConfig:
        """Ensure required top-level keys and at least one valid profile exist."""
        normalized: AppConfig = copy.deepcopy(DEFAULT_CONFIG)

        if isinstance(raw.get("game_path"), str):
            normalized["game_path"] = raw["game_path"]

        mode = raw.get("appearance_mode")
        if isinstance(mode, str) and mode.lower() in ("dark", "light", "system"):
            normalized["appearance_mode"] = mode.lower()

        raw_profiles = raw.get("profiles")
        if isinstance(raw_profiles, dict) and raw_profiles:
            profiles: dict[str, ProfileData] = {}
            for profile_id, profile_data in raw_profiles.items():
                if not isinstance(profile_id, str) or not isinstance(profile_data, dict):
                    continue
                name = profile_data.get("name")
                enabled_mods = profile_data.get("enabled_mods")
                profiles[profile_id] = {
                    "name": name if isinstance(name, str) and name.strip() else profile_id,
                    "enabled_mods": [m for m in enabled_mods if isinstance(m, str)]
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
    def appearance_mode(self) -> str:
        """Return the configured UI appearance mode ('dark', 'light', or 'system')."""
        return str(self.data.get("appearance_mode", "dark"))

    @appearance_mode.setter
    def appearance_mode(self, mode: str) -> None:
        clean = mode.lower()
        if clean not in ("dark", "light", "system"):
            raise ValueError(f"Unsupported appearance mode: {mode}")
        self.data["appearance_mode"] = clean
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
    def profiles(self) -> dict[str, ProfileData]:
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

    def create_profile(self, profile_id: str, display_name: str | None = None) -> str:
        """Validate, create a new profile, save configuration, and return its ID."""
        clean_id = validate_profile_name(profile_id)
        if clean_id in self.profiles:
            raise ValueError(f"Profile '{clean_id}' already exists.")
        self.profiles[clean_id] = {
            "name": display_name.strip() if display_name and display_name.strip() else clean_id,
            "enabled_mods": [],
        }
        self.save()
        return clean_id

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

    def export_profile(self, export_path: str | Path, profile_id: str | None = None) -> None:
        """Export a profile's metadata and enabled mod list to a JSON file."""
        pid = profile_id or self.active_profile
        if pid not in self.profiles:
            raise KeyError(f"Profile '{pid}' does not exist.")
        payload = {
            "profile_id": pid,
            "name": self.profiles[pid]["name"],
            "enabled_mods": self.get_enabled_mods(pid),
        }
        Path(export_path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def import_profile(self, import_path: str | Path) -> str:
        """Import a profile JSON file and return the created profile ID."""
        raw = json.loads(Path(import_path).read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("Imported profile must be a JSON object.")

        base_name = str(raw.get("profile_id") or raw.get("name") or "Imported").strip()
        clean_base = validate_profile_name(base_name)
        candidate = clean_base
        idx = 1
        while candidate in self.profiles:
            candidate = f"{clean_base}_{idx}"
            idx += 1

        display_name = str(raw.get("name") or candidate).strip() or candidate
        enabled_raw = raw.get("enabled_mods", [])
        enabled_mods = (
            [m for m in enabled_raw if isinstance(m, str)] if isinstance(enabled_raw, list) else []
        )
        self.create_profile(candidate, display_name)
        self.set_enabled_mods(enabled_mods, candidate)
        return candidate
