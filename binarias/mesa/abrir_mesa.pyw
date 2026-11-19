"""Botón de la Mesa de binarias: arranca el motor si no corre y abre la ventana en Chrome, sin barra y maximizada.

Chrome y no Edge: desde el 01/10 su blindaje redirige msedge.exe al Buscador. La ventana solo habla con 127.0.0.1; todo lo de
Binance sale del motor en Python."""
import ctypes
import os
import socket
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
PUERTO = 8795
CHROME = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
PERFIL = os.path.join(os.environ.get("LOCALAPPDATA", AQUI), "mesa-binarias")
RUTA = "centro" if sys.argv[1:] == ["centro"] else ""  # 07/11: el botón «Centro de estrategias» abre /centro


def corre():
    """Reservar el puerto no toca la pila de red y responde al momento; sin SO_REUSEADDR, que en Windows engaña."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", PUERTO))
        return False
    except OSError:
        return True
    finally:
        s.close()


try:
    if not corre():
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        subprocess.Popen([pyw, "-I", os.path.join(AQUI, "mesa.py")], cwd=AQUI, creationflags=subprocess.DETACHED_PROCESS)
        for _ in range(40):
            time.sleep(0.25)
            if corre():
                break
    subprocess.Popen([CHROME, f"--app=http://127.0.0.1:{PUERTO}/{RUTA}", f"--user-data-dir={PERFIL}", "--start-maximized",
                      "--no-first-run", "--autoplay-policy=no-user-gesture-required"])
except Exception as ex:
    ctypes.windll.user32.MessageBoxW(0, f"No pude abrir la Mesa: {ex}", "Mesa de binarias", 0x10)
