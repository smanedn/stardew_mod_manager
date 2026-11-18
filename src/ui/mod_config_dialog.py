"""In-app JSON editor dialog for a mod's config.json."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from src.core.mod_config import load_mod_config_text, save_mod_config_text
from src.ui.theme import COLORS, SPACING, font_small, font_title


class ModConfigDialog(ctk.CTkToplevel):
    """Modal JSON editor for a mod's config.json with live syntax validation."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        mod_name: str,
        mod_path: Path,
        on_saved: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title(f"Edit Config — {mod_name}")
        self.geometry("620x500")
        self.minsize(480, 380)
        self.transient(master)
        self.grab_set()

        self._mod_name = mod_name
        self._mod_path = mod_path
        self._on_saved = on_saved

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"{mod_name} — config.json", font=font_title(), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"])
        )

        self.textbox = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=13), wrap="none"
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])

        try:
            content = load_mod_config_text(mod_path)
        except (OSError, FileNotFoundError) as exc:
            content = ""
            self._initial_error = str(exc)
        else:
            self._initial_error = ""

        self.textbox.insert("1.0", content)

        self.error_label = ctk.CTkLabel(
            self,
            text=self._initial_error,
            font=font_small(),
            text_color=COLORS["error_text"],
            anchor="w",
        )
        self.error_label.grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(2, 4))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"])
        )
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="Format JSON",
            width=110,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self._format_json,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Cancel",
            width=90,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Save",
            width=96,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._save,
        ).grid(row=0, column=2)

    def _format_json(self) -> None:
        raw = self.textbox.get("1.0", "end-1c")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.error_label.configure(
                text=f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            )
            return
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", formatted)
        self.error_label.configure(text="")

    def _save(self) -> None:
        raw = self.textbox.get("1.0", "end-1c")
        try:
            save_mod_config_text(self._mod_path, raw)
        except (OSError, ValueError) as exc:
            self.error_label.configure(text=str(exc))
            return

        if self._on_saved is not None:
            self._on_saved(f"Saved config.json for '{self._mod_name}'.")
        self.destroy()
