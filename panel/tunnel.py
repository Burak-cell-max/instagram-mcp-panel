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

_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _resolve_bin(auto_download: bool = True) -> str | None:
    """Bundled binary -> PATH -> (last resort) download it. cloudflared is a single
    static binary from Cloudflare's GitHub releases; a "quick tunnel" needs no account."""
    from panel import get_cloudflared

    if get_cloudflared.bundled_path().exists():
        return str(get_cloudflared.bundled_path())
    on_path = shutil.which("cloudflared")
    if on_path:
        return on_path
    if auto_download:
        try:
            print("  cloudflared not found — downloading it once (~30-60 MB) ...")
            return str(get_cloudflared.main())
        except Exception as exc:  # noqa: BLE001
            print(f"  auto-download failed: {exc}")
    return None


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
                    "cloudflared unavailable — auto-download failed and it's not on PATH. "
                    "Install it manually (https://github.com/cloudflare/cloudflared) "
                    "or run: python -m panel.get_cloudflared"
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
