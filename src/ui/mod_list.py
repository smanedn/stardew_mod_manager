"""Revamped mod list panel with compact 2-row toolbar and mod thumbnail cards."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from src.core.dependencies import ModIssue
from src.core.mod_icons import load_mod_icon
from src.core.mod_scanner import ModInfo
from src.core.smapi_compat import SmapiCompatInfo
from src.core.updater import UpdateResult
from src.ui.theme import COLORS, SPACING, font_bold, font_small
from src.ui.tooltip import ToolTip


class ModListPanel(ctk.CTkFrame):
    """Scrollable mod card list with compact toolbar, filter chips, and mod thumbnails."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toggle: Callable[[list[str]], None],
        on_refresh: Callable[[], None],
        on_install_zip: Callable[[], None],
        on_install_nexus: Callable[[], None],
        on_check_updates: Callable[[], None],
        on_show_details: Callable[[ModInfo], None] | None = None,
        on_update_mod: Callable[[UpdateResult], None] | None = None,
        on_update_all: Callable[[], None] | None = None,
        on_fix_deps: Callable[[], None] | None = None,
        on_check_compat: Callable[[], None] | None = None,
        icon_cache_dir: Path | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._on_toggle = on_toggle
        self._on_refresh = on_refresh
        self._on_check_updates = on_check_updates
        self._on_check_compat = on_check_compat
        self._on_show_details = on_show_details
        self._on_update_mod = on_update_mod
        self._icon_cache_dir = icon_cache_dir or Path("SVMM_Data") / "mod_icons"
        self._mods: list[ModInfo] = []
        self._status_filter = "all"
        self._issue_folders: set[str] = set()
        self._update_folders: set[str] = set()
        # folder -> (card, img_lbl, ctk_img, switch, var,
        #            compat_lbl, compat_tip, warn_lbl, warn_tip, upd_btn, upd_tip)
        self._mod_rows: dict[
            str,
            tuple[
                ctk.CTkFrame,
                ctk.CTkLabel,
                ctk.CTkImage,
                ctk.CTkSwitch,
                ctk.BooleanVar,
                ctk.CTkLabel,
                ToolTip,
                ctk.CTkLabel,
                ToolTip,
                ctk.CTkButton,
                ToolTip,
            ],
        ] = {}
        self._search_after_id: str | None = None
        self._active_profile_name = "Default"

        # --- Row 0: Search + Primary Actions ---
        top_toolbar = ctk.CTkFrame(self, fg_color="transparent")
        top_toolbar.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["md"], 6))
        top_toolbar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._schedule_filter)
        self.search_entry = ctk.CTkEntry(
            top_toolbar,
            height=32,
            textvariable=self.search_var,
            placeholder_text="Search mods by name, author, or folder (Ctrl+F)...",
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))

        subtle_btn = {
            "height": 32,
            "font": font_small(),
            "fg_color": COLORS["neutral_btn"],
            "hover_color": COLORS["neutral_btn_hover"],
            "text_color": COLORS["neutral_btn_text"],
        }

        self.install_btn = ctk.CTkButton(
            top_toolbar,
            text="+ Install",
            height=32,
            width=96,
            font=font_small(),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=on_install_zip,
        )
        self.install_btn.grid(row=0, column=1, padx=(0, 6))

        self.nexus_btn = ctk.CTkButton(
            top_toolbar,
            text="Nexus Mods",
            width=102,
            command=on_install_nexus,
            **subtle_btn,
        )
        self.nexus_btn.grid(row=0, column=2, padx=(0, 6))

        self.actions_btn = ctk.CTkButton(
            top_toolbar,
            text="Actions ▾",
            width=92,
            command=self._show_actions_menu,
            **subtle_btn,
        )
        self.actions_btn.grid(row=0, column=3)

        self.update_all_btn = ctk.CTkButton(
            top_toolbar,
            text="Update All",
            height=32,
            width=106,
            font=font_small(),
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=on_update_all,
        )

        self.fix_deps_btn = ctk.CTkButton(
            top_toolbar,
            text="Fix Deps",
            height=32,
            width=94,
            font=font_small(),
            fg_color=COLORS["warning_bg"],
            hover_color=COLORS["warning_text"],
            text_color=COLORS["warning_text"],
            command=on_fix_deps,
        )

        # --- Row 1: Filter Chips + Mod Count Pill ---
        chip_bar = ctk.CTkFrame(self, fg_color="transparent")
        chip_bar.grid(row=1, column=0, sticky="ew", padx=SPACING["md"], pady=(0, 6))
        chip_bar.grid_columnconfigure(1, weight=1)

        self.filter_chips = ctk.CTkSegmentedButton(
            chip_bar,
            values=["All", "Enabled", "Disabled", "Issues ⚠", "Updates ↑"],
            height=28,
            font=font_small(),
            fg_color=COLORS["surface_alt"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["surface_alt"],
            unselected_hover_color=COLORS["surface_hover"],
            text_color=COLORS["text_primary"],
            command=self._on_filter_chip_changed,
        )
        self.filter_chips.set("All")
        self.filter_chips.grid(row=0, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(
            chip_bar,
            text="0 / 0 enabled",
            font=font_small(),
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.count_label.grid(row=0, column=2, sticky="e")

        # --- Row 2: Scrollable Mod Cards ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_app"], corner_radius=8)
        self.scroll_frame.grid(
            row=2, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"])
        )
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(self.scroll_frame, text="", text_color=COLORS["text_muted"])

    def _show_actions_menu(self) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = COLORS["surface"][1] if is_dark else COLORS["surface"][0]
        fg = COLORS["text_primary"][1] if is_dark else COLORS["text_primary"][0]
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=bg,
            fg=fg,
            activebackground=COLORS["accent"][0],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=1,
        )
        menu.add_command(label="Check Mod Updates", command=self._on_check_updates)
        if self._on_check_compat is not None:
            menu.add_command(label="Check SMAPI Compatibility", command=self._on_check_compat)
        menu.add_separator()
        menu.add_command(label="Select All Visible", command=self.select_all)
        menu.add_command(label="Deselect All Visible", command=self.deselect_all)
        menu.add_separator()
        menu.add_command(label="Refresh Mod List", command=self._on_refresh)

        x = self.actions_btn.winfo_rootx()
        y = self.actions_btn.winfo_rooty() + self.actions_btn.winfo_height() + 2
        menu.tk_popup(x, y)

    def focus_search(self) -> None:
        self.search_entry.focus_set()

    def clear_search(self) -> None:
        if self.search_var.get():
            self.search_var.set("")

    def set_loading(self, loading: bool, message: str = "Scanning modpack...") -> None:
        state = "disabled" if loading else "normal"
        self.actions_btn.configure(state=state)
        self.install_btn.configure(state=state)
        self.nexus_btn.configure(state=state)
        if loading:
            for card, *_ in self._mod_rows.values():
                card.grid_remove()
            self.empty_label.configure(text=message)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=32)

    def set_mods(self, mods: list[ModInfo], enabled_mods: list[str], active_profile: str) -> None:
        self._mods = mods
        self._active_profile_name = active_profile
        enabled_set = set(enabled_mods)

        for card, *_ in self._mod_rows.values():
            card.destroy()
        self._mod_rows.clear()
        self.empty_label.grid_remove()

        for mod in mods:
            card = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["surface"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["border"],
            )
            card.grid_columnconfigure(2, weight=1)

            # Column 0: 42x42 Mod Thumbnail Image
            pil_icon = load_mod_icon(mod, self._icon_cache_dir, size=84)
            ctk_img = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(42, 42))
            img_lbl = ctk.CTkLabel(card, text="", image=ctk_img, width=42, height=42)
            img_lbl.grid(row=0, column=0, rowspan=2, padx=(10, 6), pady=8)

            # Column 1: Enable/Disable Switch
            var = ctk.BooleanVar(value=mod.folder_name in enabled_set)
            switch = ctk.CTkSwitch(
                card,
                text="",
                width=42,
                variable=var,
                progress_color=COLORS["accent"],
                command=self._emit_toggle,
            )
            switch.grid(row=0, column=1, rowspan=2, padx=(4, 6), pady=10)

            # Column 2: Title + Version + Author / Folder
            title_row = ctk.CTkFrame(card, fg_color="transparent")
            title_row.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=(8, 0))

            ctk.CTkLabel(
                title_row,
                text=mod.name,
                font=font_bold(),
                text_color=COLORS["warning_text"] if mod.error else COLORS["text_primary"],
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                title_row,
                text=f"v{mod.version}",
                font=font_small(),
                fg_color=COLORS["surface_alt"],
                text_color=COLORS["text_muted"],
                corner_radius=4,
                padx=6,
                pady=1,
            ).pack(side="left", padx=(8, 0))

            if mod.author:
                ctk.CTkLabel(
                    title_row,
                    text=f"by {mod.author}",
                    font=font_small(),
                    text_color=COLORS["text_muted"],
                ).pack(side="left", padx=(8, 0))

            sub_text = mod.folder_name if not mod.error else f"{mod.folder_name}  •  {mod.error}"
            ctk.CTkLabel(
                card,
                text=sub_text,
                font=font_small(),
                text_color=COLORS["warning_text"] if mod.error else COLORS["text_muted"],
                anchor="w",
            ).grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(0, 8))

            # Right badges + Details button
            compat_lbl = ctk.CTkLabel(
                card,
                text="",
                font=font_small(),
                fg_color=COLORS["surface_alt"],
                text_color=COLORS["text_muted"],
                corner_radius=6,
                padx=8,
                pady=2,
            )
            compat_tip = ToolTip(compat_lbl, "")

            warn_lbl = ctk.CTkLabel(
                card,
                text="",
                font=font_small(),
                fg_color=COLORS["warning_bg"],
                text_color=COLORS["warning_text"],
                corner_radius=6,
                padx=8,
                pady=2,
            )
            warn_tip = ToolTip(warn_lbl, "")

            upd_btn = ctk.CTkButton(
                card,
                text="",
                width=74,
                height=26,
                font=font_small(),
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
            )
            upd_tip = ToolTip(upd_btn, "")

            if self._on_show_details is not None:
                ctk.CTkButton(
                    card,
                    text="Details",
                    width=64,
                    height=26,
                    font=font_small(),
                    fg_color=COLORS["neutral_btn"],
                    hover_color=COLORS["neutral_btn_hover"],
                    text_color=COLORS["neutral_btn_text"],
                    command=lambda m=mod: self._show_details(m),
                ).grid(row=0, column=6, rowspan=2, padx=(4, 10), pady=8)

            self._mod_rows[mod.folder_name] = (
                card,
                img_lbl,
                ctk_img,
                switch,
                var,
                compat_lbl,
                compat_tip,
                warn_lbl,
                warn_tip,
                upd_btn,
                upd_tip,
            )

        self._apply_filter()

    def update_mod_icon(self, folder_name: str, pil_image: Image.Image) -> None:
        """Update a mod card's thumbnail image after an async fetch."""
        if not self.winfo_exists():
            return
        row = self._mod_rows.get(folder_name)
        if row is None:
            return
        card, img_lbl, _old_img, *rest = row
        if not img_lbl.winfo_exists():
            return
        new_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(42, 42))
        try:
            img_lbl.configure(image=new_img)
        except tk.TclError:
            return
        self._mod_rows[folder_name] = (card, img_lbl, new_img, *rest)

    def _show_details(self, mod: ModInfo) -> None:
        if self._on_show_details is not None:
            self._on_show_details(mod)

    def set_fixable_deps_count(self, count: int) -> None:
        if count > 0:
            self.fix_deps_btn.configure(text=f"Fix Deps ({count})")
            self.fix_deps_btn.grid(row=0, column=5, padx=(6, 0))
        else:
            self.fix_deps_btn.grid_remove()

    def set_updatable_count(self, count: int) -> None:
        if count > 0:
            self.update_all_btn.configure(text=f"Update All ({count})", state="normal")
            self.update_all_btn.grid(row=0, column=4, padx=(6, 0))
        else:
            self.update_all_btn.grid_remove()

    def sync_enabled(self, enabled_mods: list[str]) -> None:
        enabled_set = set(enabled_mods)
        for folder, (_, _, _, _, var, *_) in self._mod_rows.items():
            var.set(folder in enabled_set)
        self._update_count()

    def set_compat(self, compat_map: dict[str, SmapiCompatInfo]) -> None:
        for folder, row in self._mod_rows.items():
            compat_lbl, compat_tip = row[5], row[6]
            info = compat_map.get(folder)
            if not info:
                compat_lbl.grid_remove()
                compat_tip.update_text("")
                continue
            if info.is_broken:
                fg, tc = COLORS["danger"], ("#FFFFFF", "#FFFFFF")
            elif info.is_warning:
                fg, tc = COLORS["warning_bg"], COLORS["warning_text"]
            else:
                fg, tc = COLORS["surface_alt"], COLORS["success_text"]
            compat_lbl.configure(text=info.status, fg_color=fg, text_color=tc)
            compat_lbl.grid(row=0, column=3, rowspan=2, padx=(4, 4))
            tip_lines = [f"SMAPI Status: {info.status}"]
            if info.summary:
                tip_lines.append(info.summary)
            if info.unofficial_version:
                tip_lines.append(f"Unofficial 1.6 Update: v{info.unofficial_version}")
            compat_tip.update_text("\n".join(tip_lines))

    def set_issues(self, issues: dict[str, list[ModIssue]]) -> None:
        self._issue_folders = set(issues.keys())
        for folder, row in self._mod_rows.items():
            warn_lbl, warn_tip = row[7], row[8]
            mod_issues = issues.get(folder)
            if mod_issues:
                warn_lbl.configure(text=f"⚠ {len(mod_issues)}")
                warn_lbl.grid(row=0, column=4, rowspan=2, padx=(4, 4))
                warn_tip.update_text("\n".join(i.message for i in mod_issues))
            else:
                warn_lbl.grid_remove()
                warn_tip.update_text("")
        if self._status_filter == "issues":
            self._apply_filter()

    def set_updates(self, results: list[UpdateResult]) -> None:
        by_folder = {r.folder_name: r for r in results}
        self._update_folders = {r.folder_name for r in results if r.has_update}
        for folder, row in self._mod_rows.items():
            upd_btn, upd_tip = row[9], row[10]
            res = by_folder.get(folder)
            if res and res.has_update:
                upd_btn.configure(
                    text=f"↑ v{res.latest_version}",
                    state="normal",
                    command=lambda r=res: self._trigger_update(r),
                )
                upd_btn.grid(row=0, column=5, rowspan=2, padx=(4, 4))
                upd_tip.update_text(f"Click to update to v{res.latest_version}\n{res.url}")
            else:
                upd_btn.grid_remove()
                upd_tip.update_text("")
        if self._status_filter == "updates":
            self._apply_filter()

    def _on_filter_chip_changed(self, label: str) -> None:
        mapping = {
            "All": "all",
            "Enabled": "enabled",
            "Disabled": "disabled",
            "Issues ⚠": "issues",
            "Updates ↑": "updates",
        }
        self._status_filter = mapping.get(label, "all")
        self._apply_filter()

    def _trigger_update(self, result: UpdateResult) -> None:
        if self._on_update_mod is not None:
            self._on_update_mod(result)

    def _schedule_filter(self, *_args: object) -> None:
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(150, self._apply_filter)

    def _matches_query(self, mod: ModInfo, query: str) -> bool:
        if self._status_filter == "enabled":
            if not self._mod_rows[mod.folder_name][4].get():
                return False
        elif self._status_filter == "disabled":
            if self._mod_rows[mod.folder_name][4].get():
                return False
        elif self._status_filter == "issues":
            if mod.folder_name not in self._issue_folders and not mod.error:
                return False
        elif self._status_filter == "updates":
            if mod.folder_name not in self._update_folders:
                return False

        if not query:
            return True
        return (
            query in mod.name.lower()
            or query in mod.folder_name.lower()
            or query in mod.author.lower()
        )

    def _apply_filter(self) -> None:
        self._search_after_id = None
        query = self.search_var.get().strip().lower()
        visible_idx = 0

        for mod in self._mods:
            card = self._mod_rows[mod.folder_name][0]
            if self._matches_query(mod, query):
                card.grid(row=visible_idx, column=0, sticky="ew", padx=6, pady=3)
                visible_idx += 1
            else:
                card.grid_remove()

        if visible_idx == 0:
            msg = (
                "No mods match your filter."
                if self._mods
                else (
                    f"No mods found in SVMM_Data/modpacks/{self._active_profile_name}.\n"
                    "Drag & drop .zip / .7z / .rar files here, or use + Install above."
                )
            )
            self.empty_label.configure(text=msg)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=36)
        else:
            self.empty_label.grid_remove()

        self._update_count()

    def _update_count(self) -> None:
        total = len(self._mods)
        enabled = sum(1 for row in self._mod_rows.values() if row[4].get())
        self.count_label.configure(text=f"{enabled} / {total} enabled")

    def _emit_toggle(self) -> None:
        self._update_count()
        enabled = [folder for folder, row in self._mod_rows.items() if row[4].get()]
        self._on_toggle(enabled)
        if self._status_filter in ("enabled", "disabled"):
            self._apply_filter()

    def select_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                self._mod_rows[mod.folder_name][4].set(True)
        self._emit_toggle()

    def deselect_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                self._mod_rows[mod.folder_name][4].set(False)
        self._emit_toggle()
