"""Entry point and application orchestrator for Stardew Valley Mod Manager."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)
PROJECT_ROOT = (
    Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
)
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))


def _ensure_venv() -> None:
    """Re-launch using .venv Python when double-clicked or run with system Python."""
    if IS_FROZEN:
        return
    venv_dir = PROJECT_ROOT / ".venv"
    if not venv_dir.is_dir():
        return

    try:
        in_venv = Path(sys.prefix).resolve() == venv_dir.resolve()
    except OSError:
        in_venv = False

    if in_venv:
        return

    candidates = (
        [venv_dir / "Scripts" / "pythonw.exe", venv_dir / "Scripts" / "python.exe"]
        if sys.platform == "win32"
        else [venv_dir / "bin" / "python"]
    )
    for python_bin in candidates:
        if python_bin.is_file():
            subprocess.Popen(
                [str(python_bin), str(Path(__file__).resolve()), *sys.argv[1:]],
                cwd=str(PROJECT_ROOT),
            )
            sys.exit(0)


_ensure_venv()
os.chdir(PROJECT_ROOT)

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import __version__
from src.core.config import ConfigManager
from src.core.dependencies import (
    analyze_mod_dependencies,
    format_issue_summary,
    resolve_enableable_dependencies,
)
from src.core.launcher import (
    get_installed_smapi_version,
    get_smapi_log_path,
    launch_game,
    validate_game_path,
)
from src.core.mod_installer import install_mod_archive
from src.core.mod_manager import link_game_mods, sync_profile, uninstall_mod, unlink_game_mods
from src.core.mod_scanner import ModInfo, scan_mod_pool
from src.core.modlist_export import export_modlist
from src.core.nexus_installer import NexusForbiddenError, install_from_nexus
from src.core.nxm_handler import build_nxm_command, register_nxm_protocol
from src.core.updater import (
    GitHubUpdateProvider,
    NexusUpdateProvider,
    UpdateChecker,
    UpdateResult,
    install_mod_update,
)
from src.ui.launch_bar import LaunchBar
from src.ui.mod_details_dialog import ModDetailsDialog
from src.ui.mod_list import ModListPanel
from src.ui.nexus_dialog import NexusBrowserDialog
from src.ui.profile_sidebar import ProfileSidebar
from src.ui.save_backup_dialog import SaveBackupDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.smapi_log_dialog import SmapiLogDialog
from src.ui.theme import SPACING
from src.ui.top_bar import TopBar

MODPACKS_DIR = PROJECT_ROOT / "SVMM_Data" / "modpacks"
PROFILES_DIR = PROJECT_ROOT / "SVMM_Data" / "profiles"
CONFIG_FILE = PROJECT_ROOT / "SVMM_Data" / "config.json"
UPDATE_CACHE_FILE = PROJECT_ROOT / "SVMM_Data" / "update_cache.json"
SAVE_BACKUPS_DIR = PROJECT_ROOT / "SVMM_Data" / "save_backups"
LOGO_FILE = BUNDLE_DIR / "assets" / "logo.png"
ICON_FILE = BUNDLE_DIR / "assets" / "logo.ico"


def _open_in_file_manager(target: Path) -> None:
    """Open a file or directory using the OS default handler."""
    if sys.platform == "win32":
        os.startfile(str(target))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


class SVModManagerApp(ctk.CTk):
    """Main application window coordinating core logic and UI components."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"Stardew Valley Mod Manager v{__version__}")
        self.geometry("1020x680")
        self.minsize(800, 540)
        self._set_app_icon()
        if sys.platform == "win32":
            # Override customtkinter's delayed default titlebar icon
            self.after(250, self._set_app_icon)

        MODPACKS_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

        self.config_manager = ConfigManager(CONFIG_FILE)
        ctk.set_appearance_mode(self.config_manager.appearance_mode)
        self._ensure_modpack_folders()

        self._scan_generation = 0
        self._current_mods: list[ModInfo] = []
        self._build_layout()
        self._bind_shortcuts()

        self._validate_game_path(self.config_manager.game_path)
        self._refresh_profiles()
        self._refresh_mods()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.top_bar = TopBar(
            self,
            initial_path=self.config_manager.game_path,
            initial_theme=self.config_manager.appearance_mode,
            on_path_change=self._on_game_path_changed,
            on_browse=self._browse_game_path,
            on_open_modpack=self._open_modpack_folder,
            on_theme_change=self._on_theme_changed,
            on_open_settings=self._open_settings,
        )
        self.top_bar.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        self.sidebar = ProfileSidebar(
            self,
            on_select=self._select_profile,
            on_create=self._create_profile,
            on_delete=self._delete_active_profile,
            on_import=self._import_profile,
            on_export=self._export_profile,
            on_duplicate=self._duplicate_profile,
            on_share_modlist=self._share_modlist,
        )
        self.sidebar.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(SPACING["lg"], SPACING["sm"]),
            pady=SPACING["sm"],
        )

        self.mod_list = ModListPanel(
            self,
            on_toggle=self._on_mods_toggled,
            on_refresh=self._refresh_mods,
            on_install_zip=self._install_zip,
            on_install_nexus=self._open_nexus_dialog,
            on_check_updates=self._check_updates,
            on_show_details=self._show_mod_details,
            on_update_mod=self._update_single_mod,
            on_fix_deps=self._fix_missing_dependencies,
        )
        self.mod_list.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(SPACING["sm"], SPACING["lg"]),
            pady=SPACING["sm"],
        )

        self.launch_bar = LaunchBar(
            self,
            version=__version__,
            on_launch_modded=self._launch_modded,
            on_launch_vanilla=self._launch_vanilla,
            on_open_smapi_log=self._open_smapi_log,
            on_open_saves=self._open_save_backups,
        )
        self.launch_bar.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=SPACING["lg"],
            pady=(SPACING["sm"], SPACING["lg"]),
        )

    def _set_app_icon(self) -> None:
        if sys.platform == "win32" and ICON_FILE.is_file():
            try:
                self.iconbitmap(str(ICON_FILE))
                return
            except tk.TclError:
                pass
        if LOGO_FILE.is_file():
            try:
                self._icon_image = tk.PhotoImage(file=str(LOGO_FILE))
                self.iconphoto(True, self._icon_image)
            except tk.TclError:
                pass

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-f>", lambda _e: self.mod_list.focus_search())
        self.bind("<Escape>", lambda _e: self.mod_list.clear_search())
        self.bind("<F5>", lambda _e: self._refresh_mods())

    def _ensure_modpack_folders(self) -> None:
        for pid in self.config_manager.profiles:
            (MODPACKS_DIR / pid).mkdir(parents=True, exist_ok=True)

    def _active_modpack_dir(self) -> Path:
        modpack_dir = MODPACKS_DIR / self.config_manager.active_profile
        modpack_dir.mkdir(parents=True, exist_ok=True)
        return modpack_dir

    def _validate_game_path(self, path: str) -> None:
        has_vanilla, has_smapi, msg = validate_game_path(path)
        self.top_bar.set_validation_status(has_vanilla, has_smapi, msg)

    def _on_game_path_changed(self, new_path: str) -> None:
        self.config_manager.game_path = new_path
        self._validate_game_path(new_path)

    def _browse_game_path(self) -> None:
        selected = filedialog.askdirectory(title="Select Stardew Valley Installation Folder")
        if selected:
            self.top_bar.set_path(selected)
            self._on_game_path_changed(selected)
            self.launch_bar.set_status(
                f"Game path set to: {selected}", level="success", auto_clear_ms=4000
            )

    def _open_modpack_folder(self) -> None:
        _open_in_file_manager(self._active_modpack_dir())

    def _open_smapi_log(self) -> None:
        log_path = get_smapi_log_path()
        if log_path is None:
            self.launch_bar.set_status(
                "SMAPI-latest.txt not found yet (run SMAPI at least once).",
                level="warning",
                auto_clear_ms=5000,
            )
            return
        SmapiLogDialog(self, log_path=log_path, on_open_external=_open_in_file_manager)

    def _open_save_backups(self) -> None:
        SaveBackupDialog(
            self,
            backups_root=SAVE_BACKUPS_DIR,
            on_open_folder=_open_in_file_manager,
            on_status=lambda msg, lvl: self.launch_bar.set_status(
                msg, level=lvl, auto_clear_ms=4000
            ),
        )

    def _open_settings(self) -> None:
        SettingsDialog(
            self,
            github_token=self.config_manager.github_token,
            nexus_api_key=self.config_manager.nexus_api_key,
            update_cache_path=UPDATE_CACHE_FILE,
            on_save=self._save_settings,
            on_cache_cleared=lambda: self.launch_bar.set_status(
                "Cleared update cache.", level="info", auto_clear_ms=3000
            ),
        )

    def _save_settings(self, github_token: str, nexus_api_key: str) -> None:
        self.config_manager.github_token = github_token
        self.config_manager.nexus_api_key = nexus_api_key
        self.launch_bar.set_status("Saved settings.", level="success", auto_clear_ms=3000)

    def _on_theme_changed(self, mode: str) -> None:
        self.config_manager.appearance_mode = mode
        ctk.set_appearance_mode(mode)

    def _refresh_profiles(self) -> None:
        self.sidebar.render_profiles(
            self.config_manager.profiles, self.config_manager.active_profile
        )

    def _select_profile(self, profile_id: str) -> None:
        self.config_manager.active_profile = profile_id
        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(f"Switched to modpack '{profile_id}'.", level="info")

    def _create_profile(self, name: str) -> None:
        if not name:
            self.launch_bar.set_status("Enter a modpack name first.", level="warning")
            return
        try:
            pid = self.config_manager.create_profile(name, name)
            self.config_manager.active_profile = pid
        except ValueError as exc:
            self.launch_bar.set_status(str(exc), level="error")
            return

        (MODPACKS_DIR / pid).mkdir(parents=True, exist_ok=True)
        self.sidebar.clear_new_profile_entry()
        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Created modpack '{pid}' at SVMM_Data/modpacks/{pid}.",
            level="success",
            auto_clear_ms=4000,
        )

    def _delete_active_profile(self) -> None:
        active = self.config_manager.active_profile
        confirmed = messagebox.askyesno(
            "Delete Modpack",
            f"Delete modpack profile '{active}'?\n\n"
            f"Your mod files in SVMM_Data/modpacks/{active} will NOT be deleted.",
        )
        if not confirmed:
            return

        try:
            self.config_manager.delete_profile(active)
        except ValueError as exc:
            self.launch_bar.set_status(str(exc), level="error")
            return

        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Deleted profile '{active}' (mod files kept on disk).", level="info"
        )

    def _export_profile(self) -> None:
        active = self.config_manager.active_profile
        dest = filedialog.asksaveasfilename(
            title="Export Modpack Profile",
            defaultextension=".json",
            initialfile=f"{active}.json",
            filetypes=[("JSON files", "*.json")],
        )
        if not dest:
            return
        try:
            self.config_manager.export_profile(dest, active)
            self.launch_bar.set_status(
                f"Exported '{active}' to {Path(dest).name}.",
                level="success",
                auto_clear_ms=4000,
            )
        except OSError as exc:
            self.launch_bar.set_status(f"Export failed: {exc}", level="error")

    def _import_profile(self) -> None:
        src = filedialog.askopenfilename(
            title="Import Modpack Profile",
            filetypes=[("JSON files", "*.json")],
        )
        if not src:
            return
        try:
            pid = self.config_manager.import_profile(src)
            self.config_manager.active_profile = pid
        except (OSError, ValueError) as exc:
            self.launch_bar.set_status(f"Import failed: {exc}", level="error")
            return

        (MODPACKS_DIR / pid).mkdir(parents=True, exist_ok=True)
        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Imported modpack '{pid}'. Drop its mods into SVMM_Data/modpacks/{pid}.",
            level="success",
            auto_clear_ms=5000,
        )

    def _duplicate_profile(self) -> None:
        active = self.config_manager.active_profile
        try:
            new_id = self.config_manager.duplicate_profile(active)
            src_dir = MODPACKS_DIR / active
            dst_dir = MODPACKS_DIR / new_id
            if src_dir.is_dir():
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            else:
                dst_dir.mkdir(parents=True, exist_ok=True)
            self.config_manager.active_profile = new_id
        except (OSError, ValueError, KeyError) as exc:
            self.launch_bar.set_status(f"Duplicate failed: {exc}", level="error")
            return

        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Duplicated '{active}' as '{new_id}'.", level="success", auto_clear_ms=4000
        )

    def _install_zip(self) -> None:
        archive_path = filedialog.askopenfilename(
            title="Select Mod Archive (.zip or .7z)",
            filetypes=[
                ("Mod archives", "*.zip *.7z"),
                ("Zip archives", "*.zip"),
                ("7z archives", "*.7z"),
            ],
        )
        if not archive_path:
            return

        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()
        self.mod_list.set_loading(True, f"Installing {Path(archive_path).name}...")

        def worker() -> None:
            try:
                installed = install_mod_archive(archive_path, modpack_dir)
                err = None
            except (OSError, ValueError) as exc:
                installed = []
                err = str(exc)
            self.after(0, lambda: self._on_install_complete(active, installed, err))

        threading.Thread(target=worker, daemon=True).start()

    def _share_modlist(self) -> None:
        active = self.config_manager.active_profile
        enabled = set(self.config_manager.get_enabled_mods(active))
        dest = filedialog.asksaveasfilename(
            title="Export Shareable Multiplayer Modlist",
            defaultextension=".md",
            initialfile=f"{active}_modlist.md",
            filetypes=[("Markdown (*.md)", "*.md"), ("JSON (*.json)", "*.json")],
        )
        if not dest:
            return
        try:
            export_modlist(dest, active, self._current_mods, enabled)
            self.launch_bar.set_status(
                f"Exported modlist for '{active}' to {Path(dest).name}.",
                level="success",
                auto_clear_ms=4000,
            )
        except OSError as exc:
            self.launch_bar.set_status(f"Export failed: {exc}", level="error")

    def _open_nexus_dialog(self) -> None:
        active = self.config_manager.active_profile
        NexusBrowserDialog(
            self,
            initial_api_key=self.config_manager.nexus_api_key,
            modpack_dir=self._active_modpack_dir(),
            on_save_api_key=self._save_nexus_api_key,
            on_installed=lambda folders: self._on_install_complete(active, folders, None),
            on_register_nxm=self._register_nxm_handler,
        )

    def _register_nxm_handler(self) -> None:
        try:
            cmd = build_nxm_command(IS_FROZEN, PROJECT_ROOT)
            register_nxm_protocol(cmd)
            messagebox.showinfo(
                "nxm:// Registered",
                "Registered SVModManager for 'Mod Manager Download' (nxm://) links on Nexus Mods!",
            )
        except OSError as exc:
            messagebox.showerror("Registration Failed", str(exc))

    def _save_nexus_api_key(self, api_key: str) -> None:
        if api_key != self.config_manager.nexus_api_key:
            self.config_manager.nexus_api_key = api_key

    def _on_install_complete(
        self, profile_id: str, installed: list[str], error: str | None
    ) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_loading(False)
        if error:
            self.launch_bar.set_status(f"Install failed: {error}", level="error")
            self._refresh_mods()
            return

        current = self.config_manager.get_enabled_mods(profile_id)
        self.config_manager.set_enabled_mods(current + installed, profile_id)
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Installed {', '.join(installed)} into '{profile_id}'.",
            level="success",
            auto_clear_ms=5000,
        )

    def _check_updates(self) -> None:
        if not self._current_mods:
            self.launch_bar.set_status("No mods to check for updates.", level="info")
            return

        mods_snapshot = list(self._current_mods)
        token = self.config_manager.github_token
        nexus_key = self.config_manager.nexus_api_key
        self.launch_bar.set_status("Checking for mod updates...", level="info")

        def worker() -> None:
            checker = UpdateChecker(
                providers=[
                    GitHubUpdateProvider(token=token),
                    NexusUpdateProvider(api_key=nexus_key),
                ],
                cache_path=UPDATE_CACHE_FILE,
            )
            results = checker.check_mods(mods_snapshot)
            self.after(0, lambda: self._on_updates_checked(results))

        threading.Thread(target=worker, daemon=True).start()

    def _on_updates_checked(self, results: list[UpdateResult]) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_updates(results)
        updates = [r for r in results if r.has_update]
        errors = [r for r in results if r.error]
        if updates:
            self.launch_bar.set_status(
                f"{len(updates)} update(s) available (hover ↑ badge for details).",
                level="warning",
            )
        elif errors and not results:
            self.launch_bar.set_status(
                "Update check failed (offline or rate-limited).", level="error"
            )
        elif errors:
            checked_ok = len(results) - len(errors)
            self.launch_bar.set_status(
                f"Checked {checked_ok} mod(s); {len(errors)} failed (offline/rate-limit).",
                level="warning",
            )
        else:
            self.launch_bar.set_status(
                f"Checked {len(results)} mod(s) with UpdateKeys: all up to date.",
                level="success",
                auto_clear_ms=5000,
            )

    def _update_single_mod(self, result: UpdateResult) -> None:
        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()
        nexus_key = self.config_manager.nexus_api_key
        gh_token = self.config_manager.github_token
        self.mod_list.set_loading(
            True, f"Updating {result.mod_name} to v{result.latest_version}..."
        )
        self.launch_bar.set_status(f"Downloading update for '{result.mod_name}'...", level="info")

        def worker() -> None:
            try:
                installed = install_mod_update(
                    result,
                    modpack_dir,
                    nexus_api_key=nexus_key,
                    github_token=gh_token,
                )
                err: Exception | None = None
            except Exception as exc:  # noqa: BLE001
                installed = []
                err = exc
            self.after(0, lambda: self._on_single_update_done(active, result, installed, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_update_done(
        self,
        profile_id: str,
        result: UpdateResult,
        installed: list[str],
        err: Exception | None,
    ) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_loading(False)
        if err is None:
            current = self.config_manager.get_enabled_mods(profile_id)
            self.config_manager.set_enabled_mods(current + installed, profile_id)
            self._refresh_mods()
            self.launch_bar.set_status(
                f"Updated '{result.mod_name}' to v{result.latest_version}!",
                level="success",
                auto_clear_ms=5000,
            )
            return

        self._refresh_mods()
        self.launch_bar.set_status(f"Update failed: {err}", level="error")
        if (isinstance(err, NexusForbiddenError) or result.url) and messagebox.askyesno(
            "Open Release Page?",
            f"{err}\n\nOpen '{result.mod_name}' release page in your browser?",
        ):
            webbrowser.open(result.url)

    def _refresh_mods(self) -> None:
        self._scan_generation += 1
        generation = self._scan_generation
        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()

        self.mod_list.set_loading(True, f"Scanning '{active}'...")

        def worker() -> None:
            mods = scan_mod_pool(modpack_dir)
            self.after(0, lambda: self._on_scan_complete(generation, active, mods))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_complete(self, generation: int, profile_id: str, mods: list[ModInfo]) -> None:
        if generation != self._scan_generation or not self.winfo_exists():
            return
        self._current_mods = mods
        self.mod_list.set_loading(False)
        enabled = self.config_manager.get_enabled_mods(profile_id)
        self.mod_list.set_mods(mods, enabled, profile_id)
        self._refresh_dependency_warnings(set(enabled))
        self.launch_bar.set_status(
            f"Found {len(mods)} mod(s) in modpack '{profile_id}'.", level="info"
        )

    def _on_mods_toggled(self, enabled_mods: list[str]) -> None:
        self.config_manager.set_enabled_mods(enabled_mods)
        self._refresh_dependency_warnings(set(enabled_mods))

    def _refresh_dependency_warnings(self, enabled_set: set[str]) -> None:
        smapi_ver = get_installed_smapi_version(self.config_manager.game_path)
        issues = analyze_mod_dependencies(self._current_mods, enabled_set, smapi_version=smapi_ver)
        self.mod_list.set_issues(issues)
        fixable = resolve_enableable_dependencies(self._current_mods, enabled_set)
        self.mod_list.set_fixable_deps_count(len(fixable))

    def _fix_missing_dependencies(self) -> None:
        active = self.config_manager.active_profile
        current = self.config_manager.get_enabled_mods(active)
        to_enable = resolve_enableable_dependencies(self._current_mods, set(current))
        if not to_enable:
            return
        updated = current + to_enable
        self.config_manager.set_enabled_mods(updated, active)
        self.mod_list.sync_enabled(updated)
        self._refresh_dependency_warnings(set(updated))
        self.launch_bar.set_status(
            f"Enabled {len(to_enable)} missing dependency mod(s): {', '.join(to_enable)}",
            level="success",
            auto_clear_ms=5000,
        )

    def _show_mod_details(self, mod: ModInfo) -> None:
        ModDetailsDialog(
            self,
            mod=mod,
            on_open_folder=_open_in_file_manager,
            on_uninstall=self._uninstall_mod,
        )

    def _uninstall_mod(self, mod: ModInfo) -> None:
        active = self.config_manager.active_profile
        try:
            uninstall_mod(
                mod.folder_name,
                self._active_modpack_dir(),
                profiles_root=PROFILES_DIR,
                profile_id=active,
            )
        except (OSError, ValueError) as exc:
            self.launch_bar.set_status(f"Uninstall failed: {exc}", level="error")
            return

        remaining = [
            m for m in self.config_manager.get_enabled_mods(active) if m != mod.folder_name
        ]
        self.config_manager.set_enabled_mods(remaining, active)
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Uninstalled '{mod.name}' from '{active}'.", level="success", auto_clear_ms=4000
        )

    def _launch_modded(self) -> None:
        game_path = self.top_bar.get_path()
        self._on_game_path_changed(game_path)
        active = self.config_manager.active_profile
        enabled = self.config_manager.get_enabled_mods(active)
        smapi_ver = get_installed_smapi_version(game_path)
        issues = analyze_mod_dependencies(self._current_mods, set(enabled), smapi_version=smapi_ver)
        if issues:
            summary = format_issue_summary(issues, self._current_mods)
            proceed = messagebox.askyesno(
                "Dependency / Conflict Warning",
                f"Issues detected in modpack '{active}':\n\n{summary}\n\nLaunch SMAPI anyway?",
            )
            if not proceed:
                return

        modpack_dir = self._active_modpack_dir()

        self.launch_bar.set_busy(True)
        self.launch_bar.set_status(f"Syncing '{active}' and launching SMAPI...", level="info")

        def worker() -> None:
            try:
                profile_dir = sync_profile(active, enabled, modpack_dir, PROFILES_DIR)
                ok, msg = link_game_mods(game_path, profile_dir)
                if ok:
                    ok, msg = launch_game(game_path, modded=True)
            except OSError as exc:
                ok, msg = False, f"Sync failed: {exc}"
            self.after(0, lambda: self._on_launch_complete(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_vanilla(self) -> None:
        game_path = self.top_bar.get_path()
        self._on_game_path_changed(game_path)

        self.launch_bar.set_busy(True)
        self.launch_bar.set_status("Unlinking Mods and launching Vanilla...", level="info")

        def worker() -> None:
            ok, msg = unlink_game_mods(game_path)
            if ok:
                ok, msg = launch_game(game_path, modded=False)
            self.after(0, lambda: self._on_launch_complete(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_launch_complete(self, ok: bool, msg: str) -> None:
        if not self.winfo_exists():
            return
        self.launch_bar.set_busy(False)
        self.launch_bar.set_status(msg, level="success" if ok else "error")


def main() -> None:
    """Initialize theme and run the Stardew Valley Mod Manager GUI."""
    ctk.set_default_color_theme("blue")
    nxm_status: tuple[str, str] | None = None
    if len(sys.argv) > 1 and sys.argv[1].lower().startswith("nxm://"):
        cfg = ConfigManager(CONFIG_FILE)
        active = cfg.active_profile
        modpack_dir = MODPACKS_DIR / active
        try:
            installed = install_from_nexus(sys.argv[1], cfg.nexus_api_key, modpack_dir)
            current = cfg.get_enabled_mods(active)
            cfg.set_enabled_mods(current + installed, active)
            nxm_status = (
                f"Installed {', '.join(installed)} via nxm:// into '{active}'.",
                "success",
            )
        except (OSError, ValueError) as exc:
            nxm_status = (f"nxm:// install failed: {exc}", "error")

    app = SVModManagerApp()
    if nxm_status is not None:
        msg, level = nxm_status
        app.after(300, lambda: app.launch_bar.set_status(msg, level=level))
    app.mainloop()


if __name__ == "__main__":
    main()
