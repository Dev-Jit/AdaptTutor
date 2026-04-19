from __future__ import annotations

import csv
import ctypes
import io
import json
import re
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from ..config import PANEL_MAX_HEIGHT, PANEL_PAD, PANEL_WIDTH
from ..pdf_reader import extract_window
from ..theme import (
    UiTheme,
    apply_topmost,
    configure_ttk_notebook,
    style_button,
    style_entry,
    style_text_editable,
)
from ..tutor import ask
from ..watcher import WatcherState

FLASHCARD_PROMPT = """Generate a set of flashcards from the following study material.

Rules:
- Create between 8 and 15 cards depending on content length
- Mix three types: definition cards, concept questions, and fill-in-the-blank
- Keep front of card concise (under 15 words)
- Keep back of card under 40 words
- Cover the most important concepts, not trivial details

Return as JSON array only (no markdown fences, no commentary):
[
  {{ "front": "...", "back": "...", "type": "definition" }},
  ...
]

Content:
{content}"""

FLASHCARD_SYSTEM = "You are AdaptTutor. Output only a valid JSON array of objects with keys front, back, and type as specified."


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


def _strip_json_fence(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE | re.MULTILINE)
        s = re.sub(r"\s*```\s*$", "", s).strip()
    return s


def parse_flashcards_json(raw: str) -> list[dict[str, str]]:
    s = _strip_json_fence(raw)
    data = json.loads(s)
    if not isinstance(data, list):
        raise ValueError("Response is not a JSON array")
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        f = str(item.get("front", "")).strip()
        b = str(item.get("back", "")).strip()
        if not f and not b:
            continue
        out.append({"front": f, "back": b, "type": str(item.get("type", "")).strip()})
    if not out:
        raise ValueError("No flashcards in array")
    return out


class FlashcardGeneratorPanel:
    """Source like Smart Summary; Generate → JSON cards; edit/delete; Copy as CSV (Anki)."""

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
        self._deck: list[dict[str, Any]] = []
        t = theme

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=t.window_bg)

        header = tk.Frame(self.window, bg=t.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))
        tk.Label(header, text="Flashcard Generator", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 11, "bold")).pack(
            side="left"
        )
        close_lbl = tk.Label(header, text="✕", bg=t.window_bg, fg=t.fg, cursor="hand2", font=("Segoe UI", 12))
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self._on_close())

        outer = tk.Frame(self.window, bg=t.window_bg)
        outer.pack(fill="both", expand=True, padx=PANEL_PAD, pady=(0, PANEL_PAD))

        self._notebook = ttk.Notebook(outer)
        self._notebook.pack(fill="both", expand=True)
        configure_ttk_notebook(self.window, t)

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
        pe = tk.Entry(path_row, textvariable=self._pdf_path, font=("Segoe UI", 9))
        pe.pack(side="left", fill="x", expand=True, padx=(0, 8))
        style_entry(pe, t)
        bb = tk.Button(path_row, text="Browse…", command=self._browse_pdf)
        bb.pack(side="right")
        style_button(bb, t)
        self._page_info = tk.Label(tab_page, text="", bg=t.window_bg, font=("Segoe UI", 9), fg=t.fg_soft)
        self._page_info.pack(anchor="w", pady=(4, 0))
        self._refresh_page_label()

        tab_paste = tk.Frame(self._notebook, bg=t.window_bg)
        self._notebook.add(tab_paste, text="Paste Text")
        tk.Label(tab_paste, text="Paste or type study material:", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 9)).pack(
            anchor="w", pady=(0, 4)
        )
        paste_frame = tk.Frame(tab_paste, bg=t.window_bg)
        paste_frame.pack(fill="both", expand=True)
        sp = tk.Scrollbar(paste_frame)
        sp.pack(side="right", fill="y")
        self._paste_text = tk.Text(
            paste_frame,
            height=6,
            wrap="word",
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
            yscrollcommand=sp.set,
        )
        self._paste_text.pack(side="left", fill="both", expand=True)
        style_text_editable(self._paste_text, t)
        sp.config(command=self._paste_text.yview)

        ctrl = tk.Frame(outer, bg=t.window_bg)
        ctrl.pack(fill="x", pady=(8, 8))
        self._generate_btn = tk.Button(ctrl, text="Generate", font=("Segoe UI", 10), command=self._on_generate)
        self._generate_btn.pack(side="left")
        style_button(self._generate_btn, t)
        self._thinking_lbl = tk.Label(
            ctrl,
            text="",
            bg=t.window_bg,
            fg=t.thinking_fg,
            font=("Segoe UI", 9, "italic"),
        )
        self._thinking_lbl.pack(side="left", padx=(12, 0))

        tk.Label(outer, text="Cards", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        list_frame = tk.Frame(outer, bg=t.window_bg)
        list_frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side="right", fill="y")
        self._canvas = tk.Canvas(list_frame, bg=t.canvas_bg, highlightthickness=0, yscrollcommand=scroll.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scroll.config(command=self._canvas.yview)

        self._cards_inner = tk.Frame(self._canvas, bg=t.window_bg)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._cards_inner, anchor="nw")

        def _cfg(_e: tk.Event) -> None:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfig(self._canvas_win, width=max(1, self._canvas.winfo_width()))

        self._cards_inner.bind("<Configure>", _cfg)
        self._canvas.bind("<Configure>", _cfg)

        self._cards_header = tk.Frame(self._cards_inner, bg=t.header_bg)
        self._cards_header.pack(fill="x", pady=(0, 6))
        tk.Label(
            self._cards_header,
            text="Front",
            bg=t.header_bg,
            fg=t.fg,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(
            self._cards_header,
            text="Back",
            bg=t.header_bg,
            fg=t.fg,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(self._cards_header, text="", bg=t.header_bg, width=4).pack(side="right")

        bottom = tk.Frame(outer, bg=t.window_bg)
        bottom.pack(fill="x", pady=(8, 0))
        cb = tk.Button(bottom, text="Copy as CSV", font=("Segoe UI", 9), command=self._copy_csv)
        cb.pack(side="left")
        style_button(cb, t)

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")
        self._notebook.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_page_label())

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
                messagebox.showwarning("Flashcard Generator", "Choose a PDF file for Current Page.", parent=self.window)
                return None
            st = self._get_watcher_state()
            text = extract_window(path, st.current_page, 0, 9)
            if not text.strip():
                messagebox.showwarning(
                    "Flashcard Generator",
                    "No text could be extracted from that page range.",
                    parent=self.window,
                )
                return None
            return text
        pasted = self._paste_text.get("1.0", "end").strip()
        if not pasted:
            messagebox.showwarning("Flashcard Generator", "Paste or type some study material first.", parent=self.window)
            return None
        return pasted

    def _clear_card_rows(self) -> None:
        for w in list(self._cards_inner.winfo_children()):
            if w is self._cards_header:
                continue
            w.destroy()
        self._deck.clear()

    def _add_card_row(self, front: str, back: str) -> None:
        th = self._theme
        fv = tk.StringVar(value=front)
        bv = tk.StringVar(value=back)
        wrap = max(80, (PANEL_WIDTH // 2) - 48)

        row = tk.Frame(self._cards_inner, bg=th.window_bg, highlightthickness=1, highlightbackground=th.border)
        row.pack(fill="x", pady=2)

        cols = tk.Frame(row, bg=th.window_bg)
        cols.pack(side="left", fill="both", expand=True, padx=(0, 4))

        # --- Front: label until click, then Entry ---
        f_cell = tk.Frame(cols, bg=th.window_bg)
        f_cell.pack(side="left", fill="both", expand=True, padx=4)
        fl = tk.Label(
            f_cell,
            textvariable=fv,
            bg=th.card_bg,
            fg=th.fg,
            anchor="w",
            justify="left",
            wraplength=wrap,
            font=("Segoe UI", 9),
            cursor="hand2",
            padx=6,
            pady=4,
        )
        fe = tk.Entry(f_cell, textvariable=fv, font=("Segoe UI", 9), relief="solid", borderwidth=1)
        style_entry(fe, th)

        def _show_front(_: tk.Event | None = None) -> None:
            fe.pack_forget()
            fl.pack(fill="both", expand=True)

        def _edit_front(_: tk.Event | None = None) -> None:
            fl.pack_forget()
            fe.pack(fill="both", expand=True)
            fe.focus_set()
            fe.icursor("end")
            fe.select_range(0, "end")

        fl.bind("<Button-1>", _edit_front)
        fe.bind("<FocusOut>", _show_front)
        fe.bind("<Return>", lambda e: (fe.selection_clear(), self.window.focus_set()))
        fl.pack(fill="both", expand=True)

        # --- Back ---
        b_cell = tk.Frame(cols, bg=th.window_bg)
        b_cell.pack(side="left", fill="both", expand=True, padx=4)
        bl = tk.Label(
            b_cell,
            textvariable=bv,
            bg=th.card_bg,
            fg=th.fg,
            anchor="w",
            justify="left",
            wraplength=wrap,
            font=("Segoe UI", 9),
            cursor="hand2",
            padx=6,
            pady=4,
        )
        be = tk.Entry(b_cell, textvariable=bv, font=("Segoe UI", 9), relief="solid", borderwidth=1)
        style_entry(be, th)

        def _show_back(_: tk.Event | None = None) -> None:
            be.pack_forget()
            bl.pack(fill="both", expand=True)

        def _edit_back(_: tk.Event | None = None) -> None:
            bl.pack_forget()
            be.pack(fill="both", expand=True)
            be.focus_set()
            be.icursor("end")
            be.select_range(0, "end")

        bl.bind("<Button-1>", _edit_back)
        be.bind("<FocusOut>", _show_back)
        be.bind("<Return>", lambda e: (be.selection_clear(), self.window.focus_set()))
        bl.pack(fill="both", expand=True)

        card: dict[str, Any] = {"front": fv, "back": bv, "row": row}

        def _remove() -> None:
            try:
                self._deck.remove(card)
            except ValueError:
                pass
            row.destroy()

        del_b = tk.Button(row, text="✕", font=("Segoe UI", 9), width=2, command=_remove, cursor="hand2")
        del_b.pack(side="right", padx=(0, 4), pady=2)
        style_button(del_b, th)
        self._deck.append(card)

    def _on_generate(self) -> None:
        content = self._gather_content()
        if content is None:
            return

        self._clear_card_rows()
        self._thinking_lbl.configure(text="Thinking…")
        self._generate_btn.configure(state="disabled")

        prompt = FLASHCARD_PROMPT.format(content=content)

        def on_ok(raw: str) -> None:
            self._generate_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            try:
                cards = parse_flashcards_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                self._thinking_lbl.configure(text="")
                messagebox.showerror(
                    "Flashcard Generator",
                    f"Could not parse flashcards from the model response.\n{e}",
                    parent=self.window,
                )
                return
            for c in cards:
                self._add_card_row(c["front"], c["back"])

        def on_err(err: BaseException) -> None:
            self._generate_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            messagebox.showerror("Flashcard Generator", str(err), parent=self.window)

        ask(
            prompt,
            FLASHCARD_SYSTEM,
            max_tokens=2048,
            on_complete=on_ok,
            on_error=on_err,
            ui_root=self._ui_root,
        )

    def _copy_csv(self) -> None:
        if not self._deck:
            messagebox.showinfo("Flashcard Generator", "No cards to copy.", parent=self.window)
            return
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["Front", "Back"])
        for c in self._deck:
            writer.writerow([c["front"].get().strip(), c["back"].get().strip()])
        text = buf.getvalue()
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
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