"""Entry point and GUI for the Stardew Valley Mod Manager."""

from __future__ import annotations

import os
import subprocess
import sys
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

from tkinter import filedialog
import customtkinter as ctk

from src.core.config import ConfigManager
from src.core.launcher import launch_game
from src.core.mod_manager import link_game_mods, sync_profile, unlink_game_mods
from src.core.mod_scanner import ModInfo, scan_mod_pool

MODPACKS_DIR = PROJECT_ROOT / "SVMM_Data" / "modpacks"
PROFILES_DIR = PROJECT_ROOT / "SVMM_Data" / "profiles"
CONFIG_FILE = PROJECT_ROOT / "SVMM_Data" / "config.json"


class SVModManagerApp(ctk.CTk):
    """Main application window for Stardew Valley Mod Manager."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Stardew Valley Mod Manager")
        self.geometry("960x640")
        self.minsize(780, 520)

        MODPACKS_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

        self.config_manager = ConfigManager(CONFIG_FILE)
        self._ensure_modpack_folders()
        self.mods: list[ModInfo] = []
        self.mod_vars: dict[str, ctk.BooleanVar] = {}
        self.profile_buttons: dict[str, ctk.CTkButton] = {}

        self._build_ui()
        self._refresh_profiles()
        self._refresh_mods()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top Bar ---
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_frame, text="Game Path:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(10, 6), pady=10
        )

        self.game_path_var = ctk.StringVar(value=self.config_manager.game_path)
        self.game_path_entry = ctk.CTkEntry(top_frame, textvariable=self.game_path_var)
        self.game_path_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=10)
        self.game_path_entry.bind("<FocusOut>", lambda _e: self._save_game_path())
        self.game_path_entry.bind("<Return>", lambda _e: self._save_game_path())

        ctk.CTkButton(top_frame, text="Browse", width=90, command=self._browse_game_path).grid(
            row=0, column=2, padx=4, pady=10
        )
        ctk.CTkButton(
            top_frame, text="Open Modpack Folder", width=150, command=self._open_modpack_folder
        ).grid(row=0, column=3, padx=(4, 10), pady=10)

        # --- Left Sidebar (Profiles) ---
        sidebar = ctk.CTkFrame(self, width=230)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=6)
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            sidebar, text="Profiles", font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.profile_list_frame = ctk.CTkScrollableFrame(sidebar)
        self.profile_list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.profile_list_frame.grid_columnconfigure(0, weight=1)

        add_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        add_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(6, 4))
        add_frame.grid_columnconfigure(0, weight=1)

        self.new_profile_entry = ctk.CTkEntry(add_frame, placeholder_text="New profile...")
        self.new_profile_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.new_profile_entry.bind("<Return>", lambda _e: self._create_profile())

        ctk.CTkButton(add_frame, text="+", width=36, command=self._create_profile).grid(
            row=0, column=1
        )

        ctk.CTkButton(
            sidebar,
            text="Delete Active Profile",
            fg_color="#8B2E2E",
            hover_color="#A83838",
            command=self._delete_active_profile,
        ).grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 10))

        # --- Main Area (Mods List) ---
        main_area = ctk.CTkFrame(self)
        main_area.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=6)
        main_area.grid_columnconfigure(0, weight=1)
        main_area.grid_rowconfigure(1, weight=1)

        filter_bar = ctk.CTkFrame(main_area, fg_color="transparent")
        filter_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        filter_bar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_args: self._render_mod_list())
        ctk.CTkEntry(
            filter_bar, textvariable=self.search_var, placeholder_text="Filter mods..."
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(filter_bar, text="Select All", width=90, command=self._select_all).grid(
            row=0, column=1, padx=3
        )
        ctk.CTkButton(filter_bar, text="Deselect All", width=96, command=self._deselect_all).grid(
            row=0, column=2, padx=3
        )
        ctk.CTkButton(filter_bar, text="Refresh", width=80, command=self._refresh_mods).grid(
            row=0, column=3, padx=(3, 0)
        )

        self.mods_scroll_frame = ctk.CTkScrollableFrame(main_area)
        self.mods_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.mods_scroll_frame.grid_columnconfigure(0, weight=1)

        # --- Bottom Bar (Launch Controls) ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            bottom_frame,
            text="LAUNCH MODDED (SMAPI)",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2B7A3D",
            hover_color="#35944B",
            command=self._launch_modded,
        ).grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=(10, 4))

        ctk.CTkButton(
            bottom_frame,
            text="LAUNCH VANILLA (NO MODS)",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4A5568",
            hover_color="#5A677D",
            command=self._launch_vanilla,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=(10, 4))

        self.status_label = ctk.CTkLabel(
            bottom_frame, text="Ready.", anchor="w", text_color="#A0AEC0"
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 8))

    def _set_status(self, message: str, is_error: bool = False) -> None:
        color = "#FC8181" if is_error else "#A0AEC0"
        self.status_label.configure(text=message, text_color=color)

    def _save_game_path(self) -> None:
        self.config_manager.game_path = self.game_path_var.get().strip()

    def _browse_game_path(self) -> None:
        selected = filedialog.askdirectory(title="Select Stardew Valley Installation Folder")
        if selected:
            self.game_path_var.set(selected)
            self._save_game_path()
            self._set_status(f"Game path set to: {selected}")

    def _ensure_modpack_folders(self) -> None:
        for pid in self.config_manager.profiles:
            (MODPACKS_DIR / pid).mkdir(parents=True, exist_ok=True)

    def _active_modpack_dir(self) -> Path:
        modpack_dir = MODPACKS_DIR / self.config_manager.active_profile
        modpack_dir.mkdir(parents=True, exist_ok=True)
        return modpack_dir

    def _open_modpack_folder(self) -> None:
        modpack_dir = self._active_modpack_dir()
        if sys.platform == "win32":
            os.startfile(str(modpack_dir))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(modpack_dir)])
        else:
            subprocess.Popen(["xdg-open", str(modpack_dir)])

    def _refresh_profiles(self) -> None:
        for widget in self.profile_list_frame.winfo_children():
            widget.destroy()
        self.profile_buttons.clear()

        active = self.config_manager.active_profile
        for row_idx, (pid, pdata) in enumerate(self.config_manager.profiles.items()):
            is_active = pid == active
            btn = ctk.CTkButton(
                self.profile_list_frame,
                text=pdata.get("name", pid),
                anchor="w",
                fg_color="#1F6AA5" if is_active else "transparent",
                hover_color="#144870" if is_active else "#2B2B2B",
                command=lambda p=pid: self._select_profile(p),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", pady=2)
            self.profile_buttons[pid] = btn

    def _select_profile(self, profile_id: str) -> None:
        self.config_manager.active_profile = profile_id
        self._refresh_profiles()
        self._refresh_mods()
        self._set_status(f"Switched to modpack '{profile_id}'.")

    def _create_profile(self) -> None:
        name = self.new_profile_entry.get().strip()
        if not name:
            self._set_status("Enter a profile name first.", is_error=True)
            return
        try:
            self.config_manager.create_profile(name, name)
            self.config_manager.active_profile = name
        except ValueError as exc:
            self._set_status(str(exc), is_error=True)
            return

        (MODPACKS_DIR / name).mkdir(parents=True, exist_ok=True)
        self.new_profile_entry.delete(0, "end")
        self._refresh_profiles()
        self._refresh_mods()
        self._set_status(f"Created modpack '{name}' at SVMM_Data/modpacks/{name}.")

    def _delete_active_profile(self) -> None:
        active = self.config_manager.active_profile
        try:
            self.config_manager.delete_profile(active)
        except ValueError as exc:
            self._set_status(str(exc), is_error=True)
            return

        self._refresh_profiles()
        self._refresh_mods()
        self._set_status(f"Deleted profile '{active}' (mod files in SVMM_Data/modpacks/{active} were kept).")

    def _refresh_mods(self) -> None:
        modpack_dir = self._active_modpack_dir()
        self.mods = scan_mod_pool(modpack_dir)
        self._sync_checkboxes_from_config()
        self._set_status(
            f"Found {len(self.mods)} mod(s) in modpack '{self.config_manager.active_profile}'."
        )

    def _sync_checkboxes_from_config(self) -> None:
        enabled = set(self.config_manager.get_enabled_mods())
        self.mod_vars = {
            mod.folder_name: ctk.BooleanVar(value=mod.folder_name in enabled)
            for mod in self.mods
        }
        self._render_mod_list()

    def _render_mod_list(self) -> None:
        for widget in self.mods_scroll_frame.winfo_children():
            widget.destroy()

        query = self.search_var.get().strip().lower()
        visible = [
            mod
            for mod in self.mods
            if not query
            or query in mod.name.lower()
            or query in mod.folder_name.lower()
        ]

        if not visible:
            active = self.config_manager.active_profile
            msg = (
                "No mods match your filter."
                if self.mods
                else f"No mods found in SVMM_Data/modpacks/{active}. Click 'Open Modpack Folder' to add mods."
            )
            ctk.CTkLabel(self.mods_scroll_frame, text=msg, text_color="#A0AEC0").grid(
                row=0, column=0, padx=10, pady=20
            )
            return

        for idx, mod in enumerate(visible):
            var = self.mod_vars[mod.folder_name]
            label = f"{mod.name} (v{mod.version})  [{mod.folder_name}]"
            if mod.error:
                label += f"  - {mod.error}"
            cb = ctk.CTkCheckBox(
                self.mods_scroll_frame,
                text=label,
                variable=var,
                command=self._on_mod_toggled,
            )
            cb.grid(row=idx, column=0, sticky="w", padx=8, pady=4)

    def _on_mod_toggled(self) -> None:
        enabled = [folder for folder, var in self.mod_vars.items() if var.get()]
        self.config_manager.set_enabled_mods(enabled)

    def _select_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self.mods:
            if not query or query in mod.name.lower() or query in mod.folder_name.lower():
                self.mod_vars[mod.folder_name].set(True)
        self._on_mod_toggled()

    def _deselect_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self.mods:
            if not query or query in mod.name.lower() or query in mod.folder_name.lower():
                self.mod_vars[mod.folder_name].set(False)
        self._on_mod_toggled()

    def _launch_modded(self) -> None:
        self._save_game_path()
        game_path = self.config_manager.game_path
        active = self.config_manager.active_profile
        enabled = self.config_manager.get_enabled_mods(active)

        try:
            profile_dir = sync_profile(
                active, enabled, self._active_modpack_dir(), PROFILES_DIR
            )
        except OSError as exc:
            self._set_status(f"Sync failed: {exc}", is_error=True)
            return

        ok, msg = link_game_mods(game_path, profile_dir)
        if not ok:
            self._set_status(msg, is_error=True)
            return

        ok, launch_msg = launch_game(game_path, modded=True)
        self._set_status(launch_msg, is_error=not ok)

    def _launch_vanilla(self) -> None:
        self._save_game_path()
        game_path = self.config_manager.game_path

        ok, msg = unlink_game_mods(game_path)
        if not ok:
            self._set_status(msg, is_error=True)
            return

        ok, launch_msg = launch_game(game_path, modded=False)
        self._set_status(launch_msg, is_error=not ok)


def main() -> None:
    """Initialize theme and run the Stardew Valley Mod Manager GUI."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = SVModManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
