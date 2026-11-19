from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.mod_icons import (
    extract_nexus_mod_id,
    find_local_mod_icon,
    load_mod_icon,
)
from src.core.mod_scanner import ModInfo


def test_extract_nexus_mod_id() -> None:
    mod = ModInfo(
        folder_name="CJBCheats",
        name="CJB Cheats Menu",
        version="1.42.0",
        path=Path("CJBCheats"),
        update_keys=("GitHub:CJBok/SDV-Mods", "Nexus:4"),
    )
    assert extract_nexus_mod_id(mod) == "4"


def test_load_mod_icon_uses_local_icon_or_monogram_fallback(tmp_path: Path) -> None:
    mod_dir = tmp_path / "SampleMod"
    mod_dir.mkdir()
    cache_dir = tmp_path / "cache"
    mod = ModInfo(
        folder_name="SampleMod",
        name="Sample Mod",
        version="1.0.0",
        path=mod_dir,
        unique_id="Author.SampleMod",
    )

    # Monogram fallback when no local/cached image exists
    fallback = load_mod_icon(mod, cache_dir, size=64)
    assert fallback.size == (64, 64)
    assert fallback.mode == "RGBA"

    # Local icon.png takes priority
    local_icon = mod_dir / "icon.png"
    Image.new("RGB", (120, 80), color=(20, 120, 220)).save(local_icon)
    assert find_local_mod_icon(mod) == local_icon

    loaded = load_mod_icon(mod, cache_dir, size=64)
    assert loaded.size == (64, 64)
    assert loaded.mode == "RGBA"
