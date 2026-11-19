from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.core.modpack_bundle import export_modpack_bundle, import_modpack_bundle


def test_export_and_import_modpack_bundle_round_trip(tmp_path: Path) -> None:
    src_packs = tmp_path / "src_packs"
    mod_a = src_packs / "Cozy" / "ModA"
    mod_a.mkdir(parents=True)
    (mod_a / "manifest.json").write_text('{"Name": "ModA"}', encoding="utf-8")
    (mod_a / "config.json").write_text('{"CheatMode": true}', encoding="utf-8")

    bundle_zip = tmp_path / "cozy_bundle.zip"
    export_modpack_bundle(bundle_zip, "Cozy", "Cozy Pack", src_packs / "Cozy", ["ModA"])
    assert bundle_zip.is_file()

    dest_packs = tmp_path / "dest_packs"
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.create_profile("Cozy")

    # Collision with existing "Cozy" should create "Cozy_1"
    imported_id = import_modpack_bundle(bundle_zip, dest_packs, cfg)
    assert imported_id == "Cozy_1"
    assert cfg.get_enabled_mods("Cozy_1") == ["ModA"]
    assert (dest_packs / "Cozy_1" / "ModA" / "config.json").read_text(encoding="utf-8") == (
        '{"CheatMode": true}'
    )


def test_import_modpack_bundle_blocks_zip_slip(tmp_path: Path) -> None:
    evil_zip = tmp_path / "evil_bundle.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../escape.txt", "pwned")

    cfg = ConfigManager(tmp_path / "config.json")
    with pytest.raises(ValueError, match="Unsafe archive path"):
        import_modpack_bundle(evil_zip, tmp_path / "packs", cfg)
    assert not (tmp_path / "escape.txt").exists()
