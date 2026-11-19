"""Mod update checking via UpdateKeys with caching and graceful offline handling."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.core.mod_installer import install_mod_zip
from src.core.mod_scanner import ModInfo
from src.core.nexus_installer import install_from_nexus


@dataclass(frozen=True)
class UpdateResult:
    """Result of checking a single mod for updates."""

    folder_name: str
    mod_name: str
    current_version: str
    latest_version: str = ""
    url: str = ""
    download_url: str = ""
    update_key: str = ""
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

        zip_url = ""
        assets = payload.get("assets")
        if isinstance(assets, list):
            for asset in assets:
                if isinstance(asset, dict):
                    dl = str(asset.get("browser_download_url") or "").strip()
                    if dl.lower().endswith(".zip") and dl.startswith("https://"):
                        zip_url = dl
                        break

        self._last_download_url = zip_url
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
            download_url = ""

            if isinstance(cached, dict):
                ts = cached.get("timestamp")
                ver = cached.get("version")
                url = cached.get("url")
                dl = cached.get("download_url", "")
                if (
                    isinstance(ts, (int, float))
                    and (now - ts) < self.cache_ttl_seconds
                    and isinstance(ver, str)
                    and isinstance(url, str)
                ):
                    latest_info = (ver, url)
                    download_url = dl if isinstance(dl, str) else ""

            if latest_info is None:
                provider = next(p for p in self.providers if p.supports(supported_key))
                try:
                    latest_info = provider.fetch_latest(supported_key, timeout=timeout)
                    download_url = str(getattr(provider, "_last_download_url", "") or "")
                    if latest_info is not None:
                        cache[supported_key] = {
                            "timestamp": now,
                            "version": latest_info[0],
                            "url": latest_info[1],
                            "download_url": download_url,
                        }
                        cache_dirty = True
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                    results.append(
                        UpdateResult(
                            folder_name=mod.folder_name,
                            mod_name=mod.name,
                            current_version=mod.version,
                            update_key=supported_key,
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
                    download_url=download_url,
                    update_key=supported_key,
                    has_update=is_newer_version(mod.version, latest_ver),
                )
            )

        if cache_dirty:
            self._save_cache(cache)

        return results


def install_mod_update(
    result: UpdateResult,
    modpack_dir: str | Path,
    nexus_api_key: str = "",
    github_token: str = "",
    timeout: float = 30.0,
) -> list[str]:
    """Download and install an available mod update into modpack_dir."""
    key_lower = result.update_key.lower()
    if key_lower.startswith("nexus:"):
        mod_id = result.update_key.split(":", 1)[1].split("@", 1)[0].strip()
        return install_from_nexus(mod_id, nexus_api_key, modpack_dir, timeout=timeout)

    if key_lower.startswith("github:") and result.download_url.startswith("https://"):
        headers = {"User-Agent": "SVMM-UpdateChecker"}
        if github_token.strip():
            headers["Authorization"] = f"Bearer {github_token.strip()}"
        req = urllib.request.Request(result.download_url, headers=headers)
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / f"{result.folder_name.replace('/', '_')}.zip"
            with urllib.request.urlopen(req, timeout=timeout) as resp, zip_path.open("wb") as dst:
                shutil.copyfileobj(resp, dst)
            return install_mod_zip(zip_path, modpack_dir)

    raise ValueError("No direct .zip download available for this release; open the release page.")


def can_direct_update(result: UpdateResult, has_nexus_key: bool = False) -> bool:
    """Return True if result can be updated directly via install_mod_update()."""
    if not result.has_update:
        return False
    key_lower = result.update_key.lower()
    if key_lower.startswith("github:") and result.download_url.startswith("https://"):
        return True
    if key_lower.startswith("nexus:") and has_nexus_key:
        return True
    return False
