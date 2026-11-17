"""Lightweight hover tooltip helper for customtkinter widgets."""

from __future__ import annotations

import customtkinter as ctk

from src.ui.theme import COLORS, font_small


class ToolTip:
    """Displays a floating tooltip when hovering over a widget."""

    def __init__(self, widget: ctk.CTkBaseClass, text: str) -> None:
        self.widget = widget
        self.text = text
        self._tip_window: ctk.CTkToplevel | None = None
        self.widget.bind("<Enter>", self._show, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")

    def update_text(self, text: str) -> None:
        self.text = text

    def _show(self, _event: object = None) -> None:
        if self._tip_window is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        win = ctk.CTkToplevel(self.widget)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{x}+{y}")
        win.attributes("-topmost", True)
        label = ctk.CTkLabel(
            win,
            text=self.text,
            font=font_small(),
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            padx=8,
            pady=4,
            justify="left",
        )
        label.pack()
        self._tip_window = win

    def _hide(self, _event: object = None) -> None:
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None
