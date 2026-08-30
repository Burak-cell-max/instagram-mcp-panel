"""Download the cloudflared binary into panel/bin/ for the current platform.

    python -m panel.get_cloudflared

cloudflared is Cloudflare's tunnel client (MIT / Apache-2.0). A "quick tunnel"
needs no Cloudflare account — it just gives the panel a temporary public https URL
so Instagram can fetch uploaded media. Nothing else is exposed.
"""

from __future__ import annotations

import platform
import stat
import sys
import urllib.request
from pathlib import Path

BIN_DIR = Path(__file__).parent / "bin"
BASE = "https://github.com/cloudflare/cloudflared/releases/latest/download/"

_ASSETS = {
    ("windows", "amd64"): ("cloudflared-windows-amd64.exe", "cloudflared.exe"),
    ("windows", "arm64"): ("cloudflared-windows-arm64.exe", "cloudflared.exe"),
    ("linux", "amd64"): ("cloudflared-linux-amd64", "cloudflared"),
    ("linux", "arm64"): ("cloudflared-linux-arm64", "cloudflared"),
    ("darwin", "amd64"): ("cloudflared-darwin-amd64.tgz", "cloudflared"),
    ("darwin", "arm64"): ("cloudflared-darwin-arm64.tgz", "cloudflared"),
}


def _arch() -> str:
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "amd64"
    if m in {"arm64", "aarch64"}:
        return "arm64"
    return m


def main() -> None:
    key = (sys.platform if sys.platform != "win32" else "windows", _arch())
    key = ("windows" if key[0] == "windows" else key[0], key[1])
    if sys.platform.startswith("linux"):
        key = ("linux", _arch())
    if sys.platform == "darwin":
        key = ("darwin", _arch())
    if sys.platform == "win32":
        key = ("windows", _arch())

    if key not in _ASSETS:
        sys.exit(f"No cloudflared asset for {key}. Install it manually and put it on PATH.")
    asset, local = _ASSETS[key]
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = BIN_DIR / local

    if asset.endswith(".tgz"):
        import io
        import tarfile
        print(f"downloading {asset} ...")
        data = urllib.request.urlopen(BASE + asset).read()  # noqa: S310
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            member = next(m for m in tf.getmembers() if m.name.endswith("cloudflared"))
            with tf.extractfile(member) as src, dest.open("wb") as out:  # type: ignore[union-attr]
                out.write(src.read())
    else:
        print(f"downloading {asset} ...")
        urllib.request.urlretrieve(BASE + asset, dest)  # noqa: S310

    if sys.platform != "win32":
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  -> {dest}")


if __name__ == "__main__":
    main()
