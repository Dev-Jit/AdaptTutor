from __future__ import annotations

import ctypes
import re
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from ..config import PANEL_MAX_HEIGHT, PANEL_PAD, PANEL_WIDTH
from ..pdf_reader import extract_window
from ..theme import (
    UiTheme,
    apply_topmost,
    configure_ttk_notebook,
    style_button,
    style_entry,
    style_text_editable,
    style_text_readonly,
)
from ..tutor import ask
from ..watcher import WatcherState

# PRD — Smart Summary prompt
SMART_SUMMARY_INSTRUCTIONS = """Summarise the following study material for a student preparing for an exam.

Return your response in this exact structure:

TLDR: (3 sentences maximum — the absolute core of what this content says)

KEY POINTS:
- (most important idea)
- (second most important idea)
- ... (4-6 points total)

KEY TERMS:
- Term: simple one-sentence definition
- ... (2-3 terms)

Be concise. Every word should earn its place.

Content:
{content}"""

SYSTEM_PROMPT = (
    "You are AdaptTutor. Follow the requested section headings and formatting exactly. "
    "Use the labels TLDR:, KEY POINTS:, and KEY TERMS: as specified."
)


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


def parse_summary_response(raw: str) -> tuple[str, str, str]:
    """Split model output into TL;DR body, Key Points block, Key Terms block."""
    raw = (raw or "").strip()
    if not raw:
        return "", "", ""

    key_terms = ""
    rest = raw
    m_kt = re.search(r"(?i)\nKEY TERMS:\s*", raw)
    if m_kt:
        rest = raw[: m_kt.start()].strip()
        key_terms = raw[m_kt.end() :].strip()

    tldr_block = rest
    key_points = ""
    m_kp = re.search(r"(?i)\nKEY POINTS:\s*", rest)
    if m_kp:
        tldr_block = rest[: m_kp.start()].strip()
        key_points = rest[m_kp.end() :].strip()

    tldr = re.sub(r"(?is)^\s*TLDR\s*:\s*", "", tldr_block)
    tldr = re.sub(r"(?is)^\s*TL;DR\s*:\s*", "", tldr).strip()

    return tldr, key_points, key_terms


class SmartSummaryPanel:
    """Smart Summary: Current Page vs Paste Text, Generate, structured output, Copy."""

    def __init__(
        self,
        *,
        root: tk.Tk,
        ui_root: tk.Misc,
        get_watcher_state: Callable[[], WatcherState],
        on_close: Callable[[], None],
        theme: UiTheme,
    ) -> None:
        self._on_close = on_close
        self._get_watcher_state = get_watcher_state
        self._ui_root = ui_root
        self._theme = theme
        t = theme

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=t.window_bg)

        header = tk.Frame(self.window, bg=t.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))

        tk.Label(header, text="Smart Summary", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 11, "bold")).pack(side="left")
        close_lbl = tk.Label(header, text="✕", bg=t.window_bg, fg=t.fg, cursor="hand2", font=("Segoe UI", 12))
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self._on_close())

        outer = tk.Frame(self.window, bg=t.window_bg)
        outer.pack(fill="both", expand=True, padx=PANEL_PAD, pady=(0, PANEL_PAD))

        self._notebook = ttk.Notebook(outer)
        self._notebook.pack(fill="both", expand=True)
        configure_ttk_notebook(self.window, t)

        # --- Current Page tab ---
        tab_page = tk.Frame(self._notebook, bg=t.window_bg)
        self._notebook.add(tab_page, text="Current Page")

        tk.Label(
            tab_page,
            text="Open the PDF in your reader, then choose the same file here. "
            "Text is extracted from the watcher’s current page plus the next 9 pages.",
            bg=t.window_bg,
            fg=t.fg_muted,
            wraplength=PANEL_WIDTH - 32,
            justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        path_row = tk.Frame(tab_page, bg=t.window_bg)
        path_row.pack(fill="x", pady=(0, 4))
        self._pdf_path = tk.StringVar()
        path_entry = tk.Entry(path_row, textvariable=self._pdf_path, font=("Segoe UI", 9))
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        style_entry(path_entry, t)
        browse_btn = tk.Button(path_row, text="Browse…", command=self._browse_pdf)
        browse_btn.pack(side="right")
        style_button(browse_btn, t)

        self._page_info = tk.Label(tab_page, text="", bg=t.window_bg, font=("Segoe UI", 9), fg=t.fg_soft)
        self._page_info.pack(anchor="w", pady=(4, 0))
        self._refresh_page_label()

        # --- Paste Text tab ---
        tab_paste = tk.Frame(self._notebook, bg=t.window_bg)
        self._notebook.add(tab_paste, text="Paste Text")

        tk.Label(tab_paste, text="Paste or type study material:", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 9)).pack(
            anchor="w", pady=(0, 4)
        )
        paste_frame = tk.Frame(tab_paste, bg=t.window_bg)
        paste_frame.pack(fill="both", expand=True)
        scroll_p = tk.Scrollbar(paste_frame)
        scroll_p.pack(side="right", fill="y")
        self._paste_text = tk.Text(
            paste_frame,
            height=8,
            wrap="word",
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
            yscrollcommand=scroll_p.set,
        )
        self._paste_text.pack(side="left", fill="both", expand=True)
        style_text_editable(self._paste_text, t)
        scroll_p.config(command=self._paste_text.yview)

        btn_row = tk.Frame(outer, bg=t.window_bg)
        btn_row.pack(fill="x", pady=(8, 8))

        self._generate_btn = tk.Button(
            btn_row,
            text="Generate",
            font=("Segoe UI", 10),
            command=self._on_generate,
        )
        self._generate_btn.pack(side="left")
        style_button(self._generate_btn, t)

        self._thinking_lbl = tk.Label(
            btn_row,
            text="",
            bg=t.window_bg,
            fg=t.thinking_fg,
            font=("Segoe UI", 9, "italic"),
        )
        self._thinking_lbl.pack(side="left", padx=(12, 0))

        tk.Label(outer, text="Summary", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        out_frame = tk.Frame(outer, bg=t.window_bg)
        out_frame.pack(fill="both", expand=True)
        scroll_o = tk.Scrollbar(out_frame)
        scroll_o.pack(side="right", fill="y")

        self._canvas = tk.Canvas(out_frame, bg=t.canvas_bg, highlightthickness=0, yscrollcommand=scroll_o.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scroll_o.config(command=self._canvas.yview)

        self._out_inner = tk.Frame(self._canvas, bg=t.window_bg)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._out_inner, anchor="nw")

        def _cfg_scroll(_e: tk.Event) -> None:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfig(self._canvas_win, width=max(1, self._canvas.winfo_width()))

        self._out_inner.bind("<Configure>", _cfg_scroll)
        self._canvas.bind("<Configure>", _cfg_scroll)

        self._tldr_body = self._make_section(self._out_inner, "TL;DR")
        self._kp_body = self._make_section(self._out_inner, "Key Points")
        self._kt_body = self._make_section(self._out_inner, "Key Terms")

        self._set_output_placeholders()

        copy_row = tk.Frame(outer, bg=t.window_bg)
        copy_row.pack(fill="x", pady=(8, 0))
        copy_btn = tk.Button(
            copy_row,
            text="Copy Summary",
            font=("Segoe UI", 9),
            command=self._copy_summary,
        )
        copy_btn.pack(side="left")
        style_button(copy_btn, t)

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")
        self._notebook.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_page_label())

    def _make_section(self, parent: tk.Frame, title: str) -> tk.Text:
        th = self._theme
        tk.Label(parent, text=title, bg=th.window_bg, fg=th.fg, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        t = tk.Text(
            parent,
            height=4,
            wrap="word",
            width=1,
            font=("Segoe UI", 9),
            bg=th.text_readonly_bg,
            relief="flat",
            highlightthickness=1,
            highlightbackground=th.border,
            state="disabled",
        )
        t.pack(fill="x", pady=(0, 4))
        style_text_readonly(t, th)
        return t

    def _set_text(self, widget: tk.Text, s: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", s)
        widget.configure(state="disabled")

    def _set_output_placeholders(self) -> None:
        self._set_text(self._tldr_body, "—")
        self._set_text(self._kp_body, "—")
        self._set_text(self._kt_body, "—")

    def _show_thinking(self) -> None:
        self._thinking_lbl.configure(text="Thinking…")
        self._set_text(self._tldr_body, "—")
        self._set_text(self._kp_body, "—")
        self._set_text(self._kt_body, "—")

    def _browse_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self._pdf_path.set(path)

    def _refresh_page_label(self) -> None:
        st = self._get_watcher_state()
        self._page_info.configure(text=f"Watcher current page: {st.current_page}")

    def _gather_content(self) -> str | None:
        tab_id = self._notebook.select()
        tab_title = self._notebook.tab(tab_id, "text")
        if tab_title == "Current Page":
            path = self._pdf_path.get().strip()
            if not path:
                messagebox.showwarning("Smart Summary", "Choose a PDF file for Current Page.", parent=self.window)
                return None
            st = self._get_watcher_state()
            text = extract_window(path, st.current_page, 0, 9)
            if not text.strip():
                messagebox.showwarning(
                    "Smart Summary",
                    "No text could be extracted from that page range. Check the file path and page number.",
                    parent=self.window,
                )
                return None
            return text
        pasted = self._paste_text.get("1.0", "end").strip()
        if not pasted:
            messagebox.showwarning("Smart Summary", "Paste or type some study material first.", parent=self.window)
            return None
        return pasted

    def _on_generate(self) -> None:
        content = self._gather_content()
        if content is None:
            return

        self._show_thinking()
        self._generate_btn.configure(state="disabled")

        prompt = SMART_SUMMARY_INSTRUCTIONS.format(content=content)

        def on_ok(raw: str) -> None:
            self._generate_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            tldr, kp, kt = parse_summary_response(raw)
            if not (tldr or kp or kt):
                tldr = raw
            self._set_text(self._tldr_body, tldr or "—")
            self._set_text(self._kp_body, kp or "—")
            self._set_text(self._kt_body, kt or "—")

        def on_err(err: BaseException) -> None:
            self._generate_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            self._set_text(self._tldr_body, f"Error: {err}")
            self._set_text(self._kp_body, "")
            self._set_text(self._kt_body, "")

        ask(
            prompt,
            SYSTEM_PROMPT,
            max_tokens=600,
            on_complete=on_ok,
            on_error=on_err,
            ui_root=self._ui_root,
        )

    def _copy_summary(self) -> None:
        def _get(t: tk.Text) -> str:
            return t.get("1.0", "end").strip()

        block = (
            f"TL;DR\n{_get(self._tldr_body)}\n\n"
            f"Key Points\n{_get(self._kp_body)}\n\n"
            f"Key Terms\n{_get(self._kt_body)}"
        )
        self.window.clipboard_clear()
        self.window.clipboard_append(block)
        self.window.update_idletasks()

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
