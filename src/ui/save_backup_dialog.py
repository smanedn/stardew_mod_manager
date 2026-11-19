"""Save game backup and restore dialog."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from src.core.save_backup import (
    create_save_backup,
    get_default_saves_dir,
    list_save_backups,
    restore_save_backup,
)
from src.core.save_binding import list_farm_saves
from src.ui.theme import COLORS, SPACING, font_bold, font_small


class SaveBackupDialog(ctk.CTkToplevel):
    """Manage Stardew Valley save backups (.zip) in SVMM_Data/save_backups."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        backups_root: Path,
        on_open_folder: Callable[[Path], None],
        on_status: Callable[[str, str], None] | None = None,
        profile_ids: list[str] | None = None,
        save_bindings: dict[str, str] | None = None,
        on_bind_save: Callable[[str, str | None], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Save Backups & Farm Bindings")
        self.geometry("680x520")
        self.minsize(560, 420)
        self.transient(master)
        self.grab_set()

        self._saves_dir = get_default_saves_dir()
        self._backups_root = backups_root
        self._on_open_folder = on_open_folder
        self._on_status = on_status
        self._profile_ids = profile_ids or []
        self._save_bindings = dict(save_bindings or {})
        self._on_bind_save = on_bind_save
        self._active_tab = "Backups"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Tab Switcher ---
        self.tab_switch = ctk.CTkSegmentedButton(
            self,
            values=["Backups", "Farm Bindings"],
            command=self._switch_tab,
        )
        self.tab_switch.set("Backups")
        self.tab_switch.grid(
            row=0, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"])
        )

        # --- Top Create Bar (Backups tab) ---
        self.top_bar = ctk.CTkFrame(self, border_width=1, border_color=COLORS["border"])
        self.top_bar.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["xs"])
        self.top_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.top_bar, text="Label:", font=font_bold()).grid(
            row=0, column=0, padx=(SPACING["md"], SPACING["sm"]), pady=SPACING["md"]
        )
        self.label_entry = ctk.CTkEntry(
            self.top_bar, placeholder_text="Optional label (e.g. before_sve)..."
        )
        self.label_entry.grid(row=0, column=1, sticky="ew", padx=SPACING["sm"], pady=SPACING["md"])

        ctk.CTkButton(
            self.top_bar,
            text="Backup Saves Now",
            width=145,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._create_backup,
        ).grid(row=0, column=2, padx=(4, SPACING["md"]), pady=SPACING["md"])

        # --- Scrollable List ---
        self.list_frame = ctk.CTkScrollableFrame(
            self, border_width=1, border_color=COLORS["border"]
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
        self.list_frame.grid_columnconfigure(0, weight=1)

        # --- Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"])
        )
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text=f"Saves: {self._saves_dir}",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            footer,
            text="Open Backups Folder",
            width=150,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self._open_backups_folder,
        ).grid(row=0, column=1, padx=(8, 8))

        ctk.CTkButton(footer, text="Close", width=80, command=self.destroy).grid(row=0, column=2)

        self._refresh_list()

    def _switch_tab(self, tab: str) -> None:
        self._active_tab = tab
        if tab == "Backups":
            self.top_bar.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["xs"])
            self._refresh_list()
        else:
            self.top_bar.grid_remove()
            self._refresh_bindings()

    def _refresh_bindings(self) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        farms = list_farm_saves(self._saves_dir)
        if not farms:
            ctk.CTkLabel(
                self.list_frame,
                text=f"No farm saves found in {self._saves_dir}.",
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=0, padx=SPACING["md"], pady=24)
            return

        options = ["Unbound", *self._profile_ids]
        for idx, farm in enumerate(farms):
            row = ctk.CTkFrame(
                self.list_frame,
                fg_color=COLORS["surface_alt"],
                border_width=1,
                border_color=COLORS["border"],
            )
            row.grid(row=idx, column=0, sticky="ew", padx=6, pady=4)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row, text=farm.display_label, font=font_bold(), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=(6, 0)
            )
            ctk.CTkLabel(
                row,
                text=farm.folder_name,
                font=font_small(),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

            bound = self._save_bindings.get(farm.folder_name, "Unbound")
            if bound not in options:
                bound = "Unbound"
            menu = ctk.CTkOptionMenu(
                row,
                values=options,
                width=160,
                command=lambda choice, sf=farm.folder_name: self._bind_changed(sf, choice),
            )
            menu.set(bound)
            menu.grid(row=0, column=1, rowspan=2, padx=10, pady=8)

    def _bind_changed(self, save_folder: str, choice: str) -> None:
        target = None if choice == "Unbound" else choice
        if target is None:
            self._save_bindings.pop(save_folder, None)
        else:
            self._save_bindings[save_folder] = target
        if self._on_bind_save is not None:
            self._on_bind_save(save_folder, target)

    def _open_backups_folder(self) -> None:
        self._backups_root.mkdir(parents=True, exist_ok=True)
        self._on_open_folder(self._backups_root)

    def _create_backup(self) -> None:
        label = self.label_entry.get().strip()
        try:
            archive = create_save_backup(self._saves_dir, self._backups_root, label=label)
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror("Backup Failed", str(exc), parent=self)
            return

        self.label_entry.delete(0, "end")
        self._refresh_list()
        if self._on_status is not None:
            self._on_status(f"Created save backup: {archive.name}", "success")

    def _refresh_list(self) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        backups = list_save_backups(self._backups_root)
        if not backups:
            ctk.CTkLabel(
                self.list_frame,
                text="No save backups yet. Click 'Backup Saves Now' above.",
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=0, padx=SPACING["md"], pady=24)
            return

        for idx, b in enumerate(backups):
            row = ctk.CTkFrame(
                self.list_frame,
                fg_color=COLORS["surface_alt"],
                border_width=1,
                border_color=COLORS["border"],
            )
            row.grid(row=idx, column=0, sticky="ew", padx=6, pady=4)
            row.grid_columnconfigure(0, weight=1)

            dt = datetime.fromtimestamp(b.modified_ts).strftime("%Y-%m-%d %H:%M")
            size_kb = max(1, b.size_bytes // 1024)
            ctk.CTkLabel(row, text=b.name, font=font_bold(), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=(6, 0)
            )
            ctk.CTkLabel(
                row,
                text=f"{dt}  •  {size_kb:,} KB",
                font=font_small(),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

            ctk.CTkButton(
                row,
                text="Restore",
                width=80,
                command=lambda p=b.path, n=b.name: self._restore(p, n),
            ).grid(row=0, column=1, rowspan=2, padx=(4, 4), pady=8)

            ctk.CTkButton(
                row,
                text="Delete",
                width=72,
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
                command=lambda p=b.path, n=b.name: self._delete(p, n),
            ).grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=8)

    def _restore(self, backup_path: Path, name: str) -> None:
        confirmed = messagebox.askyesno(
            "Restore Save Backup",
            f"Replace your current Stardew Valley Saves folder with '{name}'?\n\n"
            "Make sure Stardew Valley is closed before restoring.",
            parent=self,
        )
        if not confirmed:
            return
        try:
            restore_save_backup(backup_path, self._saves_dir)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Restore Failed", str(exc), parent=self)
            return

        messagebox.showinfo("Restored", f"Restored saves from '{name}'.", parent=self)
        if self._on_status is not None:
            self._on_status(f"Restored saves from '{name}'.", "success")

    def _delete(self, backup_path: Path, name: str) -> None:
        if not messagebox.askyesno("Delete Backup", f"Delete '{name}'?", parent=self):
            return
        backup_path.unlink(missing_ok=True)
        self._refresh_list()
