"""SQLite-backed queue for scheduled posts. Only runs while the panel is open."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from panel.config import QUEUE_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    media_id     TEXT,
    filename     TEXT,
    kind         TEXT NOT NULL,
    caption      TEXT,
    extra        TEXT,
    scheduled_at REAL,
    status       TEXT NOT NULL DEFAULT 'queued',
    result       TEXT,
    created_at   REAL NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(QUEUE_DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(_SCHEMA)
    return c


def add_job(job: dict[str, Any]) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO jobs (id, media_id, filename, kind, caption, extra, scheduled_at, status, created_at)"
            " VALUES (:id, :media_id, :filename, :kind, :caption, :extra, :scheduled_at, :status, :created_at)",
            {
                "id": job["id"],
                "media_id": job.get("media_id"),
                "filename": job.get("filename"),
                "kind": job["kind"],
                "caption": job.get("caption"),
                "extra": json.dumps(job.get("extra") or {}),
                "scheduled_at": job.get("scheduled_at"),
                "status": job.get("status", "queued"),
                "created_at": time.time(),
            },
        )


def list_jobs(limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs ORDER BY COALESCE(scheduled_at, created_at) DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["extra"] = json.loads(d.get("extra") or "{}")
        d["result"] = json.loads(d["result"]) if d.get("result") else None
        out.append(d)
    return out


def due_jobs(now: float) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs WHERE status='queued' AND scheduled_at IS NOT NULL AND scheduled_at <= ?"
            " ORDER BY scheduled_at ASC", (now,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["extra"] = json.loads(d.get("extra") or "{}")
        out.append(d)
    return out


def set_status(job_id: str, status: str, result: dict[str, Any] | None = None) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE jobs SET status=?, result=? WHERE id=?",
            (status, json.dumps(result) if result is not None else None, job_id),
        )


def delete_job(job_id: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
