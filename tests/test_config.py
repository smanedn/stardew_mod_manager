from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.config import ConfigManager, validate_profile_name


def test_default_config_created_when_missing(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = ConfigManager(cfg_path)
    assert cfg_path.is_file()
    assert cfg.active_profile == "Default"
    assert cfg.appearance_mode == "dark"
    assert "Default" in cfg.profiles


@pytest.mark.parametrize("raw_content", ["{not valid json", "[]", '"just a string"', "123"])
def test_invalid_config_falls_back_to_default(tmp_path: Path, raw_content: str) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(raw_content, encoding="utf-8")
    cfg = ConfigManager(cfg_path)
    assert cfg.active_profile == "Default"
    assert "Default" in cfg.profiles


def test_config_normalization_sanitizes_invalid_fields(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "game_path": 12345,
                "active_profile": "NonExistent",
                "appearance_mode": "neon",
                "profiles": {
                    "BadProfile": "not-a-dict",
                    "Cozy": {
                        "name": "   ",
                        "enabled_mods": ["ModA", 99, None, "ModB"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    cfg = ConfigManager(cfg_path)
    assert isinstance(cfg.game_path, str)
    assert cfg.appearance_mode == "dark"
    assert cfg.active_profile == "Cozy"
    assert cfg.profiles["Cozy"]["name"] == "Cozy"
    assert cfg.get_enabled_mods("Cozy") == ["ModA", "ModB"]


def test_profile_lifecycle_and_persistence(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = ConfigManager(cfg_path)
    pid = cfg.create_profile("Expanded", "Stardew Valley Expanded")
    cfg.active_profile = pid
    cfg.appearance_mode = "light"
    cfg.set_enabled_mods(["ContentPatcher", "ContentPatcher", "SMAPI"], pid)

    reloaded = ConfigManager(cfg_path)
    assert reloaded.active_profile == "Expanded"
    assert reloaded.appearance_mode == "light"
    assert reloaded.get_enabled_mods() == ["ContentPatcher", "SMAPI"]

    reloaded.delete_profile("Expanded")
    assert reloaded.active_profile == "Default"


def test_cannot_delete_last_profile(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    with pytest.raises(ValueError):
        cfg.delete_profile("Default")


@pytest.mark.parametrize("bad_name", ["", "   ", ".", "..", "bad/name", "a:b", "a*b", "end."])
def test_validate_profile_name_rejects_invalid(bad_name: str) -> None:
    with pytest.raises(ValueError):
        validate_profile_name(bad_name)


def test_validate_profile_name_strips_whitespace() -> None:
    assert validate_profile_name("  Cozy Pack  ") == "Cozy Pack"


def test_export_and_import_profile_round_trip(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.create_profile("Cozy", "Cozy Pack")
    cfg.set_enabled_mods(["ModA", "ModB"], "Cozy")

    export_file = tmp_path / "cozy.json"
    cfg.export_profile(export_file, "Cozy")

    imported_1 = cfg.import_profile(export_file)
    imported_2 = cfg.import_profile(export_file)
    assert imported_1 == "Cozy_1"
    assert imported_2 == "Cozy_2"
    assert cfg.get_enabled_mods(imported_1) == ["ModA", "ModB"]
    assert cfg.profiles[imported_1]["name"] == "Cozy Pack"


def test_import_invalid_profile_raises(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError):
        cfg.import_profile(bad_file)
