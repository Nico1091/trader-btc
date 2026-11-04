"""T33 (31/10/2026): índice de estabilidad estilo red neuronal (una neurona logística) con variables medibles en vivo.
Aprende con 2021-2023 y se mide a ciegas con 2024-2026, a 10 min, en cada cierre de 5 min. Solo indicativo: no decide apuestas.
Variables (todas con velas de 1 min cerradas antes de la entrada): rendimientos de 1, 5, 15 y 60 min sobre la volatilidad de
60 min; log de la volatilidad 15/240; posición en el rango de 240 min; log del volumen 15/240; estocástico %K(14) de 5 min;
seno y coseno de la hora UTC. Salida: t33_indice.json (pesos para Pulso) y t33_indice.txt.
Uso: python -I t33_indice.py"""
import datetime as dt
import json
import math
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
NPY = r"C:\Users\ni109\Ingresos\trader-btc\datos\um\BTCUSDT_um_1m.npy"
NOMBRES = ["rend 1 min", "rend 5 min", "rend 15 min", "rend 60 min", "volatilidad 15/240", "posición en 4 h",
           "volumen 15/240", "estocástico 5 min", "hora (seno)", "hora (coseno)"]


def rasgos(t, o, h, l, c, v, j):
    """Rasgos en la vela j (la última cerrada). Misma fórmula que Pulso en Rust."""
    lc = np.log(c)
    r1 = np.r_[0.0, np.diff(lc)]
    sig = lambda a, b: np.sqrt(np.maximum(np.mean(r1[a:b] ** 2), 1e-12))
    s60 = np.array([sig(k - 59, k + 1) for k in j])
    s15 = np.array([sig(k - 14, k + 1) for k in j])
    s240 = np.array([sig(k - 239, k + 1) for k in j])
    ret = lambda m: (lc[j] - lc[j - m]) / (s60 * math.sqrt(m))
    hi = np.array([h[k - 239:k + 1].max() for k in j])
    lo = np.array([l[k - 239:k + 1].min() for k in j])
    pos = np.where(hi > lo, (c[j] - lo) / np.maximum(hi - lo, 1e-9), 0.5)
    vol = np.log((np.array([v[k - 14:k + 1].sum() for k in j]) / 15 + 1e-9) / (np.array([v[k - 239:k + 1].sum() for k in j]) / 240 + 1e-9))
    # estocástico %K(14) sobre velas de 5 min: máximo y mínimo de 70 min, suavizado con las 3 últimas velas de 5 min
    def k5(k):
        hh, ll = h[k - 69:k + 1].max(), l[k - 69:k + 1].min()
        return (c[k] - ll) / (hh - ll) if hh > ll else 0.5
    est = np.array([(k5(k) + k5(k - 5) + k5(k - 10)) / 3 for k in j])
    hora = ((t[j] + 60) % 86400) / 3600
    X = np.column_stack([ret(1), ret(5), ret(15), ret(60), np.log(s15 / s240), pos, vol, est,
                         np.sin(2 * np.pi * hora / 24), np.cos(2 * np.pi * hora / 24)])
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def ajustar(X, y, iters=12, lam=1.0):
    w = np.zeros(X.shape[1] + 1)
    A = np.c_[np.ones(len(X)), X]
    for _ in range(iters):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - y) + lam * np.r_[0, w[1:]]
        H = (A * (p * (1 - p))[:, None]).T @ A + lam * np.diag(np.r_[0, np.ones(X.shape[1])])
        w -= np.linalg.solve(H, g)
    return w


def main():
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c, v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    fin5 = np.flatnonzero(((t + 60) % 300 == 0) & (np.arange(len(t)) >= 300) & (np.arange(len(t)) + 11 < len(t)))
    sano = np.array([t[k + 10] - t[k - 239] == 249 * 60 for k in fin5])
    j = fin5[sano]
    X = rasgos(t, o, h, l, c, v, j)
    y = (c[j + 10] > o[j + 1]).astype(float)
    empate = c[j + 10] == o[j + 1]
    ts = t[j] + 60
    c1 = int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    c2 = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    ent = (ts >= c1) & (ts < c2) & ~empate
    pru = ts >= c2
    mu, de = X[ent].mean(axis=0), X[ent].std(axis=0) + 1e-9
    Z = (X - mu) / de
    w = ajustar(Z[ent], y[ent])
    p = 1 / (1 + np.exp(-np.c_[np.ones(len(Z)), Z] @ w))
    out = ["T33 · ÍNDICE DE ESTABILIDAD (una neurona logística) · BTCUSDT · aprende 2021-23, se mide a ciegas en 2024-26, 10 min"]
    gana = lambda m: (np.sign(p[m] - 0.5) == np.where(y[m] > 0, 1, -1)) & ~empate[m]
    for umbral in (0.50, 0.52, 0.54, 0.56):
        m = pru & (np.abs(p - 0.5) >= umbral - 0.5)
        n = int(m.sum())
        if n:
            out.append(f"2024-26 con confianza ≥ {umbral:.2f}: {n} señales, acierto {100 * gana(m).sum() / n:.1f} %, {n / ((ts[-1] - c2) / 86400):.2f} al día")
    out.append("Pesos (variable estandarizada → empuje hacia la subida): " + "; ".join(f"{n} {x:+.3f}" for n, x in zip(NOMBRES, w[1:])))
    json.dump({"nombres": NOMBRES, "mu": mu.tolist(), "de": de.tolist(), "w": w.tolist()},
              open(os.path.join(AQUI, "t33_indice.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(AQUI, "t33_indice.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
