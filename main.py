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

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _HAS_DND = True
except ImportError:
    DND_FILES = "DND_Files"
    _HAS_DND = False

    class _DummyDnDWrapper:
        pass

    class TkinterDnD:  # type: ignore[no-redef]
        DnDWrapper = _DummyDnDWrapper

        @staticmethod
        def _require(_widget: object) -> str:
            return ""


from src import __version__
from src.core.app_updater import check_svmm_update
from src.core.asset_conflicts import detect_asset_conflicts, format_asset_conflicts
from src.core.config import ConfigManager
from src.core.config_presets import restore_config_preset, save_config_preset
from src.core.coop_parity import (
    CoopParityReport,
    compare_with_friend_modlist,
    load_friend_modlist,
)
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
from src.core.mod_icons import extract_nexus_mod_id, fetch_nexus_mod_thumbnail, load_mod_icon
from src.core.mod_installer import install_mod_archive, parse_dropped_archive_paths
from src.core.mod_manager import (
    TrashedMod,
    link_game_mods,
    restore_trashed_mod,
    sync_profile,
    uninstall_mod,
    unlink_game_mods,
)
from src.core.mod_scanner import ModInfo, scan_mod_pool
from src.core.modlist_export import export_modlist
from src.core.modpack_bundle import export_modpack_bundle, import_modpack_bundle
from src.core.nexus_installer import NexusForbiddenError, install_from_nexus
from src.core.nxm_handler import build_nxm_command, register_nxm_protocol
from src.core.save_backup import create_save_backup, get_default_saves_dir, prune_auto_backups
from src.core.save_binding import list_farm_saves
from src.core.shortcuts import create_modpack_shortcut
from src.core.smapi_compat import SmapiCompatInfo, check_smapi_compatibility
from src.core.smapi_installer import (
    download_and_extract_smapi,
    fetch_latest_smapi_release,
    launch_smapi_installer,
)
from src.core.updater import (
    GitHubUpdateProvider,
    NexusUpdateProvider,
    UpdateChecker,
    UpdateResult,
    can_direct_update,
    check_smapi_update,
    install_mod_update,
)
from src.ui.asset_conflict_dialog import AssetConflictDialog
from src.ui.coop_parity_dialog import CoopParityDialog
from src.ui.launch_bar import LaunchBar
from src.ui.mod_details_dialog import ModDetailsDialog
from src.ui.mod_list import ModListPanel
from src.ui.nexus_dialog import NexusBrowserDialog
from src.ui.onboarding_dialog import OnboardingDialog
from src.ui.profile_sidebar import ProfileSidebar
from src.ui.save_backup_dialog import SaveBackupDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.smapi_log_dialog import SmapiLogDialog
from src.ui.theme import COLORS, SPACING, apply_theme
from src.ui.top_bar import TopBar
from src.ui.trash_dialog import TrashBinDialog

MODPACKS_DIR = PROJECT_ROOT / "SVMM_Data" / "modpacks"
PROFILES_DIR = PROJECT_ROOT / "SVMM_Data" / "profiles"
CONFIG_FILE = PROJECT_ROOT / "SVMM_Data" / "config.json"
UPDATE_CACHE_FILE = PROJECT_ROOT / "SVMM_Data" / "update_cache.json"
SMAPI_COMPAT_CACHE_FILE = PROJECT_ROOT / "SVMM_Data" / "smapi_compat_cache.json"
MOD_ICONS_DIR = PROJECT_ROOT / "SVMM_Data" / "mod_icons"
CONFIG_PRESETS_DIR = PROJECT_ROOT / "SVMM_Data" / "config_presets"
SMAPI_INSTALLER_DIR = PROJECT_ROOT / "SVMM_Data" / "smapi_installer"
TRASH_DIR = PROJECT_ROOT / "SVMM_Data" / ".trash"
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


class SVModManagerApp(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc]
    """Main application window coordinating core logic and UI components."""

    def __init__(self) -> None:
        super().__init__()
        if _HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except tk.TclError:
                pass
        self.title(f"Stardew Valley Mod Manager v{__version__}")
        self.geometry("1120x720")
        self.minsize(880, 580)
        self.configure(fg_color=COLORS["bg_app"])
        self._set_app_icon()
        if sys.platform == "win32":
            # Override customtkinter's delayed default titlebar icon
            self.after(250, self._set_app_icon)

        MODPACKS_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

        self.config_manager = ConfigManager(CONFIG_FILE)
        apply_theme(self.config_manager.theme, self.config_manager.custom_theme)
        self.configure(fg_color=COLORS["bg_app"])
        self._ensure_modpack_folders()

        self._scan_generation = 0
        self._current_mods: list[ModInfo] = []
        self._last_update_results: list[UpdateResult] = []
        self._build_layout()
        self._bind_shortcuts()
        self._setup_drag_and_drop()

        self._validate_game_path(self.config_manager.game_path)
        self._refresh_profiles()
        self._refresh_mods()
        self._check_svmm_update_async()
        self._maybe_show_onboarding()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar = ProfileSidebar(
            self,
            version=__version__,
            logo_path=LOGO_FILE,
            on_select=self._select_profile,
            on_create=self._create_profile,
            on_delete=self._delete_active_profile,
            on_import=self._import_profile,
            on_export=self._export_profile,
            on_duplicate=self._duplicate_profile,
            on_share_modlist=self._share_modlist,
            on_export_bundle=self._export_bundle,
            on_import_bundle=self._import_bundle,
            on_open_saves=self._open_save_backups,
            on_open_smapi_log=self._open_smapi_log,
            on_open_settings=lambda: self._open_settings("General"),
            on_open_themes=lambda: self._open_settings("Themes"),
            on_rename=self._rename_active_profile,
            on_coop_check=self._coop_parity_check,
            on_open_modpack_folder=self._open_modpack_folder,
            on_create_shortcut=self._create_modpack_shortcut,
            on_save_config_preset=self._save_config_preset,
            on_restore_config_preset=self._restore_config_preset,
            on_open_asset_conflicts=self._open_asset_conflicts,
            on_open_trash=self._open_trash_bin,
            on_open_onboarding=self._open_onboarding,
        )
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")

        self.top_bar = TopBar(
            self,
            initial_path=self.config_manager.game_path,
            on_path_change=self._on_game_path_changed,
            on_browse=self._browse_game_path,
            on_install_smapi=self._install_or_update_smapi,
        )
        self.top_bar.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
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
            on_update_all=self._update_all_mods,
            on_fix_deps=self._fix_missing_dependencies,
            on_check_compat=self._check_smapi_compat,
            on_bulk_uninstall=self._bulk_uninstall_mods,
            icon_cache_dir=MOD_ICONS_DIR,
        )
        self.mod_list.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=SPACING["lg"],
            pady=SPACING["xs"],
        )

        self.launch_bar = LaunchBar(
            self,
            on_launch_modded=self._launch_modded,
            on_launch_vanilla=self._launch_vanilla,
        )
        self.launch_bar.grid(
            row=2,
            column=1,
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

    def _setup_drag_and_drop(self) -> None:
        if not _HAS_DND:
            return
        try:
            self.mod_list.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.mod_list.dnd_bind("<<Drop>>", self._on_files_dropped)  # type: ignore[attr-defined]
        except (tk.TclError, AttributeError):
            pass

    def _on_files_dropped(self, event: object) -> None:
        raw_data = str(getattr(event, "data", "") or "")
        archives = parse_dropped_archive_paths(raw_data)
        if not archives:
            self.launch_bar.set_status(
                "Drop .zip or .7z mod archives to install them.",
                level="warning",
                auto_clear_ms=4000,
            )
            return

        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()
        self.mod_list.set_loading(True, f"Installing {len(archives)} dropped archive(s)...")

        def worker() -> None:
            installed_all: list[str] = []
            err: str | None = None
            try:
                for archive in archives:
                    installed_all.extend(install_mod_archive(archive, modpack_dir))
            except (OSError, ValueError) as exc:
                err = str(exc)
            self.after(0, lambda: self._on_install_complete(active, installed_all, err))

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_modpack_folders(self) -> None:
        for pid in self.config_manager.profiles:
            (MODPACKS_DIR / pid).mkdir(parents=True, exist_ok=True)

    def _active_modpack_dir(self) -> Path:
        modpack_dir = MODPACKS_DIR / self.config_manager.active_profile
        modpack_dir.mkdir(parents=True, exist_ok=True)
        return modpack_dir

    def _validate_game_path(self, path: str) -> None:
        has_vanilla, has_smapi, msg = validate_game_path(path)
        if has_smapi:
            smapi_ver = get_installed_smapi_version(path)
            if smapi_ver:
                msg = f"{msg} (v{smapi_ver})"
                self._check_smapi_update_async(smapi_ver)
            else:
                self.top_bar.set_smapi_update(None)
        else:
            self.top_bar.set_smapi_update(None)
        self.top_bar.set_validation_status(has_vanilla, has_smapi, msg)

    def _check_smapi_update_async(self, installed_ver: str) -> None:
        token = self.config_manager.github_token

        def worker() -> None:
            res = check_smapi_update(
                installed_ver, github_token=token, cache_path=UPDATE_CACHE_FILE
            )
            self.after(0, lambda: self._on_smapi_update_checked(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_smapi_update_checked(self, result: tuple[str, str] | None) -> None:
        if not self.winfo_exists():
            return
        if result is not None:
            self.top_bar.set_smapi_update(result[0], result[1])
        else:
            self.top_bar.set_smapi_update(None)

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

    def _create_modpack_shortcut(self) -> None:
        active = self.config_manager.active_profile
        profile_name = self.config_manager.profiles[active]["name"]
        try:
            shortcut = create_modpack_shortcut(
                active,
                shortcut_name=f"Stardew - {profile_name}",
                icon_path=ICON_FILE if ICON_FILE.is_file() else None,
            )
            self.launch_bar.set_status(
                f"Created Desktop shortcut: {shortcut.name}",
                level="success",
                auto_clear_ms=5000,
            )
        except OSError as exc:
            self.launch_bar.set_status(f"Shortcut failed: {exc}", level="error")

    def _save_config_preset(self) -> None:
        active = self.config_manager.active_profile
        count = save_config_preset(self._active_modpack_dir(), CONFIG_PRESETS_DIR / active)
        self.launch_bar.set_status(
            f"Saved {count} mod config.json snapshot(s) for '{active}'.",
            level="success" if count else "warning",
            auto_clear_ms=4000,
        )

    def _restore_config_preset(self) -> None:
        active = self.config_manager.active_profile
        count = restore_config_preset(self._active_modpack_dir(), CONFIG_PRESETS_DIR / active)
        if count:
            self.launch_bar.set_status(
                f"Restored {count} mod config.json snapshot(s) for '{active}'.",
                level="success",
                auto_clear_ms=4000,
            )
        else:
            self.launch_bar.set_status(
                f"No saved config.json snapshot found for '{active}'.",
                level="warning",
                auto_clear_ms=4000,
            )

    def _open_trash_bin(self) -> None:
        TrashBinDialog(
            self,
            trash_root=TRASH_DIR,
            on_restore=self._restore_trashed_mod,
            on_emptied=lambda n: self.launch_bar.set_status(
                f"Permanently deleted {n} mod(s) from Trash.",
                level="info",
                auto_clear_ms=4000,
            ),
        )

    def _restore_trashed_mod(self, item: TrashedMod) -> None:
        target_profile = (
            item.profile_id
            if item.profile_id in self.config_manager.profiles
            else self.config_manager.active_profile
        )
        try:
            restored_folder = restore_trashed_mod(item.entry_dir, MODPACKS_DIR / target_profile)
        except (OSError, ValueError) as exc:
            self.launch_bar.set_status(f"Restore failed: {exc}", level="error")
            return

        current = self.config_manager.get_enabled_mods(target_profile)
        if restored_folder not in current:
            self.config_manager.set_enabled_mods(current + [restored_folder], target_profile)
        self._refresh_profiles()
        if target_profile == self.config_manager.active_profile:
            self._refresh_mods()
        self.launch_bar.set_status(
            f"Restored '{restored_folder}' to modpack '{target_profile}'.",
            level="success",
            auto_clear_ms=4000,
        )

    def _maybe_show_onboarding(self) -> None:
        has_vanilla, has_smapi, _ = validate_game_path(self.config_manager.game_path)
        if not has_vanilla or not has_smapi:
            self.after(350, self._open_onboarding)

    def _open_onboarding(self) -> None:
        OnboardingDialog(
            self,
            initial_path=self.config_manager.game_path,
            initial_nexus_key=self.config_manager.nexus_api_key,
            on_install_smapi=self._install_or_update_smapi,
            on_finish=self._finish_onboarding,
        )

    def _finish_onboarding(self, game_path: str, nexus_key: str) -> None:
        if game_path:
            self.top_bar.set_path(game_path)
            self._on_game_path_changed(game_path)
        if nexus_key:
            self.config_manager.nexus_api_key = nexus_key
        self.launch_bar.set_status("Setup complete!", level="success", auto_clear_ms=4000)

    def _check_svmm_update_async(self) -> None:
        token = self.config_manager.github_token

        def worker() -> None:
            res = check_svmm_update(__version__, github_token=token)
            if res is not None:
                self.after(
                    0,
                    lambda: (
                        self.launch_bar.set_app_update(res[0], res[1])
                        if self.winfo_exists() and self.launch_bar.winfo_exists()
                        else None
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _open_asset_conflicts(self) -> None:
        active = self.config_manager.active_profile
        enabled = set(self.config_manager.get_enabled_mods(active))
        conflicts = detect_asset_conflicts(self._current_mods, enabled)
        AssetConflictDialog(
            self,
            conflicts=conflicts,
            on_disable_mod=self._disable_mod_from_conflict,
            on_open_details=self._show_mod_details,
        )

    def _disable_mod_from_conflict(self, mod: ModInfo) -> None:
        active = self.config_manager.active_profile
        current = self.config_manager.get_enabled_mods(active)
        updated = [m for m in current if m != mod.folder_name]
        self.config_manager.set_enabled_mods(updated, active)
        self.mod_list.sync_enabled(updated)
        self._refresh_profiles()
        self._refresh_dependency_warnings(set(updated))
        self.launch_bar.set_status(
            f"Disabled '{mod.name}' to resolve asset conflict.",
            level="info",
            auto_clear_ms=4000,
        )

    def _install_or_update_smapi(self) -> None:
        token = self.config_manager.github_token
        self.launch_bar.set_status("Fetching latest SMAPI release...", level="info")

        def worker() -> None:
            rel = fetch_latest_smapi_release(github_token=token)
            if rel is None:
                self.after(
                    0,
                    lambda: (
                        self.launch_bar.set_status(
                            "Could not reach GitHub; opening smapi.io...", level="warning"
                        ),
                        webbrowser.open("https://smapi.io/"),
                    ),
                )
                return
            try:
                installer_dir = download_and_extract_smapi(rel.download_url, SMAPI_INSTALLER_DIR)
                ok, msg = launch_smapi_installer(installer_dir)
                err = None if ok else msg
            except (OSError, ValueError) as exc:
                err = str(exc)
            self.after(0, lambda: self._on_smapi_installer_launched(rel.version, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_smapi_installer_launched(self, version: str, err: str | None) -> None:
        if not self.winfo_exists():
            return
        if err is None:
            self.launch_bar.set_status(
                f"Launched SMAPI v{version} installer — complete it, then click Refresh.",
                level="success",
                auto_clear_ms=7000,
            )
            self.after(4000, lambda: self._validate_game_path(self.config_manager.game_path))
        else:
            self.launch_bar.set_status(f"SMAPI installer failed: {err}", level="error")

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
            profile_ids=list(self.config_manager.profiles.keys()),
            save_bindings=self.config_manager.save_bindings,
            on_bind_save=self._on_bind_save,
        )

    def _on_bind_save(self, save_folder: str, profile_id: str | None) -> None:
        self.config_manager.bind_save(save_folder, profile_id)
        self._refresh_bound_farms()
        msg = (
            f"Bound '{save_folder}' to modpack '{profile_id}'."
            if profile_id
            else f"Unbound '{save_folder}'."
        )
        self.launch_bar.set_status(msg, level="info", auto_clear_ms=4000)

    def _refresh_bound_farms(self) -> None:
        bound_folders = set(self.config_manager.get_saves_for_profile())
        if not bound_folders:
            self.top_bar.set_bound_farms([])
            return
        farms = {f.folder_name: f.display_label for f in list_farm_saves()}
        labels = [farms.get(folder, folder) for folder in sorted(bound_folders)]
        self.top_bar.set_bound_farms(labels)

    def _open_settings(self, initial_tab: str = "General") -> None:
        SettingsDialog(
            self,
            github_token=self.config_manager.github_token,
            nexus_api_key=self.config_manager.nexus_api_key,
            auto_backup_saves=self.config_manager.auto_backup_saves,
            max_auto_backups=self.config_manager.max_auto_backups,
            launch_via_steam=self.config_manager.launch_via_steam,
            launch_args=self.config_manager.launch_args,
            current_theme=self.config_manager.theme,
            custom_theme=self.config_manager.custom_theme,
            update_cache_path=UPDATE_CACHE_FILE,
            compat_cache_path=SMAPI_COMPAT_CACHE_FILE,
            icon_cache_dir=MOD_ICONS_DIR,
            on_save=self._save_settings,
            on_apply_theme=self._apply_and_refresh_theme,
            on_cache_cleared=lambda: self.launch_bar.set_status(
                "Cleared update cache.", level="info", auto_clear_ms=3000
            ),
            initial_tab=initial_tab,
        )

    def _save_settings(
        self,
        github_token: str,
        nexus_api_key: str,
        auto_backup_saves: bool,
        launch_via_steam: bool,
        launch_args: str,
    ) -> None:
        self.config_manager.github_token = github_token
        self.config_manager.nexus_api_key = nexus_api_key
        self.config_manager.auto_backup_saves = auto_backup_saves
        self.config_manager.launch_via_steam = launch_via_steam
        self.config_manager.launch_args = launch_args
        self.launch_bar.set_status("Saved settings.", level="success", auto_clear_ms=3000)

    def _apply_and_refresh_theme(self, theme_name: str, custom_theme: dict[str, str]) -> None:
        if hasattr(self, "mod_list") and self.mod_list._search_after_id is not None:
            try:
                self.mod_list.after_cancel(self.mod_list._search_after_id)
            except tk.TclError:
                pass
            self.mod_list._search_after_id = None
        if hasattr(self, "mod_list") and self.mod_list._icon_batch_after_id is not None:
            try:
                self.mod_list.after_cancel(self.mod_list._icon_batch_after_id)
            except tk.TclError:
                pass
            self.mod_list._icon_batch_after_id = None
        if hasattr(self, "launch_bar") and self.launch_bar._toast_after_id is not None:
            try:
                self.launch_bar.after_cancel(self.launch_bar._toast_after_id)
            except tk.TclError:
                pass
            self.launch_bar._toast_after_id = None

        for attr in ("sidebar", "top_bar", "mod_list", "launch_bar"):
            widget = getattr(self, attr, None)
            if widget is not None and widget.winfo_exists():
                widget.destroy()

        resolved = apply_theme(theme_name, custom_theme)
        self.config_manager.theme = resolved
        self.config_manager.custom_theme = custom_theme
        self.configure(fg_color=COLORS["bg_app"])

        self._build_layout()
        self._validate_game_path(self.config_manager.game_path)
        self._refresh_profiles()
        active = self.config_manager.active_profile
        enabled = self.config_manager.get_enabled_mods(active)
        self.mod_list.set_mods(self._current_mods, enabled, active)
        self._refresh_dependency_warnings(set(enabled))
        if self._last_update_results:
            self.mod_list.set_updates(self._last_update_results)
        self.launch_bar.set_status(
            f"Theme applied: {resolved}", level="success", auto_clear_ms=3000
        )

    def _refresh_profiles(self) -> None:
        active = self.config_manager.active_profile
        self.sidebar.render_profiles(self.config_manager.profiles, active)
        self.top_bar.set_active_modpack(active)
        self._refresh_bound_farms()

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

    def _rename_active_profile(self) -> None:
        active = self.config_manager.active_profile
        dialog = ctk.CTkInputDialog(
            text=f"Rename modpack '{active}' to:",
            title="Rename Modpack",
        )
        new_name = dialog.get_input()
        if not new_name:
            return
        try:
            new_id = self.config_manager.rename_profile(active, new_name)
            if new_id != active:
                old_dir = MODPACKS_DIR / active
                new_dir = MODPACKS_DIR / new_id
                if old_dir.is_dir() and not new_dir.exists():
                    old_dir.rename(new_dir)
                else:
                    new_dir.mkdir(parents=True, exist_ok=True)
                old_profile_dir = PROFILES_DIR / active
                if old_profile_dir.is_dir():
                    shutil.rmtree(old_profile_dir, ignore_errors=True)
        except (OSError, ValueError, KeyError) as exc:
            self.launch_bar.set_status(f"Rename failed: {exc}", level="error")
            return

        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Renamed '{active}' to '{new_id}'.", level="success", auto_clear_ms=4000
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

    def _coop_parity_check(self) -> None:
        src = filedialog.askopenfilename(
            title="Select Friend's Exported Modlist (.json)",
            filetypes=[("JSON files", "*.json")],
        )
        if not src:
            return
        try:
            friend_name, friend_mods = load_friend_modlist(src)
        except (OSError, ValueError) as exc:
            self.launch_bar.set_status(f"Co-op check failed: {exc}", level="error")
            return

        active = self.config_manager.active_profile
        enabled = set(self.config_manager.get_enabled_mods(active))
        report = compare_with_friend_modlist(friend_name, friend_mods, self._current_mods, enabled)
        CoopParityDialog(self, report=report, on_sync_toggles=self._apply_coop_sync)

    def _apply_coop_sync(self, report: CoopParityReport) -> None:
        active = self.config_manager.active_profile
        current = set(self.config_manager.get_enabled_mods(active))
        for mod in report.extra_mods:
            current.discard(mod.folder_name)
        for item in report.missing_mods:
            if item.local_folder_if_installed:
                current.add(item.local_folder_if_installed)

        ordered = [m.folder_name for m in self._current_mods if m.folder_name in current]
        self.config_manager.set_enabled_mods(ordered, active)
        self.mod_list.sync_enabled(ordered)
        self._refresh_profiles()
        self._refresh_dependency_warnings(set(ordered))
        self.launch_bar.set_status(
            f"Synced local toggles to match '{report.friend_profile}'.",
            level="success",
            auto_clear_ms=4000,
        )

    def _export_bundle(self) -> None:
        active = self.config_manager.active_profile
        profile_name = self.config_manager.profiles[active]["name"]
        enabled = self.config_manager.get_enabled_mods(active)
        dest = filedialog.asksaveasfilename(
            title="Export Full Modpack Bundle (.zip)",
            defaultextension=".zip",
            initialfile=f"{active}_modpack.zip",
            filetypes=[("Zip archive", "*.zip")],
        )
        if not dest:
            return

        modpack_dir = self._active_modpack_dir()
        self.launch_bar.set_status(f"Packaging '{active}' bundle...", level="info")

        def worker() -> None:
            try:
                out = export_modpack_bundle(dest, active, profile_name, modpack_dir, enabled)
                msg, lvl = f"Exported modpack bundle to {out.name}.", "success"
            except OSError as exc:
                msg, lvl = f"Bundle export failed: {exc}", "error"
            self.after(0, lambda: self.launch_bar.set_status(msg, level=lvl, auto_clear_ms=5000))

        threading.Thread(target=worker, daemon=True).start()

    def _import_bundle(self) -> None:
        src = filedialog.askopenfilename(
            title="Import Modpack Bundle (.zip)",
            filetypes=[("Zip archive", "*.zip")],
        )
        if not src:
            return

        self.mod_list.set_loading(True, f"Importing {Path(src).name}...")
        self.launch_bar.set_status(f"Importing modpack bundle {Path(src).name}...", level="info")

        def worker() -> None:
            try:
                new_id = import_modpack_bundle(src, MODPACKS_DIR, self.config_manager)
                err = None
            except (OSError, ValueError) as exc:
                new_id = ""
                err = str(exc)
            self.after(0, lambda: self._on_bundle_imported(new_id, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bundle_imported(self, new_id: str, error: str | None) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_loading(False)
        if error:
            self.launch_bar.set_status(f"Bundle import failed: {error}", level="error")
            self._refresh_mods()
            return
        self.config_manager.active_profile = new_id
        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Imported modpack bundle as '{new_id}'.", level="success", auto_clear_ms=5000
        )

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
            title="Select Mod Archive (.zip, .7z, or .rar)",
            filetypes=[
                ("Mod archives", "*.zip *.7z *.rar"),
                ("Zip archives", "*.zip"),
                ("7z archives", "*.7z"),
                ("RAR archives", "*.rar"),
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

    def _coop_parity_check(self) -> None:
        src = filedialog.askopenfilename(
            title="Select Friend's Exported Modlist (.json)",
            filetypes=[("JSON files", "*.json")],
        )
        if not src:
            return
        try:
            friend_name, friend_mods = load_friend_modlist(src)
        except (OSError, ValueError) as exc:
            self.launch_bar.set_status(f"Co-op check failed: {exc}", level="error")
            return

        active = self.config_manager.active_profile
        enabled = set(self.config_manager.get_enabled_mods(active))
        report = compare_with_friend_modlist(friend_name, friend_mods, self._current_mods, enabled)
        CoopParityDialog(self, report=report, on_sync_toggles=self._apply_coop_sync)

    def _apply_coop_sync(self, report: CoopParityReport) -> None:
        active = self.config_manager.active_profile
        current = set(self.config_manager.get_enabled_mods(active))
        for mod in report.extra_mods:
            current.discard(mod.folder_name)
        for item in report.missing_mods:
            if item.local_folder_if_installed:
                current.add(item.local_folder_if_installed)

        ordered = [m.folder_name for m in self._current_mods if m.folder_name in current]
        self.config_manager.set_enabled_mods(ordered, active)
        self.mod_list.sync_enabled(ordered)
        self._refresh_profiles()
        self._refresh_dependency_warnings(set(ordered))
        self.launch_bar.set_status(
            f"Synced local toggles to match '{report.friend_profile}'.",
            level="success",
            auto_clear_ms=4000,
        )

    def _export_bundle(self) -> None:
        active = self.config_manager.active_profile
        profile_name = self.config_manager.profiles[active]["name"]
        enabled = self.config_manager.get_enabled_mods(active)
        dest = filedialog.asksaveasfilename(
            title="Export Full Modpack Bundle (.zip)",
            defaultextension=".zip",
            initialfile=f"{active}_modpack.zip",
            filetypes=[("Zip archive", "*.zip")],
        )
        if not dest:
            return

        modpack_dir = self._active_modpack_dir()
        self.launch_bar.set_status(f"Packaging '{active}' bundle...", level="info")

        def worker() -> None:
            try:
                out = export_modpack_bundle(dest, active, profile_name, modpack_dir, enabled)
                msg, lvl = f"Exported modpack bundle to {out.name}.", "success"
            except OSError as exc:
                msg, lvl = f"Bundle export failed: {exc}", "error"
            self.after(0, lambda: self.launch_bar.set_status(msg, level=lvl, auto_clear_ms=5000))

        threading.Thread(target=worker, daemon=True).start()

    def _import_bundle(self) -> None:
        src = filedialog.askopenfilename(
            title="Import Modpack Bundle (.zip)",
            filetypes=[("Zip archive", "*.zip")],
        )
        if not src:
            return

        self.mod_list.set_loading(True, f"Importing {Path(src).name}...")
        self.launch_bar.set_status(f"Importing modpack bundle {Path(src).name}...", level="info")

        def worker() -> None:
            try:
                new_id = import_modpack_bundle(src, MODPACKS_DIR, self.config_manager)
                err = None
            except (OSError, ValueError) as exc:
                new_id = ""
                err = str(exc)
            self.after(0, lambda: self._on_bundle_imported(new_id, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bundle_imported(self, new_id: str, error: str | None) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_loading(False)
        if error:
            self.launch_bar.set_status(f"Bundle import failed: {error}", level="error")
            self._refresh_mods()
            return
        self.config_manager.active_profile = new_id
        self._refresh_profiles()
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Imported modpack bundle as '{new_id}'.", level="success", auto_clear_ms=5000
        )

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
        self._last_update_results = results
        self.mod_list.set_updates(results)
        has_nexus = bool(self.config_manager.nexus_api_key.strip())
        updatable = [r for r in results if can_direct_update(r, has_nexus_key=has_nexus)]
        self.mod_list.set_updatable_count(len(updatable))
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

    def _check_smapi_compat(self) -> None:
        if not self._current_mods:
            self.launch_bar.set_status("No mods to check compatibility for.", level="info")
            return

        mods_snapshot = list(self._current_mods)
        self.launch_bar.set_status("Checking smapi.io compatibility database...", level="info")

        def worker() -> None:
            compat_map = check_smapi_compatibility(
                mods_snapshot, cache_path=SMAPI_COMPAT_CACHE_FILE
            )
            self.after(0, lambda: self._on_compat_checked(compat_map))

        threading.Thread(target=worker, daemon=True).start()

    def _on_compat_checked(self, compat_map: dict[str, SmapiCompatInfo]) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_compat(compat_map)
        if not compat_map:
            self.launch_bar.set_status(
                "No compatibility data returned (offline or no UniqueIDs).", level="warning"
            )
            return
        broken = sum(1 for c in compat_map.values() if c.is_broken)
        warnings = sum(1 for c in compat_map.values() if c.is_warning)
        if broken or warnings:
            self.launch_bar.set_status(
                f"SMAPI Compat: {broken} broken/obsolete, {warnings} unofficial/workaround.",
                level="warning",
            )
        else:
            self.launch_bar.set_status(
                f"SMAPI Compat: all {len(compat_map)} checked mod(s) compatible!",
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

    def _update_all_mods(self) -> None:
        has_nexus = bool(self.config_manager.nexus_api_key.strip())
        targets = [
            r for r in self._last_update_results if can_direct_update(r, has_nexus_key=has_nexus)
        ]
        if not targets:
            return

        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()
        nexus_key = self.config_manager.nexus_api_key
        gh_token = self.config_manager.github_token
        self.mod_list.set_loading(True, f"Updating {len(targets)} mod(s)...")

        def worker() -> None:
            updated_folders: list[str] = []
            failed: list[str] = []
            total = len(targets)
            for idx, res in enumerate(targets, start=1):
                self.after(
                    0,
                    lambda i=idx, name=res.mod_name: self.launch_bar.set_status(
                        f"Updating {i}/{total}: {name}...", level="info"
                    ),
                )
                try:
                    updated_folders.extend(
                        install_mod_update(
                            res,
                            modpack_dir,
                            nexus_api_key=nexus_key,
                            github_token=gh_token,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    failed.append(f"{res.mod_name} ({exc})")
            self.after(0, lambda: self._on_update_all_done(active, updated_folders, failed))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_all_done(
        self, profile_id: str, updated_folders: list[str], failed: list[str]
    ) -> None:
        if not self.winfo_exists():
            return
        self.mod_list.set_loading(False)
        self.mod_list.set_updatable_count(0)
        self._last_update_results = []
        if updated_folders:
            current = self.config_manager.get_enabled_mods(profile_id)
            self.config_manager.set_enabled_mods(current + updated_folders, profile_id)
        self._refresh_mods()

        if failed:
            self.launch_bar.set_status(
                f"Updated {len(updated_folders)} folder(s); {len(failed)} failed.",
                level="warning",
            )
        else:
            self.launch_bar.set_status(
                f"Successfully updated {len(updated_folders)} mod folder(s)!",
                level="success",
                auto_clear_ms=5000,
            )

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
        self._prefetch_mod_icons_async(generation, mods)

    def _prefetch_mod_icons_async(self, generation: int, mods: list[ModInfo]) -> None:
        api_key = self.config_manager.nexus_api_key.strip()
        if not api_key or not mods:
            return

        def worker() -> None:
            for mod in mods:
                if generation != self._scan_generation:
                    return
                nexus_id = extract_nexus_mod_id(mod)
                if not nexus_id:
                    continue
                target = MOD_ICONS_DIR / f"nexus_{nexus_id}.png"
                if target.is_file():
                    continue
                fetched = fetch_nexus_mod_thumbnail(nexus_id, api_key, MOD_ICONS_DIR)
                if fetched is not None:
                    img = load_mod_icon(mod, MOD_ICONS_DIR, size=84)
                    self.after(
                        0,
                        lambda f=mod.folder_name, im=img: (
                            self.mod_list.update_mod_icon(f, im)
                            if self.winfo_exists() and self.mod_list.winfo_exists()
                            else None
                        ),
                    )

        threading.Thread(target=worker, daemon=True).start()

    def _on_mods_toggled(self, enabled_mods: list[str]) -> None:
        self.config_manager.set_enabled_mods(enabled_mods)
        self._refresh_profiles()
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
                trash_root=TRASH_DIR,
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
            f"Moved '{mod.name}' to Trash Bin (Tools ▾ → Mod Trash Bin to restore).",
            level="success",
            auto_clear_ms=5000,
        )

    def _bulk_uninstall_mods(self, mods: list[ModInfo]) -> None:
        if not messagebox.askyesno(
            "Uninstall Selected Mods",
            f"Move {len(mods)} selected mod(s) to the Trash Bin?",
        ):
            return
        active = self.config_manager.active_profile
        modpack_dir = self._active_modpack_dir()
        removed: set[str] = set()
        for mod in mods:
            try:
                uninstall_mod(
                    mod.folder_name,
                    modpack_dir,
                    profiles_root=PROFILES_DIR,
                    profile_id=active,
                    trash_root=TRASH_DIR,
                )
                removed.add(mod.folder_name)
            except (OSError, ValueError):
                pass
        remaining = [m for m in self.config_manager.get_enabled_mods(active) if m not in removed]
        self.config_manager.set_enabled_mods(remaining, active)
        self._refresh_mods()
        self.launch_bar.set_status(
            f"Moved {len(removed)} mod(s) to Trash Bin.",
            level="success",
            auto_clear_ms=5000,
        )

    def _launch_modded(self) -> None:
        game_path = self.top_bar.get_path()
        self._on_game_path_changed(game_path)
        active = self.config_manager.active_profile
        enabled = self.config_manager.get_enabled_mods(active)
        smapi_ver = get_installed_smapi_version(game_path)
        issues = analyze_mod_dependencies(self._current_mods, set(enabled), smapi_version=smapi_ver)
        conflicts = detect_asset_conflicts(self._current_mods, set(enabled))
        if issues or conflicts:
            sections: list[str] = []
            if issues:
                sections.append(
                    "Dependency / Version Issues:\n"
                    + format_issue_summary(issues, self._current_mods)
                )
            if conflicts:
                sections.append(
                    "Content Patcher Asset Conflicts:\n" + format_asset_conflicts(conflicts)
                )
            proceed = messagebox.askyesno(
                "Pre-Launch Warnings",
                f"Issues detected in modpack '{active}':\n\n"
                + "\n\n".join(sections)
                + "\n\nLaunch SMAPI anyway?",
            )
            if not proceed:
                return

        modpack_dir = self._active_modpack_dir()
        auto_backup = self.config_manager.auto_backup_saves
        max_auto = self.config_manager.max_auto_backups
        launch_args = self.config_manager.launch_args
        via_steam = self.config_manager.launch_via_steam

        self.launch_bar.set_busy(True)
        self.launch_bar.set_status(f"Syncing '{active}' and launching SMAPI...", level="info")

        def worker() -> None:
            try:
                if auto_backup:
                    saves_dir = get_default_saves_dir()
                    if saves_dir.is_dir():
                        create_save_backup(saves_dir, SAVE_BACKUPS_DIR, label="auto")
                        prune_auto_backups(SAVE_BACKUPS_DIR, keep=max_auto)
                profile_dir = sync_profile(active, enabled, modpack_dir, PROFILES_DIR)
                ok, msg = link_game_mods(game_path, profile_dir)
                if ok:
                    ok, msg = launch_game(
                        game_path,
                        modded=True,
                        launch_args=launch_args,
                        launch_via_steam=via_steam,
                    )
            except OSError as exc:
                ok, msg = False, f"Sync failed: {exc}"
            self.after(0, lambda: self._on_launch_complete(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_vanilla(self) -> None:
        game_path = self.top_bar.get_path()
        self._on_game_path_changed(game_path)
        launch_args = self.config_manager.launch_args
        via_steam = self.config_manager.launch_via_steam

        self.launch_bar.set_busy(True)
        self.launch_bar.set_status("Unlinking Mods and launching Vanilla...", level="info")

        def worker() -> None:
            ok, msg = unlink_game_mods(game_path)
            if ok:
                ok, msg = launch_game(
                    game_path,
                    modded=False,
                    launch_args=launch_args,
                    launch_via_steam=via_steam,
                )
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

    if len(sys.argv) > 2 and sys.argv[1] == "--launch-profile":
        target_profile = sys.argv[2]
        cfg = ConfigManager(CONFIG_FILE)
        if target_profile in cfg.profiles:
            cfg.active_profile = target_profile
            enabled = cfg.get_enabled_mods(target_profile)
            profile_dir = sync_profile(
                target_profile, enabled, MODPACKS_DIR / target_profile, PROFILES_DIR
            )
            ok, msg = link_game_mods(cfg.game_path, profile_dir)
            if ok:
                ok, msg = launch_game(
                    cfg.game_path,
                    modded=True,
                    launch_args=cfg.launch_args,
                    launch_via_steam=cfg.launch_via_steam,
                )
            if ok:
                return
            nxm_status = (f"Shortcut launch failed: {msg}", "error")
        else:
            nxm_status = (f"Modpack '{target_profile}' not found.", "error")

    app = SVModManagerApp()
    if nxm_status is not None:
        msg, level = nxm_status
        app.after(300, lambda: app.launch_bar.set_status(msg, level=level))
    app.mainloop()


if __name__ == "__main__":
    main()
