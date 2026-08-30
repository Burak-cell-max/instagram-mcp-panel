"""Local Instagram publishing panel.

Two ASGI apps:
  * control  — the UI + JSON API, bound to 127.0.0.1 only.
  * media    — static file server for panel/media, the ONLY thing the cloudflared
               tunnel exposes publicly (so Instagram can fetch the bytes).

run.py wires them together with the tunnel.
"""

from __future__ import annotations

import json
import mimetypes
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from panel.config import MEDIA_DIR, load_env_from_mcp_json

load_env_from_mcp_json()  # must run before importing instagram_mcp

from fastapi import FastAPI, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from instagram_mcp import auth as ig_auth  # noqa: E402
from instagram_mcp import server as ig  # noqa: E402
from instagram_mcp import validators as V  # noqa: E402
from panel import store  # noqa: E402
from panel.tunnel import Tunnel  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png"}
VIDEO_EXT = {".mp4", ".mov"}

tunnel = Tunnel(port=0)  # port is set by run.py before start()

# --------------------------------------------------------------------------- #
# media app (public via tunnel)
# --------------------------------------------------------------------------- #
media = FastAPI(title="ig-panel-media")
media.mount("/m", StaticFiles(directory=str(MEDIA_DIR)), name="m")


@media.get("/healthz")
def _healthz() -> dict[str, str]:
    return {"ok": "1"}


# --------------------------------------------------------------------------- #
# control app (localhost only)
# --------------------------------------------------------------------------- #
control = FastAPI(title="ig-panel")

INDEX = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@control.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX


def _public_url(filename: str) -> str:
    if not tunnel.alive:
        tunnel.start()
    return f"{tunnel.url}/m/{filename}"


def _kind_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return "unknown"


@control.get("/api/state")
def state() -> dict[str, Any]:
    health = ig.healthcheck()
    limit = ig.publishing_limit()
    quota = None
    try:
        cfg = (limit.get("limit") or [{}])[0]
        quota = {
            "used": cfg.get("quota_usage"),
            "total": (cfg.get("config") or {}).get("quota_total"),
        }
    except Exception:  # noqa: BLE001
        pass
    return {
        "health": health,
        "quota": quota,
        "tunnel": tunnel.url if tunnel.alive else None,
    }


@control.post("/api/upload")
async def upload(file: UploadFile) -> dict[str, Any]:
    orig = Path(file.filename or "upload.bin")
    ext = orig.suffix.lower()
    if ext not in IMAGE_EXT | VIDEO_EXT:
        raise HTTPException(400, f"unsupported type {ext!r}; allowed: jpg png mp4 mov")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = MEDIA_DIR / name
    size = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            fh.write(chunk)
    return {"filename": name, "size": size, "kind": _kind_for(dest),
            "url_hint": f"/m/{name}"}


def _wait_ready(client: Any, cid: str, *, timeout: int = 300, interval: int = 4) -> None:
    """Poll a media container until FINISHED. Instagram needs to fetch + process the
    bytes from our tunnel URL first — publishing too early gives 'Media ID is not
    available'. Images finish in seconds, video/reels can take a minute+."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = client.get(cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Instagram rejected the media: {st.get('status') or 'container ERROR'}")
        time.sleep(interval)
    raise RuntimeError(f"container {cid} not ready after {timeout}s")


def _publish_container(client: Any, uid: str, cid: str) -> dict[str, Any]:
    last: Exception | None = None
    for _ in range(6):
        try:
            r = client.post(f"{uid}/media_publish", creation_id=cid)
            mid = r.get("id")
            perma = None
            try:
                perma = client.get(mid, fields="permalink").get("permalink")
            except Exception:  # noqa: BLE001
                pass
            return {"ok": True, "media_id": mid, "permalink": perma, "container_id": cid}
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(4)
    raise last or RuntimeError("media_publish failed")


def _publish(kind: str, filenames: list[str], caption: str | None,
             extra: dict[str, Any] | None = None) -> dict[str, Any]:
    extra = extra or {}
    for fn in filenames:
        if not (MEDIA_DIR / fn).exists():
            raise HTTPException(404, f"media {fn!r} not found — re-upload")
    urls = [_public_url(fn) for fn in filenames]
    cap = V.validate_caption(caption) if caption else None

    collab = extra.get("collaborators") or []
    if isinstance(collab, str):
        collab = [c.strip().lstrip("@") for c in collab.replace(",", " ").split() if c.strip()]
    collab = collab[:3]
    collab_json = json.dumps(collab) if collab else None

    try:
        client, acct = ig_auth.client_for(None)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "error_class": "auth"}
    uid = acct.ig_user_id

    try:
        if kind == "image":
            c = client.post(f"{uid}/media", image_url=urls[0], caption=cap, collaborators=collab_json)
            _wait_ready(client, c["id"])
            return _publish_container(client, uid, c["id"])

        if kind == "carousel":
            if not 2 <= len(urls) <= 10:
                raise HTTPException(400, "carousel needs 2–10 images")
            children = []
            for u in urls:
                ch = client.post(f"{uid}/media", image_url=u, is_carousel_item="true")
                children.append(ch["id"])
            for ch in children:
                _wait_ready(client, ch)
            parent = client.post(f"{uid}/media", media_type="CAROUSEL",
                                 children=",".join(children), caption=cap, collaborators=collab_json)
            _wait_ready(client, parent["id"])
            return _publish_container(client, uid, parent["id"])

        if kind == "reel":
            c = client.post(f"{uid}/media", media_type="REELS", video_url=urls[0],
                            caption=cap, collaborators=collab_json,
                            share_to_feed="true" if extra.get("share_to_feed", True) else "false")
            _wait_ready(client, c["id"], timeout=600)
            return _publish_container(client, uid, c["id"])

        if kind == "video":
            c = client.post(f"{uid}/media", media_type="VIDEO", video_url=urls[0], caption=cap)
            _wait_ready(client, c["id"], timeout=600)
            return _publish_container(client, uid, c["id"])

        if kind == "story":
            is_video = _kind_for(MEDIA_DIR / filenames[0]) == "video"
            kw = {"video_url": urls[0]} if is_video else {"image_url": urls[0]}
            c = client.post(f"{uid}/media", media_type="STORIES", **kw)
            _wait_ready(client, c["id"], timeout=600 if is_video else 120)
            return _publish_container(client, uid, c["id"])
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "error_class": getattr(exc, "error_class", "upstream_error")}

    raise HTTPException(400, f"unknown kind {kind!r}")


@control.post("/api/publish")
async def publish_now(payload: dict[str, Any]) -> JSONResponse:
    kind = payload.get("kind")
    filenames = payload.get("filenames") or ([payload["filename"]] if payload.get("filename") else [])
    if not kind or not filenames:
        raise HTTPException(400, "kind and filename(s) required")
    res = _publish(kind, filenames, payload.get("caption"), payload.get("extra"))
    ok = bool(res.get("ok", True)) and "error" not in res
    return JSONResponse(res, status_code=200 if ok else 502)


@control.post("/api/schedule")
async def schedule(payload: dict[str, Any]) -> dict[str, Any]:
    kind = payload.get("kind")
    filenames = payload.get("filenames") or ([payload["filename"]] if payload.get("filename") else [])
    when = payload.get("scheduled_at")
    if not kind or not filenames or not when:
        raise HTTPException(400, "kind, filename(s) and scheduled_at required")
    job = {
        "id": secrets.token_hex(8),
        "media_id": None,
        "filename": ",".join(filenames),
        "kind": kind,
        "caption": payload.get("caption"),
        "extra": payload.get("extra") or {},
        "scheduled_at": float(when),
        "status": "queued",
    }
    store.add_job(job)
    return {"ok": True, "job": job}


@control.get("/api/jobs")
def jobs() -> dict[str, Any]:
    return {"jobs": store.list_jobs()}


@control.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str) -> dict[str, Any]:
    store.delete_job(job_id)
    return {"ok": True}


@control.get("/api/recent")
def recent(limit: int = 12) -> dict[str, Any]:
    return ig.list_media(limit=limit)


@control.get("/api/insights/{media_id}")
def insights(media_id: str) -> dict[str, Any]:
    return ig.get_media_insights(media_id=media_id)


@control.post("/api/media/{filename}/delete")
def drop_media(filename: str) -> dict[str, Any]:
    p = MEDIA_DIR / filename
    if p.exists() and p.parent == MEDIA_DIR:
        p.unlink()
        return {"ok": True}
    raise HTTPException(404, "not found")


@control.get("/api/preview/{filename}")
def preview(filename: str) -> FileResponse:
    p = MEDIA_DIR / filename
    if not p.exists() or p.parent != MEDIA_DIR:
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type=mimetypes.guess_type(str(p))[0] or "application/octet-stream")


# --------------------------------------------------------------------------- #
# scheduler
# --------------------------------------------------------------------------- #
def run_scheduler(stop_evt) -> None:  # noqa: ANN001
    while not stop_evt.is_set():
        try:
            for job in store.due_jobs(time.time()):
                store.set_status(job["id"], "publishing")
                try:
                    res = _publish(job["kind"], job["filename"].split(","),
                                   job.get("caption"), job.get("extra"))
                    ok = bool(res.get("ok", True)) and "error" not in res
                    store.set_status(job["id"], "done" if ok else "failed", res)
                except Exception as exc:  # noqa: BLE001
                    store.set_status(job["id"], "failed", {"error": str(exc)})
        except Exception:  # noqa: BLE001, S110
            pass
        stop_evt.wait(15)
