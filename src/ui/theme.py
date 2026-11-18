"""Cohesive design tokens and typography helpers for SVMM UI."""

from __future__ import annotations

import customtkinter as ctk

# Semantic (light, dark) color pairs for crisp Light and Dark modes
COLORS = {
    "bg_app": ("#F1F5F9", "#11141A"),
    "bg_sidebar": ("#E8EDF4", "#161A22"),
    "surface": ("#FFFFFF", "#1B2029"),
    "surface_alt": ("#F8FAFC", "#222834"),
    "surface_hover": ("#EFF4FA", "#2A3140"),
    "border": ("#CBD5E1", "#2D3545"),
    "text_primary": ("#0F172A", "#F1F5F9"),
    "text_muted": ("#64748B", "#94A3B8"),
    "accent": ("#2563EB", "#2563EB"),
    "accent_hover": ("#1D4ED8", "#1D4ED8"),
    "accent_soft": ("#DBEAFE", "#1E3A5F"),
    "success": ("#16A34A", "#16A34A"),
    "success_hover": ("#15803D", "#15803D"),
    "danger": ("#DC2626", "#991B1B"),
    "danger_hover": ("#B91C1C", "#B91C1C"),
    "warning_text": ("#B45309", "#FBBF24"),
    "warning_bg": ("#FEF3C7", "#3B2F13"),
    "error_text": ("#DC2626", "#F87171"),
    "success_text": ("#15803D", "#4ADE80"),
    "neutral_btn": ("#E2E8F0", "#272E3B"),
    "neutral_btn_hover": ("#CBD5E1", "#333C4D"),
    "neutral_btn_text": ("#1E293B", "#E2E8F0"),
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
}


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
