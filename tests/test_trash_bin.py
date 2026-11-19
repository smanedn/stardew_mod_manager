from __future__ import annotations

from pathlib import Path

from src.core.mod_manager import (
    empty_trash,
    list_trashed_mods,
    restore_trashed_mod,
    uninstall_mod,
)


def test_trash_bin_uninstall_restore_and_empty(tmp_path: Path) -> None:
    modpack = tmp_path / "modpack"
    trash = tmp_path / "trash"
    mod_dir = modpack / "SampleMod"
    mod_dir.mkdir(parents=True)
    (mod_dir / "manifest.json").write_text('{"Name": "Sample"}', encoding="utf-8")

    entry = uninstall_mod("SampleMod", modpack, profile_id="lite", trash_root=trash)
    assert entry is not None
    assert not mod_dir.exists()

    items = list_trashed_mods(trash)
    assert len(items) == 1
    assert items[0].folder_name == "SampleMod"
    assert items[0].profile_id == "lite"

    restored = restore_trashed_mod(items[0].entry_dir, modpack)
    assert restored == "SampleMod"
    assert (mod_dir / "manifest.json").is_file()
    assert list_trashed_mods(trash) == []

    # Trash again and empty
    uninstall_mod("SampleMod", modpack, profile_id="lite", trash_root=trash)
    assert len(list_trashed_mods(trash)) == 1
    assert empty_trash(trash) == 1
    assert list_trashed_mods(trash) == []
