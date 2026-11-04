@echo off
rem Muestra como va el papel de hoy (04/11/2026): si la caja late y el SI o NO del dia. El centinela ya no corre en el PC.
chcp 65001 >nul
cd /d "%~dp0"
python -I herramientas\estado.py
