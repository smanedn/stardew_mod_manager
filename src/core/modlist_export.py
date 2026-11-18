"""Export shareable multiplayer modlists in Markdown or JSON format."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.mod_scanner import ModInfo


def update_key_to_url(update_key: str) -> str | None:
    """Convert a SMAPI UpdateKey (Nexus/GitHub) to a clickable URL if supported."""
    clean = update_key.strip()
    lower = clean.lower()
    if lower.startswith("nexus:"):
        mod_id = clean.split(":", 1)[1].split("@", 1)[0].strip()
        if mod_id.isdigit():
            return f"https://www.nexusmods.com/stardewvalley/mods/{mod_id}"
    elif lower.startswith("github:"):
        repo = clean.split(":", 1)[1].strip()
        if "/" in repo:
            return f"https://github.com/{repo}"
    return None


def _mod_links(mod: ModInfo) -> list[str]:
    links: list[str] = []
    for key in mod.update_keys:
        url = update_key_to_url(key)
        if url and url not in links:
            links.append(url)
    return links


def build_modlist_markdown(
    profile_name: str, mods: list[ModInfo], enabled_folders: set[str]
) -> str:
    """Generate a Markdown modlist table for sharing with multiplayer friends."""
    enabled = [m for m in mods if m.folder_name in enabled_folders]
    lines = [
        f"# Stardew Valley Modlist — {profile_name}",
        "",
        f"Enabled mods: **{len(enabled)}**",
        "",
        "| Mod | Version | Author | Link |",
        "| --- | --- | --- | --- |",
    ]
    for mod in enabled:
        links = _mod_links(mod)
        link_md = f"[Download]({links[0]})" if links else "—"
        author = mod.author or "—"
        lines.append(f"| {mod.name} | v{mod.version} | {author} | {link_md} |")
    lines.append("")
    return "\n".join(lines)


def build_modlist_json(profile_name: str, mods: list[ModInfo], enabled_folders: set[str]) -> str:
    """Generate a structured JSON modlist for sharing with multiplayer friends."""
    enabled = [m for m in mods if m.folder_name in enabled_folders]
    payload = {
        "profile": profile_name,
        "count": len(enabled),
        "mods": [
            {
                "name": mod.name,
                "version": mod.version,
                "author": mod.author,
                "unique_id": mod.unique_id,
                "folder": mod.folder_name,
                "links": _mod_links(mod),
            }
            for mod in enabled
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def export_modlist(
    dest_path: str | Path,
    profile_name: str,
    mods: list[ModInfo],
    enabled_folders: set[str],
) -> None:
    """Write a shareable modlist (.md or .json) to dest_path."""
    out = Path(dest_path)
    if out.suffix.lower() == ".json":
        content = build_modlist_json(profile_name, mods, enabled_folders)
    else:
        content = build_modlist_markdown(profile_name, mods, enabled_folders)
    out.write_text(content, encoding="utf-8")
