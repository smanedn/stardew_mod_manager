"""Top bar component: Game path input, live validation badge, and quick actions."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_bold, font_small


class TopBar(ctk.CTkFrame):
    """Displays game path controls, path validation badge, and theme switcher."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_path: str,
        initial_theme: str,
        on_path_change: Callable[[str], None],
        on_browse: Callable[[], None],
        on_open_modpack: Callable[[], None],
        on_theme_change: Callable[[str], None],
    ) -> None:
        super().__init__(master, border_width=1, border_color=COLORS["border"])
        self._on_path_change = on_path_change
        self._on_theme_change = on_theme_change

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Game Path:", font=font_bold()).grid(
            row=0, column=0, padx=(SPACING["md"], SPACING["sm"]), pady=(SPACING["md"], 4)
        )

        self.game_path_var = ctk.StringVar(value=initial_path)
        self.game_path_entry = ctk.CTkEntry(self, textvariable=self.game_path_var)
        self.game_path_entry.grid(
            row=0, column=1, sticky="ew", padx=SPACING["sm"], pady=(SPACING["md"], 4)
        )
        self.game_path_entry.bind("<FocusOut>", lambda _e: self._emit_path())
        self.game_path_entry.bind("<Return>", lambda _e: self._emit_path())

        ctk.CTkButton(self, text="Browse", width=84, command=on_browse).grid(
            row=0, column=2, padx=SPACING["xs"], pady=(SPACING["md"], 4)
        )
        ctk.CTkButton(self, text="Open Modpack Folder", width=155, command=on_open_modpack).grid(
            row=0, column=3, padx=SPACING["xs"], pady=(SPACING["md"], 4)
        )

        self.theme_menu = ctk.CTkOptionMenu(
            self,
            values=["Dark", "Light", "System"],
            width=96,
            command=self._handle_theme,
        )
        self.theme_menu.set(initial_theme.capitalize())
        self.theme_menu.grid(
            row=0, column=4, padx=(SPACING["xs"], SPACING["md"]), pady=(SPACING["md"], 4)
        )

        self.validation_label = ctk.CTkLabel(
            self,
            text="",
            font=font_small(),
            anchor="w",
            text_color=COLORS["text_muted"],
        )
        self.validation_label.grid(
            row=1, column=1, columnspan=4, sticky="w", padx=SPACING["sm"], pady=(0, 8)
        )

    def _emit_path(self) -> None:
        self._on_path_change(self.game_path_var.get().strip())

    def _handle_theme(self, choice: str) -> None:
        self._on_theme_change(choice.lower())

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
        self.validation_label.configure(text=f"Status: {message}", text_color=color)
