"""Interactive Content Patcher asset conflict viewer and resolver dialog."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.core.asset_conflicts import AssetConflict
from src.core.mod_scanner import ModInfo
from src.ui.theme import COLORS, SPACING, font_bold, font_small


class AssetConflictDialog(ctk.CTkToplevel):
    """Displays Content Patcher asset collisions with 1-click Disable or Config actions."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        conflicts: list[AssetConflict],
        on_disable_mod: Callable[[ModInfo], None],
        on_open_details: Callable[[ModInfo], None],
    ) -> None:
        super().__init__(master)
        self.title("Content Patcher Asset Conflicts")
        self.geometry("680x480")
        self.minsize(560, 380)
        self.configure(fg_color=COLORS["bg_app"])
        self.transient(master)
        self.grab_set()

        self._conflicts = conflicts
        self._on_disable_mod = on_disable_mod
        self._on_open_details = on_open_details
        self._disabled_folders: set[str] = set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text=(
                f"Found {len(conflicts)} asset target(s) edited by multiple enabled mods.\n"
                "Disable one of the colliding mods or inspect its config.json."
                if conflicts
                else "No Content Patcher asset target conflicts detected in enabled mods!"
            ),
            font=font_bold(),
            text_color=COLORS["warning_text"] if conflicts else COLORS["success_text"],
            anchor="w",
            justify="left",
        )
        header.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 8))

        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, 8))
        self.scroll.grid_columnconfigure(0, weight=1)

        self._render()

        ctk.CTkButton(
            self,
            text="Close",
            width=100,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self.destroy,
        ).grid(row=2, column=0, sticky="e", padx=SPACING["lg"], pady=(0, SPACING["lg"]))

    def _render(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        if not self._conflicts:
            ctk.CTkLabel(
                self.scroll,
                text="All enabled Content Patcher packs modify distinct game assets.",
                font=font_small(),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=0, padx=16, pady=32)
            return

        for idx, conflict in enumerate(self._conflicts):
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
                text=f"Target: {conflict.target}",
                font=font_bold(),
                text_color=COLORS["warning_text"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

            for m_idx, mod in enumerate(conflict.mods, start=1):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.grid(row=m_idx, column=0, sticky="ew", padx=10, pady=(0, 6))
                row.grid_columnconfigure(0, weight=1)

                is_disabled = mod.folder_name in self._disabled_folders
                label_txt = (
                    f"• {mod.name} ({mod.folder_name}) — Disabled"
                    if is_disabled
                    else f"• {mod.name} ({mod.folder_name})"
                )
                ctk.CTkLabel(
                    row,
                    text=label_txt,
                    font=font_small(),
                    text_color=COLORS["text_muted"] if is_disabled else COLORS["text_primary"],
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkButton(
                    row,
                    text="Details",
                    width=64,
                    height=24,
                    font=font_small(),
                    fg_color=COLORS["neutral_btn"],
                    hover_color=COLORS["neutral_btn_hover"],
                    text_color=COLORS["neutral_btn_text"],
                    command=lambda m=mod: self._open_details(m),
                ).grid(row=0, column=1, padx=(6, 4))

                ctk.CTkButton(
                    row,
                    text="Disabled" if is_disabled else "Disable",
                    width=72,
                    height=24,
                    font=font_small(),
                    state="disabled" if is_disabled else "normal",
                    fg_color=COLORS["danger"],
                    hover_color=COLORS["danger_hover"],
                    command=lambda m=mod: self._disable(m),
                ).grid(row=0, column=2)

    def _disable(self, mod: ModInfo) -> None:
        self._disabled_folders.add(mod.folder_name)
        self._on_disable_mod(mod)
        self._render()

    def _open_details(self, mod: ModInfo) -> None:
        self.destroy()
        self._on_open_details(mod)
