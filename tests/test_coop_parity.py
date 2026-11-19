from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.coop_parity import (
    FriendModEntry,
    compare_with_friend_modlist,
    load_friend_modlist,
)
from src.core.mod_scanner import ModInfo


def test_load_friend_modlist_parses_and_validates(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"not_mods": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="mods"):
        load_friend_modlist(bad)

    good = tmp_path / "friend.json"
    good.write_text(
        json.dumps(
            {
                "profile": "HostFarm",
                "mods": [
                    {
                        "name": "Content Patcher",
                        "version": "2.0.0",
                        "unique_id": "Pathoschild.ContentPatcher",
                        "folder": "ContentPatcher",
                        "links": ["https://www.nexusmods.com/stardewvalley/mods/1915"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile, mods = load_friend_modlist(good)
    assert profile == "HostFarm"
    assert len(mods) == 1
    assert mods[0].unique_id == "Pathoschild.ContentPatcher"


def test_compare_with_friend_modlist_detects_missing_extra_and_mismatch(tmp_path: Path) -> None:
    local_mods = [
        ModInfo(
            folder_name="CP",
            name="Content Patcher",
            version="2.0.0",
            path=tmp_path / "CP",
            unique_id="Pathoschild.ContentPatcher",
        ),
        ModInfo(
            folder_name="Lookup",
            name="Lookup Anything",
            version="1.50.0",
            path=tmp_path / "Lookup",
            unique_id="Pathoschild.LookupAnything",
        ),
        ModInfo(
            folder_name="ExtraMod",
            name="Extra Mod",
            version="1.0.0",
            path=tmp_path / "ExtraMod",
            unique_id="Author.Extra",
        ),
        ModInfo(
            folder_name="DisabledNeeded",
            name="Disabled Needed",
            version="1.0.0",
            path=tmp_path / "DisabledNeeded",
            unique_id="Author.Needed",
        ),
    ]

    friend_mods = [
        FriendModEntry(
            name="Content Patcher",
            version="2.0.0",
            unique_id="pathoschild.contentpatcher",
        ),
        FriendModEntry(
            name="Lookup Anything",
            version="1.55.0",
            unique_id="Pathoschild.LookupAnything",
        ),
        FriendModEntry(
            name="Disabled Needed",
            version="1.0.0",
            unique_id="Author.Needed",
        ),
        FriendModEntry(
            name="Completely Missing",
            version="3.0.0",
            unique_id="Author.Missing",
        ),
    ]

    report = compare_with_friend_modlist(
        "HostFarm", friend_mods, local_mods, {"CP", "Lookup", "ExtraMod"}
    )
    assert not report.is_in_sync
    assert report.matching_count == 1
    assert [m.folder_name for m in report.extra_mods] == ["ExtraMod"]
    assert len(report.version_mismatches) == 1
    assert report.version_mismatches[0].friend_version == "1.55.0"
    assert len(report.missing_mods) == 2
    assert report.missing_mods[0].local_folder_if_installed == "DisabledNeeded"
    assert report.missing_mods[1].local_folder_if_installed == ""
