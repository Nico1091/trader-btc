@echo off
rem Hace que el centinela de binarias y el operador Claude arranquen solos al iniciar Windows (en papel, sin ventana).
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v BinariasCentinela /t REG_SZ /d "\"C:\Users\ni109\AppData\Local\Programs\Python\Python311\pythonw.exe\" -I \"C:\Users\ni109\Ingresos\binarias-papel\binarias.py\"" /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v BinariasOperador /t REG_SZ /d "\"C:\Users\ni109\AppData\Local\Programs\Python\Python311\pythonw.exe\" -I \"C:\Users\ni109\Ingresos\binarias-papel\operador.py\" arrancar" /f
echo Arranque automatico puesto.
timeout /t 4 >nul
