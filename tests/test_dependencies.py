from __future__ import annotations

from pathlib import Path

from src.core.dependencies import analyze_mod_dependencies, format_issue_summary
from src.core.mod_scanner import ModDependency, ModInfo


def test_missing_required_dependency_detected_and_optional_ignored(tmp_path: Path) -> None:
    mods = [
        ModInfo(
            folder_name="Expansion",
            name="Expansion",
            version="1.0.0",
            path=tmp_path / "Expansion",
            unique_id="Author.Expansion",
            dependencies=(
                ModDependency(unique_id="Pathoschild.ContentPatcher", is_required=True),
                ModDependency(unique_id="Optional.Helper", is_required=False),
            ),
        ),
        ModInfo(
            folder_name="CP",
            name="Content Patcher",
            version="2.0.0",
            path=tmp_path / "CP",
            unique_id="pathoschild.contentpatcher",  # case-insensitive match
        ),
    ]

    # When CP is disabled, Expansion has a missing required dep
    issues = analyze_mod_dependencies(mods, {"Expansion"})
    assert "Expansion" in issues
    assert len(issues["Expansion"]) == 1
    assert issues["Expansion"][0].kind == "missing_dep"
    assert "ContentPatcher" in format_issue_summary(issues, mods)

    # When CP is enabled, no issues (optional dep is not required)
    assert analyze_mod_dependencies(mods, {"Expansion", "CP"}) == {}


def test_duplicate_unique_id_conflict_detected(tmp_path: Path) -> None:
    mods = [
        ModInfo(
            folder_name="ModV1",
            name="Cool Mod",
            version="1.0.0",
            path=tmp_path / "ModV1",
            unique_id="Same.Mod",
        ),
        ModInfo(
            folder_name="ModV2",
            name="Cool Mod Copy",
            version="1.1.0",
            path=tmp_path / "ModV2",
            unique_id="same.mod",
        ),
    ]

    issues = analyze_mod_dependencies(mods, {"ModV1", "ModV2"})
    assert "ModV1" in issues and "ModV2" in issues
    assert issues["ModV1"][0].kind == "duplicate_id"
