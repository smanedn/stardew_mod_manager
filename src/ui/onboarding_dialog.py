"""First-run onboarding and quick setup wizard for SVMM."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import filedialog

import customtkinter as ctk

from src.core.launcher import validate_game_path
from src.ui.theme import COLORS, SPACING, font_bold, font_header, font_small


class OnboardingDialog(ctk.CTkToplevel):
    """Guided 2-step setup dialog for game folder, SMAPI, and optional Nexus API key."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_path: str,
        initial_nexus_key: str,
        on_install_smapi: Callable[[], None],
        on_finish: Callable[[str, str], None],
    ) -> None:
        super().__init__(master)
        self.title("Welcome to SVMM — Quick Setup")
        self.geometry("560x420")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_app"])
        self.transient(master)
        self.grab_set()

        self._on_install_smapi = on_install_smapi
        self._on_finish = on_finish

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Stardew Valley Mod Manager — Quick Setup",
            font=font_header(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 4))

        ctk.CTkLabel(
            self,
            text="Verify your game folder and SMAPI installation to get started in seconds.",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 12))

        # Step 1: Game Folder & SMAPI
        step1 = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        step1.grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 10))
        step1.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            step1,
            text="1. Stardew Valley Installation Folder",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 6))

        self.path_var = ctk.StringVar(value=initial_path)
        ctk.CTkEntry(
            step1,
            textvariable=self.path_var,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
        ).grid(row=1, column=0, sticky="ew", padx=(12, 6), pady=(0, 6))

        ctk.CTkButton(
            step1,
            text="Browse...",
            width=84,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._browse,
        ).grid(row=1, column=1, padx=(0, 12), pady=(0, 6))

        status_row = ctk.CTkFrame(step1, fg_color="transparent")
        status_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))
        status_row.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(status_row, text="", font=font_small(), anchor="w")
        self.status_lbl.grid(row=0, column=0, sticky="w")

        self.smapi_btn = ctk.CTkButton(
            status_row,
            text="↓ Install SMAPI",
            width=120,
            height=26,
            font=font_small(),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._install_smapi,
        )

        # Step 2: Optional Nexus Key
        step2 = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        step2.grid(row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, 12))
        step2.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            step2,
            text="2. Nexus Mods Personal API Key (Optional)",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            step2,
            text="Enables in-app Nexus browsing, mod thumbnails, and 1-click updates.",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.nexus_var = ctk.StringVar(value=initial_nexus_key)
        ctk.CTkEntry(
            step2,
            textvariable=self.nexus_var,
            show="*",
            placeholder_text="Paste Nexus API key (optional)...",
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer,
            text="Skip",
            width=84,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self.destroy,
        ).grid(row=0, column=0, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Finish Setup",
            width=120,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._finish,
        ).grid(row=0, column=1, sticky="e")

        self._check_path()

    def _browse(self) -> None:
        selected = filedialog.askdirectory(title="Select Stardew Valley Installation Folder")
        if selected:
            self.path_var.set(selected)
            self._check_path()

    def _check_path(self) -> None:
        has_vanilla, has_smapi, msg = validate_game_path(self.path_var.get().strip())
        if has_vanilla and has_smapi:
            self.status_lbl.configure(text=f"● {msg}", text_color=COLORS["success_text"])
            self.smapi_btn.grid_remove()
        elif has_vanilla:
            self.status_lbl.configure(text=f"● {msg}", text_color=COLORS["warning_text"])
            self.smapi_btn.grid(row=0, column=1, sticky="e")
        else:
            self.status_lbl.configure(text=f"● {msg}", text_color=COLORS["error_text"])
            self.smapi_btn.grid_remove()

    def _install_smapi(self) -> None:
        self._on_install_smapi()
        self.after(4000, lambda: self._check_path() if self.winfo_exists() else None)

    def _finish(self) -> None:
        self._on_finish(self.path_var.get().strip(), self.nexus_var.get().strip())
        self.destroy()
