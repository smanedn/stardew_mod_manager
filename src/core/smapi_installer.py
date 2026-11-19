"""One-click SMAPI release downloader and official installer launcher."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

SMAPI_LATEST_API = "https://api.github.com/repos/Pathoschild/SMAPI/releases/latest"


@dataclass(frozen=True)
class SmapiRelease:
    """Latest SMAPI GitHub release metadata."""

    version: str
    download_url: str
    html_url: str


def fetch_latest_smapi_release(
    github_token: str = "", timeout: float = 10.0
) -> SmapiRelease | None:
    """Fetch the latest SMAPI installer release from GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SVMM/1.0",
    }
    if github_token.strip():
        headers["Authorization"] = f"Bearer {github_token.strip()}"

    req = urllib.request.Request(SMAPI_LATEST_API, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None

    if not isinstance(payload, dict):
        return None

    tag = str(payload.get("tag_name") or "").lstrip("vV").strip()
    html_url = str(payload.get("html_url") or "https://smapi.io/")
    assets = payload.get("assets") or []
    download_url = ""
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "").lower()
            url = str(asset.get("browser_download_url") or "")
            if name.endswith("-installer.zip") and url:
                download_url = url
                break

    if not tag or not download_url:
        return None
    return SmapiRelease(version=tag, download_url=download_url, html_url=html_url)


def download_and_extract_smapi(download_url: str, dest_dir: Path, timeout: float = 60.0) -> Path:
    """Download SMAPI installer zip into dest_dir and return the extracted installer directory."""
    if dest_dir.exists():
        shutil.rmtree(dest_dir, ignore_errors=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    zip_path = dest_dir / "smapi-installer.zip"
    req = urllib.request.Request(download_url, headers={"User-Agent": "SVMM/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        zip_path.write_bytes(resp.read())

    extract_root = dest_dir / "extracted"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_root)
    zip_path.unlink(missing_ok=True)

    # Return directory containing install on Windows.bat (either extract_root or single subdir)
    for candidate in [extract_root, *extract_root.iterdir()]:
        if candidate.is_dir() and (
            (candidate / "install on Windows.bat").is_file()
            or (candidate / "install on Linux.sh").is_file()
            or (candidate / "install on macOS.command").is_file()
        ):
            return candidate
    return extract_root


def launch_smapi_installer(installer_dir: Path) -> tuple[bool, str]:
    """Launch the platform's official SMAPI installer script."""
    if sys.platform == "win32":
        script = installer_dir / "install on Windows.bat"
        if not script.is_file():
            return False, f"Installer script not found in {installer_dir}."
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(["cmd", "/c", str(script)], cwd=str(installer_dir), creationflags=flags)
        return True, "Launched official SMAPI Windows installer."

    if sys.platform == "darwin":
        script = installer_dir / "install on macOS.command"
        if not script.is_file():
            return False, f"Installer script not found in {installer_dir}."
        os.chmod(script, 0o755)
        subprocess.Popen(["open", str(script)], cwd=str(installer_dir))
        return True, "Launched official SMAPI macOS installer."

    script = installer_dir / "install on Linux.sh"
    if not script.is_file():
        return False, f"Installer script not found in {installer_dir}."
    os.chmod(script, 0o755)
    subprocess.Popen(["x-terminal-emulator", "-e", str(script)], cwd=str(installer_dir))
    return True, "Launched official SMAPI Linux installer."
