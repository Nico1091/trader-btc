"""Abre TradingView Desktop con la IP oculta.

Todo su tráfico sale por Tor (SOCKS 127.0.0.1:9050) y se le prohíbe resolver nombres por
fuera del túnel, así que ninguna conexión directa puede salir con la IP del equipo.
Si Tor no responde, no abre TradingView y lo avisa.
"""
import ctypes
import json
import os
import socket
import subprocess
import sys
from ctypes import wintypes

AUMID = "TradingView.Desktop_n534cwy3pjxzj!TradingView.Desktop"
AJUSTES = os.path.expandvars(
    r"%LOCALAPPDATA%\Packages\TradingView.Desktop_n534cwy3pjxzj\LocalCache\Roaming\TradingView\TVAppStorage\appState.json")
PROXY = {"isProxyEnabled": True, "proxyProtocol": "socks5",
         "proxyServerIpAddress": "127.0.0.1", "proxyServerPort": "9050",
         "isAppTrackingEnabled": False}
BANDERAS = ('--proxy-server="socks5://127.0.0.1:9050" '
            '--host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE 127.0.0.1" '
            '--force-webrtc-ip-handling-policy=disable_non_proxied_udp')
PRUEBA = "--prueba" in sys.argv


def aviso(texto):
    if PRUEBA:
        print(texto)
    else:
        ctypes.windll.user32.MessageBoxW(None, texto, "TradingView (IP oculta)", 0x30)


def tor_responde():
    """Saludo SOCKS5 real, no solo el puerto abierto."""
    try:
        with socket.create_connection(("127.0.0.1", 9050), timeout=4) as s:
            s.sendall(b"\x05\x01\x00")
            return s.recv(2) == b"\x05\x00"
    except OSError:
        return False


def tradingview_abierto():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq TradingView.exe", "/NH"],
                       capture_output=True, text=True, creationflags=0x08000000)
    return "TradingView.exe" in r.stdout


def fijar_proxy():
    """Repone el proxy en sus ajustes por si se apagó desde el programa."""
    datos = {}
    if os.path.exists(AJUSTES):
        try:
            with open(AJUSTES, encoding="utf-8-sig") as f:
                datos = json.load(f)
        except (OSError, ValueError):
            datos = {}
    if all(datos.get(k) == v for k, v in PROXY.items()):
        return
    datos.update(PROXY)
    os.makedirs(os.path.dirname(AJUSTES), exist_ok=True)
    with open(AJUSTES, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2)


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


def guid(texto):
    g = GUID()
    ctypes.oledll.ole32.CLSIDFromString(texto, ctypes.byref(g))
    return g


def activar(argumentos):
    """IApplicationActivationManager::ActivateApplication: la única vía que pasa banderas a una app MSIX."""
    ole32 = ctypes.oledll.ole32
    ole32.CoInitialize(None)
    clsid = guid("{45BA127D-10A8-46EA-8AB7-56EA9078943C}")
    iid = guid("{2e941141-7f97-4756-ba1d-9decde894a3d}")
    gestor = ctypes.c_void_p()
    ole32.CoCreateInstance(ctypes.byref(clsid), None, 4, ctypes.byref(iid), ctypes.byref(gestor))
    tabla = ctypes.cast(gestor, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR,
                               ctypes.c_int, ctypes.POINTER(wintypes.DWORD))
    pid = wintypes.DWORD()
    proto(tabla[3])(gestor, AUMID, argumentos, 0, ctypes.byref(pid))
    proto_liberar = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
    proto_liberar(tabla[2])(gestor)
    return pid.value


def main():
    if not tor_responde():
        aviso("Tor no responde en 127.0.0.1:9050.\n\nTradingView no se abre sin Tor, para no exponer su IP. "
              "Espere un minuto (el vigía lo reenciende solo) y vuelva a intentarlo.")
        return 1
    if tradingview_abierto():
        pid = activar("")
        if PRUEBA:
            print("ya estaba abierto; traído al frente, pid", pid)
        return 0
    fijar_proxy()
    pid = activar(BANDERAS)
    if PRUEBA:
        print("abierto con banderas, pid", pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
