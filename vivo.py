"""Datos en tiempo real de Binance para el agente (red directa, regla de Nicolás del 19/10).

- SerieViva: velas de 1 s que crecen segundo a segundo, con la misma interfaz que
  rapido.Serie para que los rasgos se calculen con el MISMO código que en el banco.
- Arranque y huecos: las velas que faltan se piden a la API (nunca se inventan).
- Flujos: contado (velas de 1 s de BTCUSDT y BTC/FDUSD, mejor compra y venta) y futuros
  (precio de marca y financiación, liquidaciones). Si un flujo se corta, se reconecta solo.
"""
import array
import bisect
import collections
import itertools
import json
import math
import queue
import threading
import time

from red import Cliente, WebSocket

SEG, MIN, HORA = 1000, 60_000, 3_600_000
NAN = float("nan")
CONTADO = "https://data-api.binance.vision/api/v3"
FUTUROS = "https://fapi.binance.com"
# El libro va como foto de 5 niveles por segundo (depth5@1000ms): el bookTicker de BTCUSDT manda
# cientos de mensajes por segundo y, con Windows frenando el proceso oculto, retrasaba las velas.
WS_CONTADO = ("wss://data-stream.binance.vision/stream?streams=btcusdt@kline_1s/btcfdusd@kline_1s/"
              "btcusdt@depth5@1000ms/btcfdusd@depth5@1000ms")
WS_FUTUROS = "wss://fstream.binance.com/market/stream?streams=btcusdt@markPrice@1s/btcusdt@forceOrder"


class SerieViva:
    """Velas de 1 s en crecimiento. Guarda `guardar` segundos (por omisión, 4 horas)."""

    def __init__(self, rasgos=True, guardar=4 * 3600):
        self.con_rasgos = rasgos
        self.guardar = guardar
        self._vaciar()

    def _vaciar(self):
        self.t = array.array("q")
        for campo in ("o", "h", "l", "c", "v", "tb", "n"):
            setattr(self, campo, array.array("d"))
        if self.con_rasgos:
            self.lc, self.r2 = array.array("d"), array.array("d")
            self.pv, self.ptb, self.pn, self.pr2 = (array.array("d", [0.0]) for _ in range(4))
            self.maxh300, self.minl300 = array.array("d"), array.array("d")
            self.maxh3600, self.minl3600 = array.array("d"), array.array("d")
        self.largo = 0

    @property
    def ultimo_t(self):
        return self.t[-1] if self.largo else None

    def indice(self, t_ms):
        return bisect.bisect_left(self.t, t_ms)

    def agregar(self, t, o, h, l, c, v, tb, n):
        if self.largo and t != self.t[-1] + SEG:
            raise ValueError(f"hueco: se esperaba {self.t[-1] + SEG} y llegó {t}")
        self.t.append(t)
        self.o.append(o)
        self.h.append(h)
        self.l.append(l)
        self.c.append(c)
        self.v.append(v)
        self.tb.append(tb)
        self.n.append(n)
        if self.con_rasgos:
            lc = math.log(c)
            r2 = (lc - self.lc[-1]) ** 2 if self.largo else 0.0
            self.lc.append(lc)
            self.r2.append(r2)
            self.pv.append(self.pv[-1] + v)
            self.ptb.append(self.ptb[-1] + tb)
            self.pn.append(self.pn[-1] + n)
            self.pr2.append(self.pr2[-1] + r2)
            k = self.largo + 1
            self.maxh300.append(max(self.h[-300:]) if k >= 300 else NAN)
            self.minl300.append(min(self.l[-300:]) if k >= 300 else NAN)
            self.maxh3600.append(max(self.h[-3600:]) if k >= 3600 else NAN)
            self.minl3600.append(min(self.l[-3600:]) if k >= 3600 else NAN)
        self.largo += 1
        if self.largo > self.guardar + 1800:
            self._recortar()

    def _recortar(self):
        corte = self.largo - self.guardar
        for campo in ("t", "o", "h", "l", "c", "v", "tb", "n"):
            setattr(self, campo, getattr(self, campo)[corte:])
        if self.con_rasgos:
            for campo in ("lc", "r2", "maxh300", "minl300", "maxh3600", "minl3600"):
                setattr(self, campo, getattr(self, campo)[corte:])
            for prefijo, base in (("pv", self.v), ("ptb", self.tb), ("pn", self.n), ("pr2", self.r2)):
                nuevo = array.array("d", [0.0])
                nuevo.extend(itertools.accumulate(base))
                setattr(self, prefijo, nuevo)
        self.largo = len(self.t)


def fila_kline(k):
    """Vela de la API REST (lista) o del flujo (dict) -> tupla (t, o, h, l, c, v, tb, n)."""
    if isinstance(k, dict):
        return (int(k["t"]), float(k["o"]), float(k["h"]), float(k["l"]), float(k["c"]), float(k["v"]),
                float(k["V"]), float(k["n"]))
    return (int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9]), float(k[8]))


class Mercado:
    """Todo lo que el agente lee de Binance, con su hora de llegada."""

    def __init__(self):
        self.rest = Cliente("directo", plazo=15, reintentos=3, etiqueta="trader-vivo")
        self.cola = queue.Queue(maxsize=100_000)
        self.libro = {}                       # mejor compra/venta por símbolo (BTCUSDT, BTCFDUSD)
        self.marca = {}                       # precio de marca y financiación estimada
        self.liquidaciones = collections.deque(maxlen=5000)    # (t_ms, lado, cantidad_btc, precio)
        self.salud = {"ws_contado": "sin conectar", "ws_futuros": "sin conectar", "reconexiones": 0,
                      "ultimo_mensaje_ms": 0}
        self._parar = threading.Event()

    # ---------- API REST ----------
    def klines(self, simbolo, intervalo, desde_ms=None, limite=1000, futuros=False):
        base = f"{FUTUROS}/fapi/v1/klines" if futuros else f"{CONTADO}/klines"
        params = {"symbol": simbolo, "interval": intervalo, "limit": limite}
        if desde_ms is not None:
            params["startTime"] = int(desde_ms)
        return [fila_kline(k) for k in self.rest.json(base, params)]

    def klines_rango(self, simbolo, intervalo, desde_ms, hasta_ms, ancho_ms):
        """Velas cerradas con t en [desde_ms, hasta_ms), en tandas de 1000."""
        out = []
        t = desde_ms
        while t < hasta_ms:
            lote = self.klines(simbolo, intervalo, t, 1000)
            lote = [k for k in lote if k[0] < hasta_ms]
            if not lote:
                break
            out.extend(lote)
            t = lote[-1][0] + ancho_ms
            if len(lote) < 1000:
                break
        return out

    def metricas_oi(self, limite=500):
        filas = self.rest.json(f"{FUTUROS}/futures/data/openInterestHist",
                               {"symbol": "BTCUSDT", "period": "5m", "limit": limite})
        return [(int(f["timestamp"]), float(f["sumOpenInterest"])) for f in filas]

    def financiacion(self, limite=50):
        filas = self.rest.json(f"{FUTUROS}/fapi/v1/fundingRate", {"symbol": "BTCUSDT", "limit": limite})
        return [(int(f["fundingTime"]), float(f["fundingRate"])) for f in filas]

    def interes_abierto_ahora(self):
        d = self.rest.json(f"{FUTUROS}/fapi/v1/openInterest", {"symbol": "BTCUSDT"})
        return float(d["openInterest"])

    def hora_servidor(self):
        return int(self.rest.json(f"{CONTADO}/time")["serverTime"])

    # ---------- flujos ----------
    def _leer(self, url, nombre, manejar):
        espera = 1
        while not self._parar.is_set():
            ws = None
            try:
                ws = WebSocket(url, "directo", circuito=nombre, plazo=30).abrir()
                self.salud[nombre] = "conectado"
                espera = 1
                while not self._parar.is_set():
                    manejar(json.loads(ws.recibir()))
                    self.salud["ultimo_mensaje_ms"] = int(time.time() * 1000)
            except Exception as e:
                self.salud[nombre] = f"reconectando ({type(e).__name__})"
                self.salud["reconexiones"] += 1
            finally:
                if ws:
                    try:
                        ws.cerrar()
                    except Exception:
                        pass
            self._parar.wait(espera)
            espera = min(espera * 2, 30)

    def _contado(self, m):
        datos = m.get("data", {})
        flujo = m.get("stream", "")
        if flujo.endswith("@kline_1s"):
            k = datos["k"]
            if k.get("x"):
                self.cola.put(("vela", k["s"], fila_kline(k)))
        elif "@depth5" in flujo:
            try:
                self.libro[flujo.split("@")[0].upper()] = {
                    "compra": float(datos["bids"][0][0]), "venta": float(datos["asks"][0][0]),
                    "compra_btc_5": round(sum(float(q) for _, q in datos["bids"]), 5),
                    "venta_btc_5": round(sum(float(q) for _, q in datos["asks"]), 5),
                    "llegada_ms": int(time.time() * 1000)}
            except (KeyError, IndexError, ValueError):
                pass

    def _futuros(self, m):
        datos = m.get("data", {})
        flujo = m.get("stream", "")
        if flujo.endswith("@markPrice@1s"):
            self.marca = {"marca": float(datos["p"]), "indice": float(datos["i"]),
                          "financiacion": float(datos["r"]), "proxima_ms": int(datos["T"]), "t": int(datos["E"])}
        elif flujo.endswith("@forceOrder"):
            o = datos.get("o", {})
            try:
                self.liquidaciones.append((int(o["T"]), o["S"], float(o["z"]), float(o["ap"])))
            except (KeyError, ValueError):
                pass

    def arrancar_flujos(self):
        for url, nombre, manejar in ((WS_CONTADO, "ws_contado", self._contado),
                                     (WS_FUTUROS, "ws_futuros", self._futuros)):
            threading.Thread(target=self._leer, args=(url, nombre, manejar), daemon=True, name=nombre).start()

    def parar(self):
        self._parar.set()

    def liquidado(self, desde_ms):
        """BTC liquidados desde `desde_ms`: (largos liquidados, cortos liquidados)."""
        largos = sum(q for t, lado, q, _ in self.liquidaciones if t >= desde_ms and lado == "SELL")
        cortos = sum(q for t, lado, q, _ in self.liquidaciones if t >= desde_ms and lado == "BUY")
        return largos, cortos
