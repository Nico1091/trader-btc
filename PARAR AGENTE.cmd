@echo off
rem Pide al agente que cierre lo abierto (en papel), guarde el estado y se apague.
cd /d "%~dp0"
echo parar> PARAR
echo Pedido de parada enviado: el agente se apaga en unos segundos.
timeout /t 4 >nul
