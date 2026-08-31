# Local Instagram publishing panel

A small self-hosted web UI on top of this repo's `instagram_mcp` package. Drag in an
image or video, write a caption, publish to your Instagram **Business/Creator**
account — feed image, carousel (2–10), reel, video, or story. Optional collaborator
invites and a scheduled-post queue.

Everything runs on your machine. The Instagram Graph API fetches media from a public
URL, so the panel starts a **cloudflared quick tunnel** (no Cloudflare account) that
exposes *only* the `panel/media/` folder for the few seconds Instagram needs it. The
control UI stays bound to `127.0.0.1`.

```
browser  ──▶  127.0.0.1:8787   (control UI + API, localhost only)
                    │
                    ├─ 127.0.0.1:8788        static server for panel/media/
                    │        │
                    │        └─ cloudflared ─▶ https://xxxx.trycloudflare.com
                    │                                   │
                    └────────── Instagram Graph API ◀───┘  fetches the bytes
```

## Setup

1. Install the base package and panel deps (from the repo root):

   ```bash
   python -m venv .venv
   .venv/bin/pip install -e .            # Windows: .venv\Scripts\pip
   .venv/bin/pip install -r panel/requirements.txt
   ```

2. Configure the token — copy `.mcp.json.example` to `.mcp.json` and fill in
   `INSTAGRAM_MCP_ACCESS_TOKEN` and `INSTAGRAM_MCP_IG_USER_ID`. See [../SETUP.md](../SETUP.md)
   for how to get them. `.mcp.json` is gitignored.

3. Get the tunnel binary:

   ```bash
   python -m panel.get_cloudflared      # downloads into panel/bin/
   ```
   (or install `cloudflared` yourself and put it on PATH.)

## Run

```bash
python -m panel.run
```

Opens `http://127.0.0.1:8787`. On Windows you can double-click `panel/start.bat`.
`Ctrl+C` stops the panel and the tunnel.

### Native window / single executable

```bash
pip install -r panel/requirements-desktop.txt
python -m panel.desktop            # runs in a pywebview window, no browser/terminal
python panel/build_desktop.py      # -> "dist/Instagram Panel(.exe)"
```

The bundled executable reads `.mcp.json` from the folder it sits in and writes
`media/`, `queue.db`, `state.json` there too — so keep your `.mcp.json` next to
`dist/Instagram Panel.exe`. That copy of `.mcp.json` holds your token; `dist/` is
gitignored, don't share the folder.

## Notes

- **Media hosting** — the tunnel URL changes every run and is only up while the panel
  runs. Fine for interactive use. For unattended 24/7 posting you want a real host
  (S3 / R2 / your own server) or a scheduled CI job instead.
- **Scheduling** — the queue lives in `panel/queue.db` (SQLite) and only fires while
  the panel is running.
- **Collaborators** — feed image / carousel / reel only, up to 3 usernames, exact
  spelling (no search). Invitees accept in their own app.
- **Aspect ratio** — Instagram rejects feed images outside 4:5–1.91:1. "Boyutu
  otomatik ayarla" (on by default) keeps the whole image and pads the short axis with
  a blurred zoomed copy of itself, so any portrait/banner/screenshot publishes. Stories
  pad to 9:16; carousels are made uniform. Turn it off to send the raw file.
- **Publishing flow** — the panel creates the media container, polls until Instagram
  reports `FINISHED`, then publishes. Publishing too early returns
  "Media ID is not available".
- Publishing quota is Instagram's: ~100 API posts per rolling 24h.
- **AI (optional)** — add a Groq API key in the Ayarlar tab to unlock "✨ Caption üret"
  / "✨ Parlat" and per-comment "✨ AI taslak" reply drafts. Text only (no vision on
  the free tier), so captions are written from a short brief you type. Key lives in
  gitignored `panel/state.json`; every AI control is hidden when no key is set.
