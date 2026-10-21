"""Red del trader: HTTPS y WebSocket por conexión directa o por Tor, solo biblioteca estándar.

Regla de privacidad (dicha por Nicolás el 19/10/2026): a Binance se va directo, porque la
casa ya conoce al titular de la cuenta y Tor le hace perder salidas; todo lo demás
(calendarios, agenda de Trump, noticias, otras casas) va por Tor, para que ningún tercero
vea su IP ni qué está mirando. Ninguna conexión sin TLS verificado.
"""
import base64
import gzip
import hashlib
import http.client
import json
import os
import socket
import ssl
import struct
import threading
import time
import urllib.parse
import zlib

TOR = ("127.0.0.1", 9050)
AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
_TLS = ssl.create_default_context()          # verifica certificado y nombre del servidor
_GUID_WS = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Códigos que en Tor suelen significar «esta salida está vetada»: se cambia de circuito.
_VETO_SALIDA = {403, 451}
_REINTENTABLES = {429, 500, 502, 503, 504}


class ErrorRed(Exception):
    """Fallo de transporte: no hubo respuesta HTTP utilizable."""


class Rechazo(ErrorRed):
    """El servidor respondió con un error HTTP; se conserva el cuerpo para diagnosticar."""

    def __init__(self, estado, cuerpo, url):
        self.estado = estado
        self.cuerpo = cuerpo
        self.url = url
        resumen = cuerpo[:300].decode("utf-8", "replace") if isinstance(cuerpo, bytes) else str(cuerpo)[:300]
        super().__init__(f"HTTP {estado} en {url}: {resumen}")


class _Redireccion(Exception):
    def __init__(self, estado, destino):
        super().__init__(f"redirección {estado} a {destino}")
        self.estado = estado
        self.destino = destino


def _leer_exacto(sock, n):
    datos = bytearray()
    while len(datos) < n:
        trozo = sock.recv(n - len(datos))
        if not trozo:
            raise ErrorRed("la conexión se cerró a mitad de lectura")
        datos += trozo
    return bytes(datos)


def socks5(host, puerto, circuito, plazo):
    """Abre un túnel por Tor. Usuario SOCKS distinto = circuito distinto (IsolateSOCKSAuth).

    El nombre viaja al proxy (ATYP 3): Windows nunca resuelve el dominio, no hay fuga DNS.
    """
    s = socket.create_connection(TOR, timeout=plazo)
    try:
        s.sendall(b"\x05\x01\x02")
        if _leer_exacto(s, 2) != b"\x05\x02":
            raise ErrorRed("Tor no aceptó autenticación por usuario")
        usuario = circuito.encode("utf-8")[:255]
        s.sendall(b"\x01" + bytes([len(usuario)]) + usuario + b"\x01x")
        if _leer_exacto(s, 2)[1] != 0:
            raise ErrorRed("Tor rechazó el usuario SOCKS")
        nombre = host.encode("idna")
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(nombre)]) + nombre + struct.pack(">H", puerto))
        cabecera = _leer_exacto(s, 4)
        if cabecera[1] != 0:
            raise ErrorRed(f"Tor no pudo abrir {host}:{puerto} (código SOCKS {cabecera[1]})")
        tipo = cabecera[3]
        if tipo == 1:
            _leer_exacto(s, 6)
        elif tipo == 3:
            _leer_exacto(s, _leer_exacto(s, 1)[0] + 2)
        elif tipo == 4:
            _leer_exacto(s, 18)
        return s
    except BaseException:
        s.close()
        raise


def tor_disponible():
    try:
        socket.create_connection(TOR, timeout=2).close()
        return True
    except OSError:
        return False


class _Conexion(http.client.HTTPSConnection):
    def __init__(self, host, por_tor, circuito, plazo):
        super().__init__(host, 443, timeout=plazo, context=_TLS)
        self._por_tor = por_tor
        self._circuito = circuito

    def connect(self):
        if self._por_tor:
            crudo = socks5(self.host, self.port, self._circuito, self.timeout)
        else:
            crudo = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(crudo, server_hostname=self.host)


class Cliente:
    """Cliente HTTPS con conexiones reutilizables por servidor.

    ruta: "directo" o "tor". Por Tor no hay plan B directo: si todas las salidas fallan,
    se informa el fallo, nunca se sale con la IP real.
    """

    def __init__(self, ruta="tor", plazo=25, reintentos=4, etiqueta="trader"):
        if ruta not in ("directo", "tor"):
            raise ValueError("ruta debe ser 'directo' o 'tor'")
        self.ruta = ruta
        self.plazo = plazo
        self.reintentos = reintentos
        self.etiqueta = etiqueta
        self._conexiones = {}
        self._candado = threading.Lock()
        self._vuelta = int.from_bytes(os.urandom(2), "big")
        self.ultimo_peso = {}            # cabeceras de consumo (Binance: X-MBX-USED-WEIGHT-1M)

    def _circuito(self):
        return f"{self.etiqueta}-{self._vuelta}"

    def cambiar_circuito(self):
        with self._candado:
            self._vuelta += 1
            viejas = list(self._conexiones.values())
            self._conexiones.clear()
        for c in viejas:
            c.close()

    def _conexion(self, host):
        with self._candado:
            c = self._conexiones.get(host)
            if c is None:
                c = _Conexion(host, self.ruta == "tor", self._circuito(), self.plazo)
                self._conexiones[host] = c
            return c

    def _soltar(self, host):
        with self._candado:
            c = self._conexiones.pop(host, None)
        if c:
            c.close()

    def pedir(self, metodo, url, cabeceras=None, cuerpo=None, redirecciones=3):
        """Devuelve (estado, cabeceras_dict, cuerpo_bytes). Lanza Rechazo/ErrorRed al agotar intentos.

        Sigue hasta 3 redirecciones de GET, solo hacia https y por la misma ruta (Tor o directo).
        """
        try:
            return self._pedir(metodo, url, cabeceras, cuerpo)
        except _Redireccion as r:
            if metodo != "GET" or redirecciones <= 0:
                raise Rechazo(r.estado, b"", url) from None
            destino = urllib.parse.urljoin(url, r.destino)
            return self.pedir(metodo, destino, cabeceras, cuerpo, redirecciones - 1)

    def _pedir(self, metodo, url, cabeceras=None, cuerpo=None):
        partes = urllib.parse.urlsplit(url)
        if partes.scheme != "https":
            raise ValueError("solo se permite https")
        host = partes.hostname
        camino = partes.path or "/"
        if partes.query:
            camino += "?" + partes.query
        cab = {"Host": host, "User-Agent": AGENTE, "Accept-Encoding": "gzip, deflate",
               "Accept": "*/*", "Connection": "keep-alive"}
        if cabeceras:
            cab.update(cabeceras)
        ultimo = None
        for intento in range(self.reintentos):
            conexion = self._conexion(host)
            try:
                conexion.request(metodo, camino, body=cuerpo, headers=cab)
                resp = conexion.getresponse()
                datos = resp.read()
                cab_resp = {k.lower(): v for k, v in resp.getheaders()}
                if resp.will_close:
                    self._soltar(host)
            except (OSError, http.client.HTTPException, ErrorRed) as e:
                self._soltar(host)
                ultimo = ErrorRed(f"{type(e).__name__}: {e}")
                if self.ruta == "tor" and intento >= 1:
                    self.cambiar_circuito()
                time.sleep(min(2 ** intento, 8))
                continue
            codificacion = cab_resp.get("content-encoding", "")
            if codificacion == "gzip":
                datos = gzip.decompress(datos)
            elif codificacion == "deflate":
                datos = zlib.decompress(datos)
            for nombre in ("x-mbx-used-weight-1m", "x-mbx-order-count-10s", "x-mbx-order-count-1d"):
                if nombre in cab_resp:
                    self.ultimo_peso[nombre] = cab_resp[nombre]
            estado = resp.status
            if 200 <= estado < 300:
                return estado, cab_resp, datos
            if estado in (301, 302, 303, 307, 308) and cab_resp.get("location"):
                raise _Redireccion(estado, cab_resp["location"])
            ultimo = Rechazo(estado, datos, url)
            if estado == 418:
                raise ultimo                     # Binance ya bloqueó la IP: insistir lo empeora
            if self.ruta == "tor" and estado in _VETO_SALIDA:
                self.cambiar_circuito()
                continue
            if estado in _REINTENTABLES:
                espera = cab_resp.get("retry-after")
                time.sleep(float(espera) if espera and espera.isdigit() else min(2 ** intento, 8))
                continue
            raise ultimo                         # 4xx de verdad: el pedido está mal, no se repite
        raise ultimo if ultimo else ErrorRed("sin respuesta")

    def json(self, url, params=None, cabeceras=None):
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        _, _, datos = self.pedir("GET", url, cabeceras)
        return json.loads(datos)

    def texto(self, url, params=None, cabeceras=None):
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        _, _, datos = self.pedir("GET", url, cabeceras)
        return datos.decode("utf-8", "replace")

    def binario(self, url):
        return self.pedir("GET", url)[2]

    def cerrar(self):
        with self._candado:
            for c in self._conexiones.values():
                c.close()
            self._conexiones.clear()


class WebSocket:
    """Cliente WebSocket (RFC 6455) mínimo sobre TLS, directo o por Tor.

    recibir() devuelve el texto del siguiente mensaje; responde solo a los ping del
    servidor (Binance corta si no hay pong en 10 minutos).
    """

    def __init__(self, url, ruta="directo", circuito="ws", plazo=30):
        partes = urllib.parse.urlsplit(url)
        if partes.scheme != "wss":
            raise ValueError("solo se permite wss")
        self.host = partes.hostname
        self.puerto = partes.port or 443
        self.camino = (partes.path or "/") + ("?" + partes.query if partes.query else "")
        self.ruta = ruta
        self.circuito = circuito
        self.plazo = plazo
        self.sock = None
        self._buf = bytearray()
        self._envio = threading.Lock()

    def abrir(self):
        if self.ruta == "tor":
            crudo = socks5(self.host, self.puerto, self.circuito, self.plazo)
        else:
            crudo = socket.create_connection((self.host, self.puerto), self.plazo)
        self.sock = _TLS.wrap_socket(crudo, server_hostname=self.host)
        self.sock.settimeout(self.plazo)
        clave = base64.b64encode(os.urandom(16)).decode()
        pedido = (f"GET {self.camino} HTTP/1.1\r\nHost: {self.host}\r\nUser-Agent: {AGENTE}\r\n"
                  f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {clave}\r\n"
                  f"Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(pedido.encode())
        cabecera = bytearray()
        while b"\r\n\r\n" not in cabecera:
            trozo = self.sock.recv(4096)
            if not trozo:
                raise ErrorRed("el servidor cerró durante el saludo WebSocket")
            cabecera += trozo
            if len(cabecera) > 65536:
                raise ErrorRed("saludo WebSocket demasiado largo")
        fin = cabecera.index(b"\r\n\r\n") + 4
        self._buf = bytearray(cabecera[fin:])
        lineas = cabecera[:fin].decode("latin-1").split("\r\n")
        if " 101 " not in lineas[0] + " ":
            raise ErrorRed(f"el servidor no aceptó WebSocket: {lineas[0]}")
        esperado = base64.b64encode(hashlib.sha1((clave + _GUID_WS).encode()).digest()).decode()
        aceptado = ""
        for linea in lineas[1:]:
            if linea.lower().startswith("sec-websocket-accept:"):
                aceptado = linea.split(":", 1)[1].strip()
        if aceptado != esperado:
            raise ErrorRed("Sec-WebSocket-Accept no coincide: posible intermediario")
        return self

    def _leer(self, n):
        while len(self._buf) < n:
            trozo = self.sock.recv(65536)
            if not trozo:
                raise ErrorRed("WebSocket cerrado por el servidor")
            self._buf += trozo
        datos = bytes(self._buf[:n])
        del self._buf[:n]
        return datos

    def _marco(self):
        b1, b2 = self._leer(2)
        fin = bool(b1 & 0x80)
        codigo = b1 & 0x0F
        enmascarado = bool(b2 & 0x80)
        largo = b2 & 0x7F
        if largo == 126:
            largo = struct.unpack(">H", self._leer(2))[0]
        elif largo == 127:
            largo = struct.unpack(">Q", self._leer(8))[0]
        mascara = self._leer(4) if enmascarado else None
        carga = self._leer(largo)
        if mascara:
            carga = bytes(c ^ mascara[i % 4] for i, c in enumerate(carga))
        return fin, codigo, carga

    def _enviar(self, codigo, carga=b""):
        mascara = os.urandom(4)
        n = len(carga)
        if n < 126:
            cabecera = struct.pack(">BB", 0x80 | codigo, 0x80 | n)
        elif n < 65536:
            cabecera = struct.pack(">BBH", 0x80 | codigo, 0x80 | 126, n)
        else:
            cabecera = struct.pack(">BBQ", 0x80 | codigo, 0x80 | 127, n)
        enmascarada = bytes(c ^ mascara[i % 4] for i, c in enumerate(carga))
        with self._envio:
            self.sock.sendall(cabecera + mascara + enmascarada)

    def enviar(self, texto):
        self._enviar(0x1, texto.encode("utf-8"))

    def recibir(self):
        partes = []
        while True:
            fin, codigo, carga = self._marco()
            if codigo == 0x9:                      # ping del servidor -> pong con la misma carga
                self._enviar(0xA, carga)
                continue
            if codigo == 0xA:
                continue
            if codigo == 0x8:
                raise ErrorRed("el servidor cerró el WebSocket")
            partes.append(carga)
            if fin:
                return b"".join(partes).decode("utf-8", "replace")

    def cerrar(self):
        if self.sock:
            try:
                self._enviar(0x8, struct.pack(">H", 1000))
            except OSError:
                pass
            self.sock.close()
            self.sock = None
