from __future__ import annotations

import time
import tkinter as tk
from typing import Callable, Optional

from pynput import keyboard

from ..theme import UiTheme, apply_topmost, load_ui_theme
from ..tutor import ask

_host: Optional[tk.Misc] = None
_bubble_theme: Optional[UiTheme] = None
_bubble_window: Optional[tk.Toplevel] = None
_go_deeper_cb: Optional[Callable[[str], None]] = None
# True while Groq is running for the current bubble — blocks show_bubble() from destroying it (e.g. clipboard flicker).
_bubble_llm_pending: bool = False

BUBBLE_WIDTH = 280
_AUTO_DISMISS_MS = 4000
_CTRL_C_WINDOW_MS = 500

SYSTEM_DEFAULT = "You are AdaptTutor, a patient study helper. Follow the user's format request. Be concise."

INSTANT_EXPLAIN_USER = """Explain the following text in the simplest possible way, as if the reader is hearing this concept for the first time. Use a relatable real-world analogy if one exists. Keep the response to 3-4 sentences maximum. Do not use jargon.

Selected text: {selected_text}"""

DEFINITION_USER = """The student highlighted a very short phrase (1–4 words). Give a concise dictionary-style gloss: meaning in plain language, at most 2 short sentences. No jargon.

Words: {selected_text}"""

LONG_OFFER_TEXT = "This is quite long — want a summary instead?"

SUMMARY_FROM_LONG_USER = """The student has a long passage. Summarize the core ideas in 4–6 short bullet lines (plain text, each line starting with "- "). Stay concise.

Text:
{chunk}"""

EXPLAIN_TRUNCATED_USER = """The following is an excerpt from a longer passage (truncated for length). Explain this excerpt simply in 3-4 sentences, with a relatable analogy if helpful. Do not use jargon.

Excerpt:
{chunk}"""


def configure_bubble_host(host_window: tk.Misc, theme: Optional[UiTheme] = None) -> None:
    global _host, _bubble_theme
    _host = host_window
    _bubble_theme = theme


def set_go_deeper_callback(cb: Optional[Callable[[str], None]]) -> None:
    global _go_deeper_cb
    _go_deeper_cb = cb


def bubble_llm_pending() -> bool:
    """True while Explain / Summary is waiting on the model for the open bubble."""
    return _bubble_llm_pending


def _dismiss_bubble() -> None:
    global _bubble_window, _bubble_llm_pending
    _bubble_llm_pending = False
    if _bubble_window is not None:
        try:
            _bubble_window.destroy()
        except tk.TclError:
            pass
        _bubble_window = None


def dismiss_if_open() -> None:
    _dismiss_bubble()


def _word_count(text: str) -> int:
    return len((text or "").strip().split())


def show_bubble(selected_text: str, cursor_position: tuple[int, int]) -> None:
    """
    Instant Explain bubble at cursor. Main-thread only.
    Edge cases: 1–4 words → definition path; >500 → summary offer + explain truncated; Ctrl+C in first 500ms → silent dismiss.
    """
    global _bubble_window
    if _host is None:
        return

    full = (selected_text or "").strip()
    x, y = int(cursor_position[0]), int(cursor_position[1])
    wc = _word_count(full)

    # Opening a new bubble while the current one is waiting on the API would destroy it (bad UX).
    if _bubble_window is not None and _bubble_llm_pending:
        return

    _dismiss_bubble()

    theme = _bubble_theme or load_ui_theme()

    top = tk.Toplevel(_host)
    _bubble_window = top
    top.overrideredirect(True)
    apply_topmost(top)
    top.configure(bg=theme.bubble_outer_bg)

    outer = tk.Frame(
        top,
        bg=theme.bubble_panel_bg,
        highlightthickness=1,
        highlightbackground=theme.border,
    )
    outer.pack(fill="both", expand=True, padx=1, pady=1)

    panel = theme.bubble_panel_bg
    preview = full if len(full) <= 60 else full[:57] + "..."
    tk.Label(
        outer,
        text=preview or "(empty)",
        bg=panel,
        fg=theme.fg,
        font=("Segoe UI", 9),
        wraplength=BUBBLE_WIDTH - 32,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(12, 4))

    prompt_lbl = tk.Label(outer, text="Explain this simply?", bg=panel, fg=theme.fg, font=("Segoe UI", 9))
    prompt_lbl.pack(anchor="w", padx=14, pady=(0, 6))

    long_frame = tk.Frame(outer, bg=panel)
    main_body = tk.Frame(outer, bg=panel)
    btn_row = tk.Frame(main_body, bg=panel)
    body_frame = tk.Frame(outer, bg=panel)

    state: dict[str, object] = {"auto_id": None, "listener": None, "opened_mono": time.monotonic(), "armed": True}

    def cancel_auto() -> None:
        aid = state.get("auto_id")
        if aid is not None:
            try:
                top.after_cancel(int(aid))
            except (tk.TclError, TypeError, ValueError):
                pass
            state["auto_id"] = None

    def stop_ctrl_listener() -> None:
        lst = state.get("listener")
        if lst is not None:
            try:
                lst.stop()
            except Exception:
                pass
            state["listener"] = None

    def dismiss_silent() -> None:
        cancel_auto()
        stop_ctrl_listener()
        _dismiss_bubble()

    def dismiss_interactive() -> None:
        state["armed"] = False
        cancel_auto()
        stop_ctrl_listener()
        _dismiss_bubble()

    def on_interact(_e: tk.Event | None = None) -> None:
        if state.get("armed"):
            cancel_auto()

    def arm_auto_dismiss() -> None:
        cancel_auto()
        state["auto_id"] = top.after(_AUTO_DISMISS_MS, dismiss_interactive)

    def _place_window(h: int) -> None:
        w = BUBBLE_WIDTH
        sx = max(0, x - w // 2)
        sy = max(0, y - int(h) - 12)
        top.geometry(f"{w}x{int(h)}+{sx}+{sy}")

    def show_expanded(response_text: str) -> None:
        try:
            main_body.pack_forget()
        except tk.TclError:
            pass
        long_frame.pack_forget()
        btn_row.pack_forget()
        for w in body_frame.winfo_children():
            w.destroy()
        body_frame.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        txt = tk.Text(
            body_frame,
            wrap="word",
            width=1,
            height=1,
            font=("Segoe UI", 10),
            bg=theme.bubble_text_bg,
            fg=theme.fg,
            relief="flat",
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        txt.insert("1.0", response_text.strip())
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=10, pady=(4, 8))

        tail = tk.Frame(body_frame, bg=panel)
        tail.pack(fill="x", padx=10, pady=(0, 10))

        def go_deeper() -> None:
            dismiss_interactive()
            if _go_deeper_cb:
                try:
                    _go_deeper_cb(full)
                except Exception:
                    pass

        tk.Button(tail, text="Go Deeper", font=("Segoe UI", 9), command=go_deeper).pack(side="left", padx=(0, 8))
        tk.Button(tail, text="Dismiss", font=("Segoe UI", 9), command=dismiss_interactive).pack(side="left")

        top.update_idletasks()
        h = min(440, max(220, top.winfo_reqheight()))
        _place_window(h)

    def show_thinking() -> None:
        try:
            main_body.pack_forget()
        except tk.TclError:
            pass
        long_frame.pack_forget()
        btn_row.pack_forget()
        for w in body_frame.winfo_children():
            w.destroy()
        body_frame.pack(fill="both", expand=True)
        tk.Label(
            body_frame,
            text="Thinking…",
            bg=panel,
            fg=theme.thinking_fg,
            font=("Segoe UI", 10, "italic"),
        ).pack(padx=14, pady=20)
        top.update_idletasks()
        _place_window(min(200, top.winfo_reqheight()))

    def run_tutor(user_prompt: str) -> None:
        global _bubble_llm_pending
        on_interact()
        _bubble_llm_pending = True

        def ok(t: str) -> None:
            global _bubble_llm_pending
            _bubble_llm_pending = False
            show_expanded(t or "(no response)")

        def err(e: BaseException) -> None:
            global _bubble_llm_pending
            _bubble_llm_pending = False
            show_expanded(f"Something went wrong.\n\n{e}")

        show_thinking()
        ask(user_prompt, SYSTEM_DEFAULT, max_tokens=600, on_complete=ok, on_error=err, ui_root=_host)

    def explain_normal() -> None:
        run_tutor(INSTANT_EXPLAIN_USER.format(selected_text=full))

    def explain_definition() -> None:
        run_tutor(DEFINITION_USER.format(selected_text=full))

    def explain_truncated() -> None:
        run_tutor(EXPLAIN_TRUNCATED_USER.format(chunk=full[:12000]))

    def summary_long() -> None:
        run_tutor(SUMMARY_FROM_LONG_USER.format(chunk=full[:12000]))

    dismiss_btn = tk.Button(btn_row, text="Dismiss", font=("Segoe UI", 9), command=dismiss_interactive)

    if wc > 500:
        prompt_lbl.configure(text=LONG_OFFER_TEXT)
        long_frame.pack(fill="x", padx=14, pady=(0, 8))
        row = tk.Frame(long_frame, bg=panel)
        row.pack(fill="x")
        tk.Button(row, text="Summary", font=("Segoe UI", 9), command=summary_long).pack(side="left", padx=(0, 8))
        tk.Button(row, text="Explain anyway", font=("Segoe UI", 9), command=explain_truncated).pack(side="left", padx=(0, 8))
        dismiss_btn.pack(side="left")
    elif 1 <= wc <= 4:
        prompt_lbl.configure(text="Short selection — a quick definition works best.")
        tk.Button(btn_row, text="Explain it", font=("Segoe UI", 9), command=explain_definition).pack(side="left", padx=(0, 8))
        dismiss_btn.pack(side="left")
    else:
        tk.Button(btn_row, text="Explain it", font=("Segoe UI", 9), command=explain_normal).pack(side="left", padx=(0, 8))
        dismiss_btn.pack(side="left")

    main_body.pack(fill="x", padx=0, pady=0)
    btn_row.pack(fill="x", padx=14, pady=(0, 12))

    for ch in outer.winfo_children():
        ch.bind("<Button-1>", on_interact, add="+")
    for ch in btn_row.winfo_children():
        ch.bind("<Button-1>", on_interact, add="+")
    long_frame.bind("<Button-1>", on_interact, add="+")

    # Ctrl+C in first 500ms → silent dismiss
    def on_ctrl_c() -> None:
        if time.monotonic() - float(state["opened_mono"]) <= (_CTRL_C_WINDOW_MS / 1000.0):
            _host.after(0, dismiss_silent)

    try:
        hk = keyboard.HotKey(keyboard.HotKey.parse("<ctrl>+c"), on_ctrl_c)

        def _press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
            hk.press(key)

        def _release(key: keyboard.Key | keyboard.KeyCode | None) -> None:
            hk.release(key)

        listener = keyboard.Listener(on_press=_press, on_release=_release)
        listener.start()
        state["listener"] = listener
        top.after(_CTRL_C_WINDOW_MS, stop_ctrl_listener)
    except Exception:
        state["listener"] = None

    arm_auto_dismiss()

    top.update_idletasks()
    _place_window(top.winfo_reqheight())
