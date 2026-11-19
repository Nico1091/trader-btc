@echo off
rem Quita el arranque al iniciar Windows. No los detiene ahora: el centinela se para creando PARAR y el operador con claude stop.
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v BinariasCentinela /f
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v BinariasOperador /f
echo Arranque automatico quitado.
timeout /t 4 >nul
