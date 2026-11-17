from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.core.launcher import launch_game, validate_game_path


@pytest.mark.parametrize("bad_path", ["", "   ", "nonexistent_dir"])
def test_validate_game_path_invalid_inputs(tmp_path: Path, bad_path: str) -> None:
    target = tmp_path / bad_path if bad_path == "nonexistent_dir" else bad_path
    assert validate_game_path(target) == (False, False, "Folder not found")


def test_validate_game_path_states(tmp_path: Path) -> None:
    game = tmp_path / "Stardew Valley"
    game.mkdir()
    assert validate_game_path(game) == (False, False, "No game executables found")

    vanilla_name = "Stardew Valley.exe" if sys.platform == "win32" else "StardewValley"
    smapi_name = "StardewModdingAPI.exe" if sys.platform == "win32" else "StardewModdingAPI"

    (game / vanilla_name).write_text("", encoding="utf-8")
    assert validate_game_path(game) == (True, False, "Vanilla ready (SMAPI missing)")

    (game / smapi_name).write_text("", encoding="utf-8")
    assert validate_game_path(game) == (True, True, "SMAPI + Vanilla ready")


def test_launch_game_reports_missing_dir_and_executable(tmp_path: Path) -> None:
    ok, msg = launch_game(str(tmp_path / "missing"), modded=False)
    assert not ok
    assert "not found" in msg.lower()

    game = tmp_path / "Stardew Valley"
    game.mkdir()
    ok, msg = launch_game(str(game), modded=True)
    assert not ok
    assert "Could not find" in msg


def test_launch_game_invokes_popen_and_handles_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = tmp_path / "Stardew Valley"
    game.mkdir()
    vanilla_name = "Stardew Valley.exe" if sys.platform == "win32" else "StardewValley"
    smapi_name = "StardewModdingAPI.exe" if sys.platform == "win32" else "StardewModdingAPI"
    (game / vanilla_name).write_text("", encoding="utf-8")
    (game / smapi_name).write_text("", encoding="utf-8")

    calls: list[tuple[list[str], str]] = []

    def fake_popen(args: list[str], cwd: str) -> Any:
        calls.append((args, cwd))
        return None

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    ok, msg = launch_game(str(game), modded=True)
    assert ok and smapi_name in msg
    assert calls[-1] == ([str(game / smapi_name)], str(game))

    ok, msg = launch_game(str(game), modded=False)
    assert ok and vanilla_name in msg
    assert calls[-1] == ([str(game / vanilla_name)], str(game))

    def failing_popen(args: list[str], cwd: str) -> Any:
        raise OSError("permission denied")

    monkeypatch.setattr(subprocess, "Popen", failing_popen)
    ok, msg = launch_game(str(game), modded=True)
    assert not ok and "permission denied" in msg
