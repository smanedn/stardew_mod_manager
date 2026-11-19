"""Co-op modlist parity checker dialog."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable

import customtkinter as ctk

from src.core.coop_parity import CoopParityReport
from src.ui.theme import COLORS, SPACING, font_bold, font_small, font_title


class CoopParityDialog(ctk.CTkToplevel):
    """Displays missing, extra, and version-mismatched mods vs. a friend's modlist."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        report: CoopParityReport,
        on_sync_toggles: Callable[[CoopParityReport], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title(f"Co-op Parity Check — vs. {report.friend_profile}")
        self.geometry("700x540")
        self.minsize(560, 420)
        self.transient(master)
        self.grab_set()

        self._report = report
        self._on_sync_toggles = on_sync_toggles

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Summary Banner ---
        banner = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
        )
        banner.grid(
            row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"])
        )
        banner.grid_columnconfigure(0, weight=1)

        if report.is_in_sync:
            title = f"✔ In Sync with '{report.friend_profile}' ({report.matching_count} mods)"
            color = COLORS["success_text"]
        else:
            title = (
                f"⚠ Differences vs. '{report.friend_profile}': "
                f"{len(report.missing_mods)} missing, "
                f"{len(report.extra_mods)} extra, "
                f"{len(report.version_mismatches)} version mismatch(es)"
            )
            color = COLORS["warning_text"]

        ctk.CTkLabel(banner, text=title, font=font_title(), text_color=color, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"]
        )

        # --- Scrollable Diff Sections ---
        body = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["bg_app"], border_width=1, border_color=COLORS["border"]
        )
        body.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
        body.grid_columnconfigure(0, weight=1)

        row_idx = 0
        if report.is_in_sync:
            ctk.CTkLabel(
                body,
                text="All enabled mods and versions match your friend's modlist!",
                text_color=COLORS["success_text"],
            ).grid(row=0, column=0, padx=SPACING["md"], pady=32)
        else:
            if report.missing_mods:
                row_idx = self._add_section_header(
                    body,
                    row_idx,
                    f"Missing Mods ({len(report.missing_mods)})",
                    COLORS["error_text"],
                )
                for item in report.missing_mods:
                    card = ctk.CTkFrame(
                        body,
                        fg_color=COLORS["surface"],
                        border_width=1,
                        border_color=COLORS["border"],
                    )
                    card.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=3)
                    card.grid_columnconfigure(0, weight=1)
                    status = (
                        "Installed (disabled)"
                        if item.local_folder_if_installed
                        else "Not installed"
                    )
                    ctk.CTkLabel(
                        card,
                        text=f"{item.entry.name} (v{item.entry.version}) — {status}",
                        font=font_small(),
                        anchor="w",
                    ).grid(row=0, column=0, sticky="ew", padx=10, pady=6)
                    if item.entry.links:
                        ctk.CTkButton(
                            card,
                            text="Get Mod",
                            width=80,
                            height=24,
                            font=font_small(),
                            command=lambda u=item.entry.links[0]: webbrowser.open(u),
                        ).grid(row=0, column=1, padx=8, pady=6)
                    row_idx += 1

            if report.extra_mods:
                row_idx = self._add_section_header(
                    body,
                    row_idx,
                    f"Extra Local Mods ({len(report.extra_mods)} — disable for co-op)",
                    COLORS["warning_text"],
                )
                for mod in report.extra_mods:
                    card = ctk.CTkFrame(
                        body,
                        fg_color=COLORS["surface"],
                        border_width=1,
                        border_color=COLORS["border"],
                    )
                    card.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=3)
                    ctk.CTkLabel(
                        card,
                        text=f"{mod.name} (v{mod.version})  [{mod.folder_name}]",
                        font=font_small(),
                        anchor="w",
                    ).pack(fill="x", padx=10, pady=6)
                    row_idx += 1

            if report.version_mismatches:
                row_idx = self._add_section_header(
                    body,
                    row_idx,
                    f"Version Mismatches ({len(report.version_mismatches)})",
                    COLORS["warning_text"],
                )
                for mm in report.version_mismatches:
                    card = ctk.CTkFrame(
                        body,
                        fg_color=COLORS["surface"],
                        border_width=1,
                        border_color=COLORS["border"],
                    )
                    card.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=3)
                    mm_text = (
                        f"{mm.name}: local v{mm.local_version} vs. friend v{mm.friend_version}"
                    )
                    ctk.CTkLabel(
                        card,
                        text=mm_text,
                        font=font_small(),
                        anchor="w",
                    ).pack(fill="x", padx=10, pady=6)
                    row_idx += 1

        # --- Footer ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(
            row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["lg"])
        )
        footer.grid_columnconfigure(1, weight=1)

        can_sync = bool(
            self._on_sync_toggles
            and (report.extra_mods or any(m.local_folder_if_installed for m in report.missing_mods))
        )
        if can_sync:
            ctk.CTkButton(
                footer,
                text="Sync Local Toggles to Match",
                width=200,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                command=self._sync_toggles,
            ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(footer, text="Close", width=90, command=self.destroy).grid(
            row=0, column=2, sticky="e"
        )

    def _add_section_header(
        self, parent: ctk.CTkScrollableFrame, row_idx: int, text: str, color: tuple[str, str]
    ) -> int:
        ctk.CTkLabel(parent, text=text, font=font_bold(), text_color=color, anchor="w").grid(
            row=row_idx, column=0, sticky="ew", padx=8, pady=(10, 4)
        )
        return row_idx + 1

    def _sync_toggles(self) -> None:
        if self._on_sync_toggles is not None:
            self._on_sync_toggles(self._report)
        self.destroy()
