"""Entry point and application orchestrator for Stardew Valley Mod Manager."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def _ensure_venv() -> None:
    """Re-launch using .venv Python when double-clicked or run with system Python."""
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

from src.core.config import ConfigManager
from src.core.launcher import get_smapi_log_path, launch_game, validate_game_path
from src.core.mod_manager import link_game_mods, sync_profile, unlink_game_mods
from src.core.mod_scanner import ModInfo, scan_mod_pool
from src.ui.launch_bar import LaunchBar
from src.ui.mod_list import ModListPanel
from src.ui.profile_sidebar import ProfileSidebar
from src.ui.theme import SPACING
from src.ui.top_bar import TopBar

MODPACKS_DIR = PROJECT_ROOT / "SVMM_Data" / "modpacks"
PROFILES_DIR = PROJECT_ROOT / "SVMM_Data" / "profiles"
CONFIG_FILE = PROJECT_ROOT / "SVMM_Data" / "config.json"
LOGO_FILE = PROJECT_ROOT / "assets" / "logo.png"
ICON_FILE = PROJECT_ROOT / "assets" / "logo.ico"


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
        self.title("Stardew Valley Mod Manager")
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
            on_launch_modded=self._launch_modded,
            on_launch_vanilla=self._launch_vanilla,
            on_open_smapi_log=self._open_smapi_log,
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
        _open_in_file_manager(log_path)

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
        self.mod_list.set_loading(False)
        enabled = self.config_manager.get_enabled_mods(profile_id)
        self.mod_list.set_mods(mods, enabled, profile_id)
        self.launch_bar.set_status(
            f"Found {len(mods)} mod(s) in modpack '{profile_id}'.", level="info"
        )

    def _on_mods_toggled(self, enabled_mods: list[str]) -> None:
        self.config_manager.set_enabled_mods(enabled_mods)

    def _launch_modded(self) -> None:
        game_path = self.top_bar.get_path()
        self._on_game_path_changed(game_path)
        active = self.config_manager.active_profile
        enabled = self.config_manager.get_enabled_mods(active)
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
    app = SVModManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
