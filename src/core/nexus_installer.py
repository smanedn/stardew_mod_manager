"""Direct mod installation from Nexus Mods URLs, IDs, and nxm:// links."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.mod_installer import install_mod_zip

_NEXUS_API_BASE = "https://api.nexusmods.com/v1/games/stardewvalley"
_NEXUS_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?nexusmods\.com/stardewvalley/mods/(\d+)", re.IGNORECASE
)


@dataclass(frozen=True)
class NexusTarget:
    """Parsed Nexus Mods target from a URL, mod ID, or nxm:// link."""

    mod_id: str
    file_id: str = ""
    nxm_key: str = ""
    nxm_expires: str = ""


def parse_nexus_input(raw_input: str) -> NexusTarget:
    """Parse a Nexus Mods URL, numeric mod ID, or nxm://stardewvalley/... link."""
    text = raw_input.strip()
    if not text:
        raise ValueError("Enter a Nexus Mods URL, mod ID, or nxm:// link.")

    if text.lower().startswith("nxm://"):
        parsed = urllib.parse.urlparse(text)
        if parsed.netloc.lower() != "stardewvalley":
            raise ValueError(f"Unsupported game in nxm:// link: {parsed.netloc}")
        match = re.match(r"^/mods/(\d+)/files/(\d+)/?$", parsed.path)
        if not match:
            raise ValueError("Invalid nxm:// link format (expected /mods/<id>/files/<file_id>).")
        qs = urllib.parse.parse_qs(parsed.query)
        return NexusTarget(
            mod_id=match.group(1),
            file_id=match.group(2),
            nxm_key=qs.get("key", [""])[0],
            nxm_expires=qs.get("expires", [""])[0],
        )

    if text.isdigit():
        return NexusTarget(mod_id=text)

    url_match = _NEXUS_URL_RE.search(text)
    if url_match:
        return NexusTarget(mod_id=url_match.group(1))

    raise ValueError("Could not recognize a Nexus Mods URL, mod ID, or nxm:// link.")


def _nexus_get_json(url: str, api_key: str, timeout: float = 15.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "apikey": api_key,
            "Accept": "application/json",
            "User-Agent": "SVMM-NexusInstaller",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ValueError("Invalid Nexus Mods API key (HTTP 401).") from exc
        if exc.code == 403:
            raise ValueError(
                "Nexus Mods API denied direct download (HTTP 403). "
                "Free accounts must paste an nxm:// Mod Manager Download link."
            ) from exc
        if exc.code == 404:
            raise ValueError("Mod or file not found on Nexus Mods (HTTP 404).") from exc
        raise ValueError(f"Nexus Mods API error (HTTP {exc.code}).") from exc


def _pick_main_file_id(files_payload: dict[str, Any]) -> str:
    files = files_payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("No downloadable files found for this mod on Nexus Mods.")

    main_files = [
        f
        for f in files
        if isinstance(f, dict) and str(f.get("category_name", "")).upper() == "MAIN"
    ]
    candidates = main_files or [f for f in files if isinstance(f, dict)]
    if not candidates:
        raise ValueError("No valid file entries returned by Nexus Mods.")

    # Pick the newest file by uploaded_timestamp
    chosen = max(candidates, key=lambda f: int(f.get("uploaded_timestamp") or 0))
    file_id = chosen.get("file_id")
    if not file_id:
        raise ValueError("Missing file_id in Nexus Mods response.")
    return str(file_id)


def install_from_nexus(
    raw_input: str,
    api_key: str,
    modpack_dir: str | Path,
    timeout: float = 30.0,
) -> list[str]:
    """Download a mod archive from Nexus Mods and safely install it into modpack_dir."""
    clean_key = api_key.strip()
    if not clean_key:
        raise ValueError("A Nexus Mods API key is required to download mods.")

    target = parse_nexus_input(raw_input)
    file_id = target.file_id
    if not file_id:
        files_data = _nexus_get_json(
            f"{_NEXUS_API_BASE}/mods/{target.mod_id}/files.json",
            clean_key,
            timeout=timeout,
        )
        file_id = _pick_main_file_id(files_data)

    dl_url = f"{_NEXUS_API_BASE}/mods/{target.mod_id}/files/{file_id}/download_link.json"
    if target.nxm_key and target.nxm_expires:
        query = urllib.parse.urlencode({"key": target.nxm_key, "expires": target.nxm_expires})
        dl_url = f"{dl_url}?{query}"

    links = _nexus_get_json(dl_url, clean_key, timeout=timeout)
    if not isinstance(links, list) or not links or not isinstance(links[0], dict):
        raise ValueError("Nexus Mods did not return a download mirror.")

    cdn_url = str(links[0].get("URI") or "").strip()
    if not cdn_url.startswith("https://"):
        raise ValueError("Invalid download URL returned by Nexus Mods.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_name = (
            Path(urllib.parse.urlparse(cdn_url).path).name or f"nexus_{target.mod_id}.zip"
        )
        if not archive_name.lower().endswith(".zip"):
            archive_name = f"{archive_name}.zip"
        archive_path = Path(tmp_dir) / archive_name

        req = urllib.request.Request(cdn_url, headers={"User-Agent": "SVMM-NexusInstaller"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, archive_path.open("wb") as dst:
            shutil.copyfileobj(resp, dst)

        return install_mod_zip(archive_path, modpack_dir)
