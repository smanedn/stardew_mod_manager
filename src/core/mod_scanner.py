"""Mod pool scanner and SMAPI manifest.json parser."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModDependency:
    """Dependency entry declared in a SMAPI manifest.json."""

    unique_id: str
    is_required: bool = True
    minimum_version: str = ""


@dataclass(frozen=True)
class ModInfo:
    """Metadata extracted from a mod directory in the mod pool."""

    folder_name: str
    name: str
    version: str
    path: Path
    unique_id: str = ""
    author: str = ""
    description: str = ""
    minimum_api_version: str = ""
    has_manifest: bool = True
    error: str | None = None
    dependencies: tuple[ModDependency, ...] = ()
    update_keys: tuple[str, ...] = ()


def _strip_json_comments_and_trailing_commas(text: str) -> str:
    """Sanitize JSON5-like SMAPI manifests (//, /* */, trailing commas) safely."""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        # Single-line comment // ...
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] not in ("\n", "\r"):
                i += 1
            continue

        # Block comment /* ... */
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        out.append(ch)
        i += 1

    # Remove trailing commas before } or ] outside strings
    no_comments = "".join(out)
    result: list[str] = []
    in_string = False
    escape = False
    m = len(no_comments)
    j = 0

    while j < m:
        ch = no_comments[j]
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            j += 1
            continue

        if ch == '"':
            in_string = True
            result.append(ch)
            j += 1
            continue

        if ch == ",":
            k = j + 1
            while k < m and no_comments[k] in " \t\r\n":
                k += 1
            if k < m and no_comments[k] in ("}", "]"):
                j += 1
                continue

        result.append(ch)
        j += 1

    return "".join(result)


def parse_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read and parse a SMAPI manifest.json file with tolerant fallback."""
    raw_text = manifest_path.read_text(encoding="utf-8-sig")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        sanitized = _strip_json_comments_and_trailing_commas(raw_text)
        parsed = json.loads(sanitized)

    if not isinstance(parsed, dict):
        raise ValueError("manifest.json root must be a JSON object.")
    return parsed


def _parse_dependencies(raw_deps: Any) -> tuple[ModDependency, ...]:
    if not isinstance(raw_deps, list):
        return ()
    deps: list[ModDependency] = []
    for item in raw_deps:
        if not isinstance(item, dict):
            continue
        uid = str(item.get("UniqueID") or "").strip()
        if not uid:
            continue
        is_req = item.get("IsRequired", True)
        min_ver = str(item.get("MinimumVersion") or "").strip()
        deps.append(
            ModDependency(
                unique_id=uid,
                is_required=bool(is_req) if isinstance(is_req, bool) else True,
                minimum_version=min_ver,
            )
        )
    return tuple(deps)


def _parse_update_keys(raw_keys: Any) -> tuple[str, ...]:
    if not isinstance(raw_keys, list):
        return ()
    return tuple(str(k).strip() for k in raw_keys if isinstance(k, str) and k.strip())


def _collect_mod_folders(root: Path, is_top_level: bool = True) -> list[Path]:
    """Recursively find mod folders containing manifest.json (preserving empty top-level dirs)."""
    if not root.is_dir():
        return []

    found: list[Path] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        if (entry / "manifest.json").is_file():
            found.append(entry)
            continue

        nested = _collect_mod_folders(entry, is_top_level=False)
        if nested:
            found.extend(nested)
        elif is_top_level:
            # Keep top-level folders that have no manifest anywhere so user sees the warning
            found.append(entry)

    return found


def scan_mod_pool(mod_pool_path: str | Path = Path("SVMM_Data") / "mod_pool") -> list[ModInfo]:
    """Scan the mod pool directory (recursively) and return metadata for each mod folder."""
    pool_dir = Path(mod_pool_path)
    if not pool_dir.exists() or not pool_dir.is_dir():
        return []

    mods: list[ModInfo] = []
    for entry in _collect_mod_folders(pool_dir):
        rel_folder = entry.relative_to(pool_dir).as_posix()
        manifest_path = entry / "manifest.json"
        if not manifest_path.is_file():
            mods.append(
                ModInfo(
                    folder_name=rel_folder,
                    name=entry.name,
                    version="Unknown",
                    path=entry,
                    has_manifest=False,
                    error="Missing manifest.json",
                )
            )
            continue

        try:
            manifest = parse_manifest(manifest_path)
            name = str(manifest.get("Name") or entry.name).strip() or entry.name
            version = str(manifest.get("Version") or "Unknown").strip() or "Unknown"
            unique_id = str(manifest.get("UniqueID") or "").strip()
            author = str(manifest.get("Author") or "").strip()
            description = str(manifest.get("Description") or "").strip()
            min_api = str(manifest.get("MinimumApiVersion") or "").strip()
            mods.append(
                ModInfo(
                    folder_name=rel_folder,
                    name=name,
                    version=version,
                    path=entry,
                    unique_id=unique_id,
                    author=author,
                    description=description,
                    minimum_api_version=min_api,
                    has_manifest=True,
                    dependencies=_parse_dependencies(manifest.get("Dependencies")),
                    update_keys=_parse_update_keys(manifest.get("UpdateKeys")),
                )
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            mods.append(
                ModInfo(
                    folder_name=rel_folder,
                    name=entry.name,
                    version="Unknown",
                    path=entry,
                    has_manifest=True,
                    error=f"Invalid manifest.json: {exc}",
                )
            )

    return mods
