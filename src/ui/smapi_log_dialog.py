"""In-app SMAPI-latest.txt error and warning log viewer."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from src.core.smapi_log import SmapiLogSummary, parse_smapi_log
from src.ui.theme import COLORS, SPACING, font_small, font_title


class SmapiLogDialog(ctk.CTkToplevel):
    """Displays parsed SMAPI errors, warnings, and full log text."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        log_path: Path,
        on_open_external: Callable[[Path], None],
    ) -> None:
        super().__init__(master)
        self.title("SMAPI Log Viewer — SMAPI-latest.txt")
        self.geometry("820x560")
        self.minsize(600, 420)
        self.transient(master)
        self.grab_set()

        self._log_path = log_path
        self._summary: SmapiLogSummary = parse_smapi_log(log_path)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header & Filter Tabs ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(
            row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"])
        )
        header.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            header,
            text=f"{len(self._summary.errors)} Error(s), {len(self._summary.warnings)} Warning(s)",
            font=font_title(),
        ).grid(row=0, column=0, padx=(0, SPACING["md"]), sticky="w")

        ctk.CTkButton(
            header,
            text=f"Errors ({len(self._summary.errors)})",
            width=100,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=lambda: self._show_tab("errors"),
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            header,
            text=f"Warnings ({len(self._summary.warnings)})",
            width=116,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=lambda: self._show_tab("warnings"),
        ).grid(row=0, column=2, padx=4)

        ctk.CTkButton(
            header,
            text="Full Log",
            width=90,
            command=lambda: self._show_tab("full"),
        ).grid(row=0, column=3, padx=4, sticky="w")

        # --- Log Textbox ---
        self.textbox = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=12), wrap="none"
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])

        # --- Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"])
        )
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text=str(log_path),
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            footer,
            text="Open in Editor",
            width=120,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=lambda: on_open_external(self._log_path),
        ).grid(row=0, column=1, padx=(8, 8))

        ctk.CTkButton(footer, text="Close", width=86, command=self.destroy).grid(row=0, column=2)

        self._show_tab("errors" if self._summary.errors else "full")

    def _show_tab(self, tab: str) -> None:
        if tab == "errors":
            content = "\n".join(self._summary.errors) or "No ERROR or ALERT entries found."
        elif tab == "warnings":
            content = "\n".join(self._summary.warnings) or "No WARN entries found."
        else:
            content = self._summary.raw_text

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", content)
        self.textbox.configure(state="disabled")
