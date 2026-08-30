"""Manage a cloudflared quick tunnel as a child process.

A quick tunnel needs no Cloudflare account: `cloudflared tunnel --url http://localhost:PORT`
prints a public https://<random>.trycloudflare.com URL that proxies to the local port.
We only ever point it at the media server (static files), never the control API.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

_BUNDLED = Path(__file__).parent / "bin" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _resolve_bin() -> str | None:
    if _BUNDLED.exists():
        return str(_BUNDLED)
    return shutil.which("cloudflared")


class Tunnel:
    def __init__(self, port: int) -> None:
        self.port = port
        self.url: str | None = None
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def start(self, timeout: float = 40.0) -> str:
        with self._lock:
            if self.url and self._proc and self._proc.poll() is None:
                return self.url
            binary = _resolve_bin()
            if not binary:
                raise RuntimeError(
                    "cloudflared not found. Put it at panel/bin/cloudflared[.exe] "
                    "(python -m panel.get_cloudflared) or install it on PATH."
                )
            self._proc = subprocess.Popen(
                [binary, "tunnel", "--url", f"http://localhost:{self.port}", "--no-autoupdate"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            deadline = time.time() + timeout
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                m = _URL_RE.search(line)
                if m:
                    self.url = m.group(0)
                    threading.Thread(target=self._drain, daemon=True).start()
                    return self.url
                if time.time() > deadline:
                    break
            self.stop()
            raise RuntimeError("cloudflared did not report a tunnel URL in time")

    def _drain(self) -> None:
        if not self._proc or not self._proc.stdout:
            return
        for _ in self._proc.stdout:
            pass

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self.url = None

    @property
    def alive(self) -> bool:
        return bool(self._proc and self._proc.poll() is None and self.url)
