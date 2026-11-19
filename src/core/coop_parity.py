"""Compare local enabled mods against a friend's exported .json modlist for co-op parity."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.core.mod_scanner import ModInfo


@dataclass(frozen=True)
class FriendModEntry:
    """Single mod entry loaded from a friend's exported modlist JSON."""

    name: str
    version: str
    unique_id: str = ""
    folder: str = ""
    links: tuple[str, ...] = ()


@dataclass(frozen=True)
class VersionMismatch:
    """Represents a mod present in both modlists with differing versions."""

    name: str
    unique_id: str
    local_version: str
    friend_version: str


@dataclass(frozen=True)
class MissingModItem:
    """A mod from the friend's list that is not currently enabled locally."""

    entry: FriendModEntry
    local_folder_if_installed: str = ""


@dataclass(frozen=True)
class CoopParityReport:
    """Diff report between the local active modpack and a friend's modlist."""

    friend_profile: str
    missing_mods: list[MissingModItem]
    extra_mods: list[ModInfo]
    version_mismatches: list[VersionMismatch]
    matching_count: int

    @property
    def is_in_sync(self) -> bool:
        return not (self.missing_mods or self.extra_mods or self.version_mismatches)


def load_friend_modlist(json_path: str | Path) -> tuple[str, list[FriendModEntry]]:
    """Load a friend's exported modlist JSON and return (profile_name, entries)."""
    raw_text = Path(json_path).read_text(encoding="utf-8-sig")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid modlist JSON: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("mods"), list):
        raise ValueError("Expected an exported SVMM modlist JSON with a 'mods' list.")

    profile_name = str(data.get("profile") or Path(json_path).stem).strip() or "Friend"
    entries: list[FriendModEntry] = []
    for item in data["mods"]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("folder") or "").strip()
        if not name:
            continue
        links_raw = item.get("links", [])
        links = (
            tuple(str(u).strip() for u in links_raw if isinstance(u, str) and u.strip())
            if isinstance(links_raw, list)
            else ()
        )
        entries.append(
            FriendModEntry(
                name=name,
                version=str(item.get("version") or "Unknown").strip(),
                unique_id=str(item.get("unique_id") or "").strip(),
                folder=str(item.get("folder") or "").strip(),
                links=links,
            )
        )
    return profile_name, entries


def _mod_match_key(unique_id: str, folder: str, name: str) -> str:
    if unique_id.strip():
        return f"id:{unique_id.strip().lower()}"
    if folder.strip():
        return f"folder:{folder.strip().lower()}"
    return f"name:{name.strip().lower()}"


def compare_with_friend_modlist(
    friend_profile: str,
    friend_mods: list[FriendModEntry],
    local_mods: list[ModInfo],
    enabled_folders: set[str],
) -> CoopParityReport:
    """Compare local enabled mods against a friend's modlist."""
    all_local_by_key: dict[str, ModInfo] = {}
    enabled_by_key: dict[str, ModInfo] = {}

    for mod in local_mods:
        key = _mod_match_key(mod.unique_id, mod.folder_name, mod.name)
        all_local_by_key.setdefault(key, mod)
        if mod.folder_name in enabled_folders:
            enabled_by_key.setdefault(key, mod)

    missing: list[MissingModItem] = []
    mismatches: list[VersionMismatch] = []
    matched_local_keys: set[str] = set()
    matching_count = 0

    for f_mod in friend_mods:
        key = _mod_match_key(f_mod.unique_id, f_mod.folder, f_mod.name)
        local_enabled = enabled_by_key.get(key)
        if local_enabled is None:
            installed_local = all_local_by_key.get(key)
            missing.append(
                MissingModItem(
                    entry=f_mod,
                    local_folder_if_installed=(
                        installed_local.folder_name if installed_local else ""
                    ),
                )
            )
            continue

        matched_local_keys.add(key)
        if local_enabled.version.strip().lower() != f_mod.version.strip().lower():
            mismatches.append(
                VersionMismatch(
                    name=local_enabled.name,
                    unique_id=local_enabled.unique_id or f_mod.unique_id,
                    local_version=local_enabled.version,
                    friend_version=f_mod.version,
                )
            )
        else:
            matching_count += 1

    extra_mods = [
        mod
        for mod in local_mods
        if mod.folder_name in enabled_folders
        and _mod_match_key(mod.unique_id, mod.folder_name, mod.name) not in matched_local_keys
    ]

    return CoopParityReport(
        friend_profile=friend_profile,
        missing_mods=missing,
        extra_mods=extra_mods,
        version_mismatches=mismatches,
        matching_count=matching_count,
    )
