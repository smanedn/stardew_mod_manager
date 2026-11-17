<p align="center">
  <img src="assets/logo.png" alt="Stardew Valley Mod Manager Logo" width="128" />
</p>

# Stardew Valley Mod Manager (SVMM)

A lightweight, dark-mode desktop mod manager for **Stardew Valley** built with Python and `customtkinter`. Each modpack has its own dedicated folder, and profile switching uses OS-level directory junctions/symlinks so mods swap instantly without copying files.

## Features

- **Per-Modpack Folders:** Keep each modpack's mods isolated under `SVMM_Data/modpacks/<ModpackName>/`.
- **Instant Profile Switching:** Rebuilds `SVMM_Data/profiles/<ProfileName>/` and links `Stardew Valley/Mods` using directory junctions (`mklink /J` on Windows, symlinks on macOS/Linux) with zero file copying.
- **Safe Vanilla Launch:** Unlinks `Stardew Valley/Mods` and launches the base game (`Stardew Valley.exe`) without touching your mod files. Any pre-existing unmanaged `Mods` folder is safely backed up to `Mods_Backup`.
- **Tolerant SMAPI Manifest Parser:** Reads `manifest.json` with UTF-8 BOM (`utf-8-sig`) support and safely handles comments and trailing commas.
- **Double-Click Ready:** Running `main.py` directly on Windows automatically re-launches using `.venv` if present.

## Tech Stack

- **Language:** Python 3.10+ (tested on Python 3.13)
- **GUI:** [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter)
- **Backend:** Python Standard Library (`json`, `pathlib`, `subprocess`, `os`, `shutil`)

## Prerequisites

- **Python 3.10+**
- **Stardew Valley** installed locally
- **[SMAPI](https://smapi.io/)** installed in your Stardew Valley directory (required for modded launches)

## Local Setup & Running

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
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
   - Click **Open Modpack Folder** to drop mod folders into the active modpack (`SVMM_Data/modpacks/<ProfileName>/`), then click **Refresh**.
   - Check the mods you want enabled and click **LAUNCH MODDED (SMAPI)** or **LAUNCH VANILLA (NO MODS)**.

> **Note:** This project does not use API keys, databases, or `.env` files. All user configuration is stored locally in `SVMM_Data/config.json` (ignored by Git).

## Project Structure

```text
stardew_mod_manager/
├── main.py                  # Entry point, .venv bootstrap, and app orchestrator
├── requirements.txt         # Runtime dependency (customtkinter)
├── requirements-dev.txt     # Dev dependencies (pytest, ruff)
├── pyproject.toml           # Ruff and pytest configuration
├── .gitignore               # Ignores .venv, __pycache__, SVMM_Data, .env*, OS/IDE files
├── assets/
│   └── logo.png             # Application icon and README logo
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # ConfigManager, validation, and profile import/export
│   │   ├── mod_scanner.py   # Mod folder scanner and SMAPI manifest.json parser
│   │   ├── mod_manager.py   # Profile junction/symlink sync and Mods_Backup handling
│   │   └── launcher.py      # Path validation, SMAPI log locator, and game launcher
│   └── ui/
│       ├── __init__.py
│       ├── theme.py         # Light/dark design tokens and typography
│       ├── top_bar.py       # Game path bar, validation status, and theme switcher
│       ├── profile_sidebar.py # Modpack list, create/delete, and import/export
│       ├── mod_list.py      # Debounced search, cached mod rows, and counter badge
│       └── launch_bar.py    # Modded/Vanilla launch buttons, SMAPI log, and status bar
└── tests/                   # Unit tests for core modules
```

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.
