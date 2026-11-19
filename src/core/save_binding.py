"""Scan Stardew Valley farm saves and bind them to modpack profiles."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from src.core.save_backup import get_default_saves_dir


@dataclass(frozen=True)
class FarmSaveInfo:
    """Metadata for a Stardew Valley farm save folder."""

    folder_name: str
    farm_name: str
    farmer_name: str
    path: Path

    @property
    def display_label(self) -> str:
        if self.farmer_name:
            return f"{self.farm_name} Farm ({self.farmer_name})"
        return self.farm_name


def _parse_save_game_info(save_dir: Path) -> tuple[str, str]:
    info_file = save_dir / "SaveGameInfo"
    fallback_farm = save_dir.name.rsplit("_", 1)[0] or save_dir.name
    if not info_file.is_file():
        return fallback_farm, ""

    try:
        tree = ET.parse(info_file)
        root = tree.getroot()
        farm_el = root.find("farmName")
        farmer_el = root.find("name")
        farm_name = (farm_el.text or "").strip() if farm_el is not None else ""
        farmer_name = (farmer_el.text or "").strip() if farmer_el is not None else ""
        return farm_name or fallback_farm, farmer_name
    except (OSError, ET.ParseError):
        return fallback_farm, ""


def list_farm_saves(saves_dir: str | Path | None = None) -> list[FarmSaveInfo]:
    """Scan the Stardew Valley Saves directory and return discovered farm saves."""
    root = Path(saves_dir) if saves_dir is not None else get_default_saves_dir()
    if not root.is_dir():
        return []

    farms: list[FarmSaveInfo] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        farm_name, farmer_name = _parse_save_game_info(entry)
        farms.append(
            FarmSaveInfo(
                folder_name=entry.name,
                farm_name=farm_name,
                farmer_name=farmer_name,
                path=entry,
            )
        )
    farms.sort(key=lambda f: f.farm_name.lower())
    return farms
