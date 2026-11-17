"""Safe .zip mod archive installer with zip-slip protection."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path


def _validate_zip_member(member_name: str, stage_root: Path) -> Path:
    """Ensure a zip member path cannot escape stage_root (zip-slip protection)."""
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


def install_mod_zip(zip_path: str | Path, modpack_dir: str | Path) -> list[str]:
    """Safely extract a .zip mod archive into modpack_dir and return installed folder names."""
    archive_path = Path(zip_path)
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    dest_root = Path(modpack_dir)
    dest_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        stage_root = Path(tmp_dir)

        with zipfile.ZipFile(archive_path, "r") as zf:
            members = zf.infolist()
            # Validate all entries before extracting anything
            validated: list[tuple[zipfile.ZipInfo, Path]] = [
                (info, _validate_zip_member(info.filename, stage_root)) for info in members
            ]
            for info, target in validated:
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info, "r") as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        mod_roots = _find_mod_roots(stage_root)
        installed: list[str] = []

        if not mod_roots:
            raise ValueError("No manifest.json found inside archive.")

        for mod_root in mod_roots:
            folder_name = archive_path.stem if mod_root == stage_root else mod_root.name
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
