"""Start the local Instagram panel: media server + cloudflared tunnel + control UI.

    python -m panel.run            # opens the panel in your browser
    python -m panel.desktop        # opens it in a native window (pywebview)

Ctrl+C (or closing the window) stops everything.
"""

from __future__ import annotations

import threading
import webbrowser

import uvicorn

from panel import app as panel_app
from panel.config import MEDIA_PORT, PANEL_PORT


def _serve(asgi, port: int, name: str) -> uvicorn.Server:
    # log_config=None: skip uvicorn's colourized formatter, which calls
    # sys.stdout.isatty() and blows up in a --windowed frozen app (no real stdout).
    cfg = uvicorn.Config(asgi, host="127.0.0.1", port=port, log_level="warning",
                         log_config=None, access_log=False)
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, name=name, daemon=True).start()
    return srv


class Panel:
    """Runs the media server + tunnel + scheduler in background threads. The control
    server runs where you call serve_control() (blocking) — or start() it too."""

    def __init__(self) -> None:
        self.stop_evt = threading.Event()
        self._control: uvicorn.Server | None = None

    def start_backend(self) -> str:
        _serve(panel_app.media, MEDIA_PORT, "media")
        panel_app.tunnel.port = MEDIA_PORT
        print(f"  starting cloudflared tunnel -> :{MEDIA_PORT} ...")
        url = panel_app.tunnel.start()
        print(f"  media tunnel: {url}")
        threading.Thread(target=panel_app.run_scheduler, args=(self.stop_evt,),
                         name="scheduler", daemon=True).start()
        return url

    def start_control_bg(self) -> None:
        self._control = _serve(panel_app.control, PANEL_PORT, "control")

    def serve_control(self) -> None:
        cfg = uvicorn.Config(panel_app.control, host="127.0.0.1", port=PANEL_PORT,
                             log_level="warning", log_config=None, access_log=False)
        self._control = uvicorn.Server(cfg)
        self._control.run()

    def shutdown(self) -> None:
        self.stop_evt.set()
        if self._control:
            self._control.should_exit = True
        panel_app.tunnel.stop()
        print("  stopped.")

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{PANEL_PORT}"


def main() -> None:
    p = Panel()
    p.start_backend()
    print(f"  panel: {p.url}")
    try:
        webbrowser.open(p.url)
    except Exception:  # noqa: BLE001
        pass
    try:
        p.serve_control()
    finally:
        p.shutdown()


if __name__ == "__main__":
    main()
