"""Rasgos e indicadores del laboratorio sobre la rejilla densa (11/11/2026). Una sola función para la historia y el vivo.

Todas las ventanas son finitas (máximos, mínimos, medias y desviaciones deslizantes; RSI de Cutler con medias simples de 14),
así que la misma vela da la misma cifra con años de historia o con tres días, y la prueba de recorte puede exigir igualdad.
Barra b de 5 min: minutos 5b a 5b+4 de la rejilla; cierra en T = t0 + 300·(b+1). La apuesta de esa barra entra con el cierre
del minuto que abre en T (índice 5b+5, 60 s tarde) y sale con el del minuto que abre en T + plazo (índice 5b+5+plazo).
Rasgos de la red (19): los diez de pruebas\\t33_indice.py con su misma fórmula, distancia al máximo y al mínimo de 20 y 50
velas de 5 min, Bollinger %b, RSI de 5 y de 15 min, cuerpo de la vela y racha."""
import math
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as ventanas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import UMBRAL_OI  # noqa: E402

BLOQUE = 20000
LIMITE_CACHE = int(float(os.environ.get("LAB_CACHE_MB", "300")) * 1e6)  # la caja tiene 2,5 GB libres y Python de 32 bits
NOMBRES_RED = ["rend 1 min", "rend 5 min", "rend 15 min", "rend 60 min", "volatilidad 15/240", "posición en 4 h",
               "volumen 15/240", "estocástico 5 min", "hora (seno)", "hora (coseno)", "distancia al máximo de 20",
               "distancia al mínimo de 20", "distancia al máximo de 50", "distancia al mínimo de 50", "Bollinger %b",
               "RSI 5 min", "RSI 15 min", "cuerpo de la vela", "racha"]


def _reducir(filas, f):
    if f == "max":
        return filas.max(axis=1)
    if f == "min":
        return filas.min(axis=1)
    if f == "mean":
        return filas.mean(axis=1)
    if f == "std":
        return filas.std(axis=1)
    if f == "sum":
        return filas.sum(axis=1)
    raise ValueError(f)


def rodar(x, W, f):
    """Reducción f sobre x[i-W+1 .. i] para cada i (NaN si falta ventana o algún dato).
    La vista deslizante se arma por tramos: en Android de 32 bits numpy no acepta una vista de más de 2 GB nominales."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.full(n, np.nan)
    if n < W:
        return out
    for a in range(W - 1, n, BLOQUE):
        b = min(n, a + BLOQUE)
        out[a:b] = _reducir(ventanas(x[a - W + 1:b], W), f)
    return out


def en(x, W, j, f):
    """Reducción f sobre x[j-W+1 .. j] solo en las posiciones j (por tramos, como rodar)."""
    x = np.asarray(x, dtype=np.float64)
    j = np.asarray(j, dtype=np.int64)
    out = np.full(len(j), np.nan)
    ok = (j >= W - 1) & (j < len(x))
    if not ok.any() or len(x) < W:
        return out
    jj = j[ok]
    res = np.empty(len(jj))
    for a in range(0, len(jj), BLOQUE):
        sel = jj[a:a + BLOQUE]
        lo = int(sel.min()) - W + 1
        sw = ventanas(x[lo:int(sel.max()) + 1], W)
        res[a:a + BLOQUE] = _reducir(sw[sel - W + 1 - lo], f)
    out[ok] = res
    return out


def previo(x):
    """x desplazado una posición: el valor de la ventana que termina en la barra anterior."""
    return np.r_[np.nan, x[:-1]]


def rsi_cutler(c, n=14):
    d = np.r_[np.nan, np.diff(c)]
    with np.errstate(invalid="ignore"):
        g = np.where(d > 0, d, np.where(d == d, 0.0, np.nan))
        p = np.where(d < 0, -d, np.where(d == d, 0.0, np.nan))
    G, P = rodar(g, n, "mean"), rodar(p, n, "mean")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(G + P > 0, 100 * G / (G + P), np.where((G + P) == 0, 50.0, np.nan))


class Contexto:
    """Velas de 5 y 15 min, disparos y filtros en caché, probabilidades de la red y cambio del interés abierto."""

    def __init__(self, vel, interes=None, prob=None):
        self.vel = vel
        self.t0 = vel.t0
        n = vel.n
        nb = n // 5
        self.nb = nb
        A = vel.A[:, :nb * 5]
        self.O5 = A[0, 0::5].copy()
        self.H5 = A[1].reshape(nb, 5).max(axis=1)
        self.L5 = A[2].reshape(nb, 5).min(axis=1)
        self.C5 = A[3, 4::5].copy()
        self.V5 = A[4].reshape(nb, 5).sum(axis=1)
        nq = n // 15
        B = vel.A[3, :nq * 15]
        self.C15 = B[14::15].copy()
        self.q15 = (np.arange(nb, dtype=np.int64) + 1) // 3 - 1
        self.T = self.t0 + 300 * (np.arange(nb, dtype=np.int64) + 1)
        self.j = 5 * np.arange(nb, dtype=np.int64) + 4
        self.C1 = vel.A[3, :n]
        self.I1 = vel.I[:n]
        self.cache = {}
        self.bytes = 0
        self.limite = LIMITE_CACHE
        self.doi = interes.cambio(self.T) if interes is not None else np.full(nb, np.nan)
        self.prob = dict(prob or {})

    # ------------------------------------------------------------ caché con tope de memoria (lo más viejo sale primero)
    def _tomar(self, clave):
        x = self.cache.pop(clave)
        self.cache[clave] = x
        return x

    def _poner(self, clave, valor):
        self.cache[clave] = valor
        self.bytes += getattr(valor, "nbytes", 0)
        while self.bytes > self.limite and len(self.cache) > 1:
            viejo = next(iter(self.cache))
            if viejo == clave:
                break
            self.bytes -= getattr(self.cache.pop(viejo), "nbytes", 0)
        return valor

    def _base(self, clave, fn):
        if clave in self.cache:
            return self._tomar(clave)
        return self._poner(clave, fn())

    def lc(self):
        return self._base("lc", lambda: np.log(self.C1))

    def r2(self):
        def f():
            lc = self.lc()
            r = np.r_[0.0, np.diff(lc)]
            return r * r
        return self._base("r2", f)

    def sigma(self, W):
        """Raíz de la media de los rendimientos de 1 min al cuadrado en W minutos, en el último minuto de cada barra."""
        return self._base(("sig", W), lambda: np.sqrt(np.maximum(en(self.r2(), W, self.j, "mean"), 1e-12)))

    def rsi(self, tf):
        def f():
            if tf == 5:
                return rsi_cutler(self.C5)
            r15 = rsi_cutler(self.C15)
            out = np.full(self.nb, np.nan)
            ok = (self.q15 >= 0) & (self.q15 < len(r15))
            out[ok] = r15[self.q15[ok]]
            return out
        return self._base(("rsi", tf), f)

    def maximo_previo(self, N):
        return self._base(("mxp", N), lambda: previo(rodar(self.H5, N, "max")))

    def minimo_previo(self, N):
        return self._base(("mnp", N), lambda: previo(rodar(self.L5, N, "min")))

    # ------------------------------------------------------------ disparos: +1 empuje hacia arriba, −1 hacia abajo
    def disparo(self, nombre, prm, plazo):
        clave = ("d", nombre, tuple(sorted(prm.items())), plazo if nombre == "red" else 0)
        if clave in self.cache:
            return self._tomar(clave)
        raw = np.zeros(self.nb, dtype=np.int8)
        with np.errstate(invalid="ignore", divide="ignore"):
            if nombre == "ruptura":
                N = int(prm["n"])
                raw[self.C5 > self.maximo_previo(N)] = 1
                raw[self.C5 < self.minimo_previo(N)] = -1
            elif nombre == "bollinger":
                W, k = int(prm["w"]), float(prm["k"])
                m = self._base(("bm", W), lambda: rodar(self.C5, W, "mean"))
                s = self._base(("bs", W), lambda: rodar(self.C5, W, "std"))
                raw[self.C5 > m + k * s] = 1
                raw[self.C5 < m - k * s] = -1
            elif nombre == "rsi":
                r, U = self.rsi(int(prm["tf"])), float(prm["u"])
                raw[r > U] = 1
                raw[r < 100 - U] = -1
            elif nombre == "impulso":
                m, z = int(prm["m"]), float(prm["z"])
                lc = self.lc()
                jm = self.j - m
                x = np.full(self.nb, np.nan)
                ok = jm >= 0
                x[ok] = (lc[self.j[ok]] - lc[jm[ok]]) / (self.sigma(60)[ok] * math.sqrt(m))
                raw[x > z] = 1
                raw[x < -z] = -1
            elif nombre == "rango":
                W, q = int(prm["h"]) * 12, float(prm["q"])
                mx = self._base(("rmx", W), lambda: rodar(self.H5, W, "max"))
                mn = self._base(("rmn", W), lambda: rodar(self.L5, W, "min"))
                pos = np.where(mx > mn, (self.C5 - mn) / (mx - mn), np.nan)
                raw[pos > q] = 1
                raw[pos < 1 - q] = -1
            elif nombre == "red":
                p, c = self.prob.get(plazo), float(prm["c"])
                if p is not None:
                    raw[p >= c] = 1
                    raw[p <= 1 - c] = -1
            else:
                raise ValueError(f"disparo desconocido: {nombre}")
        return self._poner(clave, raw)

    # ------------------------------------------------------------ filtros: máscara de barras donde la forma puede apostar
    def filtro(self, nombre, valor, plazo, apuesta):
        with np.errstate(invalid="ignore", divide="ignore"):
            if nombre == "oi":
                return self._base("f_oi", lambda: self.doi <= UMBRAL_OI) if valor else np.ones(self.nb, bool)
            if nombre == "franja":
                h0, largo = int(valor[0]), int(valor[1])
                hc = ((self.T - 18000) % 86400) // 3600
                return ((hc - h0) % 24) < largo
            if nombre == "vol":
                tipo, r = valor[0], float(valor[1])
                ratio = self._base("f_ratio", lambda: self.sigma(15) / self.sigma(240))
                return ratio < r if tipo == "baja" else ratio > r
            if nombre == "conf":
                p = self.prob.get(plazo)
                if p is None:
                    return np.zeros(self.nb, bool)
                return np.where(apuesta > 0, p, 1 - p) >= float(valor)
            if nombre == "cada10":
                return (self.T % 600) == 0 if valor else np.ones(self.nb, bool)
        raise ValueError(f"filtro desconocido: {nombre}")

    # ------------------------------------------------------------ rasgos de la red
    def rasgos_red(self, b=None):
        """Matriz (barras × 19) y máscara de barras con todos los rasgos presentes (sin rellenar con ceros)."""
        b = np.arange(self.nb, dtype=np.int64) if b is None else np.asarray(b, dtype=np.int64)
        j = 5 * b + 4
        vel = self.vel
        H1, L1, C1, V1 = vel.A[1, :vel.n], vel.A[2, :vel.n], vel.A[3, :vel.n], vel.A[4, :vel.n]
        lc = self.lc()
        r2 = self.r2()
        sig = {W: np.sqrt(np.maximum(en(r2, W, j, "mean"), 1e-12)) for W in (15, 60, 240)}
        X = np.full((len(b), 19), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            for k, m in enumerate((1, 5, 15, 60)):
                ok = j - m >= 0
                X[ok, k] = (lc[j[ok]] - lc[j[ok] - m]) / (sig[60][ok] * math.sqrt(m))
            X[:, 4] = np.log(sig[15] / sig[240])
            hi, lo = en(H1, 240, j, "max"), en(L1, 240, j, "min")
            X[:, 5] = np.where(hi > lo, (C1[np.minimum(j, len(C1) - 1)] - lo) / np.maximum(hi - lo, 1e-9),
                               np.where(hi == hi, 0.5, np.nan))
            X[:, 6] = np.log((en(V1, 15, j, "sum") / 15 + 1e-9) / (en(V1, 240, j, "sum") / 240 + 1e-9))

            def k5(k):
                hh, ll = en(H1, 70, k, "max"), en(L1, 70, k, "min")
                cc = np.where(k >= 0, C1[np.clip(k, 0, len(C1) - 1)], np.nan)
                return np.where(hh > ll, (cc - ll) / (hh - ll), np.where(hh == hh, 0.5, np.nan))
            X[:, 7] = (k5(j) + k5(j - 5) + k5(j - 10)) / 3
            t = self.t0 + 60 * j
            hora = ((t + 60) % 86400) / 3600
            X[:, 8] = np.sin(2 * np.pi * hora / 24)
            X[:, 9] = np.cos(2 * np.pi * hora / 24)
            esc = sig[60] * math.sqrt(60)
            l5 = np.log(self.C5[b])
            for k, N in ((10, 20), (12, 50)):
                X[:, k] = (l5 - np.log(self.maximo_previo(N)[b])) / esc
                X[:, k + 1] = (l5 - np.log(self.minimo_previo(N)[b])) / esc
            m = self._base(("bm", 20), lambda: rodar(self.C5, 20, "mean"))[b]
            s = self._base(("bs", 20), lambda: rodar(self.C5, 20, "std"))[b]
            X[:, 14] = np.where(s > 0, (self.C5[b] - (m - 2 * s)) / (4 * s), np.where(s == s, 0.5, np.nan))
            X[:, 15] = self.rsi(5)[b] / 100
            X[:, 16] = self.rsi(15)[b] / 100
            rng = self.H5[b] - self.L5[b]
            X[:, 17] = np.where(rng > 0, (self.C5[b] - self.O5[b]) / rng, np.where(rng == rng, 0.0, np.nan))
            X[:, 18] = self.racha()[b] / 6
        valido = np.isfinite(X).all(axis=1)
        return X, valido

    def racha(self):
        def f():
            s = np.sign(self.C5 - self.O5)
            out = np.zeros(self.nb)
            cuenta, previo_s = 0, 0.0
            for i, x in enumerate(s.tolist()):
                if x != x:
                    cuenta, previo_s, out[i] = 0, 0.0, np.nan
                    continue
                cuenta = cuenta + 1 if (x == previo_s and x != 0) else (1 if x != 0 else 0)
                previo_s = x
                out[i] = x * min(cuenta, 6)
            return out
        return self._base("racha", f)

    def etiqueta(self, plazo, b=None):
        """1 si sube, 0 si baja, −1 si empata o falta dato, con entrada 60 s tarde (cierre del minuto que abre en T)."""
        b = np.arange(self.nb, dtype=np.int64) if b is None else np.asarray(b, dtype=np.int64)
        e, s = 5 * b + 5, 5 * b + 5 + plazo
        out = np.full(len(b), -1, dtype=np.int8)
        ok = s < len(self.C1)
        ce, cs = self.C1[e[ok]], self.C1[s[ok]]
        r = np.full(ok.sum(), -1, dtype=np.int8)
        with np.errstate(invalid="ignore"):
            r[cs > ce] = 1
            r[cs < ce] = 0
        out[ok] = r
        return out
