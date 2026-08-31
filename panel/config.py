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


_BLANK = {
    "mcpServers": {
        "instagram": {
            "command": "instagram-mcp",
            "env": {
                "INSTAGRAM_MCP_ACCESS_TOKEN": "",
                "INSTAGRAM_MCP_IG_USER_ID": "",
                "INSTAGRAM_MCP_BASE_HOST": "graph.instagram.com",
            },
        }
    }
}


def has_token() -> bool:
    return bool(os.environ.get("INSTAGRAM_MCP_ACCESS_TOKEN"))


def load_env_from_mcp_json() -> dict[str, str]:
    """Populate os.environ from .mcp.json. Missing file or empty token is NOT fatal —
    the panel boots into a setup state so the user can paste a token in the Ayarlar
    tab (this is how the installed build starts on first run)."""
    if not MCP_JSON.exists():
        MCP_JSON.write_text(json.dumps(_BLANK, indent=2) + "\n", encoding="utf-8")
    try:
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
        env = data["mcpServers"]["instagram"]["env"]
    except (KeyError, TypeError, json.JSONDecodeError):
        MCP_JSON.write_text(json.dumps(_BLANK, indent=2) + "\n", encoding="utf-8")
        env = _BLANK["mcpServers"]["instagram"]["env"]
    for k, v in env.items():
        if v:
            os.environ.setdefault(k, str(v))
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return env
