"""Load the Instagram token/config from .mcp.json and put it in the env so
`instagram_mcp` resolves the same account the MCP server uses. No separate .env.

Path model:
  * source checkout — .mcp.json at the repo root; runtime files under panel/.
  * frozen .exe (PyInstaller) — everything lives next to the executable, so the
    user drops their .mcp.json beside "Instagram Panel.exe" and media/queue/state
    are written there too.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    DATA_DIR = Path(sys.executable).resolve().parent
    MCP_JSON = DATA_DIR / ".mcp.json"
    _RUNTIME = DATA_DIR
else:
    ROOT = Path(__file__).resolve().parent.parent
    MCP_JSON = ROOT / ".mcp.json"
    _RUNTIME = Path(__file__).resolve().parent

MEDIA_DIR = _RUNTIME / "media"
QUEUE_DB = _RUNTIME / "queue.db"
STATE_JSON = _RUNTIME / "state.json"

PANEL_PORT = int(os.environ.get("IG_PANEL_PORT", "8787"))
MEDIA_PORT = int(os.environ.get("IG_PANEL_MEDIA_PORT", "8788"))


def load_env_from_mcp_json() -> dict[str, str]:
    if not MCP_JSON.exists():
        raise SystemExit(
            f"{MCP_JSON} not found. "
            + ("Put your .mcp.json next to the executable "
               if _FROZEN else "Copy .mcp.json.example to .mcp.json ")
            + "and fill in INSTAGRAM_MCP_ACCESS_TOKEN + INSTAGRAM_MCP_IG_USER_ID (see SETUP.md)."
        )
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    try:
        env = data["mcpServers"]["instagram"]["env"]
    except (KeyError, TypeError) as exc:
        raise SystemExit(f"{MCP_JSON}: mcpServers.instagram.env missing") from exc
    for k, v in env.items():
        if v:
            os.environ.setdefault(k, str(v))
    if not os.environ.get("INSTAGRAM_MCP_ACCESS_TOKEN"):
        raise SystemExit("INSTAGRAM_MCP_ACCESS_TOKEN is empty in .mcp.json")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return env
