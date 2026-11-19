from __future__ import annotations

from pathlib import Path

from src.core.asset_conflicts import (
    detect_asset_conflicts,
    extract_content_patcher_targets,
    format_asset_conflicts,
)
from src.core.mod_scanner import ModInfo


def test_extract_content_patcher_targets_handles_comments_and_multi_targets(
    tmp_path: Path,
) -> None:
    mod_dir = tmp_path / "CP_Pack"
    mod_dir.mkdir()
    (mod_dir / "content.json").write_text(
        "\ufeff{\n"
        "  // Comment\n"
        '  "Format": "2.0.0",\n'
        '  "Changes": [\n'
        '    {"Action": "EditImage", "Target": "Portraits/Abigail, Portraits/Sam",},\n'
        '    {"Action": "EditData", "Target": "Data/Objects"},\n'
        "  ]\n"
        "}\n",
        encoding="utf-8",
    )

    targets = extract_content_patcher_targets(mod_dir)
    assert set(targets.keys()) == {"portraits/abigail", "portraits/sam", "data/objects"}


def test_detect_asset_conflicts_flags_overlapping_enabled_mods(tmp_path: Path) -> None:
    mod_a = tmp_path / "ModA"
    mod_b = tmp_path / "ModB"
    mod_c = tmp_path / "ModC"
    for d in (mod_a, mod_b, mod_c):
        d.mkdir()

    (mod_a / "content.json").write_text(
        '{"Changes": [{"Target": "Portraits/Abigail"}, {"Target": "Maps/Town"}]}',
        encoding="utf-8",
    )
    (mod_b / "content.json").write_text(
        '{"Changes": [{"Target": "portraits/abigail"}]}',
        encoding="utf-8",
    )
    (mod_c / "content.json").write_text(
        '{"Changes": [{"Target": "Maps/Town"}]}',
        encoding="utf-8",
    )

    mods = [
        ModInfo(folder_name="ModA", name="Mod A", version="1.0", path=mod_a),
        ModInfo(folder_name="ModB", name="Mod B", version="1.0", path=mod_b),
        ModInfo(folder_name="ModC", name="Mod C", version="1.0", path=mod_c),
    ]

    # ModC is disabled, so only Portraits/Abigail should conflict
    conflicts = detect_asset_conflicts(mods, {"ModA", "ModB"})
    assert len(conflicts) == 1
    assert conflicts[0].target.lower() == "portraits/abigail"
    assert [m.folder_name for m in conflicts[0].mods] == ["ModA", "ModB"]
    assert "Mod A, Mod B" in format_asset_conflicts(conflicts)
