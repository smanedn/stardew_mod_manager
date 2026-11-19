"""Export and import full modpack bundles (.zip) including mod files and profile metadata."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from src.core.config import ConfigManager, validate_profile_name

BUNDLE_MANIFEST_NAME = "svmm_modpack.json"


def _validate_member(member_name: str, stage_root: Path) -> Path:
    if not member_name or member_name.startswith(("/", "\\")):
        raise ValueError(f"Unsafe archive path: {member_name}")
    if len(member_name) >= 2 and member_name[1] == ":" and member_name[0].isalpha():
        raise ValueError(f"Unsafe archive path: {member_name}")
    parts = [p for p in member_name.replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"Unsafe archive path traversal: {member_name}")
    target = (stage_root / Path(*parts)).resolve()
    root_resolved = stage_root.resolve()
    if target != root_resolved and not target.is_relative_to(root_resolved):
        raise ValueError(f"Unsafe archive path escapes staging directory: {member_name}")
    return target


def export_modpack_bundle(
    dest_zip: str | Path,
    profile_id: str,
    profile_name: str,
    modpack_dir: str | Path,
    enabled_mods: list[str],
) -> Path:
    """Package a modpack's mod folders and enabled state into a single .zip bundle."""
    src_dir = Path(modpack_dir)
    out_zip = Path(dest_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    manifest_payload: dict[str, Any] = {
        "format_version": 1,
        "profile_id": profile_id,
        "name": profile_name,
        "enabled_mods": list(enabled_mods),
    }

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            BUNDLE_MANIFEST_NAME,
            json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n",
        )
        if src_dir.is_dir():
            for item in src_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(src_dir).as_posix()
                    zf.write(item, f"mods/{rel}")

    return out_zip


def import_modpack_bundle(
    bundle_zip: str | Path,
    modpacks_root: str | Path,
    config_manager: ConfigManager,
) -> str:
    """Import a .zip modpack bundle into modpacks_root and register its profile."""
    archive_path = Path(bundle_zip)
    if not archive_path.is_file():
        raise FileNotFoundError(f"Bundle archive not found: {archive_path}")
    if not zipfile.is_zipfile(archive_path):
        raise ValueError(f"Not a valid .zip modpack bundle: {archive_path.name}")

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

        manifest_file = stage / BUNDLE_MANIFEST_NAME
        if manifest_file.is_file():
            raw = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict):
                raise ValueError("Invalid svmm_modpack.json in bundle.")
            base_id = str(raw.get("profile_id") or raw.get("name") or archive_path.stem)
            display_name = str(raw.get("name") or base_id).strip()
            enabled_raw = raw.get("enabled_mods", [])
            enabled_mods = (
                [m for m in enabled_raw if isinstance(m, str)]
                if isinstance(enabled_raw, list)
                else []
            )
            mods_src = stage / "mods"
        else:
            base_id = archive_path.stem
            display_name = base_id
            enabled_mods = []
            mods_src = stage

        clean_base = validate_profile_name(base_id)
        candidate = clean_base
        idx = 1
        while candidate in config_manager.profiles:
            candidate = f"{clean_base}_{idx}"
            idx += 1

        dest_modpack = Path(modpacks_root) / candidate
        dest_modpack.mkdir(parents=True, exist_ok=True)
        if mods_src.is_dir():
            for item in mods_src.iterdir():
                target = dest_modpack / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)

        config_manager.create_profile(candidate, display_name or candidate)
        config_manager.set_enabled_mods(enabled_mods, candidate)
        return candidate
