"""Profile sidebar component: profile list, create, import/export, and delete."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import customtkinter as ctk

from src.core.config import ProfileData
from src.ui.theme import COLORS, SPACING, font_title


class ProfileSidebar(ctk.CTkFrame):
    """Left sidebar for managing modpack profiles."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select: Callable[[str], None],
        on_create: Callable[[str], None],
        on_delete: Callable[[], None],
        on_import: Callable[[], None],
        on_export: Callable[[], None],
        on_duplicate: Callable[[], None],
    ) -> None:
        super().__init__(master, width=240, border_width=1, border_color=COLORS["border"])
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._on_select = on_select
        self._on_create = on_create
        self.profile_buttons: dict[str, ctk.CTkButton] = {}

        ctk.CTkLabel(self, text="Modpacks", font=font_title()).grid(
            row=0, column=0, padx=SPACING["lg"], pady=(SPACING["md"], SPACING["sm"]), sticky="w"
        )

        self.profile_list_frame = ctk.CTkScrollableFrame(self)
        self.profile_list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=SPACING["xs"])
        self.profile_list_frame.grid_columnconfigure(0, weight=1)

        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(SPACING["sm"], SPACING["xs"]))
        add_frame.grid_columnconfigure(0, weight=1)

        self.new_profile_entry = ctk.CTkEntry(add_frame, placeholder_text="New modpack...")
        self.new_profile_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["xs"]))
        self.new_profile_entry.bind("<Return>", lambda _e: self._submit_create())

        ctk.CTkButton(add_frame, text="+", width=36, command=self._submit_create).grid(
            row=0, column=1
        )

        io_frame = ctk.CTkFrame(self, fg_color="transparent")
        io_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=SPACING["xs"])
        io_frame.grid_columnconfigure(0, weight=1)
        io_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            io_frame,
            text="Import",
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=on_import,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        ctk.CTkButton(
            io_frame,
            text="Export",
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=on_export,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        ctk.CTkButton(
            io_frame,
            text="Duplicate",
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=on_duplicate,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACING["xs"], 0))

        self.delete_btn = ctk.CTkButton(
            self,
            text="Delete Active Modpack",
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=on_delete,
        )
        self.delete_btn.grid(
            row=4, column=0, sticky="ew", padx=8, pady=(SPACING["xs"], SPACING["md"])
        )

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
            btn = ctk.CTkButton(
                self.profile_list_frame,
                text=pdata.get("name", pid),
                anchor="w",
                fg_color=COLORS["accent"] if is_active else "transparent",
                hover_color=COLORS["accent_hover"] if is_active else COLORS["surface_alt"],
                text_color=("#FFFFFF", "#FFFFFF") if is_active else COLORS["text_primary"],
                command=lambda p=pid: self._on_select(p),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", pady=2)
            self.profile_buttons[pid] = btn

        can_delete = len(profiles) > 1
        self.delete_btn.configure(state="normal" if can_delete else "disabled")
