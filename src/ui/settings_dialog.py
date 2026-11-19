"""In-app settings dialog for API keys and update cache management."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_bold, font_small


class SettingsDialog(ctk.CTkToplevel):
    """Modal dialog for configuring optional API keys and clearing caches."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        github_token: str,
        nexus_api_key: str,
        auto_backup_saves: bool,
        max_auto_backups: int,
        update_cache_path: Path,
        on_save: Callable[[str, str, bool], None],
        on_cache_cleared: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("520x340")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._update_cache_path = update_cache_path
        self._on_save = on_save
        self._on_cache_cleared = on_cache_cleared

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="GitHub Personal Access Token (optional, for update checks):",
            font=font_bold(),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 4))

        self.gh_var = ctk.StringVar(value=github_token)
        ctk.CTkEntry(self, textvariable=self.gh_var, show="*", placeholder_text="ghp_...").grid(
            row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 10)
        )

        ctk.CTkLabel(
            self,
            text="Nexus Mods Personal API Key (optional, for Nexus browser & updates):",
            font=font_bold(),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(4, 4))

        self.nexus_var = ctk.StringVar(value=nexus_api_key)
        ctk.CTkEntry(
            self, textvariable=self.nexus_var, show="*", placeholder_text="Paste Nexus API key..."
        ).grid(row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 10))

        self.auto_backup_var = ctk.BooleanVar(value=auto_backup_saves)
        ctk.CTkCheckBox(
            self,
            text=f"Auto-backup saves before modded launch (keeps last {max_auto_backups})",
            variable=self.auto_backup_var,
        ).grid(row=4, column=0, sticky="w", padx=SPACING["lg"], pady=(0, 8))

        self.info_label = ctk.CTkLabel(
            self,
            text="Keys are stored locally in SVMM_Data/config.json.",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.info_label.grid(row=5, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 12))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=6, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="Clear Update Cache",
            width=140,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self._clear_cache,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Cancel",
            width=86,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Save",
            width=90,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._save,
        ).grid(row=0, column=2)

    def _clear_cache(self) -> None:
        if self._update_cache_path.is_file():
            self._update_cache_path.unlink()
            self.info_label.configure(
                text="Cleared SVMM_Data/update_cache.json.", text_color=COLORS["success_text"]
            )
            if self._on_cache_cleared is not None:
                self._on_cache_cleared()
        else:
            self.info_label.configure(
                text="Update cache is already empty.", text_color=COLORS["text_muted"]
            )

    def _save(self) -> None:
        self._on_save(
            self.gh_var.get().strip(),
            self.nexus_var.get().strip(),
            bool(self.auto_backup_var.get()),
        )
        self.destroy()
