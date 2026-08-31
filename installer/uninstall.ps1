<#  Remove what install.ps1 created.
      powershell -ExecutionPolicy Bypass -File installer\uninstall.ps1
    Keeps nothing — including your .mcp.json token file.
#>
$ErrorActionPreference = 'SilentlyContinue'
$target = Join-Path $env:APPDATA 'Instagram Panel'
Get-Process 'Instagram Panel','cloudflared' | Stop-Process -Force
Remove-Item -Recurse -Force $target
Remove-Item -Force ([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Instagram Panel.lnk'))
Remove-Item -Force (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Instagram Panel.lnk')
Write-Host "  kaldirildi." -ForegroundColor Green
