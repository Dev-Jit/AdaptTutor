from __future__ import annotations

from .overlay import OverlayManager


def main() -> None:
    """
    AdaptTutor entry point:

    1. Build the overlay (hidden root Tk, launcher toplevel, no menu or feature panel).
    2. Start daemon background threads — window watcher (active title / study / page) and
       clipboard monitor (Instant Explain bubble when study is active).
    3. Run the Tk main loop on the launcher host window.

    On launch, ``OverlayManager.run_main_loop`` clears any menu/panel so only the launcher
    circle can appear (when the watcher decides study is active). Choosing a menu feature
    always closes the previous feature panel first — see ``OverlayManager._open_feature_panel``.
    """
    app = OverlayManager()
    assert app._watcher.daemon, "WindowWatcher must be a daemon thread"
    assert app._clipboard.daemon, "ClipboardMonitor must be a daemon thread"

    app.start_background_threads()
    app.run_main_loop()


if __name__ == "__main__":
    main()
