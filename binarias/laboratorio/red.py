"""Redes del laboratorio (11/11/2026), escritas a mano con numpy (referencia: esp32-neurona\\placa\\red.py).

- Red de mercado: perceptrón de 19 entradas, 16 y 8 neuronas con tanh y salida sigmoide; una por plazo. Aprende con
  2021-2023; desde enero de 2024 cada mes lo predice una red ajustada solo con apuestas cuya salida terminó antes del primer
  minuto del mes. Se normaliza con la media y la desviación de su propia ventana.
- Línea base: la neurona logística de t33 (sus diez rasgos), reajustada con la misma etiqueta de 60 s tarde y las mismas
  ventanas. Si la red no la supera en 0,3 puntos en «elige» (acierto con confianza de 0,56 o más), se usa la neurona.
- Red de búsqueda: recibe la ficha codificada (28 entradas) y predice su Wilson inferior menos el equilibrio en «elige».
Determinista: cada ajuste lleva su semilla."""
import datetime as dt
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import TRAMO, UTC  # noqa: E402

CONF = 0.56


class MLP:
    def __init__(self, capas, salida="sigmoide", semilla=0):
        rng = np.random.default_rng(semilla)
        self.capas, self.salida = list(capas), salida
        self.W = [rng.normal(0.0, math.sqrt(1.0 / capas[i]), (capas[i], capas[i + 1])) for i in range(len(capas) - 1)]
        self.b = [np.zeros(capas[i + 1]) for i in range(len(capas) - 1)]
        self.mu = np.zeros(capas[0])
        self.de = np.ones(capas[0])

    def _adelante(self, Z):
        acts, h = [Z], Z
        for W, b in zip(self.W[:-1], self.b[:-1]):
            with np.errstate(over="ignore"):  # numpy de ARM avisa «overflow» en tanh aunque el valor sale exacto (11/11)
                h = np.tanh(np.clip(h @ W + b, -40.0, 40.0))
            acts.append(h)
        z = (h @ self.W[-1] + self.b[-1])[:, 0]
        if self.salida == "sigmoide":
            z = 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))
        return acts, z

    def predecir(self, X):
        X = np.asarray(X, dtype=np.float64)
        out = np.empty(len(X))
        for a in range(0, len(X), 50000):
            out[a:a + 50000] = self._adelante((X[a:a + 50000] - self.mu) / self.de)[1]
        return out

    def ajustar(self, X, y, epocas, lote=2048, lr=1e-3, l2=1e-4, semilla=0, normalizar=True):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if normalizar:
            self.mu = X.mean(axis=0)
            self.de = X.std(axis=0) + 1e-9
        Z = (X - self.mu) / self.de
        rng = np.random.default_rng(semilla)
        mW = [np.zeros_like(w) for w in self.W]
        vW = [np.zeros_like(w) for w in self.W]
        mb = [np.zeros_like(b) for b in self.b]
        vb = [np.zeros_like(b) for b in self.b]
        b1, b2, paso = 0.9, 0.999, 0
        for _ in range(epocas):
            orden = rng.permutation(len(Z))
            for a in range(0, len(Z), lote):
                i = orden[a:a + lote]
                acts, out = self._adelante(Z[i])
                g = ((out - y[i]) / len(i) if self.salida == "sigmoide" else 2 * (out - y[i]) / len(i))[:, None]
                paso += 1
                for L in range(len(self.W) - 1, -1, -1):
                    gW = acts[L].T @ g + l2 * self.W[L]
                    gb = g.sum(axis=0)
                    if L > 0:
                        g = (g @ self.W[L].T) * (1 - acts[L] ** 2)
                    for P, G, M, Vv in ((self.W, gW, mW, vW), (self.b, gb, mb, vb)):
                        M[L] = b1 * M[L] + (1 - b1) * G
                        Vv[L] = b2 * Vv[L] + (1 - b2) * G * G
                        mh = M[L] / (1 - b1 ** paso)
                        vh = Vv[L] / (1 - b2 ** paso)
                        P[L] = P[L] - lr * mh / (np.sqrt(vh) + 1e-8)
        return self

    def a_dict(self):
        return {"capas": self.capas, "salida": self.salida, "W": [w.tolist() for w in self.W], "b": [b.tolist() for b in self.b],
                "mu": self.mu.tolist(), "de": self.de.tolist()}

    @staticmethod
    def desde_dict(d):
        m = MLP(d["capas"], d["salida"])
        m.W = [np.array(w) for w in d["W"]]
        m.b = [np.array(b) for b in d["b"]]
        m.mu, m.de = np.array(d["mu"]), np.array(d["de"])
        return m


class Neurona:
    """Regresión logística con Newton y penalización L2 (la misma de pruebas\\t33_indice.ajustar), sobre los diez rasgos de t33."""

    def __init__(self):
        self.w = None
        self.mu = None
        self.de = None

    def ajustar(self, X, y, iters=12, lam=1.0):
        X = np.asarray(X, dtype=np.float64)[:, :10]
        self.mu, self.de = X.mean(axis=0), X.std(axis=0) + 1e-9
        A = np.c_[np.ones(len(X)), (X - self.mu) / self.de]
        w = np.zeros(A.shape[1])
        for _ in range(iters):
            p = 1 / (1 + np.exp(-np.clip(A @ w, -40, 40)))
            g = A.T @ (p - y) + lam * np.r_[0, w[1:]]
            H = (A * (p * (1 - p))[:, None]).T @ A + lam * np.diag(np.r_[0, np.ones(A.shape[1] - 1)])
            w -= np.linalg.solve(H, g)
        self.w = w
        return self

    def predecir(self, X):
        Z = (np.asarray(X, dtype=np.float64)[:, :10] - self.mu) / self.de
        return 1 / (1 + np.exp(-np.clip(self.w[0] + Z @ self.w[1:], -40, 40)))

    def a_dict(self):
        return {"w": self.w.tolist(), "mu": self.mu.tolist(), "de": self.de.tolist()}

    @staticmethod
    def desde_dict(d):
        n = Neurona()
        n.w, n.mu, n.de = np.array(d["w"]), np.array(d["mu"]), np.array(d["de"])
        return n


def meses(desde, hasta):
    """Primeros segundos de cada mes desde `desde` hasta el mes que contiene `hasta`."""
    d = dt.datetime.fromtimestamp(desde, UTC).replace(day=1, hour=0, minute=0, second=0)
    out = []
    while d.timestamp() <= hasta:
        out.append(int(d.timestamp()))
        d = (d + dt.timedelta(days=32)).replace(day=1)
    return out


def acierto_confiado(p, y, m):
    """Acierto de la dirección con confianza de 0,56 o más: (n, acierto)."""
    s = m & (np.abs(p - 0.5) >= CONF - 0.5) & (y >= 0)
    n = int(s.sum())
    if not n:
        return 0, float("nan")
    return n, float(np.mean((p[s] > 0.5) == (y[s] == 1)))


def a_ciegas(X, valido, y, T, plazo, epocas0=10, epocas_mes=2, semilla=11, avisar=None):
    """Predicciones mensuales a ciegas desde enero de 2024 de la red y de la neurona. Devuelve (p_red, p_neurona, red, neurona,
    informe) donde red y neurona son los ajustes del último mes (los que sigue usando el vivo)."""
    T = np.asarray(T, dtype=np.int64)
    usar = valido & (y >= 0) & (T >= TRAMO["aprende"][0])
    p_red, p_neu = np.full(len(T), np.nan), np.full(len(T), np.nan)
    red = MLP([19, 16, 8, 1], "sigmoide", semilla)
    neu = Neurona()
    lista = meses(TRAMO["elige"][0], int(T[-1]))
    for k, M in enumerate(lista):
        fin = lista[k + 1] if k + 1 < len(lista) else int(T[-1]) + 1
        corte = M - 60 - 60 * plazo
        tr = usar & (T <= corte)
        red.ajustar(X[tr], y[tr].astype(np.float64), epocas0 if k == 0 else epocas_mes, semilla=semilla + k)
        neu.ajustar(X[tr], y[tr].astype(np.float64))
        m = valido & (T >= M) & (T < fin)
        if m.any():
            p_red[m] = red.predecir(X[m])
            p_neu[m] = neu.predecir(X[m])
        if avisar:
            avisar(f"plazo {plazo}: mes {dt.datetime.fromtimestamp(M, UTC):%Y-%m} listo ({int(tr.sum())} para ajustar)")
    a, b = TRAMO["elige"]
    me = (T >= a) & (T < b)
    nr, ar = acierto_confiado(p_red, y, me)
    nn, an = acierto_confiado(p_neu, y, me)
    usa = "red" if (ar == ar and an == an and ar >= an + 0.003) else "neurona"
    informe = {"plazo": plazo, "red": {"n": nr, "acierto": ar}, "neurona": {"n": nn, "acierto": an}, "usa": usa}
    return p_red, p_neu, red, neu, informe


def reajustar(X, valido, y, T, plazo, red, neu, corte, epocas=2, semilla=97):
    """Reajuste diario: sigue entrenando la red (y rehace la neurona) con todo lo que terminó antes de `corte`."""
    tr = valido & (y >= 0) & (np.asarray(T) >= TRAMO["aprende"][0]) & (np.asarray(T) <= corte - 60 - 60 * plazo)
    red.ajustar(X[tr], y[tr].astype(np.float64), epocas, semilla=semilla)
    neu.ajustar(X[tr], y[tr].astype(np.float64))
    return int(tr.sum())


def busqueda(Xf, objetivo, semilla=5):
    """Red de búsqueda: 28 entradas, 32 y 16 neuronas, salida lineal (puntos sobre el equilibrio / 10)."""
    m = MLP([len(Xf[0]), 32, 16, 1], "lineal", semilla)
    m.ajustar(np.asarray(Xf), np.asarray(objetivo) / 10.0, epocas=60, lote=256, lr=3e-3, l2=1e-4, semilla=semilla)
    return m


def guardar(ruta, datos):
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(datos, f)
    os.replace(ruta + ".tmp", ruta)
