"""Clean left navigation sidebar: brand header, modpacks, and compact action menus."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from src.core.config import ProfileData
from src.ui.theme import COLORS, SPACING, font_bold, font_header, font_small, font_title


class ProfileSidebar(ctk.CTkFrame):
    """Full-height left sidebar for modpack switching and compact tool menus."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        version: str,
        logo_path: Path | None,
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
        on_open_themes: Callable[[], None],
        on_export_bundle: Callable[[], None] | None = None,
        on_import_bundle: Callable[[], None] | None = None,
        on_rename: Callable[[], None] | None = None,
        on_coop_check: Callable[[], None] | None = None,
        on_open_modpack_folder: Callable[[], None] | None = None,
        on_create_shortcut: Callable[[], None] | None = None,
        on_save_config_preset: Callable[[], None] | None = None,
        on_restore_config_preset: Callable[[], None] | None = None,
        on_open_asset_conflicts: Callable[[], None] | None = None,
        on_open_trash: Callable[[], None] | None = None,
        on_open_onboarding: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            width=252,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0,
            border_width=0,
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._on_select = on_select
        self._on_create = on_create
        self._on_delete = on_delete
        self._on_import = on_import
        self._on_export = on_export
        self._on_duplicate = on_duplicate
        self._on_share_modlist = on_share_modlist
        self._on_export_bundle = on_export_bundle
        self._on_import_bundle = on_import_bundle
        self._on_rename = on_rename
        self._on_open_modpack_folder = on_open_modpack_folder
        self._on_create_shortcut = on_create_shortcut
        self._on_save_config_preset = on_save_config_preset
        self._on_restore_config_preset = on_restore_config_preset
        self._on_open_asset_conflicts = on_open_asset_conflicts
        self._on_open_trash = on_open_trash
        self._on_open_onboarding = on_open_onboarding
        self._on_open_saves = on_open_saves
        self._on_open_smapi_log = on_open_smapi_log
        self._on_coop_check = on_coop_check
        self._can_delete = False

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

        ctk.CTkLabel(
            brand, text="SVMM", font=font_header(), text_color=COLORS["text_primary"], anchor="w"
        ).grid(row=0, column=1, sticky="w")
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

        # --- Create / Manage Modpack Row ---
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.grid(row=3, column=0, sticky="ew", padx=SPACING["md"], pady=(8, 10))
        add_frame.grid_columnconfigure(0, weight=1)

        self.new_profile_entry = ctk.CTkEntry(
            add_frame,
            height=32,
            placeholder_text="New modpack...",
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
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
        ).grid(row=0, column=1, padx=(0, 4))

        self.manage_btn = ctk.CTkButton(
            add_frame,
            text="⋯",
            width=34,
            height=32,
            font=font_title(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._show_modpack_menu,
        )
        self.manage_btn.grid(row=0, column=2)

        # --- Divider & Clean 3-Button Utility Dock ---
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).grid(
            row=4, column=0, sticky="ew", padx=SPACING["md"], pady=(0, 10)
        )

        utils = ctk.CTkFrame(self, fg_color="transparent")
        utils.grid(row=5, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        utils.grid_columnconfigure((0, 1, 2), weight=1)

        util_cfg = {
            "height": 32,
            "font": font_small(),
            "fg_color": COLORS["surface"],
            "hover_color": COLORS["surface_hover"],
            "text_color": COLORS["text_primary"],
            "border_width": 1,
            "border_color": COLORS["border"],
        }

        self.tools_btn = ctk.CTkButton(
            utils, text="Tools ▾", command=self._show_tools_menu, **util_cfg
        )
        self.tools_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkButton(utils, text="Themes", command=on_open_themes, **util_cfg).grid(
            row=0, column=1, sticky="ew", padx=2
        )

        ctk.CTkButton(utils, text="Settings", command=on_open_settings, **util_cfg).grid(
            row=0, column=2, sticky="ew", padx=(4, 0)
        )

    def _themed_menu(self) -> tk.Menu:
        bg = COLORS["surface"][1] if ctk.get_appearance_mode() == "Dark" else COLORS["surface"][0]
        fg = (
            COLORS["text_primary"][1]
            if ctk.get_appearance_mode() == "Dark"
            else COLORS["text_primary"][0]
        )
        active_bg = COLORS["accent"][0]
        return tk.Menu(
            self,
            tearoff=0,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=1,
        )

    def _show_modpack_menu(self) -> None:
        menu = self._themed_menu()
        if self._on_rename is not None:
            menu.add_command(label="Rename Modpack", command=self._on_rename)
        menu.add_command(label="Duplicate Modpack", command=self._on_duplicate)
        menu.add_command(
            label="Delete Modpack",
            command=self._on_delete,
            state="normal" if self._can_delete else "disabled",
        )
        menu.add_separator()
        menu.add_command(label="Import Modlist (.json)", command=self._on_import)
        menu.add_command(label="Export Modlist (.json)", command=self._on_export)
        menu.add_command(label="Share Modlist (Copy / File)", command=self._on_share_modlist)
        if self._on_import_bundle is not None and self._on_export_bundle is not None:
            menu.add_separator()
            menu.add_command(label="Import Modpack Bundle (.zip)", command=self._on_import_bundle)
            menu.add_command(label="Export Modpack Bundle (.zip)", command=self._on_export_bundle)
        if self._on_save_config_preset is not None and self._on_restore_config_preset is not None:
            menu.add_separator()
            menu.add_command(label="Save Mod Configs Snapshot", command=self._on_save_config_preset)
            menu.add_command(
                label="Restore Mod Configs Snapshot", command=self._on_restore_config_preset
            )
        if self._on_create_shortcut is not None:
            menu.add_separator()
            menu.add_command(label="Create Desktop Shortcut", command=self._on_create_shortcut)
        if self._on_open_modpack_folder is not None:
            menu.add_separator()
            menu.add_command(label="Open Modpack Folder", command=self._on_open_modpack_folder)

        x = self.manage_btn.winfo_rootx()
        y = self.manage_btn.winfo_rooty() - 10
        menu.tk_popup(x, y)

    def _show_tools_menu(self) -> None:
        menu = self._themed_menu()
        menu.add_command(label="Save Backups & Farm Bindings", command=self._on_open_saves)
        menu.add_command(label="SMAPI Log Analyzer", command=self._on_open_smapi_log)
        if self._on_coop_check is not None:
            menu.add_command(label="Co-op Parity Check", command=self._on_coop_check)
        if self._on_open_asset_conflicts is not None:
            menu.add_command(label="Asset Conflict Scanner", command=self._on_open_asset_conflicts)
        if self._on_open_trash is not None:
            menu.add_command(label="Mod Trash Bin (Restore)", command=self._on_open_trash)
        if self._on_open_onboarding is not None:
            menu.add_separator()
            menu.add_command(label="Quick Setup Wizard", command=self._on_open_onboarding)
        if self._on_open_modpack_folder is not None:
            menu.add_separator()
            menu.add_command(label="Open Modpack Folder", command=self._on_open_modpack_folder)

        x = self.tools_btn.winfo_rootx()
        y = self.tools_btn.winfo_rooty() - 10
        menu.tk_popup(x, y)

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

        self._can_delete = len(profiles) > 1
