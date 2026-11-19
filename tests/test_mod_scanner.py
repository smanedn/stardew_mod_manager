from __future__ import annotations

from pathlib import Path

from src.core.mod_scanner import scan_mod_pool


def test_scan_mod_pool_parses_bom_comments_trailing_commas_and_escaped_quotes(
    tmp_path: Path,
) -> None:
    pool = tmp_path / "modpacks" / "Default"
    mod_dir = pool / "ContentPatcher"
    mod_dir.mkdir(parents=True)
    (mod_dir / "manifest.json").write_text(
        "\ufeff{\n"
        "  // Line comment\n"
        '  "Name": "Content \\"Patcher\\"",\n'
        '  "Author": "Pathoschild",\n'
        '  "Version": "2.0.0",\n'
        '  "Description": "Loads content packs.",\n'
        '  "MinimumApiVersion": "4.0.0",\n'
        '  "UpdateKeys": ["Nexus:1915", "http://example.com//keep-url",],\n'
        "  /* Block comment */\n"
        "}\n",
        encoding="utf-8",
    )

    mods = scan_mod_pool(pool)
    assert len(mods) == 1
    assert mods[0].name == 'Content "Patcher"'
    assert mods[0].author == "Pathoschild"
    assert mods[0].version == "2.0.0"
    assert mods[0].description == "Loads content packs."
    assert mods[0].minimum_api_version == "4.0.0"
    assert mods[0].error is None


def test_scan_mod_pool_handles_missing_non_object_and_malformed_manifests(
    tmp_path: Path,
) -> None:
    pool = tmp_path / "modpacks"
    (pool / "MissingManifest").mkdir(parents=True)

    broken = pool / "BrokenManifest"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{broken", encoding="utf-8")

    array_manifest = pool / "ArrayManifest"
    array_manifest.mkdir(parents=True)
    (array_manifest / "manifest.json").write_text('["not", "an", "object"]', encoding="utf-8")

    empty_fields = pool / "EmptyFields"
    empty_fields.mkdir(parents=True)
    (empty_fields / "manifest.json").write_text('{"Name": "  ", "Version": ""}', encoding="utf-8")

    (pool / ".hidden").mkdir(parents=True)
    (pool / "readme.txt").write_text("ignore me", encoding="utf-8")

    mods = scan_mod_pool(pool)
    assert [m.folder_name for m in mods] == [
        "ArrayManifest",
        "BrokenManifest",
        "EmptyFields",
        "MissingManifest",
    ]
    assert mods[0].error is not None
    assert mods[1].error is not None
    assert mods[2].name == "EmptyFields" and mods[2].version == "Unknown"
    assert not mods[3].has_manifest


def test_scan_mod_pool_nonexistent_dir_returns_empty(tmp_path: Path) -> None:
    assert scan_mod_pool(tmp_path / "does_not_exist") == []


def test_scan_mod_pool_discovers_nested_modpack_folders(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "SVE"
    (pool / "SVE Pack" / "[CP] SVE").mkdir(parents=True)
    (pool / "SVE Pack" / "[CP] SVE" / "manifest.json").write_text(
        '{"Name": "Stardew Valley Expanded", "Version": "1.15.0"}', encoding="utf-8"
    )
    # Nested asset folder inside a mod must NOT be scanned as a separate mod
    (pool / "SVE Pack" / "[CP] SVE" / "assets").mkdir()
    (pool / "SVE Pack" / "[CP] SVE" / "assets" / "manifest.json").write_text(
        '{"Name": "ShouldBeIgnored"}', encoding="utf-8"
    )
    (pool / "SVE Pack" / "[FTM] SVE").mkdir(parents=True)
    (pool / "SVE Pack" / "[FTM] SVE" / "manifest.json").write_text(
        '{"Name": "FTM SVE", "Version": "1.0.0"}', encoding="utf-8"
    )

    mods = scan_mod_pool(pool)
    assert [m.folder_name for m in mods] == [
        "SVE Pack/[CP] SVE",
        "SVE Pack/[FTM] SVE",
    ]
    assert mods[0].name == "Stardew Valley Expanded"


def test_scan_mod_pool_parses_content_pack_for_as_required_dependency(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "Default"
    pack_dir = pool / "[CP] MyPack"
    pack_dir.mkdir(parents=True)
    (pack_dir / "manifest.json").write_text(
        '{"Name": "My Pack", "Version": "1.0.0", '
        '"ContentPackFor": {"UniqueID": "Pathoschild.ContentPatcher", "MinimumVersion": "2.0.0"}}',
        encoding="utf-8",
    )

    mods = scan_mod_pool(pool)
    assert len(mods) == 1
    assert mods[0].content_pack_for == "Pathoschild.ContentPatcher"
    assert len(mods[0].dependencies) == 1
    assert mods[0].dependencies[0].unique_id == "Pathoschild.ContentPatcher"
    assert mods[0].dependencies[0].is_required is True
    assert mods[0].dependencies[0].minimum_version == "2.0.0"
