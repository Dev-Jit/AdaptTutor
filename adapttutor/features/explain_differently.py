from __future__ import annotations

import ctypes
import json
import re
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox
from typing import Callable

from ..config import PANEL_MAX_HEIGHT, PANEL_PAD, PANEL_WIDTH
from ..theme import UiTheme, apply_topmost, style_button, style_text_editable, style_text_readonly
from ..tutor import ask

# PRD feature accent (teal); three distinct left-border colors for the three modes.
_COLOR_SIMPLE = "#00BFA5"
_COLOR_ANALOGY = "#26C6DA"
_COLOR_TECHNICAL = "#00838F"

# PRD — Explain Differently user prompt; JSON shape added for reliable parsing.
EXPLAIN_DIFFERENTLY_TEMPLATE = """A student doesn't understand the following concept. Provide three different explanations:

1. SIMPLE: Explain it in plain language a 12-year-old could understand. No jargon.
2. ANALOGY: Create a relatable real-world analogy that makes the concept click.
3. TECHNICAL: Explain it precisely using correct terminology for a student who wants the accurate version.

Keep each explanation to 3-5 sentences.

Concept: {concept}

Return ONLY a single JSON object (no markdown code fences, no commentary before or after) with exactly these keys and string values:
{{"simple":"...","analogy":"...","technical":"..."}}
Use straight double quotes. If a value must contain a double quote character, escape it in JSON as a backslash followed by a double quote."""

SYSTEM_PROMPT = (
    "You are AdaptTutor. Reply with only the JSON object requested — valid JSON, no markdown fences."
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


def parse_explain_json(raw: str) -> dict[str, str]:
    """Parse model output into simple / analogy / technical strings."""
    s = (raw or "").strip()
    if not s:
        raise ValueError("Empty response")

    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE | re.MULTILINE)
        s = re.sub(r"\s*```\s*$", "", s).strip()

    data = json.loads(s)
    if not isinstance(data, dict):
        raise ValueError("Response is not a JSON object")

    def pick(*keys: str) -> str:
        lower = {str(k).lower(): v for k, v in data.items()}
        for k in keys:
            v = lower.get(k.lower())
            if v is not None:
                return str(v).strip()
        return ""

    simple = pick("simple", "SIMPLE")
    analogy = pick("analogy", "ANALOGY")
    technical = pick("technical", "TECHNICAL")
    if not (simple or analogy or technical):
        raise ValueError("JSON missing simple, analogy, or technical fields")
    return {"simple": simple, "analogy": analogy, "technical": technical}


class ExplainDifferentlyPanel:
    """Concept input, Submit → three cards (Simple / Analogy / Technical), follow-up field."""

    _COLLAPSED_LINES = 4
    _EXPANDED_LINES = 14

    def __init__(
        self,
        *,
        root: tk.Tk,
        ui_root: tk.Misc,
        on_close: Callable[[], None],
        theme: UiTheme,
    ) -> None:
        self._on_close = on_close
        self._ui_root = ui_root
        self._theme = theme
        t = theme

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=t.window_bg)

        header = tk.Frame(self.window, bg=t.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))

        tk.Label(header, text="Explain Differently", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 11, "bold")).pack(
            side="left"
        )
        close_lbl = tk.Label(header, text="✕", bg=t.window_bg, fg=t.fg, cursor="hand2", font=("Segoe UI", 12))
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self._on_close())

        outer = tk.Frame(self.window, bg=t.window_bg)
        outer.pack(fill="both", expand=True, padx=PANEL_PAD, pady=(0, PANEL_PAD))

        scroll = tk.Scrollbar(outer)
        scroll.pack(side="right", fill="y")
        canvas = tk.Canvas(outer, bg=t.canvas_bg, highlightthickness=0, yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.config(command=canvas.yview)

        inner = tk.Frame(canvas, bg=t.window_bg)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_cfg(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=max(1, canvas.winfo_width()))

        inner.bind("<Configure>", _on_cfg)
        canvas.bind("<Configure>", _on_cfg)

        tk.Label(inner, text="Concept", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 9)).pack(anchor="w")
        self._concept = tk.Text(
            inner,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
        )
        self._concept.pack(fill="x", pady=(0, 8))
        style_text_editable(self._concept, t)
        self._placeholder = "Paste a concept or sentence you don't understand..."
        self._concept.insert("1.0", self._placeholder)
        self._concept.configure(fg=t.fg_soft)
        self._concept.bind("<FocusIn>", self._clear_placeholder)
        self._concept.bind("<FocusOut>", self._restore_placeholder)
        self._had_input = False

        submit_row = tk.Frame(inner, bg=t.window_bg)
        submit_row.pack(anchor="w", fill="x", pady=(0, 12))
        self._submit_btn = tk.Button(submit_row, text="Submit", font=("Segoe UI", 10), command=self._on_submit)
        self._submit_btn.pack(side="left")
        style_button(self._submit_btn, t)
        self._thinking_lbl = tk.Label(
            submit_row,
            text="",
            bg=t.window_bg,
            fg=t.thinking_fg,
            font=("Segoe UI", 9, "italic"),
        )
        self._thinking_lbl.pack(side="left", padx=(12, 0))

        cards_frame = tk.Frame(inner, bg=t.window_bg)
        cards_frame.pack(fill="x", pady=(0, 8))

        self._card_simple = self._make_card(cards_frame, "Simple", _COLOR_SIMPLE)
        self._card_analogy = self._make_card(cards_frame, "Analogy", _COLOR_ANALOGY)
        self._card_technical = self._make_card(cards_frame, "Technical", _COLOR_TECHNICAL)

        tk.Label(inner, text="Follow-up question", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 9)).pack(
            anchor="w", pady=(4, 4)
        )
        self._followup = tk.Text(
            inner,
            height=3,
            wrap="word",
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
        )
        self._followup.pack(fill="x")
        style_text_editable(self._followup, t)

        self._set_cards_loading("Submit a concept to see three explanations here.")

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")

    def _clear_placeholder(self, _e: tk.Event) -> None:
        if not self._had_input and self._concept.get("1.0", "end").strip() == self._placeholder:
            self._concept.delete("1.0", "end")
            self._concept.configure(fg=self._theme.fg)
            self._had_input = True

    def _restore_placeholder(self, _e: tk.Event) -> None:
        if not self._concept.get("1.0", "end").strip():
            self._had_input = False
            self._concept.delete("1.0", "end")
            self._concept.insert("1.0", self._placeholder)
            self._concept.configure(fg=self._theme.fg_soft)

    def _make_card(self, parent: tk.Frame, title: str, accent: str) -> dict[str, object]:
        th = self._theme
        outer = tk.Frame(parent, bg=th.window_bg, highlightthickness=1, highlightbackground=th.border)
        outer.pack(fill="x", pady=(0, 10))

        bar = tk.Frame(outer, bg=accent, width=6)
        bar.pack(side="left", fill="y")

        body = tk.Frame(outer, bg=th.window_bg)
        body.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        lbl = tk.Label(body, text=title, bg=th.window_bg, font=("Segoe UI", 12, "bold"), fg=th.fg)
        lbl.pack(anchor="w")

        txt = tk.Text(
            body,
            height=self._COLLAPSED_LINES,
            wrap="word",
            font=("Segoe UI", 14),
            bg=th.text_readonly_bg,
            fg=th.fg,
            relief="flat",
            highlightthickness=0,
            state="disabled",
            cursor="hand2",
        )
        txt.pack(fill="x")
        style_text_readonly(txt, th)

        expanded = [False]

        def toggle(_e: tk.Event | None = None) -> None:
            expanded[0] = not expanded[0]
            txt.configure(height=self._EXPANDED_LINES if expanded[0] else self._COLLAPSED_LINES)

        outer.bind("<Button-1>", toggle)
        bar.bind("<Button-1>", toggle)
        body.bind("<Button-1>", toggle)
        lbl.bind("<Button-1>", toggle)
        txt.bind("<Button-1>", toggle)

        return {"frame": outer, "text": txt, "toggle": toggle}

    def _set_card_text(self, card: dict[str, object], s: str) -> None:
        txt = card["text"]
        if not isinstance(txt, tk.Text):
            return
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("1.0", s)
        txt.configure(state="disabled")

    def _set_cards_loading(self, msg: str) -> None:
        for c in (self._card_simple, self._card_analogy, self._card_technical):
            self._set_card_text(c, msg)

    def _concept_value(self) -> str:
        raw = self._concept.get("1.0", "end").strip()
        if raw == self._placeholder:
            return ""
        return raw

    def _on_submit(self) -> None:
        concept = self._concept_value()
        if not concept:
            messagebox.showwarning("Explain Differently", "Enter a concept first.", parent=self.window)
            return

        self._thinking_lbl.configure(text="Thinking…")
        self._set_cards_loading("…")
        self._submit_btn.configure(state="disabled")

        prompt = EXPLAIN_DIFFERENTLY_TEMPLATE.format(concept=concept)

        def on_ok(raw: str) -> None:
            self._submit_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            try:
                parts = parse_explain_json(raw)
            except Exception as e:
                self._set_card_text(self._card_simple, f"Could not parse JSON. Raw response:\n\n{raw}\n\nError: {e}")
                self._set_card_text(self._card_analogy, "")
                self._set_card_text(self._card_technical, "")
                return
            self._set_card_text(self._card_simple, parts["simple"] or "—")
            self._set_card_text(self._card_analogy, parts["analogy"] or "—")
            self._set_card_text(self._card_technical, parts["technical"] or "—")

        def on_err(err: BaseException) -> None:
            self._submit_btn.configure(state="normal")
            self._thinking_lbl.configure(text="")
            self._set_card_text(self._card_simple, f"Error: {err}")
            self._set_card_text(self._card_analogy, "")
            self._set_card_text(self._card_technical, "")

        ask(
            prompt,
            SYSTEM_PROMPT,
            max_tokens=600,
            on_complete=on_ok,
            on_error=on_err,
            ui_root=self._ui_root,
        )

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
