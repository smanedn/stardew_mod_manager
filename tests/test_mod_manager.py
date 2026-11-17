from __future__ import annotations

import shutil
from pathlib import Path

from src.core.mod_manager import link_game_mods, sync_profile, unlink_game_mods


def test_mods_backup_increments_when_backup_already_exists(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "Default"
    profiles = tmp_path / "profiles"
    game = tmp_path / "Stardew Valley"

    (pool / "ModA").mkdir(parents=True)
    (game / "Mods_Backup").mkdir(parents=True)
    (game / "Mods" / "UnmanagedMod").mkdir(parents=True)

    profile_dir = sync_profile("Default", ["ModA"], pool, profiles)
    ok, msg = link_game_mods(game, profile_dir)
    assert ok, msg
    assert "Mods_Backup_1" in msg
    assert (game / "Mods_Backup_1" / "UnmanagedMod").is_dir()
    assert (game / "Mods" / "ModA").is_dir()


def test_repeated_profile_switching_preserves_mods_and_avoids_extra_backups(
    tmp_path: Path,
) -> None:
    modpacks = tmp_path / "modpacks"
    profiles = tmp_path / "profiles"
    game = tmp_path / "Stardew Valley"
    game.mkdir()

    (modpacks / "PackA" / "ModA").mkdir(parents=True)
    (modpacks / "PackB" / "ModB").mkdir(parents=True)

    dir_a = sync_profile("PackA", ["ModA"], modpacks / "PackA", profiles)
    ok, _ = link_game_mods(game, dir_a)
    assert ok
    assert (game / "Mods" / "ModA").is_dir()

    dir_b = sync_profile("PackB", ["ModB"], modpacks / "PackB", profiles)
    ok, _ = link_game_mods(game, dir_b)
    assert ok
    assert (game / "Mods" / "ModB").is_dir()
    assert not (game / "Mods" / "ModA").exists()

    # Switch back to PackA
    dir_a_again = sync_profile("PackA", ["ModA"], modpacks / "PackA", profiles)
    ok, _ = link_game_mods(game, dir_a_again)
    assert ok
    assert (game / "Mods" / "ModA").is_dir()
    assert not (game / "Mods_Backup").exists()


def test_dangling_links_are_cleaned_up_safely(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "Default"
    profiles = tmp_path / "profiles"
    game = tmp_path / "Stardew Valley"
    game.mkdir()

    mod_a = pool / "ModA"
    mod_b = pool / "ModB"
    mod_a.mkdir(parents=True)
    mod_b.mkdir(parents=True)

    profile_dir = sync_profile("Default", ["ModA", "ModB"], pool, profiles)
    ok, _ = link_game_mods(game, profile_dir)
    assert ok

    # Delete ModA from disk so profile_dir/ModA becomes a dangling link
    shutil.rmtree(mod_a)
    sync_profile("Default", ["ModA", "ModB"], pool, profiles)
    assert not (profile_dir / "ModA").exists()
    assert (profile_dir / "ModB").is_dir()

    # Delete entire profile_dir so game/Mods becomes a dangling link
    shutil.rmtree(profile_dir)
    ok, msg = unlink_game_mods(game)
    assert ok, msg
    assert not (game / "Mods").exists()


def test_vanilla_unlink_cases_and_invalid_paths(tmp_path: Path) -> None:
    # Missing game path
    ok, msg = unlink_game_mods(tmp_path / "missing_game")
    assert not ok
    assert "not found" in msg.lower()

    ok, msg = link_game_mods(tmp_path / "missing_game", tmp_path)
    assert not ok

    game = tmp_path / "Stardew Valley"
    game.mkdir()

    # Missing profile dir
    ok, msg = link_game_mods(game, tmp_path / "missing_profile")
    assert not ok

    # No Mods folder yet
    ok, msg = unlink_game_mods(game)
    assert ok
    assert "no mods folder" in msg.lower()

    # Unmanaged Mods folder gets backed up on vanilla unlink
    (game / "Mods" / "SomeMod").mkdir(parents=True)
    ok, msg = unlink_game_mods(game)
    assert ok
    assert not (game / "Mods").exists()
    assert (game / "Mods_Backup" / "SomeMod").is_dir()
