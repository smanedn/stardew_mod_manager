"""Self-update checker for SVMM via GitHub Releases."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

SVMM_RELEASES_API = "https://api.github.com/repos/smanedn/stardew_mod_manager/releases/latest"


def _parse_semver(ver: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in ver.lstrip("vV").strip().split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_svmm_update(
    current_version: str,
    github_token: str = "",
    timeout: float = 5.0,
) -> tuple[str, str] | None:
    """Return (latest_version, release_url) if a newer SVMM release exists on GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"SVMM/{current_version}",
    }
    if github_token.strip():
        headers["Authorization"] = f"Bearer {github_token.strip()}"

    req = urllib.request.Request(SVMM_RELEASES_API, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None

    if not isinstance(payload, dict):
        return None

    tag = str(payload.get("tag_name") or "").lstrip("vV").strip()
    html_url = str(payload.get("html_url") or "")
    if not tag or not html_url:
        return None

    if _parse_semver(tag) > _parse_semver(current_version):
        return tag, html_url
    return None
