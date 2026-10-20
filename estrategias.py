"""Sistemas de entrada. El mismo código sirve al banco de pruebas y al motor en vivo.

A  «MEZCLA intradía»: la compra del retroceso de Nicolás (junio 2026, +112 % en 1h/24h) llevada
   a marcos cortos: tendencia alcista confirmada en un marco mayor + precio en la zona media del
   rango (0,35–0,65, retroceso Fibonacci) + patrones de vela que no contradigan.
B  «Rebote tras barrido»: caída brusca (z de retorno muy negativo) con volumen alto, agresores
   vendedores y, si se pide, interés abierto que cae (liquidaciones de largos): se compra el rebote.
D  «Curso Quantdemy»: el BTCUSDT.py del curso (pendiente de MA48 > 0 y precio > MA48·0,995,
   objetivo +1 %, stop −1 %) y su versión con R:R 1:2 del propio curso de riesgo.
C  «Azar»: entradas al azar con la gestión del sistema que se compara (control de ganancias falsas).
"""
import math
import random

import indicadores as ind
from simulador import Senal

MIN = 60_000
NAN = float("nan")


def _ok(*xs):
    return all(x == x for x in xs)          # descarta NaN


class Marco:
    """Indicadores de un marco de tiempo, alineados sin mirar al futuro."""

    def __init__(self, velas, minutos, metricas=None, financiacion=None, mayor=None):
        self.v = velas
        self.minutos = minutos
        self.ancho = minutos * MIN
        o, h, l, c, vol = list(velas.o), list(velas.h), list(velas.l), list(velas.c), list(velas.v)
        self.o, self.h, self.l, self.c, self.vol = o, h, l, c, vol
        self.t = list(velas.t)
        self.atr = ind.atr(h, l, c, 14)
        self.ema20 = ind.ema(c, 20)
        self.ema50 = ind.ema(c, 50)
        self.ema200 = ind.ema(c, 200)
        self.ma48 = _media_simple(c, 48)
        self.rsi = ind.rsi(c, 14)
        self.pend = {w: ind.pendiente_log(c, w) for w in (24, 48, 96)}
        self.rango = {}
        for w in (48, 96):
            mx, mn = ind.maximo_minimo(h, l, w)
            self.rango[w] = ind.posicion_rango(c, mx, mn)
        self.vz = ind.zscore(vol, 96)
        self.vwap = ind.vwap_diario(self.t, h, l, c, vol)
        tb = list(velas.tb)
        self.toma = [tb[i] / vol[i] if vol[i] > 0 else 0.5 for i in range(len(c))]
        self.ret = {k: ind.retornos(c, k) for k in (1, 3, 6)}
        ventana_sd = max(int(2 * 1440 / minutos), 48)          # dos días de velas
        self.ret_sd = {k: ind.media_desvio(self.ret[k], ventana_sd)[1] for k in (1, 3, 6)}
        self.pend_ma48 = ind.pendiente_log([x if x == x else c[i] for i, x in enumerate(self.ma48)], 24)
        self.mayor = mayor
        self.i_mayor = ind.alinear(self.t, self.ancho, mayor.t, mayor.ancho) if mayor else None
        self.met = metricas
        self.i_met = ind.alinear_puntos(self.t, self.ancho, metricas.t) if metricas is not None else None
        self.fin = financiacion
        self.i_fin = ind.alinear_puntos(self.t, self.ancho, financiacion[0]) if financiacion else None

    def cierre(self, i):
        return self.t[i] + self.ancho

    def oi_cambio(self, i, puntos):
        if self.i_met is None:
            return NAN
        k = self.i_met[i]
        if k < puntos or self.cierre(i) - self.met.t[k] > 15 * MIN:
            return NAN
        return (self.met.oi[k] / self.met.oi[k - puntos] - 1) * 100

    def financiacion(self, i):
        if self.i_fin is None or self.i_fin[i] < 0:
            return NAN
        return self.fin[1][self.i_fin[i]]

    def rasgos(self, i):
        """Variables para el modelo de probabilidad (todas conocidas al cierre de la vela i)."""
        c = self.c[i]
        k = self.i_mayor[i] if self.i_mayor else -1
        m = self.mayor
        return {
            "pend24": self.pend[24][i], "pend96": self.pend[96][i],
            "rango96": self.rango[96][i], "rsi": self.rsi[i],
            "atr_pct": self.atr[i] / c * 100 if self.atr[i] == self.atr[i] else NAN,
            "vz": self.vz[i], "toma": self.toma[i],
            "dist_vwap": (c / self.vwap[i] - 1) * 100,
            "dist_ema200": (c / self.ema200[i] - 1) * 100 if self.ema200[i] == self.ema200[i] else NAN,
            "ret3": self.ret[3][i],
            "mayor_pend48": m.pend[48][k] if k >= 0 else NAN,
            "mayor_rsi": m.rsi[k] if k >= 0 else NAN,
            "oi_1h": self.oi_cambio(i, 12), "oi_4h": self.oi_cambio(i, 48),
            "financiacion": self.financiacion(i) * 100 if self.fin else NAN,
            "hora_utc": (self.cierre(i) // 3_600_000) % 24,
        }


def _media_simple(x, n):
    out = [NAN] * len(x)
    s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def _acotar(x, lo, hi):
    return max(lo, min(hi, x))


# ---------------------------------------------------------------- Sistema A
A_BASE = dict(w=96, banda=(0.35, 0.65), pend_mayor_min=0.0, rsi_max=65.0, patron_min=0, verde=False,
              k_sl=2.0, R=2.0, be=1.0, H=32)


def senal_a(m, i, p):
    """¿Hay compra de retroceso en la vela i? Devuelve Senal o None."""
    k = m.i_mayor[i] if m.i_mayor else -1
    if k < 1:
        return None
    mayor = m.mayor
    c = m.c[i]
    pend_local = m.pend[p["w"]][i]
    pos = m.rango[p["w"]][i]
    if not _ok(pend_local, pos, m.atr[i], m.rsi[i], mayor.pend[48][k], mayor.ema50[k]):
        return None
    if mayor.pend[48][k] <= p["pend_mayor_min"] or mayor.c[k] <= mayor.ema50[k]:
        return None                                   # la tendencia mayor no es alcista
    if pend_local <= 0 or not (p["banda"][0] <= pos <= p["banda"][1]):
        return None                                   # no es un retroceso dentro de la subida
    if m.rsi[i] >= p["rsi_max"]:
        return None
    bajando = c < m.c[i - 3]
    puntaje, nombres = ind.patrones(m.o, m.h, m.l, m.c, i, bajando, not bajando)
    if puntaje < p["patron_min"]:
        return None
    if p["verde"] and c <= m.o[i]:
        return None
    stop = _acotar(p["k_sl"] * m.atr[i] / c, 0.003, 0.04)
    rasgos = m.rasgos(i)
    rasgos["patron"] = puntaje
    return Senal(m.cierre(i), stop, p["R"] * stop, p["H"] * m.minutos, p["be"], "A", rasgos)


# ---------------------------------------------------------------- Sistema B
B_BASE = dict(k=3, z=-3.0, vz=2.0, toma_max=0.45, oi_max=None, conf=False, colchon=0.3, R=1.5, be=0.8, H=24)


def senal_b(m, i, p):
    k = p["k"]
    if i < k + 2:
        return None
    r, sd = m.ret[k][i], m.ret_sd[k][i]
    if not _ok(r, sd, m.atr[i]) or sd <= 0:
        return None
    if r / sd > p["z"]:
        return None                                   # la caída no es lo bastante brusca
    vz = max((m.vz[j] for j in range(i - k + 1, i + 1) if m.vz[j] == m.vz[j]), default=NAN)
    if not _ok(vz) or vz < p["vz"]:
        return None
    vol = sum(m.vol[j] for j in range(i - k + 1, i + 1))
    toma = sum(m.toma[j] * m.vol[j] for j in range(i - k + 1, i + 1)) / vol if vol > 0 else 0.5
    if toma > p["toma_max"]:
        return None                                   # no hubo agresión vendedora
    if p["oi_max"] is not None:
        oi = m.oi_cambio(i, 12)
        if not _ok(oi) or oi > p["oi_max"]:
            return None                               # sin caída de interés abierto: no hubo liquidaciones
    if p["conf"] and m.c[i] <= m.o[i]:
        return None                                   # se exige vela de giro
    c = m.c[i]
    piso = min(m.l[j] for j in range(i - k + 1, i + 1)) - p["colchon"] * m.atr[i]
    stop = _acotar((c - piso) / c, 0.003, 0.05)
    rasgos = m.rasgos(i)
    rasgos["z_caida"] = r / sd
    rasgos["toma_barrido"] = toma
    return Senal(m.cierre(i), stop, p["R"] * stop, p["H"] * m.minutos, p["be"], "B", rasgos)


# ---------------------------------------------------------------- Sistema D (curso)
D_BASE = dict(stop=0.01, objetivo=0.01, H=96)


def senal_d(m, i, p):
    if not _ok(m.ma48[i], m.pend_ma48[i]):
        return None
    if m.pend_ma48[i] > 0 and m.c[i] > m.ma48[i] * 0.995:
        return Senal(m.cierre(i), p["stop"], p["objetivo"], p["H"] * m.minutos, 0.0, "D", m.rasgos(i))
    return None


# ---------------------------------------------------------------- generadores
def generar(m, funcion, p, desde=None, hasta=None):
    out = []
    for i in range(210, len(m.c) - 1):
        if desde is not None and m.cierre(i) < desde:
            continue
        if hasta is not None and m.cierre(i) >= hasta:
            break
        s = funcion(m, i, p)
        if s is not None:
            out.append(s)
    return out


def azar(m, referencia, semilla, desde=None, hasta=None):
    """Mismo número de entradas y misma gestión que `referencia`, en velas elegidas al azar."""
    rnd = random.Random(semilla)
    indices = [i for i in range(210, len(m.c) - 1)
               if (desde is None or m.cierre(i) >= desde) and (hasta is None or m.cierre(i) < hasta)
               and m.atr[i] == m.atr[i]]
    if not indices or not referencia:
        return []
    elegidos = sorted(rnd.sample(indices, min(len(referencia), len(indices))))
    orden = list(referencia)
    rnd.shuffle(orden)
    out = []
    for i, s in zip(elegidos, orden):
        # el stop se escala con la volatilidad del momento elegido, igual que en el sistema real
        atr_ref = s.rasgos.get("atr_pct", NAN)
        multiplo = s.stop_pct * 100 / atr_ref if atr_ref == atr_ref and atr_ref > 0 else None
        stop = _acotar(multiplo * m.atr[i] / m.c[i], 0.003, 0.05) if multiplo else s.stop_pct
        r = s.objetivo_pct / s.stop_pct if s.stop_pct > 0 else 1.0
        out.append(Senal(m.cierre(i), stop, r * stop, s.max_min, s.be_r, "C", m.rasgos(i)))
    return out
