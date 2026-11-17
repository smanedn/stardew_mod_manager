from __future__ import annotations

from pathlib import Path

from src.core.mod_manager import link_game_mods, sync_profile, unlink_game_mods


def test_sync_link_and_unlink_preserves_mod_pool(tmp_path: Path) -> None:
    pool = tmp_path / "modpacks" / "Default"
    profiles = tmp_path / "profiles"
    game = tmp_path / "Stardew Valley"

    (pool / "ModA").mkdir(parents=True)
    (pool / "ModA" / "manifest.json").write_text('{"Name": "ModA"}', encoding="utf-8")
    (pool / "ModB").mkdir(parents=True)
    (game / "Mods" / "LegacyMod").mkdir(parents=True)

    profile_dir = sync_profile("Default", ["ModA"], pool, profiles)
    assert (profile_dir / "ModA" / "manifest.json").is_file()
    assert not (profile_dir / "ModB").exists()

    # Re-syncing with same mods keeps existing link working
    sync_profile("Default", ["ModA"], pool, profiles)
    assert (profile_dir / "ModA").exists()

    ok, msg = link_game_mods(game, profile_dir)
    assert ok, msg
    assert (game / "Mods_Backup" / "LegacyMod").is_dir()
    assert (game / "Mods" / "ModA").exists()

    ok, msg = unlink_game_mods(game)
    assert ok, msg
    assert not (game / "Mods").exists()
    assert (pool / "ModA" / "manifest.json").is_file()
