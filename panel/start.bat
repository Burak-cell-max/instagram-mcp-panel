@echo off
title Instagram Panel
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [!] .venv bulunamadi. Once kurulum:
  echo     python -m venv .venv
  echo     .venv\Scripts\pip install -e . -r panel\requirements.txt
  echo.
  pause
  exit /b 1
)

echo ================================================
echo   Instagram Panel baslatiliyor...
echo   Tarayici otomatik acilacak: http://127.0.0.1:8787
echo   Durdurmak icin: bu pencereyi kapat (Ctrl+C)
echo ================================================
echo.

".venv\Scripts\python.exe" -m panel.run

echo.
echo [panel durdu]
pause
