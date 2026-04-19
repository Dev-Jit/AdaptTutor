from __future__ import annotations

import ctypes
from ctypes import wintypes
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

from .config import (
    FEATURES,
    LAUNCHER_SIZE,
    MENU_ANIM_STEP_PX,
    MENU_ANIM_TICK_MS,
    MENU_GAP,
    MENU_PILL_HEIGHT,
    MENU_PILL_WIDTH,
    MENU_STAGGER_MS,
    PANEL_MAX_HEIGHT,
    PANEL_PAD,
    PANEL_WIDTH,
)
from .clipboard_monitor import ClipboardMonitor
from .features.explain_differently import ExplainDifferentlyPanel
from .features.instant_explain import (
    configure_bubble_host,
    dismiss_if_open as dismiss_instant_bubble,
    set_go_deeper_callback,
)
from .features.flashcard_generator import FlashcardGeneratorPanel
from .features.quiz_me import QuizMePanel
from .features.smart_summary import SmartSummaryPanel
from .theme import UiTheme, apply_topmost, load_ui_theme
from .tutor import ask
from .watcher import WatcherState, WindowWatcher


@dataclass(frozen=True)
class OverlayState:
    collapsed: bool = True
    menu_open: bool = False


class OverlayManager:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()  # keep a hidden root; UI lives in toplevels
        apply_topmost(self.root)
        self._theme: UiTheme = load_ui_theme()
        self._state = OverlayState(collapsed=True, menu_open=False)

        self._launcher = _LauncherCircle(
            on_toggle_menu=self._toggle_menu,
            theme=self._theme,
        )
        # Hide immediately (prevents any initial visibility).
        self._launcher.hide()
        self._menu: Optional[_MenuWindow] = None
        self._panel: Optional[_FeaturePanel] = None

        self._watcher = WindowWatcher(
            on_change=self._on_watcher_change,
            show_launcher=self.show_launcher,
            hide_launcher=self.hide_launcher,
        )

        configure_bubble_host(self._launcher.window, self._theme)
        set_go_deeper_callback(self._on_instant_go_deeper)
        self._clipboard = ClipboardMonitor(
            get_study_active=lambda: self._watcher.get_state().study_active,
            schedule_ui=lambda fn: self._launcher.window.after(0, fn),
        )

        # "click outside" close: global mouse press handler
        self.root.bind_all("<Button-1>", self._on_global_click, add="+")
        self._launcher.window.protocol("WM_DELETE_WINDOW", self.stop)
        self._launcher.window.bind("<Escape>", lambda _e: self._close_menu())

    def start_background_threads(self) -> None:
        """
        Start daemon background threads before the Tk main loop.
        WindowWatcher and ClipboardMonitor both subclass threading.Thread with daemon=True.
        """
        if not self._watcher.is_alive():
            self._watcher.start()
        if not self._clipboard.is_alive():
            self._clipboard.start()

    def run_main_loop(self) -> None:
        """No feature panel or menu; launcher is the only UI until the user opens the menu (watcher may hide/show the circle)."""
        self._ensure_minimal_startup_ui()
        self._launcher.window.after(100, self._tick_position)
        self._launcher.window.mainloop()

    def _ensure_minimal_startup_ui(self) -> None:
        self._close_menu()
        self._close_feature_panel()
        self._state = OverlayState(collapsed=True, menu_open=False)

    def start(self) -> None:
        """Convenience: background threads + Tk main loop (same as main.py explicit sequence)."""
        self.start_background_threads()
        self.run_main_loop()

    def stop(self) -> None:
        try:
            self._clipboard.stop()
        except Exception:
            pass
        try:
            dismiss_instant_bubble()
        except Exception:
            pass
        try:
            self._watcher.stop()
        finally:
            try:
                self._launcher.window.destroy()
            except Exception:
                pass
            try:
                if self._menu:
                    self._menu.window.destroy()
            except Exception:
                pass
            try:
                if self._panel:
                    self._panel.destroy()
            except Exception:
                pass

    def _tick_position(self) -> None:
        # Keep bottom-right anchored even if resolution changes.
        apply_topmost(self._launcher.window)
        self._launcher.reposition()
        if self._menu:
            apply_topmost(self._menu.window)
            self._menu.reposition_relative_to(self._launcher.window)
        if self._panel:
            apply_topmost(self._panel.window)
            self._panel.reposition_to_launcher(self._launcher.window)
        self._launcher.window.after(500, self._tick_position)

    def _on_watcher_change(self, state: WatcherState) -> None:
        # Step 1: watcher is "live" and can be used for UX validation.
        # Keep UI-only behavior minimal; just surface state via tooltip-ish title.
        def apply() -> None:
            self._launcher.set_watcher_state(state)

        try:
            self._launcher.window.after(0, apply)
        except Exception:
            pass

    def show_launcher(self) -> None:
        def apply() -> None:
            self._launcher.show()

        try:
            self._launcher.window.after(0, apply)
        except Exception:
            pass

    def hide_launcher(self) -> None:
        def apply() -> None:
            self._close_menu()
            self._launcher.hide()

        try:
            self._launcher.window.after(0, apply)
        except Exception:
            pass

    def _toggle_menu(self) -> None:
        if self._menu and self._menu.is_open:
            self._close_menu()
        else:
            self._open_menu()

    def _open_menu(self) -> None:
        if self._menu and self._menu.is_open:
            return

        self._menu = _MenuWindow(
            anchor_window=self._launcher.window,
            on_request_close=self._close_menu,
            on_item_click=self._on_menu_item_click,
            theme=self._theme,
        )
        self._menu.open_with_animation()
        self._state = OverlayState(collapsed=False, menu_open=True)

    def _close_menu(self) -> None:
        if not self._menu:
            return
        self._menu.close()
        self._menu = None
        self._state = OverlayState(collapsed=True, menu_open=False)

    def _on_menu_item_click(self, name: str) -> None:
        self._close_menu()
        self._open_feature_panel(name)

    def _open_feature_panel(self, feature_name: str) -> None:
        # At most one feature panel: replace any existing panel before creating the next.
        if self._panel:
            self._panel.destroy()
            self._panel = None

        if feature_name == "Smart Summary":
            self._panel = SmartSummaryPanel(
                root=self.root,
                ui_root=self._launcher.window,
                get_watcher_state=self._watcher.get_state,
                on_close=self._close_feature_panel,
                theme=self._theme,
            )
            self._panel.reposition_to_launcher(self._launcher.window)
            return

        if feature_name == "Explain Differently":
            self._open_explain_differently_panel()
            return

        if feature_name == "Quiz Me":
            self._panel = QuizMePanel(
                root=self.root,
                ui_root=self._launcher.window,
                get_watcher_state=self._watcher.get_state,
                on_close=self._close_feature_panel,
                theme=self._theme,
            )
            self._panel.reposition_to_launcher(self._launcher.window)
            return

        if feature_name == "Flashcard Generator":
            self._panel = FlashcardGeneratorPanel(
                root=self.root,
                ui_root=self._launcher.window,
                get_watcher_state=self._watcher.get_state,
                on_close=self._close_feature_panel,
                theme=self._theme,
            )
            self._panel.reposition_to_launcher(self._launcher.window)
            return

        self._panel = _FeaturePanel(
            root=self.root,
            feature_title=feature_name,
            on_close=self._close_feature_panel,
            theme=self._theme,
        )
        self._panel.show_thinking()
        self._panel.reposition_to_launcher(self._launcher.window)
        apply_topmost(self._panel.window)

        system = (
            "You are AdaptTutor, a concise study assistant for desktop overlay use. "
            "Keep answers short unless the user asks for detail."
        )
        prompt = (
            f"The user chose the feature “{feature_name}” from the menu. "
            "Reply with one friendly sentence confirming you are ready to help with that feature."
        )

        def on_ok(text: str) -> None:
            if self._panel:
                self._panel.set_response(text)

        def on_err(err: BaseException) -> None:
            if self._panel:
                self._panel.set_response(f"Error: {err}")

        ask(
            prompt,
            system,
            max_tokens=600,
            on_complete=on_ok,
            on_error=on_err,
            ui_root=self._launcher.window,
        )

    def _open_explain_differently_panel(self, initial_concept: str = "", auto_submit: bool = False) -> None:
        self._panel = ExplainDifferentlyPanel(
            root=self.root,
            ui_root=self._launcher.window,
            on_close=self._close_feature_panel,
            theme=self._theme,
            initial_concept=initial_concept,
            auto_submit=auto_submit,
        )
        self._panel.reposition_to_launcher(self._launcher.window)

    def _on_instant_go_deeper(self, selected_text: str) -> None:
        # Route "Go Deeper" from Instant Explain into Explain Differently.
        # Auto-submit so the user gets deeper output in one click.
        if self._panel:
            try:
                self._panel.destroy()
            except Exception:
                pass
            self._panel = None
        self._close_menu()
        self._open_explain_differently_panel(initial_concept=selected_text, auto_submit=True)

    def _close_feature_panel(self) -> None:
        if not self._panel:
            return
        try:
            self._panel.destroy()
        except Exception:
            pass
        self._panel = None

    def _on_global_click(self, event: tk.Event) -> None:
        x_root = event.x_root
        y_root = event.y_root

        if self._panel and _point_in_window(self._panel.window, x_root, y_root):
            return
        if _point_in_window(self._launcher.window, x_root, y_root):
            return
        if self._menu and _point_in_window(self._menu.window, x_root, y_root):
            return

        if self._menu and self._menu.is_open:
            self._close_menu()
        if self._panel:
            self._close_feature_panel()


def _point_in_window(w: tk.Misc, x: int, y: int) -> bool:
    """
    Hit-test in screen coordinates. Do not rely on winfo_rootx/width alone for
    overrideredirect windows on Windows — they are often wrong until layout settles,
    which caused bind_all to treat in-panel clicks as "outside" and close the panel
    (breaking Generate, close ✕, etc.).
    """
    try:
        w.update_idletasks()
        hit = w.winfo_containing(x, y)
        if not hit:
            return False
        top = hit.winfo_toplevel()
        return str(top) == str(w.winfo_toplevel())
    except tk.TclError:
        return False


class _FeaturePanel:
    """Right-side feature panel: shows Thinking... then AI response (non-blocking via tutor.ask)."""

    def __init__(
        self,
        *,
        root: tk.Tk,
        feature_title: str,
        on_close: Callable[[], None],
        theme: UiTheme,
    ) -> None:
        self._on_close = on_close
        self._theme = theme
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=theme.window_bg)
        self.window.title("AdaptTutor — Panel")

        header = tk.Frame(self.window, bg=theme.window_bg)
        header.pack(fill="x", padx=PANEL_PAD, pady=(PANEL_PAD, 8))

        tk.Label(header, text=feature_title, bg=theme.window_bg, fg=theme.fg, font=("Segoe UI", 11, "bold")).pack(
            side="left"
        )

        close_lbl = tk.Label(header, text="✕", bg=theme.window_bg, fg=theme.fg, cursor="hand2", font=("Segoe UI", 12))
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self._on_close())

        body = tk.Frame(self.window, bg=theme.window_bg)
        body.pack(fill="both", expand=True, padx=PANEL_PAD, pady=(0, PANEL_PAD))

        self._thinking_lbl = tk.Label(
            body,
            text="",
            bg=theme.window_bg,
            fg=theme.thinking_fg,
            font=("Segoe UI", 10, "italic"),
        )
        self._thinking_lbl.pack(anchor="w", pady=(0, 4))

        text_row = tk.Frame(body, bg=theme.window_bg)
        text_row.pack(fill="both", expand=True)

        scroll = tk.Scrollbar(text_row)
        scroll.pack(side="right", fill="y")

        self._text = tk.Text(
            text_row,
            wrap="word",
            width=1,
            height=1,
            font=("Segoe UI", 10),
            bg=theme.text_readonly_bg,
            fg=theme.fg,
            relief="flat",
            highlightthickness=0,
            yscrollcommand=scroll.set,
        )
        self._text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self._text.yview)

        self.window.geometry(f"{PANEL_WIDTH}x{PANEL_MAX_HEIGHT}+0+0")

    def show_thinking(self) -> None:
        self._thinking_lbl.configure(text="Thinking…")
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", "")
        self._text.configure(state="disabled")

    def set_response(self, text: str) -> None:
        self._thinking_lbl.configure(text="")
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.configure(state="disabled")

    def reposition_to_launcher(self, launcher: tk.Toplevel) -> None:
        self.window.update_idletasks()
        launcher.update_idletasks()
        work = _get_windows_work_area()
        if work:
            _left, _top, right, bottom = work
        else:
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            right, bottom = sw, sh

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


def _get_windows_work_area() -> tuple[int, int, int, int] | None:
    """
    Returns (left, top, right, bottom) of the Windows work area (excluding taskbar).
    If unavailable, returns None.
    """
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


class _LauncherCircle:
    def __init__(self, *, on_toggle_menu: Callable[[], None], theme: UiTheme) -> None:
        self._theme = theme
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=theme.launcher_bg)
        self.window.attributes("-alpha", 1.0)
        self.window.title("AdaptTutor — Launcher")

        self._on_toggle_menu = on_toggle_menu

        self.canvas = tk.Canvas(
            self.window,
            width=LAUNCHER_SIZE,
            height=LAUNCHER_SIZE,
            highlightthickness=0,
            bg=theme.launcher_bg,
        )
        self.canvas.pack()

        pad = 2
        self._circle_id = self.canvas.create_oval(
            pad,
            pad,
            LAUNCHER_SIZE - pad,
            LAUNCHER_SIZE - pad,
            fill=theme.launcher_bg,
            outline="",
        )
        self._icon_id = self.canvas.create_text(
            LAUNCHER_SIZE // 2,
            LAUNCHER_SIZE // 2,
            text="🎓",
            fill="white",
            font=("Segoe UI Emoji", 18),
        )

        self.canvas.bind("<Button-1>", self._handle_click)
        self.canvas.bind("<Enter>", self._handle_enter)
        self.canvas.bind("<Leave>", self._handle_leave)

        self._watcher_state = WatcherState(current_context="", study_active=False, current_page=1)

        self.reposition()
        # Default to hidden until watcher says otherwise.
        self.window.withdraw()

    def show(self) -> None:
        # Ensure it's visible and above taskbar/other windows.
        self.window.attributes("-alpha", 1.0)
        self.window.deiconify()
        self.window.lift()
        apply_topmost(self.window)

    def hide(self) -> None:
        # Some Windows configs can show a withdrawn overrideredirect window
        # "behind" the taskbar; forcing alpha to 0 avoids any lingering visuals.
        self.window.attributes("-alpha", 0.0)
        self.window.withdraw()

    def reposition(self) -> None:
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()

        margin = 18
        work = _get_windows_work_area()
        if work:
            left, top, right, bottom = work
            x = right - LAUNCHER_SIZE - margin
            y = bottom - LAUNCHER_SIZE - margin
        else:
            x = sw - LAUNCHER_SIZE - margin
            y = sh - LAUNCHER_SIZE - margin
        self.window.geometry(f"{LAUNCHER_SIZE}x{LAUNCHER_SIZE}+{x}+{y}")

    def set_watcher_state(self, state: WatcherState) -> None:
        self._watcher_state = state
        # Lightweight feedback: title (helpful when running with taskbar / alt-tab).
        label = "Study" if state.study_active else "Idle"
        title_preview = (state.current_context or "").strip()
        if len(title_preview) > 50:
            title_preview = title_preview[:47] + "..."
        self.window.title(f"AdaptTutor — {label} — p{state.current_page} — {title_preview}")

    def _handle_click(self, _event: tk.Event) -> None:
        self._on_toggle_menu()

    def _handle_enter(self, _event: tk.Event) -> None:
        self.canvas.itemconfigure(self._circle_id, fill=self._theme.launcher_hover)

    def _handle_leave(self, _event: tk.Event) -> None:
        self.canvas.itemconfigure(self._circle_id, fill=self._theme.launcher_bg)


class _MenuWindow:
    def __init__(
        self,
        *,
        anchor_window: tk.Toplevel,
        on_request_close: Callable[[], None],
        on_item_click: Callable[[str], None],
        theme: UiTheme,
    ) -> None:
        self._theme = theme
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        apply_topmost(self.window)
        self.window.configure(bg=theme.menu_bg)
        self.window.title("AdaptTutor — Menu")

        self._anchor = anchor_window
        self._on_request_close = on_request_close
        self._on_item_click = on_item_click

        self.is_open = False

        # Build pills as frames placed inside a container.
        self.container = tk.Frame(self.window, bg=theme.menu_bg)
        self.container.pack(fill="both", expand=True)

        self._pill_frames: list[tk.Frame] = []
        self._pill_target_y: list[int] = []

        total_h = len(FEATURES) * MENU_PILL_HEIGHT + (len(FEATURES) - 1) * MENU_GAP
        self.window.geometry(f"{MENU_PILL_WIDTH}x{total_h}+0+0")
        self.reposition_relative_to(anchor_window)

        for idx, (name, accent, icon) in enumerate(FEATURES):
            pill = _PillButton(
                master=self.container,
                text=name,
                icon=icon,
                accent=accent,
                command=lambda n=name: self._on_item_click(n),
                theme=theme,
            )
            pill.frame.place(x=0, y=total_h, width=MENU_PILL_WIDTH, height=MENU_PILL_HEIGHT)
            self._pill_frames.append(pill.frame)

            target_y = total_h - (idx + 1) * MENU_PILL_HEIGHT - idx * MENU_GAP
            self._pill_target_y.append(target_y)

    def reposition_relative_to(self, anchor: tk.Toplevel) -> None:
        anchor.update_idletasks()
        self.window.update_idletasks()

        ax = anchor.winfo_rootx()
        ay = anchor.winfo_rooty()

        w = self.window.winfo_width()
        h = self.window.winfo_height()
        # Align right edges; menu opens upward from circle.
        x = ax + (LAUNCHER_SIZE - w)
        y = ay - h - 10
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def open_with_animation(self) -> None:
        if self.is_open:
            return
        self.is_open = True
        self.window.deiconify()
        apply_topmost(self.window)

        for i, frame in enumerate(self._pill_frames):
            self.window.after(i * MENU_STAGGER_MS, lambda idx=i: self._animate_pill_in(idx))

    def _animate_pill_in(self, idx: int) -> None:
        if not self.is_open:
            return
        frame = self._pill_frames[idx]
        target_y = self._pill_target_y[idx]
        cur = int(float(frame.place_info().get("y", 0)))
        if cur <= target_y:
            frame.place_configure(y=target_y)
            return
        frame.place_configure(y=max(target_y, cur - MENU_ANIM_STEP_PX))
        self.window.after(MENU_ANIM_TICK_MS, lambda: self._animate_pill_in(idx))

    def close(self) -> None:
        if not self.is_open:
            return
        self.is_open = False
        try:
            self.window.destroy()
        except Exception:
            pass


class _PillButton:
    def __init__(
        self,
        *,
        master: tk.Misc,
        text: str,
        icon: str,
        accent: str,
        command: Callable[[], None],
        theme: UiTheme,
    ) -> None:
        self._accent = accent
        self._command = command
        self._base_bg = theme.menu_bg

        frame = tk.Frame(master, bg=theme.menu_bg, highlightthickness=1, highlightbackground=theme.pill_border)
        self.frame = frame

        accent_bar = tk.Frame(frame, bg=accent, width=6)
        accent_bar.pack(side="left", fill="y")

        inner = tk.Frame(frame, bg=theme.menu_bg)
        inner.pack(side="left", fill="both", expand=True)

        icon_lbl = tk.Label(inner, text=icon, bg=theme.menu_bg, fg=theme.fg, font=("Segoe UI Emoji", 12))
        icon_lbl.pack(side="left", padx=(10, 8))

        txt_lbl = tk.Label(inner, text=text, bg=theme.menu_bg, fg=theme.fg, font=("Segoe UI", 10, "normal"))
        txt_lbl.pack(side="left")

        for w in (frame, accent_bar, inner, icon_lbl, txt_lbl):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_click(self, _e: tk.Event) -> None:
        self._command()

    def _on_enter(self, _e: tk.Event) -> None:
        tint = _tint_color(self._accent, 0.92)
        self._set_bg(tint)

    def _on_leave(self, _e: tk.Event) -> None:
        self._set_bg(self._base_bg)

    def _set_bg(self, bg: str) -> None:
        # Frame + inner labels share background.
        self.frame.configure(bg=bg)
        for child in self.frame.winfo_children():
            try:
                child.configure(bg=bg)
            except Exception:
                pass
            for grand in getattr(child, "winfo_children", lambda: [])():
                try:
                    grand.configure(bg=bg)
                except Exception:
                    pass


def _tint_color(hex_color: str, mix: float) -> str:
    """
    mix in [0..1]: 1 => original, 0 => white.
    """
    c = hex_color.lstrip("#")
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)

    rr = int(r * mix + 255 * (1 - mix))
    gg = int(g * mix + 255 * (1 - mix))
    bb = int(b * mix + 255 * (1 - mix))
    return f"#{rr:02X}{gg:02X}{bb:02X}"

