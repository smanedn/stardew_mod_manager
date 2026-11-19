"""Revamped bottom launch dock: status feedback and Vanilla / SMAPI launch buttons."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_action, font_small


class LaunchBar(ctk.CTkFrame):
    """Bottom action dock for launching Stardew Valley and displaying status."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_launch_modded: Callable[[], None],
        on_launch_vanilla: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.grid_columnconfigure(0, weight=1)
        self._toast_after_id: str | None = None

        self.status_label = ctk.CTkLabel(
            self,
            text="● Ready.",
            anchor="w",
            font=font_small(),
            text_color=COLORS["text_muted"],
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])

        self.app_update_btn = ctk.CTkButton(
            self,
            text="",
            height=26,
            width=116,
            font=font_small(),
            fg_color=COLORS["accent_soft"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )

        self.vanilla_btn = ctk.CTkButton(
            self,
            text="Launch Vanilla",
            height=38,
            width=140,
            font=font_action(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=on_launch_vanilla,
        )
        self.vanilla_btn.grid(row=0, column=2, padx=(SPACING["sm"], 6), pady=10)

        self.modded_btn = ctk.CTkButton(
            self,
            text="▶ Launch Modded (SMAPI)",
            height=38,
            width=210,
            font=font_action(),
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=on_launch_modded,
        )
        self.modded_btn.grid(row=0, column=3, padx=(0, SPACING["md"]), pady=10)

    def set_app_update(self, latest_version: str | None, url: str = "") -> None:
        if latest_version:
            self.app_update_btn.configure(
                text=f"↑ SVMM v{latest_version}",
                command=lambda u=url: webbrowser.open(u),
            )
            self.app_update_btn.grid(row=0, column=1, padx=(0, 6), pady=10)
        else:
            self.app_update_btn.grid_remove()

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.modded_btn.configure(state=state)
        self.vanilla_btn.configure(state=state)

    def set_status(self, message: str, level: str = "info", auto_clear_ms: int = 0) -> None:
        if self._toast_after_id is not None:
            self.after_cancel(self._toast_after_id)
            self._toast_after_id = None

        color_map = {
            "info": COLORS["text_muted"],
            "success": COLORS["success_text"],
            "warning": COLORS["warning_text"],
            "error": COLORS["error_text"],
        }
        self.status_label.configure(
            text=f"● {message}", text_color=color_map.get(level, COLORS["text_muted"])
        )

        if auto_clear_ms > 0:
            self._toast_after_id = self.after(
                auto_clear_ms,
                lambda: self.status_label.configure(
                    text="● Ready.", text_color=COLORS["text_muted"]
                ),
            )
