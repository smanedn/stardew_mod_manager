"""In-app Nexus Mods browser and 1-click installer dialog."""

from __future__ import annotations

import threading
import urllib.error
import webbrowser
from collections.abc import Callable

import customtkinter as ctk

from src.core.nexus_browser import (
    BrowseCategory,
    NexusModSummary,
    fetch_nexus_category,
    search_nexus_mods,
)
from src.ui.theme import COLORS, SPACING, font_bold, font_small, font_title


class NexusBrowserDialog(ctk.CTkToplevel):
    """Browse, search, and install Stardew Valley mods directly from Nexus Mods."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_api_key: str,
        on_save_api_key: Callable[[str], None],
        on_install_mod: Callable[[str, str], None],
    ) -> None:
        super().__init__(master)
        self.title("Browse Nexus Mods — Stardew Valley")
        self.geometry("780x580")
        self.minsize(640, 460)
        self.transient(master)
        self.grab_set()

        self._on_save_api_key = on_save_api_key
        self._on_install_mod = on_install_mod
        self._request_gen = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- API Key & Search Header ---
        header = ctk.CTkFrame(self, border_width=1, border_color=COLORS["border"])
        header.grid(
            row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"])
        )
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="API Key:", font=font_bold()).grid(
            row=0,
            column=0,
            padx=(SPACING["md"], SPACING["sm"]),
            pady=(SPACING["md"], 4),
            sticky="w",
        )
        self.key_var = ctk.StringVar(value=initial_api_key)
        self.key_entry = ctk.CTkEntry(
            header,
            textvariable=self.key_var,
            show="*",
            placeholder_text="Paste your Nexus Mods Personal API Key...",
        )
        self.key_entry.grid(
            row=0, column=1, sticky="ew", padx=SPACING["sm"], pady=(SPACING["md"], 4)
        )
        self.key_entry.bind("<FocusOut>", lambda _e: self._save_key())

        ctk.CTkButton(header, text="Save Key", width=84, command=self._save_key).grid(
            row=0, column=2, padx=(0, SPACING["md"]), pady=(SPACING["md"], 4)
        )

        ctk.CTkLabel(header, text="Search:", font=font_bold()).grid(
            row=1,
            column=0,
            padx=(SPACING["md"], SPACING["sm"]),
            pady=(4, SPACING["md"]),
            sticky="w",
        )
        self.search_entry = ctk.CTkEntry(
            header, placeholder_text="Search Stardew Valley mods by name (e.g. Expanded)..."
        )
        self.search_entry.grid(
            row=1, column=1, sticky="ew", padx=SPACING["sm"], pady=(4, SPACING["md"])
        )
        self.search_entry.bind("<Return>", lambda _e: self._do_search())

        ctk.CTkButton(header, text="Search", width=84, command=self._do_search).grid(
            row=1, column=2, padx=(0, SPACING["md"]), pady=(4, SPACING["md"])
        )

        # --- Category Tabs ---
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["xs"])

        ctk.CTkButton(
            tabs,
            text="Trending",
            width=110,
            command=lambda: self._load_category("trending"),
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(
            tabs,
            text="Latest Updated",
            width=125,
            command=lambda: self._load_category("latest_updated"),
        ).grid(row=0, column=1, padx=6)
        ctk.CTkButton(
            tabs,
            text="New Mods",
            width=110,
            command=lambda: self._load_category("latest_added"),
        ).grid(row=0, column=2, padx=6)

        self.status_label = ctk.CTkLabel(
            tabs, text="", font=font_small(), text_color=COLORS["text_muted"]
        )
        self.status_label.grid(row=0, column=3, padx=SPACING["md"], sticky="w")

        # --- Scrollable Results ---
        self.results_frame = ctk.CTkScrollableFrame(
            self, border_width=1, border_color=COLORS["border"]
        )
        self.results_frame.grid(
            row=2, column=0, sticky="nsew", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"])
        )
        self.results_frame.grid_columnconfigure(0, weight=1)

        if initial_api_key.strip():
            self.after(100, lambda: self._load_category("trending"))
        else:
            self._show_message(
                "Enter your Nexus Mods API Key above and click Trending, Latest Updated, or Search."
            )

    def _save_key(self) -> str:
        key = self.key_var.get().strip()
        self._on_save_api_key(key)
        return key

    def _clear_results(self) -> None:
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def _show_message(self, text: str, is_error: bool = False) -> None:
        self._clear_results()
        color = COLORS["error_text"] if is_error else COLORS["text_muted"]
        ctk.CTkLabel(
            self.results_frame, text=text, text_color=color, wraplength=680, justify="center"
        ).grid(row=0, column=0, padx=SPACING["lg"], pady=32)

    def _load_category(self, category: BrowseCategory) -> None:
        key = self._save_key()
        self._request_gen += 1
        gen = self._request_gen
        self.status_label.configure(
            text=f"Loading {category.replace('_', ' ')}...", text_color=COLORS["text_muted"]
        )
        self._show_message("Loading mods from Nexus Mods...")

        def worker() -> None:
            try:
                mods = fetch_nexus_category(category, key)
                err = None
            except (OSError, ValueError, urllib.error.URLError) as exc:
                mods = []
                err = str(exc)
            self.after(0, lambda: self._on_mods_loaded(gen, mods, err))

        threading.Thread(target=worker, daemon=True).start()

    def _do_search(self) -> None:
        query = self.search_entry.get().strip()
        if not query:
            self.status_label.configure(
                text="Enter a search term.", text_color=COLORS["warning_text"]
            )
            return

        self._request_gen += 1
        gen = self._request_gen
        self.status_label.configure(text=f"Searching '{query}'...", text_color=COLORS["text_muted"])
        self._show_message(f"Searching Nexus Mods for '{query}'...")

        def worker() -> None:
            try:
                mods = search_nexus_mods(query)
                err = None
            except (OSError, ValueError, urllib.error.URLError) as exc:
                mods = []
                err = str(exc)
            self.after(0, lambda: self._on_mods_loaded(gen, mods, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_mods_loaded(self, gen: int, mods: list[NexusModSummary], error: str | None) -> None:
        if gen != self._request_gen or not self.winfo_exists():
            return
        if error:
            self.status_label.configure(text="Failed", text_color=COLORS["error_text"])
            self._show_message(error, is_error=True)
            return

        self.status_label.configure(
            text=f"Showing {len(mods)} mod(s)", text_color=COLORS["success_text"]
        )
        if not mods:
            self._show_message("No mods found.")
            return

        self._clear_results()
        for idx, mod in enumerate(mods):
            card = ctk.CTkFrame(
                self.results_frame,
                fg_color=COLORS["surface_alt"],
                border_width=1,
                border_color=COLORS["border"],
            )
            card.grid(row=idx, column=0, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(0, weight=1)

            title_text = f"{mod.name}  (v{mod.version})"
            ctk.CTkLabel(card, text=title_text, font=font_title(), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=(8, 2)
            )
            meta_text = (
                f"by {mod.author}  •  ★ {mod.endorsements:,} endorsements  •  ID: {mod.mod_id}"
            )
            ctk.CTkLabel(
                card, text=meta_text, font=font_small(), text_color=COLORS["text_muted"], anchor="w"
            ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))

            if mod.summary:
                ctk.CTkLabel(
                    card,
                    text=mod.summary,
                    font=font_small(),
                    anchor="w",
                    wraplength=520,
                    justify="left",
                ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=0, column=1, rowspan=3, padx=10, pady=8, sticky="e")

            ctk.CTkButton(
                actions,
                text="Install",
                width=92,
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                command=lambda m_id=mod.mod_id: self._install_clicked(m_id),
            ).grid(row=0, column=0, pady=(0, 4))

            ctk.CTkButton(
                actions,
                text="Open Page",
                width=92,
                fg_color=COLORS["neutral_btn"],
                hover_color=COLORS["neutral_btn_hover"],
                command=lambda m_id=mod.mod_id: webbrowser.open(
                    f"https://www.nexusmods.com/stardewvalley/mods/{m_id}"
                ),
            ).grid(row=1, column=0)

    def _install_clicked(self, mod_id: str) -> None:
        key = self._save_key()
        self.destroy()
        self._on_install_mod(mod_id, key)
