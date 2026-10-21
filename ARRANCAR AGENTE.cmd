@echo off
rem Arranca el agente de trading seguido (papel) sin ventana. Panel: panel.html
cd /d "%~dp0"
if exist PARAR del PARAR
start "" pythonw -I agente.py
echo Agente arrancado en papel. El panel esta en "%~dp0panel.html" y se actualiza cada 5 segundos.
timeout /t 4 >nul
