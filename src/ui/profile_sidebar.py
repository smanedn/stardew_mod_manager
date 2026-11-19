"""Revamped left navigation sidebar: brand header, modpacks, and utilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from src.core.config import ProfileData
from src.ui.theme import COLORS, SPACING, font_bold, font_header, font_small, font_title


class ProfileSidebar(ctk.CTkFrame):
    """Full-height left sidebar for modpack management and app utilities."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        version: str,
        logo_path: Path | None,
        initial_theme: str,
        on_select: Callable[[str], None],
        on_create: Callable[[str], None],
        on_delete: Callable[[], None],
        on_import: Callable[[], None],
        on_export: Callable[[], None],
        on_duplicate: Callable[[], None],
        on_share_modlist: Callable[[], None],
        on_open_saves: Callable[[], None],
        on_open_smapi_log: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_theme_change: Callable[[str], None],
        on_export_bundle: Callable[[], None] | None = None,
        on_import_bundle: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            width=260,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0,
            border_width=0,
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._on_select = on_select
        self._on_create = on_create
        self._on_theme_change = on_theme_change
        self.profile_buttons: dict[str, ctk.CTkButton] = {}
        self._logo_img: ctk.CTkImage | None = None

        # --- Brand Header ---
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], 10))
        brand.grid_columnconfigure(1, weight=1)

        if logo_path and logo_path.is_file():
            try:
                pil_logo = Image.open(logo_path).convert("RGBA")
                self._logo_img = ctk.CTkImage(
                    light_image=pil_logo, dark_image=pil_logo, size=(30, 30)
                )
                ctk.CTkLabel(brand, text="", image=self._logo_img).grid(
                    row=0, column=0, padx=(0, 8)
                )
            except OSError:
                pass

        ctk.CTkLabel(brand, text="SVMM", font=font_header(), anchor="w").grid(
            row=0, column=1, sticky="w"
        )
        ctk.CTkLabel(
            brand,
            text=f"v{version}",
            font=font_small(),
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            padx=7,
            pady=2,
        ).grid(row=0, column=2, sticky="e")

        # --- Modpacks Section ---
        ctk.CTkLabel(
            self,
            text="MODPACKS",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(4, 4))

        self.profile_list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=8,
        )
        self.profile_list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=2)
        self.profile_list_frame.grid_columnconfigure(0, weight=1)

        # --- Create New Modpack ---
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.grid(row=3, column=0, sticky="ew", padx=SPACING["md"], pady=(6, 6))
        add_frame.grid_columnconfigure(0, weight=1)

        self.new_profile_entry = ctk.CTkEntry(
            add_frame,
            height=32,
            placeholder_text="New modpack name...",
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
        )
        self.new_profile_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.new_profile_entry.bind("<Return>", lambda _e: self._submit_create())

        ctk.CTkButton(
            add_frame,
            text="+",
            width=34,
            height=32,
            font=font_title(),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._submit_create,
        ).grid(row=0, column=1)

        # --- Compact Modpack Actions ---
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=SPACING["md"], pady=(0, 6))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        btn_cfg = {
            "height": 28,
            "font": font_small(),
            "fg_color": COLORS["neutral_btn"],
            "hover_color": COLORS["neutral_btn_hover"],
            "text_color": COLORS["neutral_btn_text"],
        }
        ctk.CTkButton(actions, text="Import", command=on_import, **btn_cfg).grid(
            row=0, column=0, sticky="ew", padx=(0, 3), pady=2
        )
        ctk.CTkButton(actions, text="Export", command=on_export, **btn_cfg).grid(
            row=0, column=1, sticky="ew", padx=(3, 0), pady=2
        )
        ctk.CTkButton(actions, text="Duplicate", command=on_duplicate, **btn_cfg).grid(
            row=1, column=0, sticky="ew", padx=(0, 3), pady=2
        )
        ctk.CTkButton(actions, text="Share List", command=on_share_modlist, **btn_cfg).grid(
            row=1, column=1, sticky="ew", padx=(3, 0), pady=2
        )
        if on_import_bundle is not None and on_export_bundle is not None:
            ctk.CTkButton(actions, text="Import .zip", command=on_import_bundle, **btn_cfg).grid(
                row=2, column=0, sticky="ew", padx=(0, 3), pady=2
            )
            ctk.CTkButton(actions, text="Export .zip", command=on_export_bundle, **btn_cfg).grid(
                row=2, column=1, sticky="ew", padx=(3, 0), pady=2
            )

        self.delete_btn = ctk.CTkButton(
            self,
            text="Delete Active Modpack",
            height=28,
            font=font_small(),
            fg_color="transparent",
            hover_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["error_text"],
            command=on_delete,
        )
        self.delete_btn.grid(row=5, column=0, sticky="ew", padx=SPACING["md"], pady=(2, 10))

        # --- Divider & Utilities ---
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).grid(
            row=6, column=0, sticky="ew", padx=SPACING["md"], pady=(2, 8)
        )

        utils = ctk.CTkFrame(self, fg_color="transparent")
        utils.grid(row=7, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        utils.grid_columnconfigure(0, weight=1)
        utils.grid_columnconfigure(1, weight=1)

        util_cfg = {
            "height": 30,
            "font": font_small(),
            "fg_color": COLORS["surface"],
            "hover_color": COLORS["surface_hover"],
            "text_color": COLORS["text_primary"],
            "border_width": 1,
            "border_color": COLORS["border"],
        }
        if on_open_saves is not None:
            ctk.CTkButton(utils, text="Save Backups", command=on_open_saves, **util_cfg).grid(
                row=0, column=0, sticky="ew", padx=(0, 3), pady=3
            )
        ctk.CTkButton(utils, text="SMAPI Log", command=on_open_smapi_log, **util_cfg).grid(
            row=0, column=1, sticky="ew", padx=(3, 0), pady=3
        )
        ctk.CTkButton(utils, text="⚙ Settings", command=on_open_settings, **util_cfg).grid(
            row=1, column=0, sticky="ew", padx=(0, 3), pady=3
        )

        self.theme_menu = ctk.CTkOptionMenu(
            utils,
            values=["Dark", "Light", "System"],
            height=30,
            font=font_small(),
            fg_color=COLORS["surface"],
            button_color=COLORS["neutral_btn"],
            button_hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_primary"],
            command=self._handle_theme,
        )
        self.theme_menu.set(initial_theme.capitalize())
        self.theme_menu.grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=3)

    def _handle_theme(self, choice: str) -> None:
        self._on_theme_change(choice.lower())

    def _submit_create(self) -> None:
        name = self.new_profile_entry.get().strip()
        self._on_create(name)

    def clear_new_profile_entry(self) -> None:
        self.new_profile_entry.delete(0, "end")

    def render_profiles(self, profiles: Mapping[str, ProfileData], active_profile: str) -> None:
        for widget in self.profile_list_frame.winfo_children():
            widget.destroy()
        self.profile_buttons.clear()

        for row_idx, (pid, pdata) in enumerate(profiles.items()):
            is_active = pid == active_profile
            count = len(pdata.get("enabled_mods", []))
            label = f"  {pdata.get('name', pid)}   ({count})"
            btn = ctk.CTkButton(
                self.profile_list_frame,
                text=label,
                height=34,
                corner_radius=8,
                anchor="w",
                font=font_bold() if is_active else font_small(),
                fg_color=COLORS["accent"] if is_active else "transparent",
                hover_color=COLORS["accent_hover"] if is_active else COLORS["surface_hover"],
                text_color=("#FFFFFF", "#FFFFFF") if is_active else COLORS["text_primary"],
                command=lambda p=pid: self._on_select(p),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", pady=2)
            self.profile_buttons[pid] = btn

        can_delete = len(profiles) > 1
        self.delete_btn.configure(state="normal" if can_delete else "disabled")
