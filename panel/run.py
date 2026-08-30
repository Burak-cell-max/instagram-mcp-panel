"""Start the local Instagram panel: media server + cloudflared tunnel + control UI.

    python -m panel.run

Then open http://127.0.0.1:8787 in a browser. Ctrl+C stops everything.
"""

from __future__ import annotations

import threading
import webbrowser

import uvicorn

from panel.config import MEDIA_PORT, PANEL_PORT
from panel import app as panel_app


def _serve(asgi, port: int, name: str) -> uvicorn.Server:
    cfg = uvicorn.Config(asgi, host="127.0.0.1", port=port, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, name=name, daemon=True).start()
    return srv


def main() -> None:
    stop_evt = threading.Event()

    _serve(panel_app.media, MEDIA_PORT, "media")

    panel_app.tunnel.port = MEDIA_PORT
    print(f"  starting cloudflared tunnel -> :{MEDIA_PORT} ...")
    url = panel_app.tunnel.start()
    print(f"  media tunnel: {url}")

    threading.Thread(target=panel_app.run_scheduler, args=(stop_evt,),
                     name="scheduler", daemon=True).start()

    print(f"  panel: http://127.0.0.1:{PANEL_PORT}")
    try:
        webbrowser.open(f"http://127.0.0.1:{PANEL_PORT}")
    except Exception:  # noqa: BLE001
        pass

    cfg = uvicorn.Config(panel_app.control, host="127.0.0.1", port=PANEL_PORT, log_level="warning")
    try:
        uvicorn.Server(cfg).run()
    finally:
        stop_evt.set()
        panel_app.tunnel.stop()
        print("  stopped.")


if __name__ == "__main__":
    main()
