"""Live SMAPI mod compatibility checker via smapi.io API v3.0."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.mod_scanner import ModInfo

_SMAPI_COMPAT_API = "https://smapi.io/api/v3.0/mods"


@dataclass(frozen=True)
class SmapiCompatInfo:
    """Compatibility status for a mod from smapi.io."""

    unique_id: str
    status: str  # e.g. "Ok", "Unofficial", "Workaround", "Broken", "Obsolete", "Abandoned"
    summary: str
    unofficial_version: str = ""
    unofficial_url: str = ""

    @property
    def is_warning(self) -> bool:
        return self.status.lower() in ("unofficial", "workaround")

    @property
    def is_broken(self) -> bool:
        return self.status.lower() in ("broken", "obsolete", "abandoned")


def _load_cache(cache_path: Path | None) -> dict[str, dict[str, Any]]:
    if not cache_path or not cache_path.is_file():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_path: Path | None, cache: dict[str, dict[str, Any]]) -> None:
    if not cache_path:
        return
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def check_smapi_compatibility(
    mods: list[ModInfo],
    cache_path: str | Path | None = None,
    cache_ttl_seconds: float = 21600.0,
    timeout: float = 10.0,
) -> dict[str, SmapiCompatInfo]:
    """Check mods with UniqueIDs against smapi.io compatibility API."""
    cpath = Path(cache_path) if cache_path else None
    cache = _load_cache(cpath)
    now = time.time()

    results: dict[str, SmapiCompatInfo] = {}
    to_query: list[ModInfo] = []

    for mod in mods:
        uid = mod.unique_id.strip()
        if not uid:
            continue
        cached = cache.get(uid.lower())
        if isinstance(cached, dict):
            ts = cached.get("timestamp")
            status = cached.get("status")
            summary = cached.get("summary", "")
            if (
                isinstance(ts, (int, float))
                and (now - ts) < cache_ttl_seconds
                and isinstance(status, str)
            ):
                results[mod.folder_name] = SmapiCompatInfo(
                    unique_id=uid,
                    status=status,
                    summary=str(summary),
                    unofficial_version=str(cached.get("unofficial_version") or ""),
                    unofficial_url=str(cached.get("unofficial_url") or ""),
                )
                continue
        to_query.append(mod)

    if not to_query:
        return results

    payload = {
        "mods": [
            {
                "id": m.unique_id.strip(),
                "installedVersion": m.version if m.version != "Unknown" else None,
            }
            for m in to_query
        ],
        "includeExtendedMetadata": True,
    }
    req = urllib.request.Request(
        _SMAPI_COMPAT_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SVMM-SmapiCompat",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return results

    if not isinstance(response_data, list):
        return results

    by_id: dict[str, dict[str, Any]] = {}
    for entry in response_data:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            by_id[entry["id"].strip().lower()] = entry

    cache_dirty = False
    for mod in to_query:
        uid_lower = mod.unique_id.strip().lower()
        entry = by_id.get(uid_lower)
        if not entry:
            continue
        meta = entry.get("metadata")
        if not isinstance(meta, dict):
            continue
        status = str(meta.get("compatibilityStatus") or "").strip()
        if not status:
            continue
        summary = str(meta.get("compatibilitySummary") or "").strip()
        unofficial = meta.get("unofficialUpdate")
        u_ver = ""
        u_url = ""
        if isinstance(unofficial, dict):
            u_ver = str(unofficial.get("version") or "").strip()
            u_url = str(unofficial.get("url") or "").strip()

        info = SmapiCompatInfo(
            unique_id=mod.unique_id,
            status=status,
            summary=summary,
            unofficial_version=u_ver,
            unofficial_url=u_url,
        )
        results[mod.folder_name] = info
        cache[uid_lower] = {
            "timestamp": now,
            "status": status,
            "summary": summary,
            "unofficial_version": u_ver,
            "unofficial_url": u_url,
        }
        cache_dirty = True

    if cache_dirty:
        _save_cache(cpath, cache)

    return results
