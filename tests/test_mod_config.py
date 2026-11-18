from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.mod_config import get_mod_config_path, load_mod_config_text, save_mod_config_text


def test_load_and_save_mod_config_round_trip(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyMod"
    mod_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        load_mod_config_text(mod_dir)

    cfg_path = get_mod_config_path(mod_dir)
    cfg_path.write_text('\ufeff{"Enabled":true,"Speed":2}', encoding="utf-8")

    loaded = load_mod_config_text(mod_dir)
    assert json.loads(loaded) == {"Enabled": True, "Speed": 2}
    assert "\n" in loaded

    save_mod_config_text(mod_dir, '{"Enabled": false, "Speed": 5}')
    assert json.loads(cfg_path.read_text(encoding="utf-8")) == {"Enabled": False, "Speed": 5}


def test_save_mod_config_rejects_invalid_json_without_overwriting(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyMod"
    mod_dir.mkdir()
    cfg_path = get_mod_config_path(mod_dir)
    cfg_path.write_text('{"Valid": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        save_mod_config_text(mod_dir, "{not valid json")

    assert json.loads(cfg_path.read_text(encoding="utf-8")) == {"Valid": True}
