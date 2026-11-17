"""Game launcher for SMAPI (modded) and Vanilla Stardew Valley."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _executable_names() -> tuple[str, str]:
    """Return (vanilla_exe, smapi_exe) for the current platform."""
    if sys.platform == "win32":
        return "Stardew Valley.exe", "StardewModdingAPI.exe"
    return "StardewValley", "StardewModdingAPI"


def validate_game_path(game_path: str | Path) -> tuple[bool, bool, str]:
    """Check whether Vanilla and SMAPI executables exist in game_path."""
    game_dir = Path(game_path)
    if not str(game_path).strip() or not game_dir.is_dir():
        return False, False, "Folder not found"

    vanilla_exe, smapi_exe = _executable_names()
    has_vanilla = (game_dir / vanilla_exe).is_file()
    has_smapi = (game_dir / smapi_exe).is_file()

    if has_vanilla and has_smapi:
        return True, True, "SMAPI + Vanilla ready"
    if has_vanilla:
        return True, False, "Vanilla ready (SMAPI missing)"
    if has_smapi:
        return False, True, "SMAPI ready (Vanilla exe missing)"
    return False, False, "No game executables found"


def get_smapi_log_path() -> Path | None:
    """Return the path to SMAPI-latest.txt if it exists on this system."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"

    log_path = base / "StardewValley" / "ErrorLogs" / "SMAPI-latest.txt"
    return log_path if log_path.is_file() else None


def launch_game(game_path: str, modded: bool) -> tuple[bool, str]:
    """Launch Stardew Valley via SMAPI (modded=True) or base game (modded=False)."""
    game_dir = Path(game_path)
    if not game_dir.is_dir():
        return False, f"Stardew Valley folder not found: {game_dir}"

    vanilla_exe, smapi_exe = _executable_names()
    exe_name = smapi_exe if modded else vanilla_exe
    label = "SMAPI (Modded)" if modded else "Vanilla"

    exe_path = game_dir / exe_name
    if not exe_path.is_file():
        return False, f"Could not find {exe_name} in {game_dir}"

    try:
        subprocess.Popen([str(exe_path)], cwd=str(game_dir))
    except OSError as exc:
        return False, f"Failed to launch {label}: {exc}"

    return True, f"Launched {label} ({exe_name})."
