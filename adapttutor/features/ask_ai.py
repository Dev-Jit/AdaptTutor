from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
import tkinter as tk
from typing import Callable

from ..config import PANEL_MAX_HEIGHT, PANEL_PAD, PANEL_WIDTH
from ..theme import UiTheme, apply_topmost, style_button, style_entry
from ..tutor import ask_general

_USER_BUBBLE_BG = "#FF8C42"
_USER_BUBBLE_FG = "#FFFFFF"
_AI_BUBBLE_BG = "#EFEFEF"
_AI_BUBBLE_FG = "#222222"


def _get_windows_work_area() -> tuple[int, int, int, int] | None:
    try:
        SPI_GETWORKAREA = 0x0030

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        rect = RECT()
        ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        if not ok:
            return None
        return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
    except Exception:
        return None


class AskAiPanel:
    def __init__(
        self,
        *,
        root: tk.Tk,
        on_close: Callable[[], None],
        theme: UiTheme,
    ) -> None:
        self._on_close = on_close
        self._theme = theme
        self._placeholder = "Ask anything..."
        self._pending = False

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=theme.window_bg)

        header = tk.Frame(self.window, bg=theme.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))

        tk.Label(header, text="Ask AI", bg=theme.window_bg, fg=theme.fg, font=("Segoe UI", 11, "bold")).pack(side="left")
        close_lbl = tk.Label(header, text="✕", bg=theme.window_bg, fg=theme.fg, cursor="hand2", font=("Segoe UI", 12))
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self._on_close())

        body = tk.Frame(self.window, bg=theme.window_bg)
        body.pack(fill="both", expand=True, padx=PANEL_PAD, pady=(0, PANEL_PAD))

        history_wrap = tk.Frame(body, bg=theme.window_bg)
        history_wrap.pack(fill="both", expand=True)
        self._history_scroll = tk.Scrollbar(history_wrap)
        self._history_scroll.pack(side="right", fill="y")
        self._history_canvas = tk.Canvas(
            history_wrap,
            bg=theme.canvas_bg,
            highlightthickness=1,
            highlightbackground=theme.border,
            yscrollcommand=self._history_scroll.set,
        )
        self._history_canvas.pack(side="left", fill="both", expand=True)
        self._history_scroll.config(command=self._history_canvas.yview)

        self._history_inner = tk.Frame(self._history_canvas, bg=theme.window_bg)
        self._history_win = self._history_canvas.create_window((0, 0), window=self._history_inner, anchor="nw")

        def _on_history_config(_e: tk.Event) -> None:
            self._history_canvas.configure(scrollregion=self._history_canvas.bbox("all"))
            self._history_canvas.itemconfig(self._history_win, width=max(1, self._history_canvas.winfo_width()))

        self._history_inner.bind("<Configure>", _on_history_config)
        self._history_canvas.bind("<Configure>", _on_history_config)

        input_row = tk.Frame(body, bg=theme.window_bg)
        input_row.pack(fill="x", pady=(8, 0))
        self._input = tk.Entry(input_row, font=("Segoe UI", 10))
        self._input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        style_entry(self._input, theme)
        self._input.bind("<Return>", self._on_send_enter)
        self._input.bind("<FocusIn>", self._on_focus_in)
        self._input.bind("<FocusOut>", self._on_focus_out)
        self._set_placeholder()

        self._send_btn = tk.Button(input_row, text="Send", font=("Segoe UI", 9), command=self._on_send)
        self._send_btn.pack(side="right")
        style_button(self._send_btn, theme)

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")

    def _set_placeholder(self) -> None:
        if self._input.get().strip():
            return
        self._input.delete(0, "end")
        self._input.insert(0, self._placeholder)
        self._input.configure(fg=self._theme.fg_soft)

    def _on_focus_in(self, _e: tk.Event) -> None:
        if self._input.get().strip() == self._placeholder:
            self._input.delete(0, "end")
            self._input.configure(fg=self._theme.fg)

    def _on_focus_out(self, _e: tk.Event) -> None:
        if not self._input.get().strip():
            self._set_placeholder()

    def _on_send_enter(self, _e: tk.Event) -> str:
        self._on_send()
        return "break"

    def _scroll_to_latest(self) -> None:
        self._history_canvas.update_idletasks()
        self._history_canvas.configure(scrollregion=self._history_canvas.bbox("all"))
        self._history_canvas.yview_moveto(1.0)

    def _add_message(self, text: str, *, is_user: bool) -> None:
        if not text.strip():
            return
        row = tk.Frame(self._history_inner, bg=self._theme.window_bg)
        row.pack(fill="x", pady=4)

        bg = _USER_BUBBLE_BG if is_user else _AI_BUBBLE_BG
        fg = _USER_BUBBLE_FG if is_user else _AI_BUBBLE_FG
        anchor = "e" if is_user else "w"
        side = "right" if is_user else "left"

        tk.Label(
            row,
            text=text.strip(),
            bg=bg,
            fg=fg,
            font=("Segoe UI", 9),
            wraplength=PANEL_WIDTH - 120,
            justify="left",
            padx=10,
            pady=8,
        ).pack(side=side, anchor=anchor)
        self._scroll_to_latest()

    def _set_pending(self, pending: bool) -> None:
        self._pending = pending
        self._send_btn.configure(state="disabled" if pending else "normal")

    def _on_send(self) -> None:
        if self._pending:
            return
        raw = self._input.get().strip()
        if not raw or raw == self._placeholder:
            return

        self._add_message(raw, is_user=True)
        self._input.delete(0, "end")
        self._set_placeholder()
        self._set_pending(True)

        def worker(question: str) -> None:
            try:
                answer = ask_general(question)
            except BaseException as err:
                answer = f"Error: {err}"

            def apply() -> None:
                self._add_message(answer or "(no response)", is_user=False)
                self._set_pending(False)

            try:
                self.window.after(0, apply)
            except tk.TclError:
                pass

        threading.Thread(target=worker, args=(raw,), daemon=True).start()

    def reposition_to_launcher(self, launcher: tk.Toplevel) -> None:
        self.window.update_idletasks()
        launcher.update_idletasks()
        work = _get_windows_work_area()
        if work:
            _left, _top, right, bottom = work
        else:
            right = self.window.winfo_screenwidth()
            bottom = self.window.winfo_screenheight()

        margin = 18
        w = PANEL_WIDTH
        h = PANEL_MAX_HEIGHT
        x = right - w - margin
        y = bottom - h - margin
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def destroy(self) -> None:
        try:
            self.window.destroy()
        except Exception:
            pass
