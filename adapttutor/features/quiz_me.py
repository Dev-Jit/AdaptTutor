from __future__ import annotations

import ctypes
import json
import re
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable

from ..config import PANEL_MAX_HEIGHT, PANEL_PAD, PANEL_WIDTH
from ..pdf_reader import extract_window
from ..theme import UiTheme, apply_topmost, style_button, style_entry, style_text_editable, style_text_readonly
from ..tutor import ask
from ..watcher import WatcherState

QUESTION_GEN_TEMPLATE = """You are a Socratic tutor. Based on the following study material, generate ONE question to test the student's understanding.

Rules:
- Ask only one question at a time
- Vary between: multiple choice (provide 4 options labeled A-D), open-ended, and fill-in-the-blank
- Target conceptual understanding, not memorisation
- Difficulty should be medium — not trivial, not postgraduate

Study material: {content}
Previous questions asked this session: {history}

Return your response as JSON only (no markdown fences, no other text):
{{
  "type": "mcq",
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "..."
}}

For type "open" or "fill", use "options": [] and still include "answer" for grading."""

QUESTION_GEN_SYSTEM = "You are AdaptTutor. Output only valid JSON matching the schema described in the user message."

EVAL_TEMPLATE = """The student answered a quiz question. Evaluate their answer using the Socratic method — guide them toward understanding rather than just marking right or wrong.

Question: {question}
Correct answer: {answer}
Student's answer: {student_answer}

Respond with:
1. Whether they were correct (be encouraging either way)
2. If wrong: a guiding hint that nudges them without giving the answer directly
3. A short follow-up question that deepens understanding of this concept"""

EVAL_SYSTEM = "You are AdaptTutor, a Socratic tutor. Be concise and warm. Follow the three-part structure requested."


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


def _title_looks_like_pdf(title: str) -> bool:
    return ".pdf" in (title or "").lower()


def _display_filename(title: str) -> str:
    t = (title or "").strip()
    if " - " in t:
        left = t.split(" - ", 1)[0].strip()
        if left:
            return left if len(left) <= 56 else left[:53] + "..."
    if len(t) > 56:
        return t[:53] + "..."
    return t or "document"


def _strip_json_fence(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE | re.MULTILINE)
        s = re.sub(r"\s*```\s*$", "", s).strip()
    return s


def parse_quiz_question_json(raw: str) -> dict[str, Any]:
    s = _strip_json_fence(raw)
    data = json.loads(s)
    if not isinstance(data, dict):
        raise ValueError("Not a JSON object")
    qtype = str(data.get("type", "open")).lower().strip()
    if qtype not in ("mcq", "open", "fill"):
        qtype = "open"
    question = str(data.get("question", "")).strip()
    if not question:
        raise ValueError("Missing question")
    options = data.get("options") or []
    if not isinstance(options, list):
        options = []
    options = [str(o).strip() for o in options if str(o).strip()]
    answer = str(data.get("answer", "")).strip()
    if qtype == "mcq" and len(options) < 2:
        raise ValueError("MCQ needs options")
    return {"type": qtype, "question": question, "options": options, "answer": answer}


class QuizMePanel:
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
        self._ui_root = ui_root
        self._get_watcher_state = get_watcher_state
        self._theme = theme
        t = theme

        self._session_count = 0
        self._history: list[str] = []
        self._current: dict[str, Any] | None = None
        self._pdf_path = tk.StringVar()

        st = get_watcher_state()
        self._pdf_mode = bool(st.current_context and _title_looks_like_pdf(st.current_context))

        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=t.window_bg)

        header = tk.Frame(self.window, bg=t.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))
        tk.Label(header, text="Quiz Me", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 11, "bold")).pack(side="left")
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
        self._inner_win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _cfg(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(self._inner_win, width=max(1, canvas.winfo_width()))

        inner.bind("<Configure>", _cfg)
        canvas.bind("<Configure>", _cfg)
        self._canvas = canvas

        # --- Source ---
        self._source_frame = tk.Frame(inner, bg=t.window_bg)
        self._source_frame.pack(fill="x", pady=(0, 8))

        if self._pdf_mode:
            fn = _display_filename(st.current_context)
            self._reading_lbl = tk.Label(
                self._source_frame,
                text=f"Reading from: {fn} · page {st.current_page}",
                bg=t.window_bg,
                font=("Segoe UI", 10, "bold"),
                fg=t.fg,
                wraplength=PANEL_WIDTH - 24,
                justify="left",
            )
            self._reading_lbl.pack(anchor="w", pady=(0, 6))
            tk.Label(
                self._source_frame,
                text="Select the same PDF file on disk so text can be extracted:",
                bg=t.window_bg,
                font=("Segoe UI", 9),
                fg=t.fg_muted,
                wraplength=PANEL_WIDTH - 24,
                justify="left",
            ).pack(anchor="w")
            row = tk.Frame(self._source_frame, bg=t.window_bg)
            row.pack(fill="x", pady=(4, 0))
            pe = tk.Entry(row, textvariable=self._pdf_path, font=("Segoe UI", 9))
            pe.pack(side="left", fill="x", expand=True, padx=(0, 8))
            style_entry(pe, t)
            bb = tk.Button(row, text="Browse…", command=self._browse_pdf)
            bb.pack(side="right")
            style_button(bb, t)
        else:
            tk.Label(
                self._source_frame,
                text="No PDF window detected in the title — paste study material below.",
                bg=t.window_bg,
                font=("Segoe UI", 9),
                fg=t.fg_muted,
                wraplength=PANEL_WIDTH - 24,
                justify="left",
            ).pack(anchor="w", pady=(0, 4))
            pf = tk.Frame(self._source_frame, bg=t.window_bg)
            pf.pack(fill="x")
            sp = tk.Scrollbar(pf)
            sp.pack(side="right", fill="y")
            self._paste = tk.Text(pf, height=6, wrap="word", font=("Segoe UI", 9), yscrollcommand=sp.set)
            self._paste.pack(side="left", fill="x", expand=True)
            style_text_editable(self._paste, t)
            sp.config(command=self._paste.yview)

        self._progress = tk.Label(inner, text="Question 0 of this session", bg=t.window_bg, font=("Segoe UI", 9), fg=t.fg_soft)
        self._progress.pack(anchor="w", pady=(4, 4))

        btn_row = tk.Frame(inner, bg=t.window_bg)
        btn_row.pack(fill="x", pady=(0, 8))
        self._btn_generate = tk.Button(btn_row, text="Generate question", command=self._on_generate_question)
        self._btn_generate.pack(side="left", padx=(0, 8))
        style_button(self._btn_generate, t)
        self._btn_next = tk.Button(btn_row, text="Next question", command=self._on_next_question, state="disabled")
        self._btn_next.pack(side="left")
        style_button(self._btn_next, t)
        self._thinking_lbl = tk.Label(
            btn_row,
            text="",
            bg=t.window_bg,
            fg=t.thinking_fg,
            font=("Segoe UI", 9, "italic"),
        )
        self._thinking_lbl.pack(side="left", padx=(8, 0))

        self._question_host = tk.Frame(inner, bg=t.window_bg)
        self._question_host.pack(fill="x", pady=(0, 8))

        tk.Label(inner, text="Feedback", bg=t.window_bg, fg=t.fg, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ff = tk.Frame(inner, bg=t.window_bg)
        ff.pack(fill="both", expand=True)
        sf = tk.Scrollbar(ff)
        sf.pack(side="right", fill="y")
        self._feedback = tk.Text(
            ff,
            height=8,
            wrap="word",
            font=("Segoe UI", 9),
            state="disabled",
            bg=t.text_readonly_bg,
            fg=t.fg,
            yscrollcommand=sf.set,
        )
        self._feedback.pack(side="left", fill="both", expand=True)
        style_text_readonly(self._feedback, t)
        sf.config(command=self._feedback.yview)

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")

    def _browse_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self._pdf_path.set(path)

    def _set_feedback(self, s: str) -> None:
        self._feedback.configure(state="normal")
        self._feedback.delete("1.0", "end")
        self._feedback.insert("1.0", s)
        self._feedback.configure(state="disabled")

    def _clear_question_ui(self) -> None:
        for w in self._question_host.winfo_children():
            w.destroy()

    def _gather_content(self) -> str | None:
        if self._pdf_mode:
            path = self._pdf_path.get().strip()
            if not path:
                messagebox.showwarning("Quiz Me", "Choose the PDF file to read study text from.", parent=self.window)
                return None
            st = self._get_watcher_state()
            text = extract_window(path, st.current_page, 0, 3)
            if not text.strip():
                messagebox.showwarning(
                    "Quiz Me",
                    "Could not read text from that PDF/page. Check the path and try again.",
                    parent=self.window,
                )
                return None
            return text
        pasted = self._paste.get("1.0", "end").strip()
        if not pasted:
            messagebox.showwarning("Quiz Me", "Paste some study material first.", parent=self.window)
            return None
        return pasted

    def _history_text(self) -> str:
        if not self._history:
            return "(none yet)"
        return "\n---\n".join(self._history[-6:])

    def _on_generate_question(self) -> None:
        content = self._gather_content()
        if content is None:
            return

        if self._pdf_mode and hasattr(self, "_reading_lbl"):
            st = self._get_watcher_state()
            fn = _display_filename(st.current_context)
            self._reading_lbl.configure(text=f"Reading from: {fn} · page {st.current_page}")

        self._clear_question_ui()
        self._thinking_lbl.configure(text="Thinking…")
        self._set_feedback("")
        self._btn_generate.configure(state="disabled")
        self._btn_next.configure(state="disabled")

        prompt = QUESTION_GEN_TEMPLATE.format(content=content, history=self._history_text())

        def on_ok(raw: str) -> None:
            self._btn_generate.configure(state="normal")
            self._thinking_lbl.configure(text="")
            try:
                q = parse_quiz_question_json(raw)
            except Exception as e:
                self._set_feedback(f"Could not parse question JSON.\n\nError: {e}\n\nRaw:\n{raw}")
                return
            self._current = q
            self._session_count += 1
            self._progress.configure(text=f"Question {self._session_count} of this session")
            self._history.append(q["question"])
            self._render_question(q)
            self._set_feedback("Answer the question above, then tap Submit answer.")

        def on_err(err: BaseException) -> None:
            self._btn_generate.configure(state="normal")
            self._thinking_lbl.configure(text="")
            self._set_feedback(f"Error: {err}")

        ask(prompt, QUESTION_GEN_SYSTEM, max_tokens=600, on_complete=on_ok, on_error=on_err, ui_root=self._ui_root)

    def _bg_for_type(self, qtype: str) -> str:
        th = self._theme
        if qtype == "mcq":
            return th.quiz_mcq
        if qtype == "fill":
            return th.quiz_fill
        return th.quiz_open

    def _render_question(self, q: dict[str, Any]) -> None:
        self._clear_question_ui()
        qtype = q["type"]
        bg = self._bg_for_type(qtype)

        th = self._theme
        card = tk.Frame(self._question_host, bg=bg, highlightthickness=1, highlightbackground=th.border)
        card.pack(fill="x", pady=(0, 8))

        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        tk.Label(
            inner,
            text=f"Type: {qtype.upper()}",
            bg=bg,
            font=("Segoe UI", 9, "bold"),
            fg=th.fg_muted,
        ).pack(anchor="w")
        tk.Label(
            inner,
            text=q["question"],
            bg=bg,
            font=("Segoe UI", 11),
            fg=th.fg,
            wraplength=PANEL_WIDTH - 48,
            justify="left",
        ).pack(anchor="w", pady=(6, 8))

        self._answer_var = tk.StringVar(value="")
        self._mcq_index = tk.IntVar(value=-1)

        if qtype == "mcq":
            for i, opt in enumerate(q["options"]):
                tk.Radiobutton(
                    inner,
                    text=opt,
                    variable=self._mcq_index,
                    value=i,
                    bg=bg,
                    fg=th.fg,
                    activebackground=bg,
                    activeforeground=th.fg,
                    selectcolor=th.input_bg,
                    font=("Segoe UI", 9),
                    anchor="w",
                    wraplength=PANEL_WIDTH - 60,
                    justify="left",
                ).pack(anchor="w", fill="x")
        else:
            tk.Label(inner, text="Your answer:", bg=bg, fg=th.fg, font=("Segoe UI", 9)).pack(anchor="w")
            self._open_answer = tk.Entry(inner, textvariable=self._answer_var, font=("Segoe UI", 10))
            self._open_answer.pack(fill="x", pady=(2, 0))
            style_entry(self._open_answer, th)

        self._btn_submit = tk.Button(self._question_host, text="Submit answer", command=self._on_submit_answer)
        self._btn_submit.pack(anchor="w")
        style_button(self._btn_submit, th)

    def _collect_student_answer(self) -> str | None:
        if not self._current:
            return None
        if self._current["type"] == "mcq":
            idx = self._mcq_index.get()
            opts: list[str] = self._current["options"]
            if idx < 0 or idx >= len(opts):
                messagebox.showwarning("Quiz Me", "Select an option (A–D).", parent=self.window)
                return None
            return opts[idx]
        ans = (self._answer_var.get() or "").strip()
        if not ans:
            messagebox.showwarning("Quiz Me", "Enter an answer.", parent=self.window)
            return None
        return ans

    def _on_submit_answer(self) -> None:
        if not self._current:
            return
        student = self._collect_student_answer()
        if student is None:
            return

        self._thinking_lbl.configure(text="Thinking…")
        self._set_feedback("")
        self._btn_submit.configure(state="disabled")
        self._btn_generate.configure(state="disabled")

        prompt = EVAL_TEMPLATE.format(
            question=self._current["question"],
            answer=self._current["answer"],
            student_answer=student,
        )

        def on_ok(text: str) -> None:
            self._btn_generate.configure(state="normal")
            self._btn_next.configure(state="normal")
            self._thinking_lbl.configure(text="")
            self._set_feedback((text or "").strip())
            try:
                self._btn_submit.configure(state="disabled")
            except (tk.TclError, AttributeError):
                pass

        def on_err(err: BaseException) -> None:
            self._btn_generate.configure(state="normal")
            self._btn_submit.configure(state="normal")
            self._thinking_lbl.configure(text="")
            self._set_feedback(f"Error: {err}")

        ask(prompt, EVAL_SYSTEM, max_tokens=600, on_complete=on_ok, on_error=on_err, ui_root=self._ui_root)

    def _on_next_question(self) -> None:
        self._current = None
        self._btn_next.configure(state="disabled")
        self._on_generate_question()

    def reposition_to_launcher(self, launcher: tk.Toplevel) -> None:
        self.window.update_idletasks()
        launcher.update_idletasks()
        work = _get_windows_work_area()
        if work:
            _l, _t, right, bottom = work
        else:
            right = self.window.winfo_screenwidth()
            bottom = self.window.winfo_screenheight()
        margin = 18
        w, h = PANEL_WIDTH, PANEL_MAX_HEIGHT
        self.window.geometry(f"{w}x{h}+{right - w - margin}+{bottom - h - margin}")

    def destroy(self) -> None:
        try:
            self.window.destroy()
        except Exception:
            pass
