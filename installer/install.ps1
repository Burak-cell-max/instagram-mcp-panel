<#
  Zero-dependency installer for the local Instagram panel (no Inno Setup needed).
  Run from the repo after `python installer/build.py` OR `python panel/build_desktop.py`:

      powershell -ExecutionPolicy Bypass -File installer\install.ps1

  Installs to %APPDATA%\Instagram Panel, drops a blank .mcp.json (kept on re-run),
  and makes Desktop + Start Menu shortcuts. Uninstall: installer\uninstall.ps1
#>
$ErrorActionPreference = 'Stop'
$repo    = Split-Path -Parent $PSScriptRoot
$exeSrc  = Join-Path $repo 'dist\Instagram Panel.exe'
$cfgSrc  = Join-Path $repo '.mcp.json.example'
$target  = Join-Path $env:APPDATA 'Instagram Panel'

if (-not (Test-Path $exeSrc)) {
  throw "dist\Instagram Panel.exe not found. Build it first:  python panel\build_desktop.py"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item $exeSrc (Join-Path $target 'Instagram Panel.exe') -Force
$cfg = Join-Path $target '.mcp.json'
if (-not (Test-Path $cfg)) { Copy-Item $cfgSrc $cfg }

$ws = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath('Desktop'),
                   (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {
  $lnk = $ws.CreateShortcut((Join-Path $dir 'Instagram Panel.lnk'))
  $lnk.TargetPath       = Join-Path $target 'Instagram Panel.exe'
  $lnk.WorkingDirectory = $target
  $lnk.IconLocation     = "$env:SystemRoot\System32\imageres.dll,168"
  $lnk.Description       = 'Instagram yayin paneli'
  $lnk.Save()
}

Write-Host ""
Write-Host "  kuruldu -> $target" -ForegroundColor Green
Write-Host "  Desktop + Baslat menusune kisayol eklendi."
Write-Host "  Ilk acilista Ayarlar sekmesinden Instagram token'ini gir."
