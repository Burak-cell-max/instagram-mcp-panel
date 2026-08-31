"""Native-window version of the panel — same server, no browser, no terminal.

    python -m panel.desktop

Needs `pywebview` (`pip install pywebview`). On Windows it uses the built-in
WebView2 runtime. Closing the window shuts the panel + tunnel down. If a native
window can't be created (rare — headless session, missing WebView2), it falls
back to opening the panel in the default browser.
"""

from __future__ import annotations

import sys
import time
import traceback
import webbrowser

from panel.config import DATA_DIR as _DATA_DIR
from panel.run import Panel

_LOG = _DATA_DIR / "panel.log"


def _tee_logs() -> None:
    """Frozen apps have no console — mirror stdout/stderr to panel.log so a failed
    launch leaves a trace the user can send us."""
    if not getattr(sys, "frozen", False):
        return
    try:
        fh = _LOG.open("w", encoding="utf-8", buffering=1)
    except Exception:  # noqa: BLE001
        return

    class _Tee:
        def __init__(self, *streams):  # noqa: ANN002
            self.streams = [s for s in streams if s]
            self.encoding = "utf-8"

        def write(self, data):  # noqa: ANN001
            for s in self.streams:
                try:
                    s.write(data)
                except Exception:  # noqa: BLE001, S110
                    pass

        def flush(self):
            for s in self.streams:
                try:
                    s.flush()
                except Exception:  # noqa: BLE001, S110
                    pass

        def isatty(self) -> bool:
            return False

        def writable(self) -> bool:
            return True

        def fileno(self):
            raise OSError("no fileno")

    sys.stdout = _Tee(sys.__stdout__, fh)
    sys.stderr = _Tee(sys.__stderr__, fh)


def main() -> None:
    _tee_logs()
    try:
        _main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise


def _main() -> None:
    p = Panel()
    p.start_backend()
    p.start_control_bg()
    time.sleep(1.0)  # let uvicorn bind

    try:
        import webview
    except ImportError:
        webview = None

    if webview is not None:
        try:
            window = webview.create_window(
                "Instagram Panel", p.url, width=1180, height=900, min_size=(900, 640)
            )
            window.events.closed += p.shutdown
            webview.start()          # blocks until the window closes
            return
        except Exception as exc:  # noqa: BLE001
            print(f"  native window unavailable ({exc}) — opening in browser")

    # fallback: browser + keep the process alive on the control server
    try:
        webbrowser.open(p.url)
    except Exception:  # noqa: BLE001
        pass
    print(f"  panel: {p.url}  (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        p.shutdown()


if __name__ == "__main__":
    main()
