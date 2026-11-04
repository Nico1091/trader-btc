@echo off
rem Abre las binarias en papel: arranca el bot si no esta corriendo y abre su pantalla.
cd /d "%~dp0"
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath (Join-Path (Split-Path (Get-Command python).Source) pythonw.exe) -ArgumentList binarias.py -WorkingDirectory %~dp0 -WindowStyle Hidden; Start-Sleep -Seconds 3 }"
start "" http://127.0.0.1:8792
