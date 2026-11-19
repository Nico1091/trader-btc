"""Paridad de las cinco líneas entre Pulso (Rust) y graficas.py (Python), píxel a píxel y texto a texto (04/11/2026).

Para cada ventana de herramientas/fixtures_lineas/*.csv:
- Pulso: `pulso lineas-archivo VELAS.csv SALIDA.png` dentro de WSL (no necesita parar el servicio);
- Python: graficas.cinco_lineas, grafica y lectura con las mismas velas.
Compara los píxeles decodificados de los dos PNG y el texto. Con --huellas solo imprime la huella SHA-256 de los píxeles y
del texto de Python, para correrlo en el teléfono (Python 3.14) y compararlo con el PC.

Uso:
  python -I paridad_lineas.py [--pulso ~/.pulso/prueba/pulso]
  python -I paridad_lineas.py --huellas        (en cualquier equipo)
"""
import glob
import hashlib
import os
import struct
import subprocess
import sys
import zlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
for candidato in (os.path.join(os.path.dirname(AQUI), "dispositivos"), AQUI):
    if os.path.exists(os.path.join(candidato, "graficas.py")):
        sys.path.insert(0, candidato)
        break
import graficas as G  # noqa: E402

FIXTURES = os.path.join(AQUI, "fixtures_lineas")
SALIDA = os.path.join(AQUI, "fixtures_lineas", "salida")


def leer_csv(ruta):
    v = []
    for lin in open(ruta, encoding="utf-8"):
        c = lin.strip().split(",")
        try:
            v.append((int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4])))
        except (ValueError, IndexError):
            continue
    return v


def pixeles(png):
    pos, idat, ancho = 8, b"", None
    while pos < len(png):
        n = struct.unpack(">I", png[pos:pos + 4])[0]
        tipo, datos = png[pos + 4:pos + 8], png[pos + 8:pos + 8 + n]
        if tipo == b"IHDR":
            ancho = struct.unpack(">I", datos[:4])[0]
        elif tipo == b"IDAT":
            idat += datos
        pos += 12 + n
    crudo = zlib.decompress(idat)
    return bytes(b for i, b in enumerate(crudo) if i % (ancho + 1))


def a_wsl(ruta):
    ruta = os.path.abspath(ruta).replace("\\", "/")
    return "/mnt/" + ruta[0].lower() + ruta[2:]


def main():
    args = sys.argv[1:]
    archivos = sorted(glob.glob(os.path.join(FIXTURES, "*.csv")))
    if not archivos:
        print("no hay ventanas: corra antes fixtures_lineas.py")
        return 1
    if "--huellas" in args:
        for ruta in archivos:
            v = leer_csv(ruta)
            s = G.cinco_lineas(v)
            print(os.path.basename(ruta), hashlib.sha256(pixeles(G.grafica(v, s))).hexdigest()[:16],
                  hashlib.sha256(G.lectura(v, s).encode()).hexdigest()[:16])
        return 0
    binario = args[args.index("--pulso") + 1] if "--pulso" in args else "~/.pulso/prueba/pulso"
    os.makedirs(SALIDA, exist_ok=True)
    malos = 0
    for ruta in archivos:
        nombre = os.path.splitext(os.path.basename(ruta))[0]
        png_rust = os.path.join(SALIDA, nombre + "_rust.png")
        r = subprocess.run(["wsl.exe", "-d", "Ubuntu-26.04", "-u", "rojo", "-e", "bash", "-c",
                            f'{binario} lineas-archivo "{a_wsl(ruta)}" "{a_wsl(png_rust)}"'],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        txt_rust = r.stdout.strip()
        v = leer_csv(ruta)
        s = G.cinco_lineas(v)
        png_py = G.grafica(v, s)
        open(os.path.join(SALIDA, nombre + "_python.png"), "wb").write(png_py)
        txt_py = G.lectura(v, s)
        pr, pp = pixeles(open(png_rust, "rb").read()), pixeles(png_py)
        distintos = sum(1 for a, b in zip(pr, pp) if a != b) + abs(len(pr) - len(pp))
        ok = distintos == 0 and txt_rust == txt_py
        malos += not ok
        print(f"{'OK ' if ok else 'MAL'} {nombre}: {distintos} píxeles distintos de {len(pp)} · texto {'igual' if txt_rust == txt_py else 'DISTINTO'}")
        if txt_rust != txt_py:
            print("   Rust  :", txt_rust)
            print("   Python:", txt_py)
        print("   huella", hashlib.sha256(pp).hexdigest()[:16], hashlib.sha256(txt_py.encode()).hexdigest()[:16])
    print(f"ventanas: {len(archivos)} · con diferencias: {malos}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
