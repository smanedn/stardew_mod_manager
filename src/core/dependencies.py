"""Dependency, MinimumVersion, MinimumApiVersion, and conflict detection for SMAPI mods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.mod_scanner import ModInfo
from src.core.updater import is_newer_version


@dataclass(frozen=True)
class ModIssue:
    """Represents a dependency, version, or UniqueID conflict for a mod."""

    kind: Literal["missing_dep", "duplicate_id", "version_too_low", "smapi_version_too_low"]
    message: str


def analyze_mod_dependencies(
    mods: list[ModInfo],
    enabled_folders: set[str],
    smapi_version: str | None = None,
) -> dict[str, list[ModIssue]]:
    """Analyze enabled mods for missing deps, min-version mismatches, and duplicate IDs."""
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

    # Missing required dependencies, dependency MinimumVersion, and SMAPI MinimumApiVersion
    for mod in enabled_mods:
        if (
            smapi_version
            and mod.minimum_api_version
            and is_newer_version(smapi_version, mod.minimum_api_version)
        ):
            issues.setdefault(mod.folder_name, []).append(
                ModIssue(
                    kind="smapi_version_too_low",
                    message=(
                        f"Requires SMAPI >= {mod.minimum_api_version} (installed: {smapi_version})"
                    ),
                )
            )

        for dep in mod.dependencies:
            matched = id_to_mods.get(dep.unique_id.lower())
            if not matched:
                if dep.is_required:
                    issues.setdefault(mod.folder_name, []).append(
                        ModIssue(
                            kind="missing_dep",
                            message=f"Missing required dependency: {dep.unique_id}",
                        )
                    )
                continue

            if dep.minimum_version:
                for installed_dep in matched:
                    if (
                        installed_dep.version
                        and installed_dep.version.lower() != "unknown"
                        and is_newer_version(installed_dep.version, dep.minimum_version)
                    ):
                        issues.setdefault(mod.folder_name, []).append(
                            ModIssue(
                                kind="version_too_low",
                                message=(
                                    f"Requires {dep.unique_id} >= {dep.minimum_version} "
                                    f"(installed: {installed_dep.version})"
                                ),
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
