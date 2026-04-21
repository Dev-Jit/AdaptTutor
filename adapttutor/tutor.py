from __future__ import annotations

import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from groq import Groq, RateLimitError

try:
    from .config import GROQ_API_KEY
except ImportError:
    # Running `python tutor.py` (not as part of the package) — add repo root so `adapttutor` resolves.
    _repo_root = Path(__file__).resolve().parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from adapttutor.config import GROQ_API_KEY

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_429_ATTEMPTS = max(1, min(6, int(os.environ.get("GROQ_429_ATTEMPTS", "2"))))
_ASK_AI_SYSTEM_PROMPT = (
    "You are Ask AI, a general purpose assistant. Answer any question the user asks\n"
    "clearly and concisely. Keep responses under 150 words unless asked for more.\n"
    "Do not use heavy markdown formatting — plain sentences only."
)


def _is_groq_rate_limit(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    s = str(exc).lower()
    return "429" in s or "rate limit" in s


def _retry_after_seconds_groq(exc: BaseException) -> float:
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            ra = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
            if ra:
                return max(2.0, min(float(ra), 120.0))
        except (TypeError, ValueError, AttributeError):
            pass
    m = re.search(r"retry in ([\d.]+)\s*s", str(exc), re.IGNORECASE)
    if m:
        return max(2.0, min(float(m.group(1)) + 1.0, 120.0))
    return 8.0


def _rate_limit_user_message() -> str:
    return (
        f"Groq rate limit exceeded (HTTP 429) for model {_GROQ_MODEL!r}. "
        "Wait briefly and try again, or check your plan and limits: https://console.groq.com/"
    )


def _call_groq_sync(prompt: str, system: str, max_tokens: int) -> str:
    if not (GROQ_API_KEY or "").strip():
        raise RuntimeError("GROQ_API_KEY is not set (see config.py or environment GROQ_API_KEY).")
    client = Groq(api_key=GROQ_API_KEY)
    sys_text = (system or "").strip() or "You are a helpful study assistant."
    messages = [
        {"role": "system", "content": sys_text},
        {"role": "user", "content": prompt},
    ]
    last_err: BaseException | None = None
    for attempt in range(_GROQ_429_ATTEMPTS):
        try:
            completion = client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
            )
            choice = completion.choices[0] if completion.choices else None
            msg = getattr(choice, "message", None) if choice else None
            text = getattr(msg, "content", None) if msg else None
            if text is not None and str(text).strip():
                return str(text).strip()
            return ""
        except BaseException as e:
            last_err = e
            if not _is_groq_rate_limit(e):
                raise
            if attempt + 1 >= _GROQ_429_ATTEMPTS:
                break
            time.sleep(_retry_after_seconds_groq(e))
    if last_err is not None and _is_groq_rate_limit(last_err):
        raise RuntimeError(_rate_limit_user_message()) from last_err
    if last_err is not None:
        raise last_err
    raise RuntimeError("Groq request failed with no response.")


def ask_general(question: str) -> str:
    """Synchronous single-turn Ask AI call."""
    q = (question or "").strip()
    if not q:
        return ""
    return _call_groq_sync(q, _ASK_AI_SYSTEM_PROMPT, max_tokens=600)


def ask(
    prompt: str,
    system: str,
    max_tokens: int = 600,
    *,
    on_complete: Callable[[str], None],
    on_error: Optional[Callable[[BaseException], None]] = None,
    ui_root: Optional[tk.Misc] = None,
) -> None:
    """
    Call Groq (Llama 3.3 70B) in a background thread so the Tk UI never blocks.

    The HTTP call runs on a worker thread; ``on_complete`` / ``on_error`` are always
    scheduled back onto the Tk main thread via ``ui_root.after(0, ...)`` when
    ``ui_root`` is provided, so widgets may be updated safely from those callbacks.
    """

    def _deliver_success(text: str) -> None:
        on_complete(text)

    def _deliver_error(err: BaseException) -> None:
        if on_error:
            on_error(err)

    def worker() -> None:
        try:
            text = _call_groq_sync(prompt, system, max_tokens)
        except BaseException as e:
            if ui_root is not None:
                ui_root.after(0, lambda err=e: _deliver_error(err))
            else:
                _deliver_error(e)
            return

        if ui_root is not None:
            ui_root.after(0, lambda t=text: _deliver_success(t))
        else:
            _deliver_success(text)

    threading.Thread(target=worker, daemon=True).start()
