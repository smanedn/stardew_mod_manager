"""Mod update checking via UpdateKeys with caching and graceful offline handling."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.core.mod_scanner import ModInfo


@dataclass(frozen=True)
class UpdateResult:
    """Result of checking a single mod for updates."""

    folder_name: str
    mod_name: str
    current_version: str
    latest_version: str = ""
    url: str = ""
    has_update: bool = False
    error: str | None = None


class UpdateProvider(Protocol):
    """Interface for resolving latest version info from a SMAPI UpdateKey."""

    def supports(self, update_key: str) -> bool: ...

    def fetch_latest(self, update_key: str, timeout: float = 5.0) -> tuple[str, str] | None: ...


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("vV")
    nums = [int(part) for part in re.findall(r"\d+", cleaned)]
    return tuple(nums) if nums else (0,)


def is_newer_version(current: str, latest: str) -> bool:
    """Return True if latest is strictly newer than current."""
    cur_t = _parse_version_tuple(current)
    lat_t = _parse_version_tuple(latest)
    max_len = max(len(cur_t), len(lat_t))
    cur_padded = cur_t + (0,) * (max_len - len(cur_t))
    lat_padded = lat_t + (0,) * (max_len - len(lat_t))
    return lat_padded > cur_padded


class GitHubUpdateProvider:
    """Checks GitHub Releases API for `GitHub:owner/repo` UpdateKeys."""

    def __init__(self, token: str = "") -> None:
        self.token = token.strip()

    def supports(self, update_key: str) -> bool:
        return update_key.lower().startswith("github:") and "/" in update_key.split(":", 1)[1]

    def fetch_latest(self, update_key: str, timeout: float = 5.0) -> tuple[str, str] | None:
        repo = update_key.split(":", 1)[1].strip()
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SVMM-UpdateChecker",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        tag = str(payload.get("tag_name") or "").strip()
        html_url = str(payload.get("html_url") or f"https://github.com/{repo}/releases").strip()
        if not tag:
            return None
        return tag.lstrip("vV"), html_url


class NexusUpdateProvider:
    """Checks Nexus Mods API v1 for `Nexus:<mod_id>` UpdateKeys when an API key is configured."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key.strip()

    def _extract_mod_id(self, update_key: str) -> str | None:
        if not update_key.lower().startswith("nexus:"):
            return None
        raw_id = update_key.split(":", 1)[1].split("@", 1)[0].strip()
        return raw_id if raw_id.isdigit() else None

    def supports(self, update_key: str) -> bool:
        return bool(self.api_key) and self._extract_mod_id(update_key) is not None

    def fetch_latest(self, update_key: str, timeout: float = 5.0) -> tuple[str, str] | None:
        mod_id = self._extract_mod_id(update_key)
        if not mod_id or not self.api_key:
            return None
        api_url = f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{mod_id}.json"
        headers = {
            "apikey": self.api_key,
            "Accept": "application/json",
            "User-Agent": "SVMM-UpdateChecker",
        }
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        version = str(payload.get("version") or "").strip()
        if not version:
            return None
        return version.lstrip("vV"), f"https://www.nexusmods.com/stardewvalley/mods/{mod_id}"


class UpdateChecker:
    """Checks mods against UpdateProviders with optional JSON file caching."""

    def __init__(
        self,
        providers: Sequence[UpdateProvider] | None = None,
        cache_path: str | Path | None = None,
        cache_ttl_seconds: float = 3600.0,
    ) -> None:
        self.providers: list[UpdateProvider] = (
            list(providers) if providers is not None else [GitHubUpdateProvider()]
        )
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache_ttl_seconds = cache_ttl_seconds

    def _load_cache(self) -> dict[str, dict[str, object]]:
        if not self.cache_path or not self.cache_path.is_file():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_cache(self, cache: dict[str, dict[str, object]]) -> None:
        if not self.cache_path:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def check_mods(self, mods: list[ModInfo], timeout: float = 5.0) -> list[UpdateResult]:
        """Check all mods that declare a supported UpdateKey."""
        cache = self._load_cache()
        now = time.time()
        results: list[UpdateResult] = []
        cache_dirty = False

        for mod in mods:
            supported_key = next(
                (k for k in mod.update_keys if any(p.supports(k) for p in self.providers)),
                None,
            )
            if supported_key is None:
                continue

            cached = cache.get(supported_key)
            latest_info: tuple[str, str] | None = None

            if isinstance(cached, dict):
                ts = cached.get("timestamp")
                ver = cached.get("version")
                url = cached.get("url")
                if (
                    isinstance(ts, (int, float))
                    and (now - ts) < self.cache_ttl_seconds
                    and isinstance(ver, str)
                    and isinstance(url, str)
                ):
                    latest_info = (ver, url)

            if latest_info is None:
                provider = next(p for p in self.providers if p.supports(supported_key))
                try:
                    latest_info = provider.fetch_latest(supported_key, timeout=timeout)
                    if latest_info is not None:
                        cache[supported_key] = {
                            "timestamp": now,
                            "version": latest_info[0],
                            "url": latest_info[1],
                        }
                        cache_dirty = True
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                    results.append(
                        UpdateResult(
                            folder_name=mod.folder_name,
                            mod_name=mod.name,
                            current_version=mod.version,
                            error=f"Update check failed: {exc}",
                        )
                    )
                    continue

            if latest_info is None:
                continue

            latest_ver, release_url = latest_info
            results.append(
                UpdateResult(
                    folder_name=mod.folder_name,
                    mod_name=mod.name,
                    current_version=mod.version,
                    latest_version=latest_ver,
                    url=release_url,
                    has_update=is_newer_version(mod.version, latest_ver),
                )
            )

        if cache_dirty:
            self._save_cache(cache)

        return results
