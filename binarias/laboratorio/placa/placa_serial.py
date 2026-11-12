"""Habla con la ESP32-S3 por el puerto serie (11/11/2026): ejecuta código, sube archivos con su huella y la reinicia.

Abre el puerto con DTR y RTS apagados para no reiniciarla al conectar. En cada orden alimenta al perro guardián del programa
que estaba corriendo (si existe), para que no la reinicie a mitad de una copia. Busca la placa por el puente CH343 (1a86) o
por el USB nativo de Espressif (303a).
Uso: python placa_serial.py info | ls | subir LOCAL[=REMOTO] ... | ejecutar "código" | reiniciar | duro"""
import binascii
import hashlib
import sys
import time

import serial
from serial.tools import list_ports

ALIMENTAR = ("try:\n import acortador\n acortador.wdt and acortador.wdt.feed()\nexcept Exception:\n pass\n"
             "try:\n import binarias_placa\n binarias_placa.WDT and binarias_placa.WDT.feed()\nexcept Exception:\n pass\n")


def puerto():
    for _ in range(20):
        p = [x.device for x in list_ports.comports() if x.vid in (0x303A, 0x1A86)]
        if p:
            return p[0]
        time.sleep(1)
    raise SystemExit("no encuentro la placa por USB")


def abrir():
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = puerto(), 115200, 1
    s.dtr = False
    s.rts = False
    s.open()
    time.sleep(0.3)
    s.write(b"\r\x03\x03")
    time.sleep(0.6)
    s.write(b"\x01")
    time.sleep(0.6)
    s.read_all()
    return s


def ejecutar(s, codigo, espera=20):
    s.write((ALIMENTAR + codigo).encode() + b"\x04")
    t, b = time.time(), b""
    while time.time() - t < espera:
        b += s.read_all()
        if b.count(b"\x04") >= 2:
            break
        time.sleep(0.05)
    texto = b.decode("utf-8", "replace")
    salida = texto.split("\x04")
    out = salida[0].lstrip("OK")
    err = salida[1] if len(salida) > 1 else ""
    return out.strip() + (("\nERROR: " + err.strip()) if err.strip() else "")


def subir(s, local, remoto):
    datos = open(local, "rb").read()
    r = ejecutar(s, "import binascii\nf=open(%r,'wb')" % (remoto + ".tmp"))
    if "ERROR" in r:
        raise SystemExit(r)
    for i in range(0, len(datos), 512):
        orden = "f.write(binascii.a2b_base64(%r))" % binascii.b2a_base64(datos[i:i + 512]).decode().strip()
        for intento in range(4):  # si se pierde un carácter por el puerto, el trozo falla antes de escribirse: se repite
            r = ejecutar(s, orden)
            if "ERROR" not in r:
                break
            time.sleep(0.3)
            s.read_all()
        else:
            raise SystemExit(r)
    ejecutar(s, "f.close()\nimport os\ntry:\n os.remove(%r)\nexcept OSError:\n pass\nos.rename(%r,%r)" % (remoto, remoto + ".tmp", remoto))
    r = ejecutar(s, "import hashlib,binascii\nh=hashlib.sha256()\nf=open(%r,'rb')\nwhile True:\n b=f.read(1024)\n"
                    " if not b: break\n h.update(b)\nf.close()\nprint(binascii.hexlify(h.digest()).decode())" % remoto)
    ok = r.strip() == hashlib.sha256(datos).hexdigest()
    print(f"{remoto}: {len(datos)} bytes, huella {'igual' if ok else 'DISTINTA: ' + r[:80]}")
    return ok


def reiniciar(s):
    s.write(b"\x02")
    time.sleep(0.2)
    s.write(b"import machine\r\nmachine.reset()\r\n")
    time.sleep(0.5)


def duro(s):
    """Reinicio por hardware (EN), como apretar el botón: RTS un instante."""
    s.dtr = False
    s.rts = True
    time.sleep(0.2)
    s.rts = False


INFO = r"""
import sys, os, gc
print('version', sys.version, sys.implementation)
print('doble', (1.0 + 1e-10) != 1.0)
gc.collect(); print('libre', gc.mem_free())
st = os.statvfs('/'); print('flash_libre', st[0] * st[3])
print('archivos', sorted(os.listdir()))
for m in ('ssl', 'tls', 'requests', 'urequests', 'ntptime', 'hashlib'):
    try:
        __import__(m); print('modulo', m, 'si')
    except ImportError:
        print('modulo', m, 'no')
import network
w = network.WLAN(network.STA_IF); print('wifi', w.isconnected(), w.ifconfig()[0] if w.isconnected() else '')
"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    orden = sys.argv[1]
    s = abrir()
    try:
        if orden == "info":
            print(ejecutar(s, INFO, 30))
        elif orden == "ls":
            print(ejecutar(s, "import os\nfor n in sorted(os.listdir()):\n print(n, os.stat(n)[6])"))
        elif orden == "subir":
            ok = all(subir(s, a.partition("=")[0], a.partition("=")[2] or a.replace("\\", "/").split("/")[-1]) for a in sys.argv[2:])
            return 0 if ok else 1
        elif orden == "ejecutar":
            print(ejecutar(s, sys.argv[2], 60))
        elif orden == "reiniciar":
            reiniciar(s)
            print("reinicio suave pedido")
        elif orden == "duro":
            duro(s)
            print("reinicio por hardware pedido")
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
