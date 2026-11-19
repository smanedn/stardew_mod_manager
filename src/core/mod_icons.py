"""Mod thumbnail resolution, local/cached icon loading, and monogram fallback generation."""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.core.mod_scanner import ModInfo

_NEXUS_KEY_RE = re.compile(r"^\s*Nexus\s*:\s*(\d+)\s*$", re.IGNORECASE)

_LOCAL_ICON_CANDIDATES = (
    "icon.png",
    "icon.jpg",
    "preview.png",
    "preview.jpg",
    "logo.png",
    "thumbnail.png",
    "banner.png",
    "assets/icon.png",
    "assets/preview.png",
)

_BADGE_PALETTE = (
    "#2563EB",
    "#7C3AED",
    "#059669",
    "#D97706",
    "#DC2626",
    "#0891B2",
    "#DB2777",
    "#4F46E5",
    "#65A30D",
    "#EA580C",
)


def extract_nexus_mod_id(mod: ModInfo) -> str | None:
    """Return the numeric Nexus Mods ID from a mod's UpdateKeys, if present."""
    for raw_key in mod.update_keys:
        match = _NEXUS_KEY_RE.match(raw_key)
        if match:
            return match.group(1)
    return None


def _round_corners(image: Image.Image, radius: int) -> Image.Image:
    """Apply smooth rounded corners to an RGBA square image."""
    rgba = image.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (rgba.width - 1, rgba.height - 1)], radius=radius, fill=255)
    result = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    result.paste(rgba, (0, 0), mask)
    return result


def _mod_initials(name: str) -> str:
    """Return 1-2 uppercase initials for a mod name."""
    words = [w for w in re.split(r"[\s_\-]+", name.strip()) if w and w[0].isalnum()]
    if not words:
        return "M"
    if len(words) == 1:
        return words[0][:2].upper()
    return f"{words[0][0]}{words[1][0]}".upper()


def generate_monogram_icon(mod: ModInfo, size: int = 84) -> Image.Image:
    """Generate a crisp rounded monogram badge when no mod image is available."""
    seed = (mod.unique_id or mod.folder_name or mod.name).encode("utf-8", errors="ignore")
    digest = hashlib.sha256(seed).digest()
    bg_hex = _BADGE_PALETTE[digest[0] % len(_BADGE_PALETTE)]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = max(8, size // 5)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=bg_hex)

    # Subtle top-edge highlight
    draw.rounded_rectangle(
        [(1, 1), (size - 2, size - 2)],
        radius=max(6, radius - 1),
        outline=(255, 255, 255, 45),
        width=2,
    )

    initials = _mod_initials(mod.name)
    font_size = round(size * 0.38)
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    try:
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = (size - text_w) / 2 - bbox[0]
    ty = (size - text_h) / 2 - bbox[1]
    draw.text((tx, ty), initials, fill="#FFFFFF", font=font)
    return img


def find_local_mod_icon(mod: ModInfo) -> Path | None:
    """Return the first local icon/preview image inside a mod folder, if any."""
    if not mod.path.is_dir():
        return None
    for rel in _LOCAL_ICON_CANDIDATES:
        candidate = mod.path / rel
        if candidate.is_file():
            return candidate
    return None


def get_cached_icon_path(mod: ModInfo, cache_dir: Path) -> Path | None:
    """Return path to a cached icon PNG in cache_dir if one exists."""
    nexus_id = extract_nexus_mod_id(mod)
    if nexus_id:
        nexus_cached = cache_dir / f"nexus_{nexus_id}.png"
        if nexus_cached.is_file():
            return nexus_cached
    folder_cached = cache_dir / f"{mod.folder_name}.png"
    if folder_cached.is_file():
        return folder_cached
    return None


def load_mod_icon(mod: ModInfo, cache_dir: Path, size: int = 84) -> Image.Image:
    """Load local/cached mod image as a rounded square PIL Image, or monogram fallback."""
    source_path = find_local_mod_icon(mod) or get_cached_icon_path(mod, cache_dir)
    if source_path is not None:
        try:
            with Image.open(source_path) as raw:
                fitted = ImageOps.fit(
                    raw.convert("RGBA"),
                    (size, size),
                    method=Image.Resampling.LANCZOS,
                )
            return _round_corners(fitted, max(8, size // 5))
        except OSError:
            pass
    return generate_monogram_icon(mod, size=size)


def fetch_nexus_mod_thumbnail(
    mod_id: str,
    api_key: str,
    cache_dir: Path,
    size: int = 84,
    timeout: float = 8.0,
) -> Path | None:
    """Fetch and cache a mod's thumbnail from Nexus Mods API v1."""
    if not api_key.strip() or not mod_id.isdigit():
        return None

    target = cache_dir / f"nexus_{mod_id}.png"
    if target.is_file():
        return target

    api_url = f"https://api.nexusmods.com/v1/games/stardewvalley/mods/{mod_id}.json"
    req = urllib.request.Request(
        api_url,
        headers={
            "apikey": api_key.strip(),
            "Accept": "application/json",
            "User-Agent": "SVMM/0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None

    picture_url = payload.get("picture_url") if isinstance(payload, dict) else None
    if not isinstance(picture_url, str) or not picture_url.startswith(("http://", "https://")):
        return None

    img_req = urllib.request.Request(picture_url, headers={"User-Agent": "SVMM/0.8"})
    try:
        with urllib.request.urlopen(img_req, timeout=timeout) as img_resp:
            raw_bytes = img_resp.read()
        with Image.open(io.BytesIO(raw_bytes)) as raw_img:
            fitted = ImageOps.fit(
                raw_img.convert("RGBA"),
                (size, size),
                method=Image.Resampling.LANCZOS,
            )
            rounded = _round_corners(fitted, max(8, size // 5))
        cache_dir.mkdir(parents=True, exist_ok=True)
        rounded.save(target, format="PNG")
        return target
    except (OSError, ValueError, urllib.error.URLError):
        return None
