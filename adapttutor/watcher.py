from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import pygetwindow as gw

from .config import STUDY_APP_TITLE_SUFFIXES, STUDY_KEYWORDS


def _safe_get_active_window_title() -> str:
    try:
        win = gw.getActiveWindow()
        title = getattr(win, "title", "") if win else ""
        return title or ""
    except Exception:
        return ""


def _is_adapttutor_overlay_title(title: str) -> bool:
    """Launcher sets WM title like 'AdaptTutor — Study — p1 — …'; never treat as document context."""
    t = (title or "").strip()
    return t.startswith("AdaptTutor —")


def _title_has_study_keyword(title: str) -> bool:
    """Substring match on extensions / terms (browsers and generic study strings)."""
    t = (title or "").lower()
    if not t:
        return False
    return any(k in t for k in STUDY_KEYWORDS)


def _title_has_native_study_suffix(title: str) -> bool:
    """
    Native apps: e.g. 'Document1.docx - Word', 'Chapter3.pdf - Adobe Acrobat'.
    Match known ' - AppName' endings (case-insensitive).
    """
    t = (title or "").strip().lower()
    if not t:
        return False
    return any(t.endswith(suffix) for suffix in STUDY_APP_TITLE_SUFFIXES)


def _is_study_title(title: str) -> bool:
    if not (title or "").strip():
        return False
    return _title_has_study_keyword(title) or _title_has_native_study_suffix(title)

_PDF_PAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bpage\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*/\s*\d+\b"),
    re.compile(r"\b(\d+)\s+of\s+\d+\b", re.IGNORECASE),
]


def _extract_page_number(title: str) -> int:
    t = (title or "").strip()
    for pat in _PDF_PAGE_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        try:
            n = int(m.group(1))
            return n if n >= 1 else 1
        except Exception:
            continue
    return 1


@dataclass(frozen=True)
class WatcherState:
    current_context: str
    study_active: bool
    current_page: int


class WindowWatcher(threading.Thread):
    def __init__(
        self,
        *,
        poll_seconds: float = 3.0,
        on_change: Optional[Callable[[WatcherState], None]] = None,
        show_launcher: Optional[Callable[[], None]] = None,
        hide_launcher: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(daemon=True)
        self._poll_seconds = poll_seconds
        self._on_change = on_change
        self._show_launcher = show_launcher
        self._hide_launcher = hide_launcher
        self._stop = threading.Event()
        self._lock = threading.Lock()

        # Shared variables requested by PRD Step 1/Watcher spec
        self.study_active: bool = False
        self.current_context: str = ""
        self.current_page: int = 1

        self._state = WatcherState(current_context="", study_active=False, current_page=1)

    def stop(self) -> None:
        self._stop.set()

    def get_state(self) -> WatcherState:
        with self._lock:
            return self._state

    def run(self) -> None:
        last_title = None
        last_study = None
        last_page = None

        while not self._stop.is_set():
            title = _safe_get_active_window_title()
            print(f"Active window: {title}")
            # Ignore our own overlay windows and transient empty titles.
            # Some overrideredirect Tk windows can momentarily report blank titles
            # while focus shifts, which would otherwise flip study_active False and
            # briefly hide the launcher/bubble.
            if _is_adapttutor_overlay_title(title) or not (title or "").strip():
                self._stop.wait(self._poll_seconds)
                continue

            study = _is_study_title(title)
            page = _extract_page_number(title)

            if title != last_title or study != last_study or page != last_page:
                state = WatcherState(current_context=title, study_active=study, current_page=page)
                with self._lock:
                    self._state = state
                    self.study_active = study
                    self.current_context = title
                    self.current_page = page

                if self._on_change:
                    try:
                        self._on_change(state)
                    except Exception:
                        pass

                # Wire watcher -> launcher visibility.
                if study != last_study:
                    if study:
                        if self._show_launcher:
                            try:
                                self._show_launcher()
                            except Exception:
                                pass
                    else:
                        if self._hide_launcher:
                            try:
                                self._hide_launcher()
                            except Exception:
                                pass

                last_title = title
                last_study = study
                last_page = page

            self._stop.wait(self._poll_seconds)

