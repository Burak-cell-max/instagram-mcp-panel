# Windows installer

Two ways to package the panel as an installed desktop app. Both start from the
PyInstaller build (`dist/Instagram Panel.exe`) — self-contained, Python and
`cloudflared` bundled, nothing else to install.

## Proper installer (Inno Setup)

```bash
winget install JRSoftware.InnoSetup      # once
python installer/build.py                # -> installer/Output/Instagram-Panel-Setup.exe
```

`Instagram-Panel-Setup.exe` installs per-user (no admin) into
`%APPDATA%\Instagram Panel`, drops a blank `.mcp.json`, makes Desktop + Start Menu
shortcuts, and registers an uninstaller in *Apps & features*.

## No-dependency install (PowerShell)

```bash
python panel/build_desktop.py            # -> dist/Instagram Panel.exe
powershell -ExecutionPolicy Bypass -File installer/install.ps1
```

Same layout, no Inno Setup needed. Remove with `installer/uninstall.ps1`.

## First run

The app starts in **setup mode** — open the **Ayarlar** tab and paste a long-lived
Instagram Graph API token (see [../SETUP.md](../SETUP.md)). It's validated, written to
the `.mcp.json` next to the executable, and the app reconnects. Upgrades keep that
file, so the token survives reinstalls.
