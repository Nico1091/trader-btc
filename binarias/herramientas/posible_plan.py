"""Posible plan de las binarias al día (04/11/2026). Sale de posible_plan_v7.py, que vivía en una carpeta temporal.

Deja la versión vigente del plan (PLAN-TOTAL.md, INFORME-TOTAL.md y OPERATIVA.md, más su texto para el Bloc de notas) en
Descargas\\POSIBLE PLAN BINARIAS BTC\\<versión> y en la USB (partición NUEVO, buscada por su etiqueta, porque las letras
cambian solas), y el texto en el Escritorio. Comprueba que las huellas SHA-256 coincidan en los dos lados.
Uso: python -I posible_plan.py [--version "v7 (04-11-2026)"] [--sin-usb]
"""
import ctypes
import hashlib
import os
import shutil
import string
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
S = r"C:\Users\ni109\Ingresos\binarias-papel"
ESC = r"C:\Users\ni109\Desktop"
NOMBRE = "POSIBLE PLAN BINARIAS BTC"
args = sys.argv[1:]
VERSION = args[args.index("--version") + 1] if "--version" in args else "v7 (04-11-2026)"
CORTA = VERSION.split(" ")[0]


def unidad_por_etiqueta(etiqueta):
    for letra in string.ascii_uppercase:
        raiz = f"{letra}:\\"
        if not os.path.exists(raiz):
            continue
        nombre = ctypes.create_unicode_buffer(261)
        if ctypes.windll.kernel32.GetVolumeInformationW(raiz, nombre, 261, None, None, None, None, 0) and nombre.value == etiqueta:
            return raiz
    return None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# 1) texto plano del plan (CRLF, UTF-8 sin BOM) para el Bloc de notas
md = open(os.path.join(S, "PLAN-TOTAL.md"), encoding="utf-8").read()
out = []
for lin in md.splitlines():
    if lin.startswith("# "):
        out += [lin[2:].upper(), "Copia en texto del PLAN-TOTAL.md (C:\\Users\\ni109\\Ingresos\\binarias-papel). La evidencia y la "
                "auditoría de congruencia están en INFORME-TOTAL.md, en la misma carpeta."]
        continue
    if lin.startswith("### ") or lin.startswith("## "):
        lin = lin.lstrip("#").strip().upper()
    out.append(lin.replace("**", "").replace("`", ""))
texto = "\r\n".join(out).rstrip() + "\r\n"
txt = os.path.join(ESC, f"PLAN TOTAL BINARIAS BTC - {CORTA}.txt")
open(txt, "w", encoding="utf-8", newline="").write(texto)
print("Escritorio:", txt)

# 2) carpeta de la versión en Descargas y en la USB
destinos = [os.path.join(r"C:\Users\ni109\Downloads", NOMBRE)]
usb = None if "--sin-usb" in args else unidad_por_etiqueta("NUEVO")
if usb:
    destinos.append(os.path.join(usb, NOMBRE))
elif "--sin-usb" not in args:
    print("La USB (NUEVO) no aparece: solo se actualiza Descargas.")
for D in destinos:
    d = os.path.join(D, VERSION)
    os.makedirs(d, exist_ok=True)
    for f in ("PLAN-TOTAL.md", "INFORME-TOTAL.md", "OPERATIVA.md"):
        shutil.copy2(os.path.join(S, f), os.path.join(d, f))
    shutil.copy2(txt, os.path.join(d, f"{NOMBRE} - {VERSION}.txt"))
    leeme = os.path.join(D, "LEEME.txt")
    open(leeme, "w", encoding="utf-8", newline="").write(
        "Posible plan de las binarias en BTC/USDT (Contratos de Evento de Binance).\r\n"
        "v7 (04/11/2026): manda. El real solo en las señales SÍ (papel de hoy sumando, ningún SÍ perdido, interés abierto que no "
        "sube) y con su 76 % (19 de las últimas 25 de papel); cinco líneas en cada foto; jamás apalancamiento; tope del 16 %.\r\n"
        "v6 (03/11/2026, 21:41): el posible plan que pidió guardar; real solo en días VERDES.\r\n"
        "Original: C:\\Users\\ni109\\Ingresos\\binarias-papel. Sin claves ni datos de cuentas.\r\n")
    print("al día:", d)

# 3) verificación: misma huella en todos los destinos
if len(destinos) > 1:
    malos = 0
    a, b = (os.path.join(x, VERSION) for x in destinos)
    for f in sorted(os.listdir(a)):
        ok = sha(os.path.join(a, f)) == sha(os.path.join(b, f))
        malos += not ok
        print(f"{'OK ' if ok else 'MAL'} {VERSION}\\{f}")
    print("diferencias entre Descargas y la USB:", malos)
for f in ("PLAN-TOTAL.md", "INFORME-TOTAL.md", "OPERATIVA.md"):
    assert sha(os.path.join(S, f)) == sha(os.path.join(destinos[0], VERSION, f)), f
print("Las copias de Descargas son idénticas al original.")
