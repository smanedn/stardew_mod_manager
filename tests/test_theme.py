from __future__ import annotations

from pathlib import Path

from src.core.config import ConfigManager
from src.ui.theme import COLORS, THEME_NAMES, THEMES, apply_theme, sanitize_custom_theme


def test_builtin_themes_and_apply_theme_in_place() -> None:
    assert len(THEMES) >= 10
    assert "Custom" in THEME_NAMES

    original_dict_id = id(COLORS)
    applied = apply_theme("Pelican Town")
    assert applied == "Pelican Town"
    assert id(COLORS) == original_dict_id
    assert COLORS["accent"][0] == "#3E7B27"

    # Unknown theme falls back to Midnight
    assert apply_theme("NonExistentTheme") == "Midnight"
    assert COLORS["accent"][0] == "#2563EB"


def test_custom_theme_sanitization_and_config_persistence(tmp_path: Path) -> None:
    sanitized = sanitize_custom_theme(
        {
            "mode": "light",
            "accent": "#ff5500",
            "bg_app": "not-a-hex",
        }
    )
    assert sanitized["mode"] == "light"
    assert sanitized["accent"] == "#FF5500"
    assert sanitized["bg_app"] == "#11141A"

    cfg_path = tmp_path / "config.json"
    cfg = ConfigManager(cfg_path)
    cfg.theme = "Custom"
    cfg.custom_theme = sanitized

    reloaded = ConfigManager(cfg_path)
    assert reloaded.theme == "Custom"
    assert reloaded.custom_theme["accent"] == "#FF5500"
    assert reloaded.custom_theme["mode"] == "light"

    # Applying custom theme updates COLORS
    assert apply_theme("Custom", reloaded.custom_theme) == "Custom"
    assert COLORS["accent"][0] == "#FF5500"
