"""Backup and restore Stardew Valley save folders as .zip archives."""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SaveBackupInfo:
    """Metadata for a single save backup archive."""

    name: str
    path: Path
    size_bytes: int
    modified_ts: float


def get_default_saves_dir() -> Path:
    """Return the default Stardew Valley Saves directory for the current OS."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"
    return base / "StardewValley" / "Saves"


def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", label.strip()).strip("_")
    return cleaned[:32]


def create_save_backup(
    saves_dir: str | Path,
    backups_root: str | Path,
    label: str = "",
) -> Path:
    """Create a timestamped .zip backup of saves_dir inside backups_root."""
    src_dir = Path(saves_dir)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Saves folder not found: {src_dir}")

    dest_root = Path(backups_root)
    dest_root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_label = _sanitize_label(label)
    name = f"Saves_{clean_label}_{stamp}.zip" if clean_label else f"Saves_{stamp}.zip"
    archive_path = dest_root / name
    idx = 1
    while archive_path.exists():
        stem = name[:-4]
        archive_path = dest_root / f"{stem}_{idx}.zip"
        idx += 1

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in src_dir.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(src_dir).as_posix())

    return archive_path


def list_save_backups(backups_root: str | Path) -> list[SaveBackupInfo]:
    """List available .zip save backups sorted newest first."""
    root = Path(backups_root)
    if not root.is_dir():
        return []

    backups: list[SaveBackupInfo] = []
    for entry in root.glob("*.zip"):
        if not entry.is_file():
            continue
        stat = entry.stat()
        backups.append(
            SaveBackupInfo(
                name=entry.name,
                path=entry,
                size_bytes=stat.st_size,
                modified_ts=stat.st_mtime,
            )
        )
    backups.sort(key=lambda b: b.modified_ts, reverse=True)
    return backups


def _validate_member(member_name: str, dest_dir: Path) -> Path:
    if not member_name or member_name.startswith(("/", "\\")):
        raise ValueError(f"Unsafe archive path: {member_name}")
    if len(member_name) >= 2 and member_name[1] == ":" and member_name[0].isalpha():
        raise ValueError(f"Unsafe archive path: {member_name}")
    parts = [p for p in member_name.replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"Unsafe archive path traversal: {member_name}")
    target = (dest_dir / Path(*parts)).resolve()
    root_resolved = dest_dir.resolve()
    if target != root_resolved and not target.is_relative_to(root_resolved):
        raise ValueError(f"Unsafe archive path escapes target: {member_name}")
    return target


def restore_save_backup(backup_zip: str | Path, saves_dir: str | Path) -> None:
    """Safely restore a .zip save backup into saves_dir."""
    archive_path = Path(backup_zip)
    if not archive_path.is_file():
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")

    dest_dir = Path(saves_dir)

    with tempfile.TemporaryDirectory() as tmp_dir:
        stage = Path(tmp_dir)
        with zipfile.ZipFile(archive_path, "r") as zf:
            validated = [(info, _validate_member(info.filename, stage)) for info in zf.infolist()]
            for info, target in validated:
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info, "r") as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(stage, dest_dir)
