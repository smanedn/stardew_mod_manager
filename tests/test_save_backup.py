from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.core.save_backup import (
    create_save_backup,
    list_save_backups,
    restore_save_backup,
)


def test_create_list_and_restore_save_backup(tmp_path: Path) -> None:
    saves_dir = tmp_path / "Saves"
    farm_dir = saves_dir / "Farm_12345"
    farm_dir.mkdir(parents=True)
    (farm_dir / "SaveGameInfo").write_text("<save>v1</save>", encoding="utf-8")

    backups_dir = tmp_path / "save_backups"
    archive = create_save_backup(saves_dir, backups_dir, label="before SVE!")
    assert archive.is_file()
    assert "before_SVE" in archive.name

    listed = list_save_backups(backups_dir)
    assert len(listed) == 1
    assert listed[0].name == archive.name

    # Mutate save and restore
    (farm_dir / "SaveGameInfo").write_text("<save>corrupted</save>", encoding="utf-8")
    restore_save_backup(archive, saves_dir)
    assert (farm_dir / "SaveGameInfo").read_text(encoding="utf-8") == "<save>v1</save>"


def test_restore_save_backup_blocks_zip_slip(tmp_path: Path) -> None:
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../escape.txt", "pwned")

    with pytest.raises(ValueError, match="Unsafe archive path"):
        restore_save_backup(evil_zip, tmp_path / "Saves")
    assert not (tmp_path / "escape.txt").exists()


def test_create_save_backup_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_save_backup(tmp_path / "missing_saves", tmp_path / "backups")
