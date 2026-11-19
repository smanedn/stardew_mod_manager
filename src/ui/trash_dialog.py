"""Trash bin dialog for restoring uninstalled mods or emptying trash."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from src.core.mod_manager import TrashedMod, empty_trash, list_trashed_mods
from src.ui.theme import COLORS, SPACING, font_bold, font_small


class TrashBinDialog(ctk.CTkToplevel):
    """Modal dialog listing recently uninstalled mods with 1-click Restore."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        trash_root: Path,
        on_restore: Callable[[TrashedMod], None],
        on_emptied: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Mod Trash Bin")
        self.geometry("560x420")
        self.minsize(480, 340)
        self.configure(fg_color=COLORS["bg_app"])
        self.transient(master)
        self.grab_set()

        self._trash_root = trash_root
        self._on_restore = on_restore
        self._on_emptied = on_emptied

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Recently uninstalled mods can be restored back to their modpack:",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 8))

        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, 8))
        self.scroll.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        footer.grid_columnconfigure(0, weight=1)

        self.empty_btn = ctk.CTkButton(
            footer,
            text="Empty Trash",
            width=110,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=self._empty,
        )
        self.empty_btn.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Close",
            width=90,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e")

        self._render()

    def _render(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        items = list_trashed_mods(self._trash_root)
        self.empty_btn.configure(state="normal" if items else "disabled")
        if not items:
            ctk.CTkLabel(
                self.scroll,
                text="Trash bin is empty.",
                font=font_small(),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=0, padx=16, pady=36)
            return

        for idx, item in enumerate(items):
            card = ctk.CTkFrame(
                self.scroll,
                fg_color=COLORS["surface_alt"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["border"],
            )
            card.grid(row=idx, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card,
                text=item.folder_name,
                font=font_bold(),
                text_color=COLORS["text_primary"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))

            meta = f"Modpack: {item.profile_id}"
            if item.trashed_at:
                meta += f"  •  {item.trashed_at}"
            ctk.CTkLabel(
                card,
                text=meta,
                font=font_small(),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

            ctk.CTkButton(
                card,
                text="Restore",
                width=82,
                height=28,
                font=font_small(),
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                command=lambda it=item: self._restore(it),
            ).grid(row=0, column=1, rowspan=2, padx=10, pady=8)

    def _restore(self, item: TrashedMod) -> None:
        self._on_restore(item)
        self._render()

    def _empty(self) -> None:
        removed = empty_trash(self._trash_root)
        if self._on_emptied is not None:
            self._on_emptied(removed)
        self._render()
