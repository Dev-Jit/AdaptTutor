from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from typing import Literal

Appearance = Literal["light", "dark"]


def detect_os_appearance() -> Appearance:
    """Windows 10/11: AppsUseLightTheme registry value. Else default to light."""
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            try:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if int(value) == 1 else "dark"
            finally:
                winreg.CloseKey(key)
        except OSError:
            pass
    return "light"


@dataclass(frozen=True, slots=True)
class UiTheme:
    appearance: Appearance
    window_bg: str
    fg: str
    fg_muted: str
    fg_soft: str
    border: str
    input_bg: str
    card_bg: str
    header_bg: str
    canvas_bg: str
    text_readonly_bg: str
    highlight: str
    select_bg: str
    select_fg: str
    thinking_fg: str
    launcher_bg: str
    launcher_hover: str
    menu_bg: str
    pill_border: str
    bubble_outer_bg: str
    bubble_panel_bg: str
    bubble_text_bg: str
    quiz_mcq: str
    quiz_open: str
    quiz_fill: str


LIGHT_THEME = UiTheme(
    appearance="light",
    window_bg="#FFFFFF",
    fg="#222222",
    fg_muted="#444444",
    fg_soft="#666666",
    border="#D0D0D0",
    input_bg="#FFFFFF",
    card_bg="#FAFAFA",
    header_bg="#F5F5F5",
    canvas_bg="#FFFFFF",
    text_readonly_bg="#FAFAFA",
    highlight="#6C63FF",
    select_bg="#C5CEFF",
    select_fg="#111111",
    thinking_fg="#5C57D9",
    launcher_bg="#6C63FF",
    launcher_hover="#7A72FF",
    menu_bg="#FFFFFF",
    pill_border="#EAEAF2",
    bubble_outer_bg="#F0F0F2",
    bubble_panel_bg="#FFFFFF",
    bubble_text_bg="#FAFAFA",
    quiz_mcq="#FFEBEE",
    quiz_open="#E3F2FD",
    quiz_fill="#FFF8E1",
)

DARK_THEME = UiTheme(
    appearance="dark",
    window_bg="#1E1E1E",
    fg="#E8E8E8",
    fg_muted="#B8B8B8",
    fg_soft="#909090",
    border="#3D3D3D",
    input_bg="#2D2D2D",
    card_bg="#252526",
    header_bg="#333333",
    canvas_bg="#1E1E1E",
    text_readonly_bg="#2A2D2E",
    highlight="#7A7AE8",
    select_bg="#264F78",
    select_fg="#FFFFFF",
    thinking_fg="#82AAFF",
    launcher_bg="#5C57D9",
    launcher_hover="#6B66E8",
    menu_bg="#1E1E1E",
    pill_border="#454545",
    bubble_outer_bg="#2A2A2A",
    bubble_panel_bg="#252526",
    bubble_text_bg="#2A2D2E",
    quiz_mcq="#4A2A2D",
    quiz_open="#1E3550",
    quiz_fill="#4A3F1E",
)


def load_ui_theme() -> UiTheme:
    return LIGHT_THEME if detect_os_appearance() == "light" else DARK_THEME


def apply_topmost(w: tk.Misc) -> None:
    try:
        w.attributes("-topmost", True)
    except tk.TclError:
        pass


def configure_ttk_notebook(master: tk.Misc, theme: UiTheme) -> None:
    from tkinter import ttk

    style = ttk.Style(master)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TNotebook", background=theme.window_bg, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=theme.card_bg,
        foreground=theme.fg,
        padding=[10, 5],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme.input_bg)],
        foreground=[("selected", theme.fg)],
    )


def style_entry(w: tk.Entry, theme: UiTheme) -> None:
    w.configure(
        bg=theme.input_bg,
        fg=theme.fg,
        insertbackground=theme.fg,
        highlightthickness=1,
        highlightbackground=theme.border,
        highlightcolor=theme.highlight,
    )


def style_text_editable(w: tk.Text, theme: UiTheme) -> None:
    w.configure(
        bg=theme.input_bg,
        fg=theme.fg,
        insertbackground=theme.fg,
        highlightthickness=1,
        highlightbackground=theme.border,
        highlightcolor=theme.highlight,
        selectbackground=theme.select_bg,
        selectforeground=theme.select_fg,
    )


def style_text_readonly(w: tk.Text, theme: UiTheme) -> None:
    # tk.Text does not support -disabledforeground on Windows; use fg + state disabled only.
    w.configure(
        bg=theme.text_readonly_bg,
        fg=theme.fg,
        highlightthickness=1,
        highlightbackground=theme.border,
        highlightcolor=theme.highlight,
        selectbackground=theme.select_bg,
        selectforeground=theme.select_fg,
    )


def style_button(w: tk.Button, theme: UiTheme) -> None:
    if theme.appearance == "dark":
        w.configure(
            bg=theme.input_bg,
            fg=theme.fg,
            activebackground=theme.card_bg,
            activeforeground=theme.fg,
            highlightthickness=0,
        )
