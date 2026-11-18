"""Profile directory syncing and Stardew Valley Mods junction/symlink manager."""

from __future__ import annotations

import os
import shutil
import stat
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
    if sys.platform == "win32":
        try:
            lstat = os.lstat(path)
        except OSError:
            return False
        reparse_tag = getattr(lstat, "st_reparse_tag", 0)
        mount_point_tag = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
        if reparse_tag and reparse_tag == mount_point_tag:
            return True
        attrs = getattr(lstat, "st_file_attributes", 0)
        return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
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
            raise OSError(
                f"Failed to create junction '{link_path}' -> '{target_path}': {error_msg}"
            )
    else:
        os.symlink(target_path, link_path, target_is_directory=True)


def _backup_unmanaged_mods(game_dir: Path, mods_path: Path) -> Path:
    """Rename an existing unmanaged Mods folder to Mods_Backup (or Mods_Backup_N)."""
    backup_path = game_dir / "Mods_Backup"
    if backup_path.exists():
        idx = 1
        while (game_dir / f"Mods_Backup_{idx}").exists():
            idx += 1
        backup_path = game_dir / f"Mods_Backup_{idx}"
    mods_path.rename(backup_path)
    return backup_path


def _sync_profile_tree(current_dir: Path, profile_root: Path, desired: dict[str, Path]) -> set[str]:
    """Recursively clean stale entries in current_dir without descending into junctions."""
    existing_valid: set[str] = set()
    for entry in list(current_dir.iterdir()):
        rel_key = entry.relative_to(profile_root).as_posix()
        if _is_link_or_junction(entry):
            if rel_key in desired:
                try:
                    if entry.resolve() == desired[rel_key].resolve():
                        existing_valid.add(rel_key)
                        continue
                except OSError:
                    pass
            _remove_link_or_junction(entry)
        elif entry.is_dir():
            # Keep parent container dir if any desired nested mod lives under it
            prefix = f"{rel_key}/"
            if any(k.startswith(prefix) for k in desired):
                existing_valid.update(_sync_profile_tree(entry, profile_root, desired))
                if not any(entry.iterdir()):
                    entry.rmdir()
            else:
                shutil.rmtree(entry)
        else:
            entry.unlink()
    return existing_valid


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

    desired = {
        mod_folder.replace("\\", "/"): (pool_dir / mod_folder)
        for mod_folder in enabled_mods
        if (pool_dir / mod_folder).is_dir()
    }

    existing_valid = _sync_profile_tree(profile_dir, profile_dir, desired)

    for mod_folder, target in desired.items():
        if mod_folder not in existing_valid:
            link_path = profile_dir / mod_folder
            link_path.parent.mkdir(parents=True, exist_ok=True)
            _create_dir_link(link_path, target)

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
        backup_path = _backup_unmanaged_mods(game_dir, mods_path)
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
        backup_path = _backup_unmanaged_mods(game_dir, mods_path)
        return True, f"Moved unmanaged Mods folder to {backup_path.name} for Vanilla launch."

    return True, "No Mods folder to unlink."


def uninstall_mod(
    mod_folder: str,
    modpack_dir: str | Path,
    profiles_root: str | Path | None = None,
    profile_id: str | None = None,
) -> None:
    """Safely remove a mod folder from modpack_dir and unlink it from the profile."""
    pack_root = Path(modpack_dir).resolve()
    target = (pack_root / mod_folder).resolve()
    if target == pack_root or not target.is_relative_to(pack_root):
        raise ValueError(f"Unsafe mod folder path: {mod_folder}")
    if not target.exists():
        raise FileNotFoundError(f"Mod folder not found: {target}")

    shutil.rmtree(target)

    # Clean up empty intermediate parent folders for nested mods
    parent = target.parent
    while parent != pack_root and parent.is_dir():
        if any(parent.iterdir()):
            break
        parent.rmdir()
        parent = parent.parent

    if profiles_root is not None and profile_id:
        profile_link = Path(profiles_root) / profile_id / mod_folder
        if _is_link_or_junction(profile_link):
            _remove_link_or_junction(profile_link)
