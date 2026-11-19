"""Save and restore mod config.json snapshots per modpack profile."""

from __future__ import annotations

import shutil
from pathlib import Path


def save_config_preset(modpack_dir: Path, preset_dir: Path) -> int:
    """Snapshot all mod config.json files from modpack_dir into preset_dir."""
    if not modpack_dir.is_dir():
        return 0
    if preset_dir.exists():
        shutil.rmtree(preset_dir, ignore_errors=True)
    preset_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for child in sorted(modpack_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        cfg = child / "config.json"
        if cfg.is_file():
            dest_dir = preset_dir / child.name
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cfg, dest_dir / "config.json")
            count += 1
    return count


def restore_config_preset(modpack_dir: Path, preset_dir: Path) -> int:
    """Restore saved mod config.json files from preset_dir into matching installed mods."""
    if not modpack_dir.is_dir() or not preset_dir.is_dir():
        return 0

    count = 0
    for child in sorted(preset_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        saved_cfg = child / "config.json"
        target_mod_dir = modpack_dir / child.name
        if saved_cfg.is_file() and target_mod_dir.is_dir():
            shutil.copy2(saved_cfg, target_mod_dir / "config.json")
            count += 1
    return count
