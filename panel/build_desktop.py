"""Bundle the panel into a single desktop executable with PyInstaller.

    python panel/build_desktop.py

Output: dist/Instagram Panel(.exe). Bundles panel/index.html and, if present,
panel/bin/cloudflared[.exe]. The token is NOT bundled — the .exe still reads
.mcp.json next to it at runtime (and writes panel/state.json beside itself).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "panel"
SEP = ";" if sys.platform == "win32" else ":"
CF = PANEL / "bin" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")

args = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
    "--name", "Instagram Panel",
    "--onefile", "--windowed",
    "--paths", str(ROOT),
    "--add-data", f"{PANEL / 'index.html'}{SEP}panel",
    "--collect-submodules", "instagram_mcp",
    "--collect-submodules", "panel",
    "--collect-all", "fastmcp",
    "--collect-all", "uvicorn",
    "--collect-all", "webview",
    "--hidden-import", "uvicorn.loops.asyncio",
    "--hidden-import", "uvicorn.protocols.http.h11_impl",
    "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
    "--hidden-import", "uvicorn.lifespan.on",
]
if CF.exists():
    args += ["--add-data", f"{CF}{SEP}panel/bin"]
else:
    print(f"note: {CF} not found — the .exe will fetch cloudflared on first run "
          "or expect it on PATH")
args += [str(PANEL / "desktop.py")]

print(" ".join(f'"{a}"' if " " in a else a for a in args))
raise SystemExit(subprocess.call(args, cwd=ROOT))
