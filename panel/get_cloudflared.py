"""Download the cloudflared binary for the current platform.

    python -m panel.get_cloudflared

cloudflared is Cloudflare's tunnel client (Apache-2.0), a single static binary. A
"quick tunnel" needs no Cloudflare account — it just gives the panel a temporary
public https URL so Instagram can fetch uploaded media. Nothing else is exposed.
The panel calls this automatically on first run if the binary is missing.
"""

from __future__ import annotations

import io
import platform
import stat
import sys
import tarfile
import urllib.request
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)
BIN_DIR = (Path(sys.executable).resolve().parent / "bin") if _FROZEN \
    else (Path(__file__).resolve().parent / "bin")

BASE = "https://github.com/cloudflare/cloudflared/releases/latest/download/"
_LOCAL = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"


def bundled_path() -> Path:
    return BIN_DIR / _LOCAL


def _arch() -> str:
    m = platform.machine().lower()
    return {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(m, m)


def _asset() -> str:
    arch = _arch()
    if sys.platform == "win32":
        return f"cloudflared-windows-{arch}.exe"
    if sys.platform == "darwin":
        return f"cloudflared-darwin-{arch}.tgz"
    if sys.platform.startswith("linux"):
        return f"cloudflared-linux-{arch}"
    raise SystemExit(f"no cloudflared build for {sys.platform}/{arch} — install it on PATH")


def main() -> Path:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = bundled_path()
    if dest.exists():
        return dest
    asset = _asset()
    print(f"  downloading {asset} -> {dest}")
    data = urllib.request.urlopen(BASE + asset).read()  # noqa: S310
    if asset.endswith(".tgz"):
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            member = next(m for m in tf.getmembers() if m.name.rsplit("/", 1)[-1] == "cloudflared")
            with tf.extractfile(member) as src, dest.open("wb") as out:  # type: ignore[union-attr]
                out.write(src.read())
    else:
        dest.write_bytes(data)
    if sys.platform != "win32":
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return dest


if __name__ == "__main__":
    print(f"  -> {main()}")
