"""Contexto de fuera de Binance, siempre por Tor: calendario macro, agenda de Trump, miedo y
codicia, dólar sintético e interés abierto de otras casas.

Regla de Nicolás (19/10/2026): todo lo que no es Binance va por Tor, para que ningún tercero
vea su IP ni qué está mirando. Si Tor no responde, el dato queda vacío; nunca se sale directo.

Uso en el agente: solo FRENA entradas (nunca abre una). Estos frenos no están en el banco de
pruebas, porque no hay histórico fiable de ellos: se anotan aparte para medir su efecto.
"""
import csv
import datetime as dt
import io
import json
import math
import threading
import time

from red import Cliente, tor_disponible

UTC = dt.timezone.utc
NUEVA_YORK_INVIERNO = dt.timezone(dt.timedelta(hours=-5))
NUEVA_YORK_VERANO = dt.timezone(dt.timedelta(hours=-4))

FUENTES = {
    "calendario": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "trump": "https://media-cdn.factba.se/rss/csv/trump/calendar.csv",
    "miedo": "https://api.alternative.me/fng/?limit=1",
    "divisas": "https://api.kraken.com/0/public/Ticker?pair=EURUSD,GBPUSD,USDJPY,USDCAD,USDCHF",
    "bybit": "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=5min&limit=1",
    "okx": "https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP",
    "deribit": "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future",
}
REFRESCO = {"calendario": 3600, "trump": 1800, "miedo": 3600, "divisas": 300, "bybit": 300, "okx": 300,
            "deribit": 300}
# Ventanas de freno (minutos antes, minutos después)
VENTANA_MACRO_ALTO = (15, 30)
VENTANA_MACRO_MEDIO = (5, 10)
VENTANA_TRUMP = (10, 30)
PALABRAS_TRUMP = ("remarks", "speech", "address", "press conference", "interview", "statement", "rally",
                  "q&a", "announcement", "signs", "signing", "briefing", "truth social", "meets with")
# Pesos del índice del dólar (ICE): EUR, JPY, GBP, CAD, SEK, CHF. Sin SEK en Kraken: se reparte.
PESOS_DXY = {"EURUSD": -0.576, "USDJPY": 0.136, "GBPUSD": -0.119, "USDCAD": 0.091, "USDCHF": 0.036}


def _hora_nueva_york(fecha):
    """Desfase de Nueva York (horario de verano de EE. UU.: 2.º domingo de marzo a 1.er domingo de noviembre)."""
    a = fecha.year
    marzo = dt.date(a, 3, 8 + (6 - dt.date(a, 3, 8).weekday()) % 7)
    noviembre = dt.date(a, 11, 1 + (6 - dt.date(a, 11, 1).weekday()) % 7)
    return NUEVA_YORK_VERANO if marzo <= fecha < noviembre else NUEVA_YORK_INVIERNO


class Contexto:
    def __init__(self):
        self.red = Cliente("tor", plazo=45, reintentos=3, etiqueta="trader-contexto")
        self.datos = {}
        self.cuando = {}
        self.errores = {}
        self.eventos = []           # (inicio_ms, fin_ms, motivo)
        self._candado = threading.Lock()
        self._parar = threading.Event()

    # ---------- lectura ----------
    def _bajar(self, nombre):
        url = FUENTES[nombre]
        if nombre == "trump":
            return self.red.texto(url)
        return self.red.json(url)

    def refrescar(self, forzar=False):
        if not tor_disponible():
            self.errores["tor"] = "Tor no escucha en 127.0.0.1:9050"
            return
        ahora = time.time()
        for nombre in FUENTES:
            if not forzar and ahora - self.cuando.get(nombre, 0) < REFRESCO[nombre]:
                continue
            try:
                crudo = self._bajar(nombre)
                with self._candado:
                    self.datos[nombre] = crudo
                    self.cuando[nombre] = ahora
                    self.errores.pop(nombre, None)
            except Exception as e:                 # una fuente caída no detiene a las demás
                self.errores[nombre] = f"{type(e).__name__}: {str(e)[:120]}"
                self.cuando[nombre] = ahora - REFRESCO[nombre] + 120     # reintento en 2 minutos
        self._armar_eventos()

    def correr(self):
        while not self._parar.is_set():
            try:
                self.refrescar()
            except Exception as e:
                self.errores["ciclo"] = str(e)[:160]
            self._parar.wait(60)

    def parar(self):
        self._parar.set()

    # ---------- eventos que frenan ----------
    def _armar_eventos(self):
        eventos = []
        cal = self.datos.get("calendario")
        if isinstance(cal, list):
            for e in cal:
                if e.get("country") != "USD" or e.get("impact") not in ("High", "Medium"):
                    continue
                try:
                    inicio = dt.datetime.fromisoformat(e["date"])
                except (KeyError, ValueError):
                    continue
                antes, despues = VENTANA_MACRO_ALTO if e["impact"] == "High" else VENTANA_MACRO_MEDIO
                ms = int(inicio.timestamp() * 1000)
                eventos.append((ms - antes * 60_000, ms + despues * 60_000,
                                f"dato de EE. UU. ({e['impact']}): {e.get('title', '')}"))
        trump = self.datos.get("trump")
        if isinstance(trump, str):
            for fila in csv.DictReader(io.StringIO(trump)):
                texto = (fila.get("Details") or "").lower()
                if not any(p in texto for p in PALABRAS_TRUMP):
                    continue
                try:
                    fecha = dt.date.fromisoformat(fila["Date"])
                    hora = dt.time.fromisoformat(fila["Time"]) if fila.get("Time") else None
                except (KeyError, ValueError):
                    continue
                if hora is None:
                    continue
                inicio = dt.datetime.combine(fecha, hora, _hora_nueva_york(fecha))
                ms = int(inicio.timestamp() * 1000)
                antes, despues = VENTANA_TRUMP
                eventos.append((ms - antes * 60_000, ms + despues * 60_000,
                                f"Trump: {(fila.get('Details') or '')[:90]}"))
        eventos.sort()
        with self._candado:
            self.eventos = eventos

    def bloqueo(self, t_ms):
        """Motivo para no abrir un ciclo en el instante t_ms (hora del servidor), o None."""
        with self._candado:
            for a, b, motivo in self.eventos:
                if a <= t_ms <= b:
                    return motivo
                if a > t_ms:
                    break
        return None

    def proximo(self, t_ms):
        with self._candado:
            for a, b, motivo in self.eventos:
                if b >= t_ms:
                    return {"desde_ms": a, "hasta_ms": b, "motivo": motivo}
        return None

    # ---------- lecturas para el panel ----------
    def resumen(self):
        out = {"errores": dict(self.errores)}
        d = self.datos
        try:
            f = d["miedo"]["data"][0]
            out["miedo_codicia"] = {"valor": int(f["value"]), "clase": f["value_classification"]}
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        try:
            r = d["divisas"]["result"]
            precios = {}
            for clave, v in r.items():                  # Kraken nombra ZEURZUSD, ZUSDZJPY, USDCHF…
                limpio = clave.replace("Z", "")
                if limpio in PESOS_DXY:
                    precios[limpio] = float(v["c"][0])
            if len(precios) == len(PESOS_DXY):
                escala = 1 / sum(abs(p) for p in PESOS_DXY.values()) * (0.576 + 0.136 + 0.119 + 0.091 + 0.042 + 0.036)
                dxy = 50.14348112 * math.prod(precios[p] ** (w * escala) for p, w in PESOS_DXY.items())
                out["dolar_sintetico"] = round(dxy, 3)
        except (KeyError, TypeError, ValueError):
            pass
        total, partes = 0.0, {}
        try:
            partes["bybit"] = float(d["bybit"]["result"]["list"][0]["openInterest"])
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        try:
            partes["okx"] = float(d["okx"]["data"][0]["oiCcy"])
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        try:
            usd = sum(x.get("open_interest", 0) for x in d["deribit"]["result"])
            precio = d["deribit"]["result"][0].get("estimated_delivery_price") or 0
            if precio:
                partes["deribit"] = usd / precio
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError):
            pass
        if partes:
            out["interes_abierto_otras_btc"] = {k: round(v) for k, v in partes.items()}
            total = sum(partes.values())
            out["interes_abierto_otras_total_btc"] = round(total)
        out["actualizado"] = {k: dt.datetime.fromtimestamp(v, UTC).isoformat(timespec="seconds")
                              for k, v in self.cuando.items()}
        return out
