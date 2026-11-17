from __future__ import annotations

from pathlib import Path

from src.core.mod_scanner import scan_mod_pool


def test_scan_mod_pool_parses_bom_comments_and_trailing_commas(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "Default"
    mod_dir = pool / "ContentPatcher"
    mod_dir.mkdir(parents=True)
    (mod_dir / "manifest.json").write_text(
        "\ufeff{\n"
        "  // Line comment\n"
        '  "Name": "Content Patcher",\n'
        '  "Author": "Pathoschild",\n'
        '  "Version": "2.0.0",\n'
        '  "UpdateKeys": ["Nexus:1915", "http://example.com//keep-url"],\n'
        "  /* Block comment */\n"
        "}\n",
        encoding="utf-8",
    )

    mods = scan_mod_pool(pool)
    assert len(mods) == 1
    assert mods[0].name == "Content Patcher"
    assert mods[0].author == "Pathoschild"
    assert mods[0].version == "2.0.0"
    assert mods[0].error is None


def test_scan_mod_pool_handles_missing_and_invalid_manifests(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks"
    (pool / "MissingManifest").mkdir(parents=True)
    broken = pool / "BrokenManifest"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{broken", encoding="utf-8")
    (pool / ".hidden").mkdir(parents=True)

    mods = scan_mod_pool(pool)
    assert [m.folder_name for m in mods] == ["BrokenManifest", "MissingManifest"]
    assert mods[0].error is not None
    assert not mods[1].has_manifest
