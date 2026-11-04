"""Cómo va el papel de hoy, en una ventana (04/11/2026). Lo abre el botón «Binarias en tiempo real» del Escritorio.

Mira si la caja late (puerto 8793 de la red de la casa), trae su semaforo.json por ADB (o el del teléfono, si la caja no
responde) y dice en pocas líneas: papel de hoy (SÍ o NO), sus apuestas, los SÍ del día, el papel reciente frente a su 76 % y
si el dinero real está autorizado. Solo lee: no cambia nada en los equipos.
Uso: python -I estado.py
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
COL = dt.timezone(dt.timedelta(hours=-5))
CAJA, TELEFONO = "192.168.20.45:5555", "bced910f"
ADB = shutil.which("adb") or os.path.expanduser(
    r"~\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\adb.exe")
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def adb(*args, timeout=40):
    try:
        r = subprocess.run([ADB, *args], capture_output=True, timeout=timeout, creationflags=SIN_VENTANA)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def latido():
    try:
        d = json.loads(urllib.request.urlopen("http://192.168.20.45:8793/latido", timeout=5).read())
        return float(d["ahora"]) - float(d["latido"])
    except Exception:
        return None


def main():
    ahora = dt.datetime.now(COL)
    print(f"Binarias BTC · {ahora:%d/%m/%Y %H:%M} (hora de Colombia)\n")
    edad = latido()
    if edad is not None and edad < 600:
        print("La caja late: ella vigila y avisa.")
    else:
        print("La caja no late: el teléfono la releva y avisa." if edad is None else f"La caja no late hace {edad / 60:.0f} min: avisa el teléfono.")
    adb("connect", CAJA, timeout=15)
    datos, quien = adb("-s", CAJA, "exec-out", "cat", "/data/local/tmp/centinela/semaforo.json"), "la caja"
    real = adb("-s", CAJA, "shell", "ls /data/local/tmp/centinela/REAL_AUTORIZADO")
    if not datos:
        datos, quien = adb("-s", TELEFONO, "exec-out", "run-as", "com.termux", "cat", "files/home/centinela/semaforo.json"), "el teléfono"
        real = adb("-s", TELEFONO, "exec-out", "run-as", "com.termux", "ls", "files/home/centinela/REAL_AUTORIZADO")
    if not datos:
        print("\nNo pude leer el papel de ningún equipo (¿ADB desconectado?).")
        return 1
    e = json.loads(datos.decode("utf-8"))
    ini = dt.datetime(ahora.year, ahora.month, ahora.day, tzinfo=COL).timestamp()
    hoy = [a for a in e.get("apuestas", []) if a["t"] >= ini]
    cerradas = [a for a in hoy if a.get("res") is not None]
    neto = 0.0
    for a in cerradas:
        neto += 0.85 if a["res"] else -1.0
    perdio = bool(e.get("hoy", {}).get("perdio")) and e.get("hoy", {}).get("dia") == ahora.strftime("%Y-%m-%d")
    estado = "NO (el SÍ ya perdió hoy)" if perdio else ("SÍ cuando llegue la señal, si el interés abierto no sube" if neto > 0 else "NO (todavía no va sumando)")
    print(f"\nPapel de hoy, según {quien}: {estado}.")
    print(f"  {len(hoy)} señales, {len(cerradas)} cerradas, {sum(a['res'] for a in cerradas)} aciertos, neto {neto:+.2f} apuestas.".replace(".", ",", 1))
    si = [a for a in hoy if a.get("si")]
    if si:
        print("  SÍ de hoy: " + ", ".join(f"{dt.datetime.fromtimestamp(a['t'], COL):%H:%M} "
                                         f"{'acierto' if a.get('res') == 1 else ('fallo' if a.get('res') == 0 else 'abierto')}"
                                         f"{' (real)' if a.get('real') else ''}" for a in si) + ".")
    ult = [a for a in e.get("apuestas", []) if a.get("res") is not None][-25:]
    print(f"  Papel reciente: {sum(a['res'] for a in ult)} de {len(ult)}; su 76 % pide 19 de 25 para el dinero real.")
    print(f"  Dinero real: {'autorizado (solo en los SÍ con su 76 %)' if real else 'no autorizado'}; nunca apalancamiento.")
    return 0


if __name__ == "__main__":
    codigo = main()
    if "--sin-pausa" not in sys.argv:
        try:
            input("\nPulse Enter para cerrar.")
        except EOFError:
            pass
    sys.exit(codigo)
