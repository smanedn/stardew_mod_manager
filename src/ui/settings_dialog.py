"""Tabbed settings and theme studio dialog for SVMM."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from tkinter import colorchooser

import customtkinter as ctk

from src.ui.theme import (
    COLORS,
    DEFAULT_CUSTOM_THEME,
    SPACING,
    THEME_NAMES,
    THEMES,
    font_bold,
    font_small,
    resolve_theme,
    sanitize_custom_theme,
)


class SettingsDialog(ctk.CTkToplevel):
    """Clean tabbed dialog for Launch/General settings, Themes & Customizer, and Integrations."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        github_token: str,
        nexus_api_key: str,
        auto_backup_saves: bool,
        max_auto_backups: int,
        launch_via_steam: bool,
        launch_args: str,
        current_theme: str,
        custom_theme: dict[str, str],
        update_cache_path: Path,
        compat_cache_path: Path,
        icon_cache_dir: Path,
        on_save: Callable[[str, str, bool, bool, str], None],
        on_apply_theme: Callable[[str, dict[str, str]], None],
        on_cache_cleared: Callable[[], None] | None = None,
        initial_tab: str = "General",
    ) -> None:
        super().__init__(master)
        self.title("Settings & Themes")
        self.geometry("620x540")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_app"])
        self.transient(master)
        self.grab_set()

        self._update_cache_path = update_cache_path
        self._compat_cache_path = compat_cache_path
        self._icon_cache_dir = icon_cache_dir
        self._on_save = on_save
        self._on_apply_theme = on_apply_theme
        self._on_cache_cleared = on_cache_cleared
        self._selected_theme = current_theme
        self._custom_theme = sanitize_custom_theme(custom_theme)
        self._preset_buttons: dict[str, ctk.CTkButton] = {}
        self._color_vars: dict[str, ctk.StringVar] = {}
        self._color_swatches: dict[str, ctk.CTkButton] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            segmented_button_unselected_hover_color=COLORS["surface_hover"],
            text_color=COLORS["text_primary"],
        )
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=(SPACING["md"], 8))

        tab_general = self.tabs.add("General")
        tab_themes = self.tabs.add("Themes")
        tab_integrations = self.tabs.add("Integrations")

        self._build_general_tab(
            tab_general, auto_backup_saves, max_auto_backups, launch_via_steam, launch_args
        )
        self._build_themes_tab(tab_themes)
        self._build_integrations_tab(tab_integrations, github_token, nexus_api_key)

        if initial_tab in ("General", "Themes", "Integrations"):
            self.tabs.set(initial_tab)

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        footer.grid_columnconfigure(0, weight=1)

        self.info_label = ctk.CTkLabel(
            footer,
            text="Settings are saved in SVMM_Data/config.json",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.info_label.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            footer,
            text="Cancel",
            width=86,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self.destroy,
        ).grid(row=0, column=1, padx=(8, 6))

        ctk.CTkButton(
            footer,
            text="Save",
            width=96,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._save,
        ).grid(row=0, column=2)

    def _build_general_tab(
        self,
        parent: ctk.CTkFrame,
        auto_backup_saves: bool,
        max_auto_backups: int,
        launch_via_steam: bool,
        launch_args: str,
    ) -> None:
        parent.grid_columnconfigure(0, weight=1)

        launch_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        launch_card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 10))
        launch_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            launch_card,
            text="Launch Options",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        self.steam_var = ctk.BooleanVar(value=launch_via_steam)
        ctk.CTkSwitch(
            launch_card,
            text="Launch via Steam (enables Steam Overlay)",
            variable=self.steam_var,
            progress_color=COLORS["accent"],
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 10))

        ctk.CTkLabel(
            launch_card,
            text="Custom Launch Arguments (used when launching SMAPI directly):",
            font=font_small(),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

        self.args_var = ctk.StringVar(value=launch_args)
        ctk.CTkEntry(
            launch_card,
            textvariable=self.args_var,
            placeholder_text="e.g. --skip-intro",
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
        ).grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        backup_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        backup_card.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        backup_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            backup_card,
            text="Save Protection",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        self.auto_backup_var = ctk.BooleanVar(value=auto_backup_saves)
        ctk.CTkSwitch(
            backup_card,
            text=f"Auto-backup saves before modded launch (keeps last {max_auto_backups})",
            variable=self.auto_backup_var,
            progress_color=COLORS["accent"],
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 12))

    def _build_themes_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="Preset Themes (click to apply live):",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))

        preset_grid = ctk.CTkFrame(parent, fg_color="transparent")
        preset_grid.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        preset_grid.grid_columnconfigure((0, 1, 2), weight=1)

        for idx, name in enumerate(THEME_NAMES):
            theme_def = resolve_theme(name, self._custom_theme)
            accent_hex = theme_def.palette["accent"][0]
            bg_hex = theme_def.palette["bg_app"][0]
            is_selected = name == self._selected_theme

            btn = ctk.CTkButton(
                preset_grid,
                text=f"● {name}",
                height=32,
                corner_radius=8,
                font=font_small(),
                fg_color=accent_hex if is_selected else COLORS["surface_alt"],
                hover_color=accent_hex,
                border_width=1,
                border_color=accent_hex if is_selected else COLORS["border"],
                text_color="#FFFFFF" if is_selected else COLORS["text_primary"],
                command=lambda n=name: self._select_preset_theme(n),
            )
            btn.grid(row=idx // 3, column=idx % 3, sticky="ew", padx=3, pady=3)
            self._preset_buttons[name] = btn
            # Subtle indicator tooltip-like text via bg swatch isn't needed; accent dot is clear
            _ = bg_hex

        # Custom Theme Editor
        custom_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        custom_card.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 4))
        custom_card.grid_columnconfigure((0, 1, 2), weight=1)

        header = ctk.CTkFrame(custom_card, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Custom Theme Studio",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._custom_mode_var = ctk.StringVar(
            value="Light" if self._custom_theme.get("mode") == "light" else "Dark"
        )
        ctk.CTkSegmentedButton(
            header,
            values=["Dark", "Light"],
            variable=self._custom_mode_var,
            height=24,
            font=font_small(),
        ).grid(row=0, column=1, sticky="e")

        fields = [
            ("bg_app", "App Bg"),
            ("bg_sidebar", "Sidebar"),
            ("surface", "Card"),
            ("accent", "Accent"),
            ("success", "Success"),
            ("text_primary", "Text"),
        ]
        for idx, (key, label) in enumerate(fields):
            col = idx % 3
            row = 1 + (idx // 3)
            cell = ctk.CTkFrame(custom_card, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew", padx=8, pady=4)
            cell.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                cell, text=label, font=font_small(), text_color=COLORS["text_muted"], width=48
            ).grid(row=0, column=0, sticky="w")

            hex_val = self._custom_theme.get(key, DEFAULT_CUSTOM_THEME[key])
            var = ctk.StringVar(value=hex_val)
            self._color_vars[key] = var

            swatch = ctk.CTkButton(
                cell,
                text="",
                width=24,
                height=24,
                corner_radius=5,
                fg_color=hex_val,
                hover_color=hex_val,
                border_width=1,
                border_color=COLORS["border"],
                command=lambda k=key: self._pick_color(k),
            )
            swatch.grid(row=0, column=1, padx=(4, 4))
            self._color_swatches[key] = swatch

            entry = ctk.CTkEntry(
                cell,
                textvariable=var,
                height=24,
                width=72,
                font=font_small(),
                fg_color=COLORS["surface"],
                border_color=COLORS["border"],
            )
            entry.grid(row=0, column=2, sticky="ew")

        actions_row = ctk.CTkFrame(custom_card, fg_color="transparent")
        actions_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 10))
        actions_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            actions_row,
            text="Reset Custom",
            width=100,
            height=28,
            font=font_small(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._reset_custom_theme,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            actions_row,
            text="Apply Custom Theme",
            width=148,
            height=28,
            font=font_small(),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._apply_custom_theme,
        ).grid(row=0, column=1, sticky="e")

    def _build_integrations_tab(
        self, parent: ctk.CTkFrame, github_token: str, nexus_api_key: str
    ) -> None:
        parent.grid_columnconfigure(0, weight=1)

        api_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        api_card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 10))
        api_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            api_card,
            text="Nexus Mods Personal API Key (mod browser, thumbnails & updates):",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))

        self.nexus_var = ctk.StringVar(value=nexus_api_key)
        self.nexus_entry = ctk.CTkEntry(
            api_card,
            textvariable=self.nexus_var,
            show="*",
            placeholder_text="Paste Nexus API key...",
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
        )
        self.nexus_entry.grid(row=1, column=0, sticky="ew", padx=(12, 6), pady=(0, 10))
        ctk.CTkButton(
            api_card,
            text="Show",
            width=60,
            height=28,
            font=font_small(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=lambda: self._toggle_secret(self.nexus_entry),
        ).grid(row=1, column=1, padx=(0, 12), pady=(0, 10))

        ctk.CTkLabel(
            api_card,
            text="GitHub Token (optional, raises API rate limit for update checks):",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 4))

        self.gh_var = ctk.StringVar(value=github_token)
        self.gh_entry = ctk.CTkEntry(
            api_card,
            textvariable=self.gh_var,
            show="*",
            placeholder_text="ghp_...",
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
        )
        self.gh_entry.grid(row=3, column=0, sticky="ew", padx=(12, 6), pady=(0, 12))
        ctk.CTkButton(
            api_card,
            text="Show",
            width=60,
            height=28,
            font=font_small(),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=lambda: self._toggle_secret(self.gh_entry),
        ).grid(row=3, column=1, padx=(0, 12), pady=(0, 12))

        cache_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        cache_card.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        cache_card.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            cache_card,
            text="Local Caches",
            font=font_bold(),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 6))

        btn_cfg = {
            "height": 30,
            "font": font_small(),
            "fg_color": COLORS["neutral_btn"],
            "hover_color": COLORS["neutral_btn_hover"],
            "text_color": COLORS["neutral_btn_text"],
        }
        ctk.CTkButton(
            cache_card, text="Clear Update Cache", command=self._clear_cache, **btn_cfg
        ).grid(row=1, column=0, sticky="ew", padx=(12, 4), pady=(0, 12))
        ctk.CTkButton(
            cache_card, text="Clear SMAPI Cache", command=self._clear_compat_cache, **btn_cfg
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 12))
        ctk.CTkButton(
            cache_card, text="Clear Mod Icons", command=self._clear_icon_cache, **btn_cfg
        ).grid(row=1, column=2, sticky="ew", padx=(4, 12), pady=(0, 12))

    @staticmethod
    def _toggle_secret(entry: ctk.CTkEntry) -> None:
        entry.configure(show="" if entry.cget("show") == "*" else "*")

    def _pick_color(self, key: str) -> None:
        initial = self._color_vars[key].get().strip()
        _, chosen = colorchooser.askcolor(color=initial or "#2563EB", parent=self)
        if chosen:
            upper = chosen.upper()
            self._color_vars[key].set(upper)
            self._color_swatches[key].configure(fg_color=upper, hover_color=upper)

    def _select_preset_theme(self, name: str) -> None:
        self._selected_theme = name
        if name in THEMES:
            t = THEMES[name]
            self.info_label.configure(
                text=f"Applied theme: {name} ({t.mode})", text_color=COLORS["success_text"]
            )
        else:
            self.info_label.configure(
                text="Applied Custom theme.", text_color=COLORS["success_text"]
            )
        self._on_apply_theme(name, self._collect_custom_theme())
        self._refresh_preset_highlights()

    def _refresh_preset_highlights(self) -> None:
        for name, btn in self._preset_buttons.items():
            theme_def = resolve_theme(name, self._custom_theme)
            accent_hex = theme_def.palette["accent"][0]
            is_selected = name == self._selected_theme
            btn.configure(
                fg_color=accent_hex if is_selected else COLORS["surface_alt"],
                border_color=accent_hex if is_selected else COLORS["border"],
                text_color="#FFFFFF" if is_selected else COLORS["text_primary"],
            )

    def _collect_custom_theme(self) -> dict[str, str]:
        raw = {"mode": self._custom_mode_var.get().lower()}
        for key, var in self._color_vars.items():
            raw[key] = var.get().strip()
        self._custom_theme = sanitize_custom_theme(raw)
        return dict(self._custom_theme)

    def _reset_custom_theme(self) -> None:
        self._custom_theme = dict(DEFAULT_CUSTOM_THEME)
        self._custom_mode_var.set("Dark")
        for key, val in DEFAULT_CUSTOM_THEME.items():
            if key in self._color_vars:
                self._color_vars[key].set(val)
                self._color_swatches[key].configure(fg_color=val, hover_color=val)
        self.info_label.configure(text="Custom colors reset to Midnight defaults.")

    def _apply_custom_theme(self) -> None:
        custom = self._collect_custom_theme()
        for key, swatch in self._color_swatches.items():
            val = custom.get(key, DEFAULT_CUSTOM_THEME[key])
            self._color_vars[key].set(val)
            swatch.configure(fg_color=val, hover_color=val)
        self._selected_theme = "Custom"
        self._on_apply_theme("Custom", custom)
        self._refresh_preset_highlights()
        self.info_label.configure(
            text="Applied Custom theme live.", text_color=COLORS["success_text"]
        )

    def _clear_cache(self) -> None:
        if self._update_cache_path.is_file():
            self._update_cache_path.unlink()
            self.info_label.configure(
                text="Cleared update cache.", text_color=COLORS["success_text"]
            )
            if self._on_cache_cleared is not None:
                self._on_cache_cleared()
        else:
            self.info_label.configure(
                text="Update cache is already empty.", text_color=COLORS["text_muted"]
            )

    def _clear_compat_cache(self) -> None:
        if self._compat_cache_path.is_file():
            self._compat_cache_path.unlink()
            self.info_label.configure(
                text="Cleared SMAPI compatibility cache.", text_color=COLORS["success_text"]
            )
        else:
            self.info_label.configure(
                text="SMAPI compatibility cache is already empty.", text_color=COLORS["text_muted"]
            )

    def _clear_icon_cache(self) -> None:
        if self._icon_cache_dir.is_dir():
            shutil.rmtree(self._icon_cache_dir, ignore_errors=True)
            self.info_label.configure(
                text="Cleared cached mod thumbnails.", text_color=COLORS["success_text"]
            )
        else:
            self.info_label.configure(
                text="Mod thumbnail cache is already empty.", text_color=COLORS["text_muted"]
            )

    def _save(self) -> None:
        self._on_save(
            self.gh_var.get().strip(),
            self.nexus_var.get().strip(),
            bool(self.auto_backup_var.get()),
            bool(self.steam_var.get()),
            self.args_var.get().strip(),
        )
        self.destroy()
