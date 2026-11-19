"""Content Patcher content.json Target scanner for pre-launch asset conflict detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.core.mod_scanner import ModInfo, _strip_json_comments_and_trailing_commas


@dataclass(frozen=True)
class AssetConflict:
    """Represents a game asset target modified by two or more enabled mods."""

    target: str
    mods: tuple[ModInfo, ...]


def extract_content_patcher_targets(mod_path: Path) -> dict[str, str]:
    """Return {normalized_target: display_target} from a mod's content.json."""
    content_file = mod_path / "content.json"
    if not content_file.is_file():
        return {}

    try:
        raw_text = content_file.read_text(encoding="utf-8-sig")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            data = json.loads(_strip_json_comments_and_trailing_commas(raw_text))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    changes = data.get("Changes")
    if not isinstance(changes, list):
        return {}

    targets: dict[str, str] = {}
    for change in changes:
        if not isinstance(change, dict):
            continue
        raw_target = change.get("Target")
        if not isinstance(raw_target, str) or not raw_target.strip():
            continue
        for part in raw_target.split(","):
            display = part.strip().replace("\\", "/")
            if display:
                targets.setdefault(display.lower(), display)
    return targets


def detect_asset_conflicts(mods: list[ModInfo], enabled_folders: set[str]) -> list[AssetConflict]:
    """Find Content Patcher Target assets edited by 2+ enabled mods."""
    target_to_mods: dict[str, list[ModInfo]] = {}
    display_names: dict[str, str] = {}

    for mod in mods:
        if mod.folder_name not in enabled_folders:
            continue
        targets = extract_content_patcher_targets(mod.path)
        for norm, display in targets.items():
            display_names.setdefault(norm, display)
            target_to_mods.setdefault(norm, []).append(mod)

    conflicts: list[AssetConflict] = []
    for norm in sorted(target_to_mods):
        group = target_to_mods[norm]
        if len(group) > 1:
            conflicts.append(AssetConflict(target=display_names[norm], mods=tuple(group)))
    return conflicts


def format_asset_conflicts(conflicts: list[AssetConflict], max_items: int = 12) -> str:
    """Format a concise summary of Content Patcher asset conflicts."""
    lines: list[str] = []
    for conflict in conflicts[:max_items]:
        mod_names = ", ".join(m.name for m in conflict.mods)
        lines.append(f"• {conflict.target}: {mod_names}")
    if len(conflicts) > max_items:
        lines.append(f"• ...and {len(conflicts) - max_items} more conflict(s)")
    return "\n".join(lines)
