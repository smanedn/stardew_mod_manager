"""Main mod list component with debounced search, cached rows, and counter badge."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.core.mod_scanner import ModInfo
from src.ui.theme import COLORS, SPACING, font_small


class ModListPanel(ctk.CTkFrame):
    """Scrollable mod list with debounced search filtering and cached row widgets."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toggle: Callable[[list[str]], None],
        on_refresh: Callable[[], None],
    ) -> None:
        super().__init__(master, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._on_toggle = on_toggle
        self._mods: list[ModInfo] = []
        self._mod_rows: dict[str, tuple[ctk.CTkCheckBox, ctk.BooleanVar]] = {}
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

        ctk.CTkButton(filter_bar, text="Select All", width=86, command=self.select_all).grid(
            row=0, column=2, padx=3
        )
        ctk.CTkButton(filter_bar, text="Deselect All", width=92, command=self.deselect_all).grid(
            row=0, column=3, padx=3
        )
        self.refresh_btn = ctk.CTkButton(filter_bar, text="Refresh", width=76, command=on_refresh)
        self.refresh_btn.grid(row=0, column=4, padx=(3, 0))

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
        self.refresh_btn.configure(state="disabled" if loading else "normal")
        if loading:
            for cb, _ in self._mod_rows.values():
                cb.grid_remove()
            self.empty_label.configure(text=message)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=24)

    def set_mods(self, mods: list[ModInfo], enabled_mods: list[str], active_profile: str) -> None:
        self._mods = mods
        self._active_profile_name = active_profile
        enabled_set = set(enabled_mods)

        # Destroy old cached checkboxes only when the mod list itself reloads
        for cb, _ in self._mod_rows.values():
            cb.destroy()
        self._mod_rows.clear()
        self.empty_label.grid_remove()

        for mod in mods:
            var = ctk.BooleanVar(value=mod.folder_name in enabled_set)
            author_part = f" by {mod.author}" if mod.author else ""
            label = f"{mod.name} (v{mod.version}){author_part}  [{mod.folder_name}]"
            if mod.error:
                label += f"  [{mod.error}]"
            cb = ctk.CTkCheckBox(
                self.scroll_frame,
                text=label,
                variable=var,
                command=self._emit_toggle,
                text_color=COLORS["warning_text"] if mod.error else COLORS["text_primary"],
            )
            self._mod_rows[mod.folder_name] = (cb, var)

        self._apply_filter()

    def sync_enabled(self, enabled_mods: list[str]) -> None:
        enabled_set = set(enabled_mods)
        for folder, (_, var) in self._mod_rows.items():
            var.set(folder in enabled_set)
        self._update_count()

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
            cb, _ = self._mod_rows[mod.folder_name]
            if self._matches_query(mod, query):
                cb.grid(row=visible_idx, column=0, sticky="w", padx=8, pady=4)
                visible_idx += 1
            else:
                cb.grid_remove()

        if visible_idx == 0:
            msg = (
                "No mods match your filter."
                if self._mods
                else (
                    f"No mods found in SVMM_Data/modpacks/{self._active_profile_name}.\n"
                    "Click 'Open Modpack Folder' above to add mods, then click Refresh."
                )
            )
            self.empty_label.configure(text=msg)
            self.empty_label.grid(row=0, column=0, padx=SPACING["md"], pady=24)
        else:
            self.empty_label.grid_remove()

        self._update_count()

    def _update_count(self) -> None:
        total = len(self._mods)
        enabled = sum(1 for _, var in self._mod_rows.values() if var.get())
        self.count_label.configure(text=f"{enabled} / {total} enabled")

    def _emit_toggle(self) -> None:
        self._update_count()
        enabled = [folder for folder, (_, var) in self._mod_rows.items() if var.get()]
        self._on_toggle(enabled)

    def select_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                _, var = self._mod_rows[mod.folder_name]
                var.set(True)
        self._emit_toggle()

    def deselect_all(self) -> None:
        query = self.search_var.get().strip().lower()
        for mod in self._mods:
            if self._matches_query(mod, query):
                _, var = self._mod_rows[mod.folder_name]
                var.set(False)
        self._emit_toggle()
