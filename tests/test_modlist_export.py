from __future__ import annotations

import json
from pathlib import Path

from src.core.mod_scanner import ModInfo
from src.core.modlist_export import (
    build_modlist_json,
    build_modlist_markdown,
    export_modlist,
    update_key_to_url,
)


def test_update_key_to_url() -> None:
    assert (
        update_key_to_url("Nexus:1915@ContentPatcher")
        == "https://www.nexusmods.com/stardewvalley/mods/1915"
    )
    assert update_key_to_url("GitHub:Pathoschild/LookupAnything") == (
        "https://github.com/Pathoschild/LookupAnything"
    )
    assert update_key_to_url("ModDrop:123") is None


def test_export_modlist_markdown_and_json(tmp_path: Path) -> None:
    mods = [
        ModInfo(
            folder_name="CP",
            name="Content Patcher",
            version="2.0.0",
            path=tmp_path / "CP",
            unique_id="Pathoschild.ContentPatcher",
            author="Pathoschild",
            update_keys=("Nexus:1915", "GitHub:Pathoschild/StardewMods"),
        ),
        ModInfo(
            folder_name="DisabledMod",
            name="Disabled Mod",
            version="1.0.0",
            path=tmp_path / "DisabledMod",
        ),
    ]

    md = build_modlist_markdown("CoopPack", mods, {"CP"})
    assert "# Stardew Valley Modlist — CoopPack" in md
    assert "Content Patcher" in md
    assert "https://www.nexusmods.com/stardewvalley/mods/1915" in md
    assert "Disabled Mod" not in md

    raw_json = build_modlist_json("CoopPack", mods, {"CP"})
    parsed = json.loads(raw_json)
    assert parsed["profile"] == "CoopPack"
    assert parsed["count"] == 1
    assert parsed["mods"][0]["unique_id"] == "Pathoschild.ContentPatcher"

    md_file = tmp_path / "list.md"
    json_file = tmp_path / "list.json"
    export_modlist(md_file, "CoopPack", mods, {"CP"})
    export_modlist(json_file, "CoopPack", mods, {"CP"})
    assert "Content Patcher" in md_file.read_text(encoding="utf-8")
    assert json.loads(json_file.read_text(encoding="utf-8"))["count"] == 1
