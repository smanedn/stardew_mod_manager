"""Safe .zip and .7z mod archive installer with zip-slip protection."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import py7zr
import rarfile


def _validate_archive_member(member_name: str, stage_root: Path) -> Path:
    """Ensure an archive member path cannot escape stage_root (zip-slip protection)."""
    if not member_name or member_name.startswith(("/", "\\")):
        raise ValueError(f"Unsafe archive path: {member_name}")
    # Reject Windows drive letters like C:foo
    if len(member_name) >= 2 and member_name[1] == ":" and member_name[0].isalpha():
        raise ValueError(f"Unsafe archive path: {member_name}")

    normalized = member_name.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"Unsafe archive path traversal: {member_name}")

    target = (stage_root / Path(*parts)).resolve()
    root_resolved = stage_root.resolve()
    if target != root_resolved and not target.is_relative_to(root_resolved):
        raise ValueError(f"Unsafe archive path escapes staging directory: {member_name}")
    return target


def _find_mod_roots(stage_root: Path) -> list[Path]:
    """Find top-most directories containing manifest.json inside stage_root."""
    manifests = sorted(stage_root.rglob("manifest.json"), key=lambda p: len(p.parts))
    mod_roots: list[Path] = []
    for manifest in manifests:
        parent = manifest.parent
        # Skip nested manifests inside an already-selected mod root
        if any(parent == existing or parent.is_relative_to(existing) for existing in mod_roots):
            continue
        mod_roots.append(parent)
    return mod_roots


def _extract_zip(archive_path: Path, stage_root: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = zf.infolist()
        validated: list[tuple[zipfile.ZipInfo, Path]] = [
            (info, _validate_archive_member(info.filename, stage_root)) for info in members
        ]
        for info, target in validated:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def _extract_7z(archive_path: Path, stage_root: Path) -> None:
    with py7zr.SevenZipFile(archive_path, mode="r") as szf:
        for name in szf.getnames():
            _validate_archive_member(name, stage_root)
        szf.extractall(path=stage_root)


def _extract_rar(archive_path: Path, stage_root: Path) -> None:
    try:
        with rarfile.RarFile(archive_path, "r") as rf:
            for info in rf.infolist():
                _validate_archive_member(info.filename, stage_root)
            rf.extractall(path=stage_root)
    except rarfile.RarCannotExec as exc:
        raise ValueError(
            "Cannot extract .rar archive: install UnRAR, 7-Zip, or bsdtar on your PATH."
        ) from exc
    except rarfile.Error as exc:
        raise ValueError(f"Invalid or corrupted .rar archive: {exc}") from exc


def install_mod_archive(archive_path: str | Path, modpack_dir: str | Path) -> list[str]:
    """Safely extract a .zip, .7z, or .rar mod archive into modpack_dir."""
    src_path = Path(archive_path)
    if not src_path.is_file():
        raise FileNotFoundError(f"Archive not found: {src_path}")

    dest_root = Path(modpack_dir)
    dest_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        stage_root = Path(tmp_dir)
        suffix = src_path.suffix.lower()

        if suffix == ".rar" or (suffix not in (".zip", ".7z") and rarfile.is_rarfile(src_path)):
            _extract_rar(src_path, stage_root)
        elif suffix == ".7z" or (suffix != ".zip" and py7zr.is_7zfile(src_path)):
            _extract_7z(src_path, stage_root)
        elif zipfile.is_zipfile(src_path):
            _extract_zip(src_path, stage_root)
        else:
            raise ValueError(f"Unsupported or corrupted archive format: {src_path.name}")

        mod_roots = _find_mod_roots(stage_root)
        if not mod_roots:
            raise ValueError("No manifest.json found inside archive.")

        installed: list[str] = []
        for mod_root in mod_roots:
            folder_name = src_path.stem if mod_root == stage_root else mod_root.name
            dest_dir = dest_root / folder_name
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            if mod_root == stage_root:
                dest_dir.mkdir(parents=True, exist_ok=True)
                for item in stage_root.iterdir():
                    shutil.move(str(item), str(dest_dir / item.name))
            else:
                shutil.move(str(mod_root), str(dest_dir))
            installed.append(folder_name)

        return installed


def install_mod_zip(zip_path: str | Path, modpack_dir: str | Path) -> list[str]:
    """Backward-compatible wrapper for install_mod_archive."""
    return install_mod_archive(zip_path, modpack_dir)


def parse_dropped_archive_paths(raw_drop_data: str) -> list[Path]:
    """Parse a TkDND <<Drop>> data string into existing .zip/.7z archive paths."""
    if not raw_drop_data or not raw_drop_data.strip():
        return []

    tokens: list[str] = []
    i = 0
    n = len(raw_drop_data)
    while i < n:
        if raw_drop_data[i].isspace():
            i += 1
            continue
        if raw_drop_data[i] == "{":
            end = raw_drop_data.find("}", i + 1)
            if end == -1:
                tokens.append(raw_drop_data[i + 1 :].strip())
                break
            tokens.append(raw_drop_data[i + 1 : end])
            i = end + 1
        else:
            end = i
            while end < n and not raw_drop_data[end].isspace():
                end += 1
            tokens.append(raw_drop_data[i:end])
            i = end

    archives: list[Path] = []
    for tok in tokens:
        path = Path(tok)
        if path.is_file() and path.suffix.lower() in (".zip", ".7z", ".rar"):
            archives.append(path)
    return archives
