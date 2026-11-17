"""Modal dialog for installing mods directly from Nexus Mods."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.ui.theme import COLORS, SPACING, font_bold, font_small


class NexusInstallDialog(ctk.CTkToplevel):
    """Prompts for a Nexus Mods URL / ID / nxm:// link and API key."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_api_key: str,
        on_submit: Callable[[str, str], None],
    ) -> None:
        super().__init__(master)
        self.title("Install from Nexus Mods")
        self.geometry("500x260")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._on_submit = on_submit
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Nexus Mod URL, Mod ID, or nxm:// link:",
            font=font_bold(),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 4))

        self.target_entry = ctk.CTkEntry(
            self,
            placeholder_text="https://www.nexusmods.com/stardewvalley/mods/1915 or nxm://...",
        )
        self.target_entry.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 8))
        self.target_entry.bind("<Return>", lambda _e: self._submit())

        ctk.CTkLabel(
            self,
            text="Nexus Mods API Key (saved locally in SVMM_Data/config.json):",
            font=font_bold(),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(4, 4))

        self.key_var = ctk.StringVar(value=initial_api_key)
        self.key_entry = ctk.CTkEntry(
            self,
            textvariable=self.key_var,
            show="*",
            placeholder_text="Paste your Nexus Mods Personal API Key...",
        )
        self.key_entry.grid(row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 6))

        ctk.CTkLabel(
            self,
            text="Note: Free Nexus accounts must paste an nxm:// Mod Manager Download link.",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="e", padx=SPACING["lg"], pady=(0, SPACING["lg"]))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=90,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Download & Install",
            width=140,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._submit,
        ).grid(row=0, column=1)

        self.after(50, self.target_entry.focus_set)

    def _submit(self) -> None:
        raw_target = self.target_entry.get().strip()
        api_key = self.key_var.get().strip()
        self.destroy()
        self._on_submit(raw_target, api_key)
