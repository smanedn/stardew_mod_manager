"""Modal dialog displaying mod manifest details and safe uninstall action."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from src.core.mod_config import get_mod_config_path
from src.core.mod_scanner import ModInfo
from src.ui.mod_config_dialog import ModConfigDialog
from src.ui.theme import COLORS, SPACING, font_bold, font_small, font_title


class ModDetailsDialog(ctk.CTkToplevel):
    """Displays manifest metadata for a mod and allows uninstalling it."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        mod: ModInfo,
        on_open_folder: Callable[[Path], None],
        on_uninstall: Callable[[ModInfo], None],
    ) -> None:
        super().__init__(master)
        self.title(f"Mod Details — {mod.name}")
        self.geometry("560x480")
        self.minsize(480, 400)
        self.transient(master)
        self.grab_set()

        self._mod = mod
        self._on_uninstall = on_uninstall

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header = ctk.CTkFrame(self, border_width=1, border_color=COLORS["border"])
        header.grid(
            row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"])
        )
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=f"{mod.name}  (v{mod.version})", font=font_title(), anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["md"], 2))
        author_text = f"by {mod.author}" if mod.author else "Author: Unknown"
        ctk.CTkLabel(
            header, text=author_text, font=font_small(), text_color=COLORS["text_muted"], anchor="w"
        ).grid(row=1, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))

        # --- Scrollable Metadata ---
        body = ctk.CTkScrollableFrame(self, border_width=1, border_color=COLORS["border"])
        body.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
        body.grid_columnconfigure(1, weight=1)

        rows: list[tuple[str, str]] = [
            ("Folder:", mod.folder_name),
            ("UniqueID:", mod.unique_id or "Not specified"),
            ("Min SMAPI:", mod.minimum_api_version or "Not specified"),
            ("Description:", mod.description or "No description provided."),
            (
                "Dependencies:",
                "\n".join(
                    f"{d.unique_id} ({'required' if d.is_required else 'optional'}"
                    f"{f', >= {d.minimum_version}' if d.minimum_version else ''})"
                    for d in mod.dependencies
                )
                or "None",
            ),
            ("UpdateKeys:", ", ".join(mod.update_keys) if mod.update_keys else "None"),
        ]
        if mod.error:
            rows.append(("Manifest Error:", mod.error))

        for idx, (label, value) in enumerate(rows):
            ctk.CTkLabel(body, text=label, font=font_bold(), anchor="nw").grid(
                row=idx, column=0, sticky="nw", padx=(SPACING["md"], SPACING["sm"]), pady=6
            )
            color = COLORS["warning_text"] if label == "Manifest Error:" else COLORS["text_primary"]
            ctk.CTkLabel(
                body,
                text=value,
                font=font_small(),
                text_color=color,
                anchor="nw",
                wraplength=360,
                justify="left",
            ).grid(row=idx, column=1, sticky="ew", padx=(0, SPACING["md"]), pady=6)

        # --- Footer Actions ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["lg"])
        )
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="Uninstall Mod",
            width=116,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=self._confirm_uninstall,
        ).grid(row=0, column=0, sticky="w")

        has_config = get_mod_config_path(mod.path).is_file()
        ctk.CTkButton(
            footer,
            text="Edit Config",
            width=104,
            state="normal" if has_config else "disabled",
            command=self._open_config_editor,
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Open Folder",
            width=104,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            command=lambda: on_open_folder(mod.path),
        ).grid(row=0, column=2, sticky="e", padx=(0, 8))

        ctk.CTkButton(footer, text="Close", width=80, command=self.destroy).grid(row=0, column=3)

    def _open_config_editor(self) -> None:
        ModConfigDialog(self, mod_name=self._mod.name, mod_path=self._mod.path)

    def _confirm_uninstall(self) -> None:
        confirmed = messagebox.askyesno(
            "Uninstall Mod",
            f"Permanently delete '{self._mod.name}' ({self._mod.folder_name}) "
            "from this modpack?\n\nThis cannot be undone.",
            parent=self,
        )
        if not confirmed:
            return
        mod = self._mod
        self.destroy()
        self._on_uninstall(mod)
