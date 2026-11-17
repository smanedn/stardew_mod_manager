"""Game launcher for SMAPI (modded) and Vanilla Stardew Valley."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def launch_game(game_path: str, modded: bool) -> tuple[bool, str]:
    """Launch Stardew Valley via SMAPI (modded=True) or base game (modded=False)."""
    game_dir = Path(game_path)
    if not game_dir.is_dir():
        return False, f"Stardew Valley folder not found: {game_dir}"

    if modded:
        exe_name = "StardewModdingAPI.exe" if sys.platform == "win32" else "StardewModdingAPI"
        label = "SMAPI (Modded)"
    else:
        exe_name = "Stardew Valley.exe" if sys.platform == "win32" else "StardewValley"
        label = "Vanilla"

    exe_path = game_dir / exe_name
    if not exe_path.is_file():
        return False, f"Could not find {exe_name} in {game_dir}"

    try:
        subprocess.Popen([str(exe_path)], cwd=str(game_dir))
    except OSError as exc:
        return False, f"Failed to launch {label}: {exc}"

    return True, f"Launched {label} ({exe_name})."
