"""Trae al PC una copia de la base del laboratorio que corre en la caja (11/11/2026). Solo lee: no cambia nada en la caja.

Pide a la caja una copia en caliente (API de copia de SQLite, corre como Termux) y la baja a laboratorio\\caja\\.
Uso: python -I traer_laboratorio.py"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CAJA = "192.168.20.45:5555"
LAB = "/data/local/tmp/laboratorio"
DESTINO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "laboratorio", "caja")
ADB = shutil.which("adb") or os.path.expanduser(
    r"~\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\adb.exe")
ENTORNO = dict(os.environ, MSYS_NO_PATHCONV="1")


def adb(*args, timeout=120):
    r = subprocess.run([ADB, *args], capture_output=True, text=True, timeout=timeout, env=ENTORNO)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    adb("connect", CAJA, timeout=20)
    py = "/data/data/com.termux/files/usr/bin/python3"
    codigo, salida = adb("-s", CAJA, "shell", f"run-as com.termux sh -c 'cd {LAB} && {py} -I base.py --copia copia.db'")
    if codigo != 0 or "copia en" not in salida:
        print("No pude pedir la copia a la caja:", salida.strip()[:300])
        return 1
    os.makedirs(DESTINO, exist_ok=True)
    local = os.path.join(DESTINO, time.strftime("lab-caja-%Y%m%d-%H%M.db"))
    codigo, salida = adb("-s", CAJA, "pull", f"{LAB}/copia.db", local, timeout=600)
    if codigo != 0:
        print("No pude bajar la copia:", salida.strip()[:300])
        return 1
    sys.path.insert(0, os.path.join(os.path.dirname(DESTINO)))
    import base
    print(f"Copia en {local}\n")
    print(base.resumen(sqlite3.connect(local)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
