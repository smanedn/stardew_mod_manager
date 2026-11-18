"""Revamped top header bar: active modpack title, game path, and status pill."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_header, font_small


class TopBar(ctk.CTkFrame):
    """Clean top header card showing active modpack, game path, and live validation."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_path: str,
        on_path_change: Callable[[str], None],
        on_browse: Callable[[], None],
        on_open_modpack: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self._on_path_change = on_path_change
        self.grid_columnconfigure(1, weight=1)

        # --- Row 0: Active Modpack Title + Live Game Status Pill ---
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=SPACING["md"],
            pady=(SPACING["md"], 4),
        )
        header_row.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header_row, text="Modpack: Default", font=font_header(), anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.validation_label = ctk.CTkLabel(
            header_row,
            text="● Checking...",
            font=font_small(),
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.validation_label.grid(row=0, column=1, sticky="e")

        # --- Row 1: Game Path Input + Subtle Actions ---
        ctk.CTkLabel(
            self, text="Game Folder:", font=font_small(), text_color=COLORS["text_muted"]
        ).grid(row=1, column=0, padx=(SPACING["md"], SPACING["sm"]), pady=(2, SPACING["md"]))

        self.game_path_var = ctk.StringVar(value=initial_path)
        self.game_path_entry = ctk.CTkEntry(
            self,
            textvariable=self.game_path_var,
            height=30,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
        )
        self.game_path_entry.grid(
            row=1, column=1, sticky="ew", padx=(0, SPACING["sm"]), pady=(2, SPACING["md"])
        )
        self.game_path_entry.bind("<FocusOut>", lambda _e: self._emit_path())
        self.game_path_entry.bind("<Return>", lambda _e: self._emit_path())

        btn_cfg = {
            "height": 30,
            "font": font_small(),
            "fg_color": COLORS["neutral_btn"],
            "hover_color": COLORS["neutral_btn_hover"],
            "text_color": COLORS["neutral_btn_text"],
        }
        ctk.CTkButton(self, text="Browse...", width=82, command=on_browse, **btn_cfg).grid(
            row=1, column=2, padx=(0, 6), pady=(2, SPACING["md"])
        )
        ctk.CTkButton(
            self, text="Open Modpack Folder", width=148, command=on_open_modpack, **btn_cfg
        ).grid(row=1, column=3, padx=(0, SPACING["md"]), pady=(2, SPACING["md"]))

    def _emit_path(self) -> None:
        self._on_path_change(self.game_path_var.get().strip())

    def set_active_modpack(self, name: str) -> None:
        self.title_label.configure(text=f"Modpack: {name}")

    def set_path(self, path: str) -> None:
        self.game_path_var.set(path)

    def get_path(self) -> str:
        return self.game_path_var.get().strip()

    def set_validation_status(self, has_vanilla: bool, has_smapi: bool, message: str) -> None:
        if has_vanilla and has_smapi:
            color = COLORS["success_text"]
        elif has_vanilla or has_smapi:
            color = COLORS["warning_text"]
        else:
            color = COLORS["error_text"]
        self.validation_label.configure(text=f"● {message}", text_color=color)
