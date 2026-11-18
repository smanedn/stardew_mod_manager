"""Bottom launch bar component: Modded/Vanilla launch, SMAPI log, and status toast."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_action, font_small


class LaunchBar(ctk.CTkFrame):
    """Bottom action bar for launching Stardew Valley and showing feedback."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        version: str,
        on_launch_modded: Callable[[], None],
        on_launch_vanilla: Callable[[], None],
        on_open_smapi_log: Callable[[], None],
        on_open_saves: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._toast_after_id: str | None = None

        self.modded_btn = ctk.CTkButton(
            self,
            text="LAUNCH MODDED (SMAPI)",
            height=42,
            font=font_action(),
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=on_launch_modded,
        )
        self.modded_btn.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(SPACING["md"], SPACING["sm"]),
            pady=(SPACING["md"], 4),
        )

        self.vanilla_btn = ctk.CTkButton(
            self,
            text="LAUNCH VANILLA (NO MODS)",
            height=42,
            font=font_action(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=on_launch_vanilla,
        )
        self.vanilla_btn.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(SPACING["sm"], SPACING["sm"]),
            pady=(SPACING["md"], 4),
        )

        ctk.CTkButton(
            self,
            text="SMAPI Log",
            height=42,
            width=96,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=on_open_smapi_log,
        ).grid(row=0, column=2, padx=(0, SPACING["sm"]), pady=(SPACING["md"], 4))

        if on_open_saves is not None:
            ctk.CTkButton(
                self,
                text="Saves",
                height=42,
                width=74,
                fg_color=COLORS["surface_alt"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                command=on_open_saves,
            ).grid(row=0, column=3, padx=(0, SPACING["md"]), pady=(SPACING["md"], 4))

        self.status_label = ctk.CTkLabel(
            self,
            text="Ready.",
            anchor="w",
            font=font_small(),
            text_color=COLORS["text_muted"],
        )
        self.status_label.grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=SPACING["lg"], pady=(2, 8)
        )

        ctk.CTkLabel(
            self,
            text=f"v{version}",
            anchor="e",
            font=font_small(),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=3, sticky="e", padx=SPACING["lg"], pady=(2, 8))

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
            text=message, text_color=color_map.get(level, COLORS["text_muted"])
        )

        if auto_clear_ms > 0:
            self._toast_after_id = self.after(
                auto_clear_ms,
                lambda: self.status_label.configure(text="Ready.", text_color=COLORS["text_muted"]),
            )
