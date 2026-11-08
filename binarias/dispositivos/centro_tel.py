"""Centro de estrategias en el teléfono (07/11/2026): las cinco en papel, 24/7, con su página local y los avisos a Telegram.

Pedido del dueño del 07/11: que el programa quede instalado también en su celular y que los avisos salgan en vivo en la pantalla
y en su Telegram. Aquí no hay botones ni llave de Binance: la llave con permisos de operar no sale del PC (decisión suya del
04/11). Solo datos públicos de futuros (directo a Binance, como permite su regla) y Telegram por Tor.
- Página: http://127.0.0.1:8797 en el navegador del teléfono: la misma pantalla del Centro del PC.
- Telegram: cada señal de las cinco, su resultado sobre el mismo mensaje y cuando una llega a 75 %, queda apta (82 %) o baja.
  Los manda solo el teléfono, que corre las 24 horas; el PC los muestra en su pantalla sin repetirlos en Telegram.
- Mismo motor que el PC (centro.py), con paridad exacta frente al estudio c12.
Uso: python3 -I centro_tel.py · Arranca con arrancar.sh · Parar: crear PARAR en esta carpeta.
"""
import datetime as dt
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import avisos  # noqa: E402  (clave del bot, Tor y comillas, los mismos de la caja)
import centro as CE  # noqa: E402

PUERTO = 8797
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m"
FOI = "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=12"
REGISTRO = os.path.join(AQUI, "centro_tel.log")
PARAR = os.path.join(AQUI, "PARAR")
COL = dt.timezone(dt.timedelta(hours=-5))
H = {"User-Agent": "centro-binarias"}


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


# ---------------------------------------------------------------- datos públicos (lo mismo que conexion.py, sin la llave)
def _json(url, plazo=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=plazo) as r:
        return json.loads(r.read())


class Publico:
    @staticmethod
    def velas(limite=170, desde_ms=None):
        x = _json(FAPI + f"&limit={limite}" + (f"&startTime={desde_ms}" if desde_ms else ""))
        ahora, cerr, viva = time.time() * 1000, [], None
        for k in x:
            v = (int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]))
            if int(k[6]) < ahora:
                cerr.append(v)
            else:
                viva = v
        return cerr, viva

    @staticmethod
    def historial(dias):
        out, desde = [], int((time.time() - dias * 86400) * 1000)
        while True:
            x, _ = Publico.velas(1500, desde)
            if not x:
                break
            out += x
            desde = (x[-1][0] + 60) * 1000
            if len(x) < 1400:
                break
        return sorted({v[0]: v for v in out}.values())

    @staticmethod
    def cambio_interes(t_dec):
        pts = sorted((int(k["timestamp"]) // 1000, float(k["sumOpenInterest"])) for k in _json(FOI))
        a = [p for p in pts if p[0] <= t_dec - 300]
        b = [p for p in pts if p[0] <= t_dec - 1200]
        if not a or not b or t_dec - 300 - a[-1][0] > 600 or t_dec - 1200 - b[-1][0] > 600 or b[-1][1] <= 0:
            return None
        return a[-1][1] / b[-1][1] - 1


# ---------------------------------------------------------------- Telegram por Tor, con corrección del mismo mensaje
def telegram(texto, editar=None):
    try:
        partes = open(avisos.CLAVE, encoding="utf-8").read().split()
        token, chat = partes[0], partes[1]
    except Exception:
        log("falta ~/.config/binarias/telegram")
        return None
    metodo = "editMessageText" if editar else "sendMessage"
    conf = ["url = " + avisos.comillas(f"https://api.telegram.org/bot{token}/{metodo}"),
            "form-string = " + avisos.comillas(f"chat_id={chat}"),
            "form-string = " + avisos.comillas(f"text={texto[:4000]}")]
    if editar:
        conf.append("form-string = " + avisos.comillas(f"message_id={editar}"))
    for intento in range(3):
        usuario = f"centro{int(time.time()) % 100000}:x"
        try:
            r = subprocess.run(["curl", "-s", "--max-time", "90", "--socks5-hostname", f"{usuario}@{avisos.TOR}", "-K", "-"],
                               input="\n".join(conf) + "\n", capture_output=True, text=True, timeout=120)
            d = json.loads(r.stdout or "{}")
        except Exception as ex:
            d = {"description": type(ex).__name__}
        if d.get("ok"):
            return (d.get("result") or {}).get("message_id")
        if editar and "not modified" in str(d.get("description", "")):
            return editar
        if editar and d.get("error_code") == 400:
            return telegram(texto, None)
        log(f"Telegram sin confirmar (intento {intento + 1}): {str(d.get('description'))[:120]}")
        time.sleep(10)
    return None


class Notificador:
    def __init__(self):
        self.cola = queue.Queue()
        threading.Thread(target=self._correr, daemon=True).start()

    def avisar(self, aviso, al_enviar=None):
        self.cola.put((aviso, al_enviar))

    def _correr(self):
        while True:
            aviso, al_enviar = self.cola.get()
            try:
                mid = telegram(aviso["texto"], aviso.get("editar"))
                if mid and al_enviar:
                    al_enviar(mid)
                log(("corregido " if aviso.get("editar") else "enviado ") + aviso.get("corto", "")[:90])
            except Exception as ex:
                log(f"aviso sin enviar: {type(ex).__name__}: {ex}")


# ---------------------------------------------------------------- página del teléfono
CENTRO = None


class Pagina(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/api/centro":
            c = json.dumps(CENTRO.foto if CENTRO else {"listo": False}, ensure_ascii=False, default=str).replace("NaN", "null").encode("utf-8")
            tipo = "application/json; charset=utf-8"
        else:
            with open(os.path.join(AQUI, "centro.html"), encoding="utf-8") as f:
                html = f.read().replace('<a id="volver" href="/">← volver a la Mesa</a>', '<span class="dato">en el teléfono · sin botones</span>')
            c, tipo = html.encode("utf-8"), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(c)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(c)


def main():
    global CENTRO
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PUERTO), Pagina)
    except OSError:
        log("ya hay un centro corriendo en el puerto 8797")
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    CENTRO = CE.Centro(Publico)
    CENTRO.cada_foto = 10
    CENTRO.notificar = Notificador().avisar
    n = CENTRO.sembrar()
    log(f"centro en marcha en el teléfono · {len(n) if isinstance(n, list) else n} señales rehechas con velas · página en 127.0.0.1:{PUERTO}")
    while not os.path.exists(PARAR):
        try:
            cerr, viva = Publico.velas(170)
            CENTRO.actualizar(cerr, viva)
            if not CENTRO.listo:
                CENTRO.sembrar()
            time.sleep(5)
        except Exception as ex:
            log(f"error: {type(ex).__name__}: {str(ex)[:120]}")
            time.sleep(20)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
