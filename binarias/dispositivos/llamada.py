"""Llamada al teléfono desde el propio teléfono (04/11/2026). Usa la app Llamada Claude, versión 5.

Pedido suyo: que cuando las operaciones estén acertando le timbre el teléfono a cualquier hora, aunque esté en silencio. La app
timbra por el canal de alarma y sube el volumen al máximo. Este cliente se conecta a la dirección del propio teléfono con la
misma línea del PC (TLS 1.3 con huella fijada y token). Si contesta, le dice el aviso en voz y cuelga.
Certificado y token: ~/.config/binarias/llamada (cert.der y token.bin). Uso de prueba: python3 -I llamada.py "texto" audio.mp3
"""
import hashlib
import os
import socket
import ssl
import struct
import sys
import time

CONF = os.path.expanduser("~/.config/binarias/llamada")
PUERTO = 47123
TIMBRE = 45


def mi_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.20.1", 9))  # no manda nada: solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def conectar():
    with open(os.path.join(CONF, "cert.der"), "rb") as f:
        huella = hashlib.sha256(f.read()).digest()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # la confianza la da la huella fijada
    s = ctx.wrap_socket(socket.create_connection((mi_ip(), PUERTO), timeout=10))
    if hashlib.sha256(s.getpeercert(binary_form=True)).digest() != huella:
        s.close()
        raise ConnectionError("no es el certificado de la app")
    return s


def enviar(s, tipo, datos=b""):
    s.sendall(tipo.encode() + struct.pack(">I", len(datos)) + datos)


def exacto(s, n):
    b = b""
    while len(b) < n:
        x = s.recv(n - len(b))
        if not x:
            raise ConnectionError("línea cerrada")
        b += x
    return b


def recibir(s, plazo):
    s.settimeout(plazo)
    try:
        cab = exacto(s, 5)
    except socket.timeout:
        return None
    return cab[:1].decode(), exacto(s, struct.unpack(">I", cab[1:])[0])


def una_llamada(texto, mp3, quien):
    """Devuelve «contesto», «rechazo» o «no contesto»."""
    s = conectar()
    try:
        with open(os.path.join(CONF, "token.bin"), "rb") as f:
            enviar(s, "T", f.read())
        r = recibir(s, 10)
        if not r or r[0] != "O":
            raise ConnectionError("la app no aceptó")
        enviar(s, "R", quien.encode())
        fin = time.time() + TIMBRE
        while time.time() < fin:
            r = recibir(s, 1)
            if r and r[0] == "a":
                enviar(s, "S", texto.encode())
                if mp3 and os.path.exists(mp3):
                    with open(mp3, "rb") as f:
                        enviar(s, "A", f.read())
                fin2 = time.time() + 40
                while time.time() < fin2:
                    r = recibir(s, 1)
                    if r and r[0] in "fcrX":
                        break
                enviar(s, "C")
                return "contesto"
            if r and r[0] in "rcX":
                return "rechazo"
        enviar(s, "C")
        return "no contesto"
    finally:
        s.close()


def llamar(texto, mp3=None, quien="Binarias BTC", intentos=3, espera=30):
    """Insiste hasta tres veces si no contesta. Si él rechaza, no insiste."""
    ultimo = "sin intentar"
    for i in range(intentos):
        try:
            ultimo = una_llamada(texto, mp3, quien)
        except OSError as ex:
            ultimo = f"sin línea ({type(ex).__name__}: {ex})"
        if ultimo in ("contesto", "rechazo"):
            break
        if i + 1 < intentos:
            time.sleep(espera)
    return ultimo


if __name__ == "__main__":
    print(llamar(sys.argv[1] if len(sys.argv) > 1 else "Prueba de llamada", sys.argv[2] if len(sys.argv) > 2 else None, intentos=1))
