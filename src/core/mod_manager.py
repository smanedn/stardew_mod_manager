"""Profile directory syncing and Stardew Valley Mods junction/symlink manager."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _is_link_or_junction(path: Path) -> bool:
    """Return True if path is a symlink or a Windows directory junction."""
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        return bool(is_junction())
    return False


def _remove_link_or_junction(path: Path) -> None:
    """Remove a symlink or directory junction without touching target contents."""
    if path.is_symlink():
        path.unlink()
    elif _is_link_or_junction(path):
        os.rmdir(path)


def _create_dir_link(link_path: Path, target_path: Path) -> None:
    """Create a directory junction on Windows or symlink on POSIX."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout).strip() or "mklink /J failed"
            raise OSError(f"Failed to create junction '{link_path}' -> '{target_path}': {error_msg}")
    else:
        os.symlink(target_path, link_path, target_is_directory=True)


def sync_profile(
    profile_id: str,
    enabled_mods: list[str],
    mod_pool_path: str | Path = Path("SVMM_Data") / "mod_pool",
    profiles_root: str | Path = Path("SVMM_Data") / "profiles",
) -> Path:
    """Rebuild a profile's directory with links to its enabled mods in mod_pool."""
    pool_dir = Path(mod_pool_path).resolve()
    profile_dir = (Path(profiles_root) / profile_id).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing links or stale entries in the profile folder
    for entry in list(profile_dir.iterdir()):
        if _is_link_or_junction(entry):
            _remove_link_or_junction(entry)
        elif entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()

    for mod_folder in enabled_mods:
        target = pool_dir / mod_folder
        if not target.is_dir():
            continue
        link = profile_dir / mod_folder
        _create_dir_link(link, target)

    return profile_dir


def link_game_mods(game_path: str | Path, profile_dir: str | Path) -> tuple[bool, str]:
    """Point <game_path>/Mods to <profile_dir>, backing up any unmanaged Mods folder."""
    game_dir = Path(game_path)
    if not game_dir.is_dir():
        return False, f"Game folder not found: {game_dir}"

    target_profile = Path(profile_dir).resolve()
    if not target_profile.is_dir():
        return False, f"Profile folder not found: {target_profile}"

    mods_path = game_dir / "Mods"
    backup_msg = ""

    if _is_link_or_junction(mods_path):
        _remove_link_or_junction(mods_path)
    elif mods_path.exists():
        backup_path = game_dir / "Mods_Backup"
        if backup_path.exists():
            idx = 1
            while (game_dir / f"Mods_Backup_{idx}").exists():
                idx += 1
            backup_path = game_dir / f"Mods_Backup_{idx}"
        mods_path.rename(backup_path)
        backup_msg = f" (backed up existing Mods to {backup_path.name})"

    try:
        _create_dir_link(mods_path, target_profile)
    except OSError as exc:
        return False, str(exc)

    return True, f"Linked Mods to profile '{target_profile.name}'{backup_msg}."


def unlink_game_mods(game_path: str | Path) -> tuple[bool, str]:
    """Safely remove <game_path>/Mods link/junction for Vanilla launch."""
    game_dir = Path(game_path)
    if not game_dir.is_dir():
        return False, f"Game folder not found: {game_dir}"

    mods_path = game_dir / "Mods"
    if _is_link_or_junction(mods_path):
        _remove_link_or_junction(mods_path)
        return True, "Unlinked Mods folder for Vanilla launch."

    if mods_path.exists():
        backup_path = game_dir / "Mods_Backup"
        if backup_path.exists():
            idx = 1
            while (game_dir / f"Mods_Backup_{idx}").exists():
                idx += 1
            backup_path = game_dir / f"Mods_Backup_{idx}"
        mods_path.rename(backup_path)
        return True, f"Moved unmanaged Mods folder to {backup_path.name} for Vanilla launch."

    return True, "No Mods folder to unlink."
