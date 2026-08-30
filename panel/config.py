"""Load the Instagram token/config from the project .mcp.json and put it in the env
so `instagram_mcp` resolves the same account the MCP server uses. No separate .env.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_JSON = ROOT / ".mcp.json"

MEDIA_DIR = Path(__file__).parent / "media"
QUEUE_DB = Path(__file__).parent / "queue.db"

PANEL_PORT = int(os.environ.get("IG_PANEL_PORT", "8787"))
MEDIA_PORT = int(os.environ.get("IG_PANEL_MEDIA_PORT", "8788"))


def load_env_from_mcp_json() -> dict[str, str]:
    if not MCP_JSON.exists():
        raise SystemExit(
            f"{MCP_JSON} not found. Copy .mcp.json.example to .mcp.json and fill in "
            "INSTAGRAM_MCP_ACCESS_TOKEN + INSTAGRAM_MCP_IG_USER_ID (see SETUP.md)."
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
