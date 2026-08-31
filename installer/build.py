"""One command to produce the Windows installer.

    python installer/build.py

1. PyInstaller  -> dist/Instagram Panel.exe   (via panel/build_desktop.py)
2. Inno Setup   -> installer/Output/Instagram-Panel-Setup.exe

Needs Inno Setup 6 (ISCC.exe). Install it once:  winget install JRSoftware.InnoSetup
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISS = ROOT / "installer" / "setup.iss"
VERSION = os.environ.get("PANEL_VERSION", "0.1.0")

_ISCC_CANDIDATES = [
    Path(os.environ.get("ISCC", "")),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
    Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
]


def _find_iscc() -> str:
    from shutil import which
    for c in _ISCC_CANDIDATES:
        if c and c.is_file():
            return str(c)
    w = which("iscc") or which("ISCC")
    if w:
        return w
    sys.exit("ISCC.exe not found — install Inno Setup 6 (winget install JRSoftware.InnoSetup) "
             "or set the ISCC env var to its path.")


def main() -> None:
    if sys.platform != "win32":
        sys.exit("the installer target is Windows only")

    print("[1/2] PyInstaller ...")
    rc = subprocess.call([sys.executable, str(ROOT / "panel" / "build_desktop.py")], cwd=ROOT)
    if rc != 0:
        sys.exit(f"PyInstaller failed ({rc})")
    exe = ROOT / "dist" / "Instagram Panel.exe"
    if not exe.is_file():
        sys.exit(f"expected {exe} — PyInstaller did not produce it")

    print("[2/2] Inno Setup ...")
    iscc = _find_iscc()
    rc = subprocess.call([iscc, f"/DMyAppVersion={VERSION}", f"/DRepoRoot={ROOT}", str(ISS)], cwd=ROOT)
    if rc != 0:
        sys.exit(f"ISCC failed ({rc})")

    out = ROOT / "installer" / "Output" / "Instagram-Panel-Setup.exe"
    print(f"\n  done -> {out}  ({out.stat().st_size / 1e6:.0f} MB)" if out.is_file() else "\n  done (check installer/Output)")


if __name__ == "__main__":
    main()
