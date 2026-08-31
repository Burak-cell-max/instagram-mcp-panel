"""Native-window version of the panel — same server, no browser, no terminal.

    python -m panel.desktop

Needs `pywebview` (`pip install pywebview`). On Windows it uses the built-in
WebView2 runtime. Closing the window shuts the panel + tunnel down.
"""

from __future__ import annotations

import sys
import threading

from panel.run import Panel


def main() -> None:
    try:
        import webview
    except ImportError:
        sys.exit("pywebview not installed — run: pip install pywebview")

    p = Panel()
    p.start_backend()
    p.start_control_bg()

    window = webview.create_window("Instagram Panel", p.url, width=1180, height=900, min_size=(900, 640))

    def _on_closed() -> None:
        p.shutdown()

    window.events.closed += _on_closed
    # give uvicorn a beat to bind before the webview loads the URL
    threading.Event().wait(1.5)
    webview.start()


if __name__ == "__main__":
    main()
