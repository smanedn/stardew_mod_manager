from __future__ import annotations

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


def test_corrupted_config_falls_back_to_default(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{not valid json", encoding="utf-8")
    cfg = ConfigManager(cfg_path)
    assert cfg.active_profile == "Default"


def test_profile_lifecycle_and_persistence(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = ConfigManager(cfg_path)
    pid = cfg.create_profile("Expanded", "Stardew Valley Expanded")
    cfg.active_profile = pid
    cfg.set_enabled_mods(["ContentPatcher", "ContentPatcher", "SMAPI"], pid)

    reloaded = ConfigManager(cfg_path)
    assert reloaded.active_profile == "Expanded"
    assert reloaded.get_enabled_mods() == ["ContentPatcher", "SMAPI"]

    reloaded.delete_profile("Expanded")
    assert reloaded.active_profile == "Default"


def test_cannot_delete_last_profile(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    with pytest.raises(ValueError):
        cfg.delete_profile("Default")


@pytest.mark.parametrize("bad_name", ["", "   ", ".", "..", "bad/name", "a:b", "end."])
def test_validate_profile_name_rejects_invalid(bad_name: str) -> None:
    with pytest.raises(ValueError):
        validate_profile_name(bad_name)


def test_export_and_import_profile(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.create_profile("Cozy")
    cfg.set_enabled_mods(["ModA", "ModB"], "Cozy")

    export_file = tmp_path / "cozy.json"
    cfg.export_profile(export_file, "Cozy")

    imported_id = cfg.import_profile(export_file)
    assert imported_id == "Cozy_1"
    assert cfg.get_enabled_mods(imported_id) == ["ModA", "ModB"]
