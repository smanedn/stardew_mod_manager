"""Main mod list component with debounced search, cached rows, warnings, and updates."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.core.dependencies import ModIssue
from src.core.mod_scanner import ModInfo
from src.core.updater import UpdateResult
from src.ui.theme import COLORS, SPACING, font_small
from src.ui.tooltip import ToolTip


class ModListPanel(ctk.CTkFrame):
    """Scrollable mod list with debounced search, cached rows, and status badges."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toggle: Callable[[list[str]], None],
        on_refresh: Callable[[], None],
        on_install_zip: Callable[[], None],
        on_install_nexus: Callable[[], None],
        on_check_updates: Callable[[], None],
    ) -> None:
        super().__init__(master, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._on_toggle = on_toggle
        self._mods: list[ModInfo] = []
        # folder -> (row_frame, checkbox, var, warning_label, warning_tip, update_label, update_tip)
        self._mod_rows: dict[
            str,
            tuple[
                ctk.CTkFrame,
                ctk.CTkCheckBox,
                ctk.BooleanVar,
                ctk.CTkLabel,
                ToolTip,
                ctk.CTkLabel,
                ToolTip,
            ],
        ] = {}
        self._search_after_id: str | None = None
        self._active_profile_name = "Default"

        # --- Filter & Action Bar ---
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.grid(
            row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"])
        )
        filter_bar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._schedule_filter)
        self.search_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self.search_var,
            placeholder_text="Filter mods by name, author, or folder (Ctrl+F)...",
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))

        self.count_label = ctk.CTkLabel(
            filter_bar, text="0 / 0 enabled", font=font_small(), text_color=COLORS["text_muted"]
        )
        self.count_label.grid(row=0, column=1, padx=SPACING["sm"])

        ctk.CTkButton(filter_bar, text="Select All", width=80, command=self.select_all).grid(
            row=0, column=2, padx=2
        )
        ctk.CTkButton(filter_bar, text="Deselect All", width=88, command=self.deselect_all).grid(
            row=0, column=3, padx=2
        )
        self.install_btn = ctk.CTkButton(
            filter_bar, text="Install .zip", width=82, command=on_install_zip
        )
        self.install_btn.grid(row=0, column=4, padx=2)
        self.nexus_btn = ctk.CTkButton(filter_bar, text="Nexus", width=66, command=on_install_nexus)
        self.nexus_btn.grid(row=0, column=5, padx=2)
        self.update_btn = ctk.CTkButton(
            filter_bar,
            text="Updates",
            width=72,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=on_check_updates,
        )
        self.update_btn.grid(row=0, column=6, padx=2)
        self.refresh_btn = ctk.CTkButton(filter_bar, text="Refresh", width=70, command=on_refresh)
        self.refresh_btn.grid(row=0, column=7, padx=(2, 0))

        # --- Scrollable Mods Area ---
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(
            row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"])
        )
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(self.scroll_frame, text="", text_color=COLORS["text_muted"])

    def focus_search(self) -> None:
        self.search_entry.focus_set()

    def clear_search(self) -> None:
        if self.search_var.get():
            self.search_var.set("")

    def set_loading(self, loading: bool, message: str = "Scanning modpack...") -> None:
        state = "disabled" if loading else "normal"
        self.refresh_btn.configure(state=state)
        self.install_btn.configure(state=state)
        self.nexus_btn.configure(state=state)
        if loading:
            for row_frame, *_ in self._mod_rows.values():
                row_frame.grid_remove()
            self.empty_label.configure(text=message)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=24)

    def set_mods(self, mods: list[ModInfo], enabled_mods: list[str], active_profile: str) -> None:
        self._mods = mods
        self._active_profile_name = active_profile
        enabled_set = set(enabled_mods)

        for row_frame, *_ in self._mod_rows.values():
            row_frame.destroy()
        self._mod_rows.clear()
        self.empty_label.grid_remove()

        for mod in mods:
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)

            var = ctk.BooleanVar(value=mod.folder_name in enabled_set)
            author_part = f" by {mod.author}" if mod.author else ""
            label = f"{mod.name} (v{mod.version}){author_part}  [{mod.folder_name}]"
            if mod.error:
                label += f"  [{mod.error}]"
            cb = ctk.CTkCheckBox(
                row_frame,
                text=label,
                variable=var,
                command=self._emit_toggle,
                text_color=COLORS["warning_text"] if mod.error else COLORS["text_primary"],
            )
            cb.grid(row=0, column=0, sticky="w", padx=4, pady=3)

            warn_lbl = ctk.CTkLabel(
                row_frame, text="", font=font_small(), text_color=COLORS["warning_text"]
            )
            warn_tip = ToolTip(warn_lbl, "")

            upd_lbl = ctk.CTkLabel(
                row_frame, text="", font=font_small(), text_color=COLORS["success_text"]
            )
            upd_tip = ToolTip(upd_lbl, "")

            self._mod_rows[mod.folder_name] = (
                row_frame,
                cb,
                var,
                warn_lbl,
                warn_tip,
                upd_lbl,
                upd_tip,
            )

        self._apply_filter()

    def set_issues(self, issues: dict[str, list[ModIssue]]) -> None:
        for folder, (_, _, _, warn_lbl, warn_tip, _, _) in self._mod_rows.items():
            mod_issues = issues.get(folder)
            if mod_issues:
                warn_lbl.configure(text="⚠")
                warn_lbl.grid(row=0, column=1, padx=(6, 2))
                warn_tip.update_text("\n".join(i.message for i in mod_issues))
            else:
                warn_lbl.grid_remove()
                warn_tip.update_text("")

    def set_updates(self, results: list[UpdateResult]) -> None:
        by_folder = {r.folder_name: r for r in results}
        for folder, (_, _, _, _, _, upd_lbl, upd_tip) in self._mod_rows.items():
            res = by_folder.get(folder)
            if res and res.has_update:
                upd_lbl.configure(text=f"↑ v{res.latest_version}")
                upd_lbl.grid(row=0, column=2, padx=(4, 6))
                upd_tip.update_text(f"Update available: v{res.latest_version}\n{res.url}")
            else:
                upd_lbl.grid_remove()
                upd_tip.update_text("")

    def _schedule_filter(self, *_args: object) -> None:
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(150, self._apply_filter)

    def _matches_query(self, mod: ModInfo, query: str) -> bool:
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
            row_frame, *_ = self._mod_rows[mod.folder_name]
            if self._matches_query(mod, query):
                row_frame.grid(row=visible_idx, column=0, sticky="ew", padx=4, pady=1)
                visible_idx += 1
            else:
                row_frame.grid_remove()

        if visible_idx == 0:
            msg = (
                "No mods match your filter."
                if self._mods
                else (
                    f"No mods found in SVMM_Data/modpacks/{self._active_profile_name}.\n"
                    "Click 'Open Modpack Folder' or 'Install .zip' to add mods."
                )
            )
            self.empty_label.configure(text=msg)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=24)
        else:
            self.empty_label.grid_remove()

        self._update_count()

    def _update_count(self) -> None:
        total = len(self._mods)
        enabled = sum(1 for _, _, var, *_ in self._mod_rows.values() if var.get())
        self.count_label.configure(text=f"{enabled} / {total} enabled")

    def _emit_toggle(self) -> None:
        self._update_count()
        enabled = [folder for folder, (_, _, var, *_) in self._mod_rows.items() if var.get()]
        self._on_toggle(enabled)

    def select_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                _, _, var, *_ = self._mod_rows[mod.folder_name]
                var.set(True)
        self._emit_toggle()

    def deselect_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                _, _, var, *_ = self._mod_rows[mod.folder_name]
                var.set(False)
        self._emit_toggle()
