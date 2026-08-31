"""Account + token management for the panel.

`.mcp.json` stays the source of truth for the token (shared with the MCP server).
`panel/state.json` (gitignored) holds derived metadata the token itself doesn't
carry — when it was last set, and the lifetime the last refresh reported — so the
panel can show a "N days left" countdown and warn before it expires.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from panel.config import MCP_JSON, STATE_JSON

STATE_PATH = STATE_JSON
_DEFAULT_LIFETIME = 60 * 24 * 3600  # Instagram long-lived tokens: ~60 days
_GRAPH = "graph.instagram.com"
_VER = os.environ.get("INSTAGRAM_MCP_GRAPH_VERSION", "v21.0")


# --------------------------------------------------------------------------- #
# state.json
# --------------------------------------------------------------------------- #
def _load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_state(d: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")


def mark_token_set(expires_in: int | None = None) -> None:
    st = _load_state()
    st["token_set_at"] = int(time.time())
    st["token_lifetime"] = int(expires_in) if expires_in else _DEFAULT_LIFETIME
    _save_state(st)


def token_days_left() -> float | None:
    st = _load_state()
    if not st.get("token_set_at"):
        return None
    end = st["token_set_at"] + st.get("token_lifetime", _DEFAULT_LIFETIME)
    return round((end - time.time()) / 86400, 1)


# --------------------------------------------------------------------------- #
# .mcp.json read / write
# --------------------------------------------------------------------------- #
def _read_mcp() -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    env = data["mcpServers"]["instagram"]["env"]
    return data, env


def _write_token(token: str, ig_user_id: str | None = None) -> None:
    data, env = _read_mcp()
    env["INSTAGRAM_MCP_ACCESS_TOKEN"] = token
    if ig_user_id:
        env["INSTAGRAM_MCP_IG_USER_ID"] = ig_user_id
    MCP_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    # instagram_mcp.auth reads os.environ on every call — keep it in sync
    os.environ["INSTAGRAM_MCP_ACCESS_TOKEN"] = token
    if ig_user_id:
        os.environ["INSTAGRAM_MCP_IG_USER_ID"] = ig_user_id


def _current() -> tuple[str, str, str]:
    _, env = _read_mcp()
    return (
        env.get("INSTAGRAM_MCP_ACCESS_TOKEN", ""),
        env.get("INSTAGRAM_MCP_IG_USER_ID", ""),
        env.get("INSTAGRAM_MCP_BASE_HOST", "graph.facebook.com"),
    )


# --------------------------------------------------------------------------- #
# operations
# --------------------------------------------------------------------------- #
def status() -> dict[str, Any]:
    token, uid, host = _current()
    out: dict[str, Any] = {
        "ig_user_id": uid,
        "base_host": host,
        "token_days_left": token_days_left(),
        "token_tail": token[-6:] if token else None,
        "valid": None,
    }
    if not token:
        out["valid"] = False
        return out
    try:
        me = httpx.get(
            f"https://{_GRAPH}/{_VER}/me",
            params={"fields": "user_id,username,account_type", "access_token": token},
            timeout=15,
        ).json()
        if "error" in me:
            out["valid"] = False
            out["error"] = me["error"].get("message")
        else:
            out["valid"] = True
            out["username"] = me.get("username")
            out["account_type"] = me.get("account_type")
    except Exception as exc:  # noqa: BLE001
        out["valid"] = False
        out["error"] = str(exc)
    return out


def refresh() -> dict[str, Any]:
    """Extend the long-lived token by ~60 days. Call at most once per attempt —
    hammering this endpoint gets the token blocked (OAuthException code 200)."""
    token, _, _ = _current()
    if not token:
        return {"ok": False, "error": "no token configured"}
    r = httpx.get(
        f"https://{_GRAPH}/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=20,
    ).json()
    if "error" in r or "access_token" not in r:
        return {"ok": False, "error": (r.get("error") or {}).get("message", "refresh failed")}
    _write_token(r["access_token"])
    mark_token_set(r.get("expires_in"))
    return {"ok": True, "token_days_left": token_days_left()}


def set_token(new_token: str, ig_user_id: str | None = None) -> dict[str, Any]:
    new_token = new_token.strip()
    if not new_token.startswith(("IGAA", "EAA", "IGQV")):
        return {"ok": False, "error": "that doesn't look like a Graph API token"}
    try:
        me = httpx.get(
            f"https://{_GRAPH}/{_VER}/me",
            params={"fields": "user_id,username", "access_token": new_token},
            timeout=15,
        ).json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    if "error" in me:
        return {"ok": False, "error": me["error"].get("message", "token rejected")}
    _write_token(new_token, ig_user_id or me.get("user_id"))
    mark_token_set(None)
    return {"ok": True, "username": me.get("username"), "token_days_left": token_days_left()}
