"""Cohesive design tokens, theme presets, custom theme builder, and typography helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import customtkinter as ctk

ColorPair = tuple[str, str]
Palette = dict[str, ColorPair]


@dataclass(frozen=True)
class ThemeDefinition:
    """Named UI theme with appearance mode and semantic color palette."""

    name: str
    mode: Literal["dark", "light"]
    palette: Palette


DEFAULT_CUSTOM_THEME: dict[str, str] = {
    "mode": "dark",
    "bg_app": "#11141A",
    "bg_sidebar": "#161A22",
    "surface": "#1B2029",
    "accent": "#2563EB",
    "success": "#16A34A",
    "text_primary": "#F1F5F9",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        return (30, 30, 30)
    try:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    except ValueError:
        return (30, 30, 30)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, c)) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _mix(hex_a: str, hex_b: str, weight_b: float) -> str:
    r1, g1, b1 = _hex_to_rgb(hex_a)
    r2, g2, b2 = _hex_to_rgb(hex_b)
    w = max(0.0, min(1.0, weight_b))
    return _rgb_to_hex(
        (
            round(r1 * (1 - w) + r2 * w),
            round(g1 * (1 - w) + g2 * w),
            round(b1 * (1 - w) + b2 * w),
        )
    )


def _is_valid_hex(value: str) -> bool:
    clean = value.strip()
    if len(clean) != 7 or not clean.startswith("#"):
        return False
    try:
        int(clean[1:], 16)
        return True
    except ValueError:
        return False


def build_palette(
    *,
    mode: Literal["dark", "light"],
    bg_app: str,
    bg_sidebar: str,
    surface: str,
    accent: str,
    success: str,
    text_primary: str,
    surface_alt: str | None = None,
    surface_hover: str | None = None,
    border: str | None = None,
    text_muted: str | None = None,
    accent_hover: str | None = None,
    accent_soft: str | None = None,
    success_hover: str | None = None,
    neutral_btn: str | None = None,
    neutral_btn_hover: str | None = None,
    neutral_btn_text: str | None = None,
) -> Palette:
    """Construct a complete semantic palette from core theme colors."""
    is_dark = mode == "dark"
    mix_target = "#FFFFFF" if is_dark else "#000000"

    s_alt = surface_alt or _mix(surface, mix_target, 0.05 if is_dark else 0.03)
    s_hover = surface_hover or _mix(surface, mix_target, 0.10 if is_dark else 0.06)
    bdr = border or _mix(surface, mix_target, 0.16 if is_dark else 0.18)
    t_muted = text_muted or _mix(text_primary, bg_app, 0.42)
    a_hover = accent_hover or _mix(accent, "#000000", 0.16)
    a_soft = accent_soft or _mix(surface, accent, 0.28)
    suc_hover = success_hover or _mix(success, "#000000", 0.16)
    n_btn = neutral_btn or _mix(surface, mix_target, 0.10 if is_dark else 0.10)
    n_btn_hover = neutral_btn_hover or _mix(surface, mix_target, 0.18 if is_dark else 0.18)
    n_btn_text = neutral_btn_text or text_primary

    def pair(val: str) -> ColorPair:
        return (val, val)

    return {
        "bg_app": pair(bg_app),
        "bg_sidebar": pair(bg_sidebar),
        "surface": pair(surface),
        "surface_alt": pair(s_alt),
        "surface_hover": pair(s_hover),
        "border": pair(bdr),
        "text_primary": pair(text_primary),
        "text_muted": pair(t_muted),
        "accent": pair(accent),
        "accent_hover": pair(a_hover),
        "accent_soft": pair(a_soft),
        "success": pair(success),
        "success_hover": pair(suc_hover),
        "danger": pair("#DC2626" if not is_dark else "#991B1B"),
        "danger_hover": pair("#B91C1C"),
        "warning_text": pair("#B45309" if not is_dark else "#FBBF24"),
        "warning_bg": pair("#FEF3C7" if not is_dark else "#3B2F13"),
        "error_text": pair("#DC2626" if not is_dark else "#F87171"),
        "success_text": pair("#15803D" if not is_dark else "#4ADE80"),
        "neutral_btn": pair(n_btn),
        "neutral_btn_hover": pair(n_btn_hover),
        "neutral_btn_text": pair(n_btn_text),
    }


THEMES: dict[str, ThemeDefinition] = {
    "Midnight": ThemeDefinition(
        name="Midnight",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#11141A",
            bg_sidebar="#161A22",
            surface="#1B2029",
            surface_alt="#222834",
            surface_hover="#2A3140",
            border="#2D3545",
            text_primary="#F1F5F9",
            text_muted="#94A3B8",
            accent="#2563EB",
            accent_hover="#1D4ED8",
            accent_soft="#1E3A5F",
            success="#16A34A",
            success_hover="#15803D",
            neutral_btn="#272E3B",
            neutral_btn_hover="#333C4D",
            neutral_btn_text="#E2E8F0",
        ),
    ),
    "Daylight": ThemeDefinition(
        name="Daylight",
        mode="light",
        palette=build_palette(
            mode="light",
            bg_app="#F1F5F9",
            bg_sidebar="#E8EDF4",
            surface="#FFFFFF",
            surface_alt="#F8FAFC",
            surface_hover="#EFF4FA",
            border="#CBD5E1",
            text_primary="#0F172A",
            text_muted="#64748B",
            accent="#2563EB",
            accent_hover="#1D4ED8",
            accent_soft="#DBEAFE",
            success="#16A34A",
            success_hover="#15803D",
            neutral_btn="#E2E8F0",
            neutral_btn_hover="#CBD5E1",
            neutral_btn_text="#1E293B",
        ),
    ),
    "Pelican Town": ThemeDefinition(
        name="Pelican Town",
        mode="light",
        palette=build_palette(
            mode="light",
            bg_app="#F5EFE0",
            bg_sidebar="#EAE0C8",
            surface="#FFFDF7",
            surface_alt="#F7F1E3",
            surface_hover="#EFE6D0",
            border="#D6C7A9",
            text_primary="#2C2218",
            text_muted="#6E5D4B",
            accent="#3E7B27",
            accent_hover="#2F611C",
            accent_soft="#DCECD4",
            success="#2E7D32",
            success_hover="#1B5E20",
            neutral_btn="#E5D8BC",
            neutral_btn_hover="#D6C6A3",
            neutral_btn_text="#2C2218",
        ),
    ),
    "Junimo Forest": ThemeDefinition(
        name="Junimo Forest",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#0F1914",
            bg_sidebar="#14231B",
            surface="#1A2D23",
            border="#274334",
            text_primary="#ECFDF5",
            accent="#22C55E",
            success="#16A34A",
        ),
    ),
    "Stardrop": ThemeDefinition(
        name="Stardrop",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#161124",
            bg_sidebar="#1D1630",
            surface="#241C3B",
            border="#3A2D5C",
            text_primary="#F5F3FF",
            accent="#A855F7",
            success="#22C55E",
        ),
    ),
    "Ginger Island": ThemeDefinition(
        name="Ginger Island",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#0D1B21",
            bg_sidebar="#11242C",
            surface="#17303A",
            border="#244856",
            text_primary="#ECFEFF",
            accent="#06B6D4",
            success="#10B981",
        ),
    ),
    "Skull Cavern": ThemeDefinition(
        name="Skull Cavern",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#131115",
            bg_sidebar="#1A171D",
            surface="#231F28",
            border="#393242",
            text_primary="#FAF5FF",
            accent="#F97316",
            success="#22C55E",
        ),
    ),
    "Nordic Frost": ThemeDefinition(
        name="Nordic Frost",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#1A1F29",
            bg_sidebar="#202734",
            surface="#273040",
            border="#384459",
            text_primary="#F0F9FF",
            accent="#38BDF8",
            success="#34D399",
        ),
    ),
    "Rose Quartz": ThemeDefinition(
        name="Rose Quartz",
        mode="dark",
        palette=build_palette(
            mode="dark",
            bg_app="#1C131A",
            bg_sidebar="#251922",
            surface="#2F202B",
            border="#493142",
            text_primary="#FDF2F8",
            accent="#EC4899",
            success="#34D399",
        ),
    ),
    "Honeywood": ThemeDefinition(
        name="Honeywood",
        mode="light",
        palette=build_palette(
            mode="light",
            bg_app="#FDF6E9",
            bg_sidebar="#F4E9D2",
            surface="#FFFFFF",
            border="#E2D3B3",
            text_primary="#2D2114",
            accent="#D97706",
            success="#15803D",
        ),
    ),
}

THEME_NAMES: list[str] = [*THEMES.keys(), "Custom"]

# Mutable global color map read by UI widgets. Updated in-place by apply_theme().
COLORS: Palette = dict(THEMES["Midnight"].palette)

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
}


def sanitize_custom_theme(raw: dict[str, Any] | None) -> dict[str, str]:
    """Normalize a custom theme dictionary, filling any invalid fields from defaults."""
    clean = dict(DEFAULT_CUSTOM_THEME)
    if not isinstance(raw, dict):
        return clean

    mode = str(raw.get("mode", "")).lower()
    if mode in ("dark", "light"):
        clean["mode"] = mode

    for key in ("bg_app", "bg_sidebar", "surface", "accent", "success", "text_primary"):
        val = raw.get(key)
        if isinstance(val, str) and _is_valid_hex(val):
            clean[key] = val.strip().upper()
    return clean


def resolve_theme(theme_name: str, custom_theme: dict[str, Any] | None = None) -> ThemeDefinition:
    """Resolve a built-in or custom theme definition."""
    if theme_name == "Custom":
        cfg = sanitize_custom_theme(custom_theme)
        mode: Literal["dark", "light"] = "light" if cfg["mode"] == "light" else "dark"
        return ThemeDefinition(
            name="Custom",
            mode=mode,
            palette=build_palette(
                mode=mode,
                bg_app=cfg["bg_app"],
                bg_sidebar=cfg["bg_sidebar"],
                surface=cfg["surface"],
                accent=cfg["accent"],
                success=cfg["success"],
                text_primary=cfg["text_primary"],
            ),
        )
    return THEMES.get(theme_name, THEMES["Midnight"])


def apply_theme(theme_name: str, custom_theme: dict[str, Any] | None = None) -> str:
    """Apply a theme in-place to COLORS and CustomTkinter appearance mode."""
    resolved = resolve_theme(theme_name, custom_theme)
    COLORS.clear()
    COLORS.update(resolved.palette)
    ctk.set_appearance_mode(resolved.mode)
    return resolved.name


def font_header() -> ctk.CTkFont:
    return ctk.CTkFont(size=18, weight="bold")


def font_title() -> ctk.CTkFont:
    return ctk.CTkFont(size=14, weight="bold")


def font_bold() -> ctk.CTkFont:
    return ctk.CTkFont(size=13, weight="bold")


def font_body() -> ctk.CTkFont:
    return ctk.CTkFont(size=13)


def font_action() -> ctk.CTkFont:
    return ctk.CTkFont(size=13, weight="bold")


def font_small() -> ctk.CTkFont:
    return ctk.CTkFont(size=11)
