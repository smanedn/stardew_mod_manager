from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.core.mod_installer import install_mod_zip


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
