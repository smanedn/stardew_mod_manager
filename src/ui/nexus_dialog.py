"""In-app Nexus Mods browser with mod icons, pagination (10-100), and 1-click install."""

from __future__ import annotations

import io
import threading
import urllib.error
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from src.core.nexus_browser import (
    BrowseSort,
    NexusModSummary,
    browse_nexus_mods,
    fetch_nexus_thumbnail,
    search_nexus_mods,
)
from src.core.nexus_installer import NexusForbiddenError, install_from_nexus
from src.ui.theme import COLORS, SPACING, font_bold, font_small, font_title


class NexusBrowserDialog(ctk.CTkToplevel):
    """Browse, search, and install Stardew Valley mods directly from Nexus Mods."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_api_key: str,
        modpack_dir: Path,
        on_save_api_key: Callable[[str], None],
        on_installed: Callable[[list[str]], None],
    ) -> None:
        super().__init__(master)
        self.title("Browse Nexus Mods — Stardew Valley")
        self.geometry("860x640")
        self.minsize(700, 500)
        self.transient(master)
        self.grab_set()

        self._modpack_dir = modpack_dir
        self._on_save_api_key = on_save_api_key
        self._on_installed = on_installed
        self._request_gen = 0
        self._page = 1
        self._per_page = 25
        self._mode: str = "browse"  # "browse" or "search"
        self._sort_by: BrowseSort = "endorsements"
        self._search_query = ""
        self._last_count = 0
        self._icon_cache: dict[str, ctk.CTkImage] = {}
        self._icon_labels: dict[str, ctk.CTkLabel] = {}
        self._install_buttons: dict[str, ctk.CTkButton] = {}

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
            placeholder_text=(
                "Paste your Nexus Mods Personal API Key (required for 1-click Install)..."
            ),
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
        self.search_entry.bind("<Return>", lambda _e: self._start_search())

        ctk.CTkButton(header, text="Search", width=84, command=self._start_search).grid(
            row=1, column=2, padx=(0, SPACING["md"]), pady=(4, SPACING["md"])
        )

        # --- Category Tabs & Per-Page Selector ---
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["xs"])
        tabs.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(
            tabs,
            text="Popular",
            width=96,
            command=lambda: self._start_browse("endorsements"),
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(
            tabs,
            text="Latest Updated",
            width=120,
            command=lambda: self._start_browse("updatedAt"),
        ).grid(row=0, column=1, padx=6)
        ctk.CTkButton(
            tabs,
            text="New Mods",
            width=100,
            command=lambda: self._start_browse("createdAt"),
        ).grid(row=0, column=2, padx=6)

        self.status_label = ctk.CTkLabel(
            tabs, text="", font=font_small(), text_color=COLORS["text_muted"]
        )
        self.status_label.grid(row=0, column=3, padx=SPACING["md"], sticky="w")

        ctk.CTkLabel(tabs, text="Per page:", font=font_small()).grid(row=0, column=4, padx=(0, 4))
        self.per_page_menu = ctk.CTkOptionMenu(
            tabs,
            values=["10", "25", "50", "100"],
            width=74,
            command=self._on_per_page_changed,
        )
        self.per_page_menu.set("25")
        self.per_page_menu.grid(row=0, column=5)

        # --- Scrollable Results ---
        self.results_frame = ctk.CTkScrollableFrame(
            self, border_width=1, border_color=COLORS["border"]
        )
        self.results_frame.grid(
            row=2, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"]
        )
        self.results_frame.grid_columnconfigure(0, weight=1)

        # --- Pagination Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"])
        )
        footer.grid_columnconfigure(1, weight=1)

        self.prev_btn = ctk.CTkButton(
            footer, text="◀ Prev", width=90, state="disabled", command=self._prev_page
        )
        self.prev_btn.grid(row=0, column=0, sticky="w")

        self.page_label = ctk.CTkLabel(
            footer, text="Page 1", font=font_small(), text_color=COLORS["text_muted"]
        )
        self.page_label.grid(row=0, column=1)

        self.next_btn = ctk.CTkButton(
            footer, text="Next ▶", width=90, state="disabled", command=self._next_page
        )
        self.next_btn.grid(row=0, column=2, sticky="e")

        self.after(80, lambda: self._start_browse("endorsements"))

    def _save_key(self) -> str:
        key = self.key_var.get().strip()
        self._on_save_api_key(key)
        return key

    def _clear_results(self) -> None:
        self._icon_labels.clear()
        self._install_buttons.clear()
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def _show_message(self, text: str, is_error: bool = False) -> None:
        self._clear_results()
        color = COLORS["error_text"] if is_error else COLORS["text_muted"]
        ctk.CTkLabel(
            self.results_frame, text=text, text_color=color, wraplength=720, justify="center"
        ).grid(row=0, column=0, padx=SPACING["lg"], pady=32)

    def _on_per_page_changed(self, value: str) -> None:
        self._per_page = int(value)
        self._page = 1
        self._fetch_current_page()

    def _prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._fetch_current_page()

    def _next_page(self) -> None:
        if self._last_count >= self._per_page:
            self._page += 1
            self._fetch_current_page()

    def _start_browse(self, sort_by: BrowseSort) -> None:
        self._mode = "browse"
        self._sort_by = sort_by
        self._page = 1
        self._fetch_current_page()

    def _start_search(self) -> None:
        query = self.search_entry.get().strip()
        if not query:
            self.status_label.configure(
                text="Enter a search term.", text_color=COLORS["warning_text"]
            )
            return
        self._mode = "search"
        self._search_query = query
        self._page = 1
        self._fetch_current_page()

    def _fetch_current_page(self) -> None:
        self._request_gen += 1
        gen = self._request_gen
        offset = (self._page - 1) * self._per_page
        count = self._per_page

        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.page_label.configure(text=f"Page {self._page}")
        self.status_label.configure(text="Loading...", text_color=COLORS["text_muted"])
        self._show_message("Loading mods from Nexus Mods...")

        mode = self._mode
        sort_by = self._sort_by
        query = self._search_query

        def worker() -> None:
            try:
                if mode == "search":
                    mods = search_nexus_mods(query, count=count, offset=offset)
                else:
                    mods = browse_nexus_mods(sort_by=sort_by, count=count, offset=offset)
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

        self._last_count = len(mods)
        self.prev_btn.configure(state="normal" if self._page > 1 else "disabled")
        self.next_btn.configure(state="normal" if len(mods) >= self._per_page else "disabled")
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
            card.grid_columnconfigure(1, weight=1)

            # --- Mod Icon (64x64) ---
            cached_img = self._icon_cache.get(mod.mod_id)
            icon_lbl = ctk.CTkLabel(
                card,
                text="" if cached_img else "MOD",
                image=cached_img,
                width=64,
                height=64,
                fg_color=COLORS["surface"],
                corner_radius=6,
                font=font_small(),
                text_color=COLORS["text_muted"],
            )
            icon_lbl.grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=10, sticky="n")
            self._icon_labels[mod.mod_id] = icon_lbl
            if not cached_img and mod.picture_url:
                self._load_icon_async(gen, mod.mod_id, mod.picture_url)

            # --- Mod Details ---
            title_text = f"{mod.name}  (v{mod.version})"
            ctk.CTkLabel(card, text=title_text, font=font_title(), anchor="w").grid(
                row=0, column=1, sticky="ew", padx=4, pady=(8, 2)
            )
            meta_text = f"by {mod.author}  •  ★ {mod.endorsements:,}  •  ID: {mod.mod_id}"
            ctk.CTkLabel(
                card, text=meta_text, font=font_small(), text_color=COLORS["text_muted"], anchor="w"
            ).grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 2))

            if mod.summary:
                ctk.CTkLabel(
                    card,
                    text=mod.summary,
                    font=font_small(),
                    anchor="w",
                    wraplength=500,
                    justify="left",
                ).grid(row=2, column=1, sticky="ew", padx=4, pady=(0, 8))

            # --- Action Buttons ---
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=0, column=2, rowspan=3, padx=10, pady=10, sticky="e")

            inst_btn = ctk.CTkButton(
                actions,
                text="Install",
                width=96,
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                command=lambda m_id=mod.mod_id, m_name=mod.name: self._install_clicked(
                    m_id, m_name
                ),
            )
            inst_btn.grid(row=0, column=0, pady=(0, 4))
            self._install_buttons[mod.mod_id] = inst_btn

            ctk.CTkButton(
                actions,
                text="Open Page",
                width=96,
                fg_color=COLORS["neutral_btn"],
                hover_color=COLORS["neutral_btn_hover"],
                command=lambda m_id=mod.mod_id: webbrowser.open(
                    f"https://www.nexusmods.com/stardewvalley/mods/{m_id}?tab=files"
                ),
            ).grid(row=1, column=0)

    def _load_icon_async(self, gen: int, mod_id: str, url: str) -> None:
        def worker() -> None:
            raw = fetch_nexus_thumbnail(url)
            if raw is None:
                return
            try:
                pil_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                pil_img.thumbnail((64, 64))
                size = pil_img.size
            except OSError:
                return
            self.after(0, lambda: self._apply_icon(gen, mod_id, pil_img, size))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_icon(
        self, gen: int, mod_id: str, pil_img: Image.Image, size: tuple[int, int]
    ) -> None:
        if gen != self._request_gen or not self.winfo_exists():
            return
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        self._icon_cache[mod_id] = ctk_img
        lbl = self._icon_labels.get(mod_id)
        if lbl and lbl.winfo_exists():
            lbl.configure(image=ctk_img, text="")

    def _install_clicked(self, mod_id: str, mod_name: str) -> None:
        key = self._save_key()
        if not key:
            messagebox.showwarning(
                "API Key Required",
                "Paste your Nexus Mods Personal API Key at the top first to install mods.",
                parent=self,
            )
            self.key_entry.focus_set()
            return

        btn = self._install_buttons.get(mod_id)
        if btn and btn.winfo_exists():
            btn.configure(state="disabled", text="Installing...")
        self.status_label.configure(
            text=f"Installing {mod_name}...", text_color=COLORS["text_muted"]
        )

        def worker() -> None:
            try:
                installed = install_from_nexus(mod_id, key, self._modpack_dir)
                err: Exception | None = None
            except Exception as exc:  # noqa: BLE001
                installed = []
                err = exc
            self.after(0, lambda: self._on_install_done(mod_id, mod_name, installed, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_done(
        self, mod_id: str, mod_name: str, installed: list[str], err: Exception | None
    ) -> None:
        if not self.winfo_exists():
            return
        btn = self._install_buttons.get(mod_id)

        if err is None:
            if btn and btn.winfo_exists():
                btn.configure(state="disabled", text="Installed ✓")
            self.status_label.configure(
                text=f"Installed {', '.join(installed)}!", text_color=COLORS["success_text"]
            )
            self._on_installed(installed)
            return

        if btn and btn.winfo_exists():
            btn.configure(state="normal", text="Install")
        self.status_label.configure(text="Install failed", text_color=COLORS["error_text"])

        if isinstance(err, NexusForbiddenError):
            open_page = messagebox.askyesno(
                "Nexus Premium Required for 1-Click",
                f"{err}\n\nOpen '{mod_name}' Files page in your browser to download manually?",
                parent=self,
            )
            if open_page:
                webbrowser.open(f"https://www.nexusmods.com/stardewvalley/mods/{mod_id}?tab=files")
        else:
            messagebox.showerror("Install Failed", str(err), parent=self)
