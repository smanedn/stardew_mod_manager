"""Dependency and conflict detection for SMAPI mods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.mod_scanner import ModInfo


@dataclass(frozen=True)
class ModIssue:
    """Represents a missing dependency or UniqueID conflict for a mod."""

    kind: Literal["missing_dep", "duplicate_id"]
    message: str


def analyze_mod_dependencies(
    mods: list[ModInfo], enabled_folders: set[str]
) -> dict[str, list[ModIssue]]:
    """Analyze enabled mods for missing required dependencies and duplicate UniqueIDs."""
    issues: dict[str, list[ModIssue]] = {}
    enabled_mods = [m for m in mods if m.folder_name in enabled_folders]

    id_to_mods: dict[str, list[ModInfo]] = {}
    for mod in enabled_mods:
        if mod.unique_id:
            id_to_mods.setdefault(mod.unique_id.lower(), []).append(mod)

    # Duplicate UniqueID conflicts among enabled mods
    for uid_lower, group in id_to_mods.items():
        if len(group) > 1:
            others = ", ".join(m.folder_name for m in group)
            for mod in group:
                issues.setdefault(mod.folder_name, []).append(
                    ModIssue(
                        kind="duplicate_id",
                        message=f"Duplicate UniqueID '{mod.unique_id or uid_lower}' ({others})",
                    )
                )

    # Missing required dependencies for enabled mods
    for mod in enabled_mods:
        for dep in mod.dependencies:
            if not dep.is_required:
                continue
            if dep.unique_id.lower() not in id_to_mods:
                issues.setdefault(mod.folder_name, []).append(
                    ModIssue(
                        kind="missing_dep",
                        message=f"Missing required dependency: {dep.unique_id}",
                    )
                )

    return issues


def format_issue_summary(issues: dict[str, list[ModIssue]], mods: list[ModInfo]) -> str:
    """Format a human-readable summary of all detected dependency/conflict issues."""
    name_map = {m.folder_name: m.name for m in mods}
    lines: list[str] = []
    for folder, mod_issues in issues.items():
        mod_name = name_map.get(folder, folder)
        for issue in mod_issues:
            lines.append(f"• {mod_name}: {issue.message}")
    return "\n".join(lines)
