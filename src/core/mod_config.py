"""Load, validate, and save per-mod config.json files."""

from __future__ import annotations

import json
from pathlib import Path


def get_mod_config_path(mod_path: Path) -> Path:
    """Return the path to a mod's config.json file."""
    return mod_path / "config.json"


def load_mod_config_text(mod_path: Path) -> str:
    """Read and pretty-print a mod's config.json, or return raw text if unparseable."""
    cfg_path = get_mod_config_path(mod_path)
    if not cfg_path.is_file():
        raise FileNotFoundError(f"No config.json found in {mod_path}")

    raw = cfg_path.read_text(encoding="utf-8-sig")
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    except json.JSONDecodeError:
        return raw


def save_mod_config_text(mod_path: Path, raw_text: str) -> None:
    """Validate JSON syntax and write formatted config.json to disk."""
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    cfg_path = get_mod_config_path(mod_path)
    cfg_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
