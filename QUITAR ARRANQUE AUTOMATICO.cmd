@echo off
rem Quita el arranque del agente al encender Windows. No lo detiene ahora: para eso, PARAR AGENTE.cmd.
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v AgenteTradingSeguido /f
echo Arranque automatico quitado.
timeout /t 4 >nul
