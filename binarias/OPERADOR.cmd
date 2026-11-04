@echo off
rem Enciende al operador Claude de las binarias si no esta vivo y muestra como van las cuentas.
cd /d "%~dp0"
python -I operador.py arrancar
echo.
python -I operador.py estado
echo.
pause
