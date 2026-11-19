<p align="center">
  <img src="assets/logo.png" alt="Stardew Valley Mod Manager Logo" width="128" />
</p>

# Stardew Valley Mod Manager (SVMM)

[![CI](https://github.com/smanedn/stardew_mod_manager/actions/workflows/ci.yml/badge.svg)](https://github.com/smanedn/stardew_mod_manager/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Latest Release](https://img.shields.io/github/v/release/smanedn/stardew_mod_manager?include_prereleases)](https://github.com/smanedn/stardew_mod_manager/releases)

A lightweight desktop mod manager for **Stardew Valley** built with Python and `customtkinter`. Each modpack has its own dedicated folder, and profile switching uses OS-level directory junctions/symlinks so mods swap instantly without copying files.

## Features

- **Per-Modpack Folders:** Keep each modpack's mods isolated under `SVMM_Data/modpacks/<ModpackName>/`.
- **Instant Profile Switching:** Rebuilds `SVMM_Data/profiles/<ProfileName>/` and links `Stardew Valley/Mods` using directory junctions (`mklink /J` on Windows) or symlinks (macOS/Linux, experimental) with zero file copying.
- **Safe Vanilla Launch:** Unlinks `Stardew Valley/Mods` and launches the base game (`Stardew Valley.exe`) without touching your mod files. Any pre-existing unmanaged `Mods` folder is safely backed up to `Mods_Backup`.
- **Tolerant SMAPI Manifest Parser:** Reads `manifest.json` with UTF-8 BOM (`utf-8-sig`) support and safely handles comments and trailing commas.
- **Dependency & Conflict Warnings:** Flags missing required `Dependencies` and `ContentPackFor` frameworks, `MinimumVersion` / `MinimumApiVersion` mismatches, and duplicate `UniqueID`s (`⚠` + hover tooltip) with 1-click **Fix Deps** and pre-launch confirmation.
- **Safe Archive Installer & Drag-and-Drop:** Install `.zip`, `.7z`, and `.rar` mod archives (via button or drag-and-drop) with zip-slip path traversal protection.
- **Mod & SMAPI Update Checker:** Checks `GitHub:owner/repo` and `Nexus:<id>` `UpdateKeys` in the background with **1-Click Update**, **Update All**, TTL caching, and an automatic `↑ SMAPI` update indicator.
- **Quick Filter Chips & Mod Details:** Filter by `All`, `Enabled`, `Disabled`, `Issues ⚠`, or `Updates ↑`, inspect full `manifest.json` metadata, edit per-mod `config.json`, or safely uninstall mods.
- **Modpack Bundles, Save Backups & Steam Launch:** Export/import full modpack `.zip` bundles, duplicate/rename/share modlists, back up/restore `Saves` (with optional auto-backup before modded launch), view parsed `SMAPI-latest.txt` errors/warnings, and optionally launch via Steam or with custom CLI arguments.
- **Double-Click Ready:** Running `main.py` directly on Windows automatically re-launches using `.venv` if present.

## Screenshots

| Dark Mode | Light Mode |
| --- | --- |
| ![Dark Mode](assets/screenshots/main-dark.png) | ![Light Mode](assets/screenshots/main-light.png) |

## Platform Support

| Platform | Status | Linking Mechanism & Permissions |
| --- | --- | --- |
| **Windows** | **Tested** (Windows + Python 3.13; CI runs Python 3.11 & 3.13) | Uses NTFS **Directory Junctions** (`cmd /c mklink /J`). Works out of the box without Administrator privileges. |
| **macOS** | **Experimental** (untested on hardware) | Uses POSIX **symbolic links** (`os.symlink(..., target_is_directory=True)`). Standard user permissions are sufficient on APFS/HFS+. |
| **Linux** | **Experimental** (untested on hardware; unit tests run in CI) | Uses POSIX **symbolic links** (`os.symlink(..., target_is_directory=True)`). Requires a POSIX filesystem supporting symlinks. |

## Tech Stack

- **Language:** Python 3.10+
- **GUI:** [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter)
- **Backend:** Python Standard Library (`json`, `pathlib`, `subprocess`, `os`, `shutil`, `stat`)

## Download

Pre-built Windows executables are available on the [Releases page](https://github.com/smanedn/stardew_mod_manager/releases/latest):

1. Download `SVModManager-vX.Y.Z-windows-x64.zip` and extract `SVModManager.exe` into its own folder.
2. Double-click `SVModManager.exe` to launch (it stores `SVMM_Data/` right next to the executable).
3. If Windows SmartScreen appears for an unsigned binary, click **More info → Run anyway**.

## Prerequisites

- **Python 3.10+**
- **Stardew Valley** installed locally
- **[SMAPI](https://smapi.io/)** installed in your Stardew Valley directory (required for modded launches)

## Local Setup & Running

1. **Clone the repository:**
   ```bash
   git clone https://github.com/smanedn/stardew_mod_manager.git
   cd stardew_mod_manager
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`)*

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   - **Terminal:**
     ```powershell
     .\.venv\Scripts\python.exe main.py
     ```
   - **Windows File Explorer:** Double-click `main.py` (it automatically detects and uses `.venv`).

5. **Configure in the UI:**
   - Click **Browse** to select your Stardew Valley installation folder (saved locally to `SVMM_Data/config.json`).
   - Click **Open Modpack Folder** to drop mod folders into the active modpack (`SVMM_Data/modpacks/<ProfileName>/`), then click **Refresh** (`F5`).
   - Check the mods you want enabled and click **LAUNCH MODDED (SMAPI)** or **LAUNCH VANILLA (NO MODS)**.

> **Note:** This project does not use API keys, databases, or `.env` files. All user configuration is stored locally in `SVMM_Data/config.json` (ignored by Git).

## Project Structure

```text
stardew_mod_manager/
├── main.py                      # Entry point, .venv/frozen bootstrap, and app orchestrator
├── requirements.txt             # Runtime dependency (customtkinter)
├── requirements-dev.txt         # Dev dependencies (pytest, pytest-cov, ruff, mypy)
├── pyproject.toml               # Ruff, mypy, and pytest configuration
├── .gitignore                   # Ignores .venv, __pycache__, SVMM_Data, .env*, build/dist
├── CHANGELOG.md                 # Release history (Keep a Changelog)
├── CONTRIBUTING.md              # Local dev setup and contribution guidelines
├── LICENSE                      # MIT License
├── .github/
│   ├── ISSUE_TEMPLATE/          # Bug report and feature request templates
│   └── workflows/
│       ├── ci.yml               # Cross-platform lint, format, mypy, and pytest CI
│       └── release.yml          # Windows PyInstaller .exe release workflow on v* tags
├── assets/
│   ├── logo.png                 # Application icon and README logo
│   ├── logo.ico                 # Windows titlebar icon
│   └── screenshots/             # Screenshots for documentation
├── src/
│   ├── __init__.py              # Package version (__version__)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # ConfigManager, validation, import/export/duplicate/rename
│   │   ├── dependencies.py      # Missing deps, ContentPackFor, min-version & ID conflicts
│   │   ├── mod_config.py        # Per-mod config.json loader, validator, and formatter
│   │   ├── mod_installer.py     # Safe .zip/.7z/.rar extractor and drag-and-drop parser
│   │   ├── mod_scanner.py       # Recursive mod scanner and SMAPI manifest.json parser
│   │   ├── mod_manager.py       # Profile junction/symlink sync, uninstall, Mods_Backup
│   │   ├── modlist_export.py    # Shareable Markdown/JSON multiplayer modlist exporter
│   │   ├── modpack_bundle.py    # Full modpack .zip bundle export and import
│   │   ├── nexus_browser.py     # In-app Nexus Mods browser and GraphQL search
│   │   ├── nexus_installer.py   # Nexus Mods API and nxm:// archive installer
│   │   ├── nxm_handler.py       # Windows HKCU nxm:// protocol registration
│   │   ├── save_backup.py       # Stardew Valley Saves .zip backup, restore, and pruning
│   │   ├── smapi_log.py         # SMAPI-latest.txt error and warning log parser
│   │   ├── launcher.py          # Path validation, SMAPI version, Steam/CLI launcher
│   │   └── updater.py           # UpdateProvider interface, GitHub/Nexus/SMAPI updates
│   └── ui/
│       ├── __init__.py
│       ├── theme.py             # Light/dark design tokens and typography
│       ├── tooltip.py           # Hover tooltip widget for warnings and updates
│       ├── top_bar.py           # Active modpack title, game path, SMAPI update badge
│       ├── profile_sidebar.py   # Brand header, modpacks, bundle/JSON actions, utilities
│       ├── mod_list.py          # Quick filter chips, mod cards, Fix Deps, Update All
│       ├── mod_details_dialog.py # Manifest details, open folder, config edit, uninstall
│       ├── mod_config_dialog.py # In-app JSON editor for per-mod config.json
│       ├── nexus_dialog.py      # Nexus Mods browser with icons, pagination, 1-click install
│       ├── save_backup_dialog.py # Save backup/restore manager dialog
│       ├── settings_dialog.py   # API keys, Steam/CLI launch options, auto-backup, cache
│       ├── smapi_log_dialog.py  # In-app SMAPI-latest.txt error/warning viewer
│       └── launch_bar.py        # Status dock and Vanilla / SMAPI launch buttons
└── tests/                       # Unit tests for core modules
```

## Roadmap

- [x] Per-modpack folder isolation (`SVMM_Data/modpacks/<ProfileName>/`)
- [x] Zero-copy Windows directory junction syncing & safe `Mods_Backup`
- [x] Tolerant SMAPI `manifest.json` parser (BOM, comments, trailing commas)
- [x] Dark / Light / System theme switcher & profile import/export/duplicate
- [x] Ruff linting, `pytest` suite, and GitHub Actions CI
- [x] Dependency/conflict hints using `UniqueID` and `Dependencies` in `manifest.json`
- [x] Safe `.zip` mod installation and `UpdateKeys` update checker (`GitHub:owner/repo`)
- [x] Recursive scanning for nested modpacks containing subfolder `manifest.json` files
- [x] Additional update providers (Nexus Mods via optional `nexus_api_key` in `SVMM_Data/config.json`)
- [x] Windows `.exe` release workflow via PyInstaller on `v*` tags
- [ ] Verified macOS and Linux runtime testing

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.
