# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-19

### Added
- **Co-op Modlist Parity Checker** (`src/core/coop_parity.py`, `src/ui/coop_parity_dialog.py`): Compare a friend's exported `.json` modlist to spot missing mods, extra mods, and version mismatches with 1-click toggle sync.
- **Content Patcher Asset Conflict Detector & Resolver** (`src/core/asset_conflicts.py`, `src/ui/asset_conflict_dialog.py`): Scans `content.json` `Target` fields across enabled packs and lets you disable colliding mods or inspect configs.
- **Save-to-Modpack Binding** (`src/core/save_binding.py`, `src/ui/save_backup_dialog.py`): Bind actual Stardew Valley farm saves from `%APPDATA%\StardewValley\Saves` to specific modpacks.
- **Live SMAPI Compatibility Status** (`src/core/smapi_compat.py`): Queries `smapi.io/api/v3.0/mods` to flag `Broken`, `Obsolete`, `Abandoned`, and `Unofficial` 1.6 updates.
- **Mod Thumbnails & Batched Icon Loading** (`src/core/mod_icons.py`, `src/ui/mod_list.py`): Displays 42×42 local/cached Nexus thumbnails or monogram badges on every mod card with non-blocking batched loading.
- **10 Built-in Themes & Custom Theme Studio** (`src/ui/theme.py`, `src/ui/settings_dialog.py`): Live theme switching across Midnight, Daylight, Pelican Town, Junimo Forest, Stardrop, Ginger Island, Skull Cavern, Nordic Frost, Rose Quartz, Honeywood, and Custom themes.
- **1-Click SMAPI Installer & Auto-Updater** (`src/core/smapi_installer.py`, `src/ui/top_bar.py`): Download and launch the official SMAPI installer directly from SVMM.
- **Desktop Modpack Shortcuts & Config Snapshots** (`src/core/shortcuts.py`, `src/core/config_presets.py`): Create Desktop shortcuts (`--launch-profile`) and snapshot/restore per-modpack `config.json` presets.
- **Mod Trash Bin, Multi-Select Bulk Actions, Quick Setup Wizard & SVMM Update Checker** (`src/core/mod_manager.py`, `src/ui/trash_dialog.py`, `src/ui/onboarding_dialog.py`, `src/core/app_updater.py`).

### Changed
- **Revamped Clean UI**: Streamlined the sidebar with compact `⋯` and `Tools ▾` menus, simplified the mod toolbar to 2 rows, and redesigned Settings into a tabbed dialog.

## [0.8.0] - 2026-11-19

### Added
- **Full Modpack `.zip` Bundle Export/Import** (`src/core/modpack_bundle.py`): Package or import entire modpacks (mod folders, `config.json` tweaks, and enabled-mod state) as a single `.zip`.
- **Update All (N) & SMAPI Update Indicator** (`src/core/updater.py`, `src/ui/mod_list.py`, `src/ui/top_bar.py`): Batch-update all eligible outdated mods in one click and display an `↑ SMAPI vX.Y.Z` indicator when a newer SMAPI release is available.
- **Auto-Backup Saves & Modpack Rename** (`src/core/save_backup.py`, `src/core/config.py`, `src/ui/settings_dialog.py`): Optional automatic save backup before modded launches (retaining the newest 5 auto-backups) and **Rename** support for modpacks.
- **`ContentPackFor` Dependency Detection** (`src/core/mod_scanner.py`, `src/ui/mod_details_dialog.py`): Treats `ContentPackFor` frameworks as required SMAPI dependencies.
- **Quick Filter Chips** (`src/ui/mod_list.py`): Filter mods by `All`, `Enabled`, `Disabled`, `Issues ⚠`, or `Updates ↑`.
- **`.rar` Archive Support & Steam/Custom Launch Options** (`src/core/mod_installer.py`, `src/core/launcher.py`, `src/ui/settings_dialog.py`): Added `.rar` extraction via `rarfile`, optional `steam://rungameid/413150` launch for Steam Overlay, and custom CLI launch arguments.

## [0.7.0] - 2026-11-18

### Changed
- **Complete GUI Revamp** (`src/ui/`, `main.py`): Redesigned with a full-height navigation sidebar, layered light/dark palette (`theme.py`), focused top header with live game status pill, two-row mod toolbar, structured 2-line mod cards with `CTkSwitch` toggles, and a grounded launch dock.
- **App Logo**: Updated `assets/logo.png` and `assets/logo.ico` to a pixel-art Stardew chicken icon with a golden modding gear badge.

### Added
- **Drag-and-Drop Archive Install** (`main.py`, `src/core/mod_installer.py`, `.github/workflows/release.yml`): Drag and drop `.zip` or `.7z` mod archives directly onto the mod list to install them into the active modpack (powered by `tkinterdnd2` with graceful fallback).

## [0.5.2] - 2026-11-18

### Added
- **Save Game Backup & Restore** (`src/core/save_backup.py`, `src/ui/save_backup_dialog.py`): Snapshot and restore your Stardew Valley `Saves` folder as `.zip` archives in `SVMM_Data/save_backups/` via the **Saves** button.
- **In-App Settings Dialog (`⚙`)** (`src/ui/settings_dialog.py`, `src/core/config.py`): Configure optional `github_token` and `nexus_api_key` and clear `update_cache.json` directly from the UI.

## [0.5.1] - 2026-11-18

### Added
- **1-Click "Fix Deps" Button** (`src/core/dependencies.py`, `src/ui/mod_list.py`): Automatically detects and enables disabled mods in the active modpack that satisfy required dependencies.
- **In-App SMAPI Log Viewer** (`src/core/smapi_log.py`, `src/ui/smapi_log_dialog.py`): Parses `SMAPI-latest.txt` into **Errors**, **Warnings**, and **Full Log** tabs with an **Open in Editor** option.

## [0.5.0] - 2026-11-18

### Added
- **1-Click Mod Updates** (`src/core/updater.py`, `src/ui/mod_list.py`): `↑ vX.Y.Z` badges are now clickable buttons that download and install `.zip` release assets for `GitHub:owner/repo` mods (or trigger Nexus updates / open the release page).
- **Dependency `MinimumVersion` & `MinimumApiVersion` Checks** (`src/core/dependencies.py`, `src/core/launcher.py`): Reads the installed SMAPI version from `StardewModdingAPI.deps.json` and warns when an enabled dependency or SMAPI installation is older than required.
- **Multiplayer Modlist Export** (`src/core/modlist_export.py`, `src/ui/profile_sidebar.py`): Added **Share Modlist** to export enabled mods as shareable Markdown (`.md`) or JSON (`.json`) with versions and Nexus/GitHub links.
- **`.7z` Archive Support** (`src/core/mod_installer.py`, `src/core/nexus_installer.py`): Added `py7zr`-powered `.7z` extraction with zip-slip path validation alongside `.zip` archives.

## [0.4.0] - 2026-11-18

### Added
- **Mod Details & Safe Uninstall** (`src/ui/mod_details_dialog.py`, `src/core/mod_manager.py`): View full `manifest.json` metadata (`UniqueID`, `MinimumApiVersion`, `Description`, `Dependencies`, `UpdateKeys`), open mod folders, and safely uninstall mods from the active modpack.
- **In-App Mod `config.json` Editor** (`src/core/mod_config.py`, `src/ui/mod_config_dialog.py`): Edit and format per-mod `config.json` files directly inside the app with JSON syntax validation before saving.

## [0.3.0] - 2026-11-17

### Added
- In-app **Nexus Mods Browser** (`src/core/nexus_browser.py`, `src/ui/nexus_dialog.py`) with Popular / Latest Updated / New Mods tabs, keyword search, mod icons, and 10–100 per-page pagination.
- Direct **Nexus Mods Installer** (`src/core/nexus_installer.py`) with 1-click install (Nexus Premium), automatic `Downloads` folder watcher for browser downloads, and `nxm://` protocol handler registration (`src/core/nxm_handler.py`).
- Recursive scanning for nested modpack subfolders (`src/core/mod_scanner.py`, `src/core/mod_manager.py`).
- **Nexus Mods Update Provider** (`NexusUpdateProvider`) supporting `Nexus:<id>` `UpdateKeys` with optional `nexus_api_key` in `SVMM_Data/config.json`.
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
