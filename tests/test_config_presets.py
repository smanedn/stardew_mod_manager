from __future__ import annotations

from pathlib import Path

from src.core.config_presets import restore_config_preset, save_config_preset


def test_save_and_restore_config_preset(tmp_path: Path) -> None:
    modpack = tmp_path / "modpack"
    preset = tmp_path / "preset"
    (modpack / "ModA").mkdir(parents=True)
    (modpack / "ModB").mkdir(parents=True)
    (modpack / "ModA" / "config.json").write_text('{"Cheats": true}', encoding="utf-8")

    saved = save_config_preset(modpack, preset)
    assert saved == 1
    assert (preset / "ModA" / "config.json").read_text(encoding="utf-8") == '{"Cheats": true}'

    # Modify live config then restore
    (modpack / "ModA" / "config.json").write_text('{"Cheats": false}', encoding="utf-8")
    restored = restore_config_preset(modpack, preset)
    assert restored == 1
    assert (modpack / "ModA" / "config.json").read_text(encoding="utf-8") == '{"Cheats": true}'
