from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import pyperclip
from pynput import mouse

from .features import instant_explain

_POLL_SECONDS = 0.5
_MOUSE_IDLE_SECONDS = 1.0
# Bubble handles 1–4 (definition), 5–500 (explain), >500 (long-offer) inside instant_explain.
_MIN_WORDS_FOR_BUBBLE = 1


def _word_count(text: str) -> int:
    return len((text or "").split())


class ClipboardMonitor(threading.Thread):
    """
    Polls the clipboard every 500ms. When text changes, word count is at least 1,
    the mouse has been still for >= 1s, and study_active is True, opens the Instant Explain bubble.
    """

    def __init__(
        self,
        *,
        get_study_active: Callable[[], bool],
        schedule_ui: Callable[[Callable[[], None]], None],
    ) -> None:
        super().__init__(daemon=True)
        self._get_study_active = get_study_active
        self._schedule_ui = schedule_ui
        self._stop = threading.Event()
        self._prev_clip: str = ""
        self._lock = threading.Lock()
        self._last_mouse_move_mono: float = 0.0
        self._listener: Optional[mouse.Listener] = None

    def stop(self) -> None:
        self._stop.set()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_mouse_move(self, x: float, y: float) -> None:
        with self._lock:
            self._last_mouse_move_mono = time.monotonic()

    def run(self) -> None:
        self._last_mouse_move_mono = time.monotonic()
        try:
            self._listener = mouse.Listener(on_move=self._on_mouse_move)
            self._listener.start()
        except Exception:
            self._listener = None

        while not self._stop.is_set():
            try:
                current = pyperclip.paste()
            except Exception:
                current = ""

            if not isinstance(current, str):
                current = str(current)

            changed = current != self._prev_clip
            if not changed:
                self._stop.wait(_POLL_SECONDS)
                continue

            now = time.monotonic()
            with self._lock:
                idle_ok = (now - self._last_mouse_move_mono) >= _MOUSE_IDLE_SECONDS

            words = _word_count(current)
            words_ok = words >= _MIN_WORDS_FOR_BUBBLE and bool(current.strip())
            study = False
            try:
                study = bool(self._get_study_active())
            except Exception:
                study = False

            if words_ok and idle_ok and study:
                try:
                    pos = mouse.Controller().position
                except Exception:
                    pos = (0, 0)
                text_snapshot = current
                self._schedule_ui(
                    lambda t=text_snapshot, px=int(pos[0]), py=int(pos[1]): instant_explain.show_bubble(
                        t, (px, py)
                    )
                )
                self._prev_clip = current
            elif not words_ok:
                # Empty clipboard: Windows often briefly clears it on UI clicks. If a bubble is waiting
                # on the LLM, do not update _prev_clip so we do not re-trigger show_bubble on restore.
                cur_st = (current or "").strip()
                prev_st = (self._prev_clip or "").strip()
                if not cur_st and prev_st and instant_explain.bubble_llm_pending():
                    pass
                else:
                    self._prev_clip = current
            # else: have words but waiting on idle or study_active — keep _prev_clip unchanged

            self._stop.wait(_POLL_SECONDS)
