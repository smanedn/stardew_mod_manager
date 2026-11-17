"""Design tokens and typography helpers for SVMM UI."""

from __future__ import annotations

import customtkinter as ctk

# Semantic (light, dark) color pairs for automatic Light/Dark mode support
COLORS = {
    "surface": ("#F4F5F7", "#1E222A"),
    "surface_alt": ("#E8EBEF", "#262B35"),
    "border": ("#D1D5DB", "#363D4A"),
    "text_primary": ("#111827", "#F3F4F6"),
    "text_muted": ("#4B5563", "#9CA3AF"),
    "accent": ("#1D6FA5", "#1F6AA5"),
    "accent_hover": ("#155784", "#144870"),
    "success": ("#1E7E34", "#2B7A3D"),
    "success_hover": ("#19692C", "#35944B"),
    "danger": ("#B91C1C", "#8B2E2E"),
    "danger_hover": ("#991B1B", "#A83838"),
    "warning_text": ("#B45309", "#FBBF24"),
    "error_text": ("#DC2626", "#FC8181"),
    "success_text": ("#15803D", "#68D391"),
    "neutral_btn": ("#64748B", "#4A5568"),
    "neutral_btn_hover": ("#475569", "#5A677D"),
}

SPACING = {
    "xs": 4,
    "sm": 6,
    "md": 10,
    "lg": 12,
}


def font_title() -> ctk.CTkFont:
    return ctk.CTkFont(size=15, weight="bold")


def font_bold() -> ctk.CTkFont:
    return ctk.CTkFont(size=13, weight="bold")


def font_action() -> ctk.CTkFont:
    return ctk.CTkFont(size=14, weight="bold")


def font_small() -> ctk.CTkFont:
    return ctk.CTkFont(size=12)
