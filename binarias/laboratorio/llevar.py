"""Lleva el laboratorio del PC a la caja con su huella (11/11/2026).

Copia el código, los guiones y los datos de la historia a /data/local/tmp/laboratorio y compara la huella SHA-256 de cada
archivo en los dos lados. El historial de velas se copia dentro de la caja desde el archivo del centinela (es el mismo que
tiene el PC). La base lab.db solo se lleva con --base (la primera vez): después es la de la caja y no se pisa.
Uso: python -I llevar.py [--base] [--solo-codigo]"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CAJA = "192.168.20.45:5555"
LAB = "/data/local/tmp/laboratorio"
ADB = shutil.which("adb") or os.path.expanduser(
    r"~\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1\adb.exe")
ENTORNO = dict(os.environ, MSYS_NO_PATHCONV="1")
CODIGO = ["comun.py", "base.py", "velas.py", "rasgos.py", "formas.py", "juez.py", "red.py", "busqueda.py", "emulador.py",
          "partes.py", "peticiones.py", "perdida.py", "laboratorio.py", "prueba_laboratorio.py", "construir.py", "centro.py", "graficas.py",
          "validacion.py", "arrancar_lab.sh", "probar.sh", "motor/senales.py", "motor/patrones_std.py",
          "PROMPT-FINAL.md", "REVISION.md"]
DATOS = ["datos/interes.npz", "datos/indice.npz", "datos/red_X.npz", "datos/red_p.npz", "datos/redes.json", "datos/t33_indice.json", "datos/perdida.json"]


def adb(*args, timeout=600):
    r = subprocess.run([ADB, "-s", CAJA, *args], capture_output=True, text=True, timeout=timeout, env=ENTORNO)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def huella(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    subprocess.run([ADB, "connect", CAJA], capture_output=True, timeout=20, env=ENTORNO)
    adb("shell", f"mkdir -p {LAB}/datos {LAB}/motor {LAB}/respaldos && chmod 777 {LAB} {LAB}/datos {LAB}/motor {LAB}/respaldos")
    lista = list(CODIGO)
    if "--solo-codigo" not in sys.argv:
        lista += DATOS
    if "--base" in sys.argv:
        lista.append("lab.db")
    malas = []
    for rel in lista:
        local = os.path.join(AQUI, rel.replace("/", os.sep))
        codigo, salida = adb("push", local, f"{LAB}/{rel}")
        if codigo != 0:
            malas.append(f"{rel}: {salida.strip()[-120:]}")
            continue
        adb("shell", f"chmod 666 {LAB}/{rel}")
        _c, s = adb("shell", f"sha256sum {LAB}/{rel}")
        if s.split()[0:1] != [huella(local)]:
            malas.append(f"{rel}: huella distinta")
    hist = os.path.join(AQUI, "datos", "BTCUSDT_1m.npy")
    h_pc = huella(hist)
    _c, s = adb("shell", f"sha256sum {LAB}/datos/BTCUSDT_1m.npy 2>/dev/null")
    if s.split()[0:1] != [h_pc]:
        adb("shell", f"cp /data/local/tmp/centinela/datos/BTCUSDT_um_1m_vivo.npy {LAB}/datos/BTCUSDT_1m.npy && "
                     f"chmod 666 {LAB}/datos/BTCUSDT_1m.npy")
        _c, s = adb("shell", f"sha256sum {LAB}/datos/BTCUSDT_1m.npy")
        if s.split()[0:1] != [h_pc]:
            malas.append("datos/BTCUSDT_1m.npy: la copia de la caja no tiene la huella del PC")
    print(f"llevados {len(lista) + 1} archivos; huellas distintas o fallas: {len(malas)}")
    for m in malas:
        print("  " + m)
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
