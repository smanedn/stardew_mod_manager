from __future__ import annotations

import sys
from pathlib import Path

from src.core.launcher import launch_game, validate_game_path


def test_validate_game_path_states(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent"
    assert validate_game_path(missing) == (False, False, "Folder not found")

    game = tmp_path / "Stardew Valley"
    game.mkdir()
    assert validate_game_path(game) == (False, False, "No game executables found")

    vanilla_name = "Stardew Valley.exe" if sys.platform == "win32" else "StardewValley"
    smapi_name = "StardewModdingAPI.exe" if sys.platform == "win32" else "StardewModdingAPI"

    (game / vanilla_name).write_text("", encoding="utf-8")
    assert validate_game_path(game) == (True, False, "Vanilla ready (SMAPI missing)")

    (game / smapi_name).write_text("", encoding="utf-8")
    assert validate_game_path(game) == (True, True, "SMAPI + Vanilla ready")


def test_launch_game_reports_missing_executable(tmp_path: Path) -> None:
    game = tmp_path / "Stardew Valley"
    game.mkdir()
    ok, msg = launch_game(str(game), modded=True)
    assert not ok
    assert "Could not find" in msg
