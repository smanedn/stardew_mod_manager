# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dependency and duplicate `UniqueID` conflict detection (`src/core/dependencies.py`) with `⚠` tooltips and pre-launch confirmation.
- Safe `.zip` mod archive installer (`src/core/mod_installer.py`) with zip-slip path traversal protection and multi-mod folder support.
- Mod update checker (`src/core/updater.py`) with `UpdateProvider` interface, `GitHubUpdateProvider`, TTL caching, and graceful offline handling.
- Profile duplication (`Duplicate` button) and optional `github_token` setting in `SVMM_Data/config.json`.

## [0.1.0] - 2026-11-17

### Added
- Per-modpack folder management under `SVMM_Data/modpacks/<ProfileName>/`.
- Instant profile switching using Windows directory junctions (`mklink /J`) and experimental POSIX symlinks.
- Safe `Mods_Backup` handling when an unmanaged `Stardew Valley/Mods` folder is present.
- Tolerant SMAPI `manifest.json` parser supporting UTF-8 BOM, `//` and `/* */` comments, and trailing commas.
- Modular `customtkinter` UI (`src/ui/`) with Dark / Light / System themes, debounced search, cached mod rows, live game path validation, profile import/export, and SMAPI log shortcut.
- Double-click `.venv` auto-bootstrap in `main.py` for Windows Explorer.
- `ruff` + `pytest` unit test suite and GitHub Actions CI workflow.
