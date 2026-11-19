from __future__ import annotations

import sys
from pathlib import Path

from src.core.shortcuts import build_shortcut_target, create_modpack_shortcut


def test_build_shortcut_target_frozen_and_script(tmp_path: Path) -> None:
    exe, args, workdir = build_shortcut_target(
        "Expanded",
        is_frozen=True,
        executable=str(tmp_path / "SVModManager.exe"),
    )
    assert exe.endswith("SVModManager.exe")
    assert args == ["--launch-profile", "Expanded"]
    assert Path(workdir) == tmp_path.resolve()

    script = tmp_path / "main.py"
    exe2, args2, workdir2 = build_shortcut_target(
        "Cozy",
        is_frozen=False,
        executable=sys.executable,
        script_path=script,
    )
    assert Path(exe2).exists()
    assert args2 == [str(script.resolve()), "--launch-profile", "Cozy"]
    assert Path(workdir2) == tmp_path.resolve()


def test_create_modpack_shortcut_writes_file(tmp_path: Path) -> None:
    created = create_modpack_shortcut(
        "lite",
        shortcut_name="Stardew Lite",
        desktop_dir=tmp_path,
    )
    assert created.is_file()
    assert created.parent == tmp_path
