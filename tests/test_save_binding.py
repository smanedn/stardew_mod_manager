from __future__ import annotations

from pathlib import Path

from src.core.config import ConfigManager
from src.core.save_binding import list_farm_saves


def test_list_farm_saves_parses_save_game_info_xml(tmp_path: Path) -> None:
    saves_dir = tmp_path / "Saves"
    farm1 = saves_dir / "Meadow_12345"
    farm1.mkdir(parents=True)
    (farm1 / "SaveGameInfo").write_text(
        "<Farmer><name>Loren</name><farmName>Meadow</farmName></Farmer>",
        encoding="utf-8",
    )

    farm2 = saves_dir / "River_999"
    farm2.mkdir(parents=True)

    farms = list_farm_saves(saves_dir)
    assert len(farms) == 2
    assert farms[0].farm_name == "Meadow"
    assert farms[0].farmer_name == "Loren"
    assert farms[0].display_label == "Meadow Farm (Loren)"
    assert farms[1].farm_name == "River"


def test_config_save_bindings_lifecycle(tmp_path: Path) -> None:
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.create_profile("Expanded")
    cfg.bind_save("Meadow_12345", "Expanded")
    assert cfg.get_saves_for_profile("Expanded") == ["Meadow_12345"]

    new_id = cfg.rename_profile("Expanded", "SVE")
    assert cfg.get_saves_for_profile(new_id) == ["Meadow_12345"]

    cfg.delete_profile("SVE")
    assert cfg.save_bindings == {}
