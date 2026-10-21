@echo off
rem Hace que el agente arranque solo al encender Windows (en papel, sin ventana).
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v AgenteTradingSeguido /t REG_SZ /d "\"C:\Users\ni109\AppData\Local\Programs\Python\Python311\pythonw.exe\" -I \"C:\Users\ni109\Ingresos\trader-btc\agente.py\"" /f
echo Arranque automatico puesto.
timeout /t 4 >nul
