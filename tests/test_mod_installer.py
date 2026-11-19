from __future__ import annotations

import zipfile
from pathlib import Path

import py7zr
import pytest

from src.core.mod_installer import (
    install_mod_archive,
    install_mod_zip,
    parse_dropped_archive_paths,
)


def test_install_single_and_multiple_mod_folders(tmp_path: Path) -> None:
    modpack = tmp_path / "modpacks" / "Default"
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Wrapper/ModA/manifest.json", '{"Name": "ModA"}')
        zf.writestr("Wrapper/ModA/ModA.dll", "binary")
        zf.writestr("Wrapper/ModB/manifest.json", '{"Name": "ModB"}')

    installed = install_mod_zip(archive, modpack)
    assert sorted(installed) == ["ModA", "ModB"]
    assert (modpack / "ModA" / "ModA.dll").is_file()
    assert (modpack / "ModB" / "manifest.json").is_file()


def test_install_root_level_manifest_uses_archive_stem(tmp_path: Path) -> None:
    modpack = tmp_path / "modpacks" / "Default"
    archive = tmp_path / "SoloMod.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", '{"Name": "SoloMod"}')

    installed = install_mod_zip(archive, modpack)
    assert installed == ["SoloMod"]
    assert (modpack / "SoloMod" / "manifest.json").is_file()


@pytest.mark.parametrize(
    "malicious_entry",
    [
        "../../escape.txt",
        "ModA/../../../escape.txt",
        "/etc/passwd",
        "\\Windows\\System32\\evil.dll",
        "C:\\evil.txt",
    ],
)
def test_install_mod_zip_blocks_zip_slip(tmp_path: Path, malicious_entry: str) -> None:
    modpack = tmp_path / "modpacks" / "Default"
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("ModA/manifest.json", '{"Name": "ModA"}')
        zf.writestr(malicious_entry, "pwned")

    with pytest.raises(ValueError, match="Unsafe archive path"):
        install_mod_zip(archive, modpack)

    assert not (tmp_path / "escape.txt").exists()
    assert not (modpack / "ModA").exists()


def test_install_mod_zip_rejects_archive_without_manifest(tmp_path: Path) -> None:
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "no manifest here")

    with pytest.raises(ValueError, match="No manifest.json"):
        install_mod_zip(archive, tmp_path / "modpack")


def test_install_7z_archive_extracts_mod_and_blocks_traversal(tmp_path: Path) -> None:
    modpack = tmp_path / "modpacks" / "Default"
    src_mod = tmp_path / "src_mod" / "My7zMod"
    src_mod.mkdir(parents=True)
    (src_mod / "manifest.json").write_text('{"Name": "My7zMod"}', encoding="utf-8")

    archive_7z = tmp_path / "my7zmod.7z"
    with py7zr.SevenZipFile(archive_7z, "w") as szf:
        szf.writeall(src_mod, "My7zMod")

    installed = install_mod_archive(archive_7z, modpack)
    assert installed == ["My7zMod"]
    assert (modpack / "My7zMod" / "manifest.json").is_file()

    # Corrupt / unsupported file fails cleanly
    bad_file = tmp_path / "not_an_archive.rar"
    bad_file.write_text("not a zip or 7z", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid or corrupted .rar archive"):
        install_mod_archive(bad_file, modpack)


def test_parse_dropped_archive_paths_handles_braces_and_filters_extensions(
    tmp_path: Path,
) -> None:
    zip_spaces = tmp_path / "mod with spaces.zip"
    mod_7z = tmp_path / "pack.7z"
    mod_rar = tmp_path / "legacy.rar"
    ignored_txt = tmp_path / "notes.txt"
    zip_spaces.write_text("", encoding="utf-8")
    mod_7z.write_text("", encoding="utf-8")
    mod_rar.write_text("", encoding="utf-8")
    ignored_txt.write_text("", encoding="utf-8")

    raw = f"{{{zip_spaces}}} {mod_7z} {mod_rar} {ignored_txt} {tmp_path / 'missing.zip'}"
    parsed = parse_dropped_archive_paths(raw)
    assert parsed == [zip_spaces, mod_7z, mod_rar]
