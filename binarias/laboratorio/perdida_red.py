"""La red que propone comprar el lado perdedor al final de la ventana de 15 min (11/11/2026, pedido suyo).

En cada minuto cerrado de los últimos cinco (m = 10 a 14), estima la probabilidad de que el lado que va perdiendo frente a la
apertura gane al cierre. Propone comprarlo solo cuando el precio real está por debajo de 0,98 × esa probabilidad (comisión del
2 %): ahí la compra tiene ganancia esperada. Regla escrita antes de ver resultados: aprende con 2021-2023, se calibra y se
juzga a ciegas en «elige» (ene-2024 a jun-2025) y «juzga» (jul-2025 a oct-2026); el modelo es una regresión logística con
penalización (la neurona del laboratorio), suficiente y bien calibrada para probabilidades pequeñas.
Rasgos, todos con velas ya cerradas: lo atrasado (|z| y su cuadrado), minutos que faltan, salto de volatilidad (5 frente a 60
min), cuánto se devolvió en el último minuto y en los últimos tres hacia la apertura, rango de la ventana, cruces de la apertura,
volumen de los últimos 3 min frente a la hora y la hora del día. La misma función sirve en la historia y en vivo."""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import DATOS, TRAMOS  # noqa: E402

MINUTOS = (10, 11, 12, 13, 14)
NOMBRES = ["atraso |z|", "atraso al cuadrado", "minutos que faltan", "volatilidad 5/60", "devolución del último minuto",
           "devolución de 3 min", "rango de la ventana", "cruces de la apertura", "volumen 3/60", "hora (seno)", "hora (coseno)",
           "log del atraso"]
ARCHIVO = os.path.join(DATOS, "perdida_red.json")
COMISION = 0.02


def rasgos(C, H, L, V, s, m, ref, t_j):
    """Rasgos del minuto m (1 a 14) de la ventana que empieza en el índice s, con apertura ref. Devuelve (x, lado) o None.
    C, H, L, V: listas o arreglos de velas de 1 min (al menos 60 antes de s + m − 1); t_j: apertura (s) de la vela j."""
    j = s + m - 1
    if j < 61 or ref <= 0:
        return None
    r = [math.log(C[i] / C[i - 1]) for i in range(j - 59, j + 1)]
    sig = math.sqrt(max(sum(v * v for v in r) / 60, 1e-12))
    sig5 = math.sqrt(max(sum(v * v for v in r[-5:]) / 5, 1e-12))
    mov = math.log(C[j] / ref)
    if mov == 0:
        return None
    z = mov / (sig * math.sqrt(15 - m))
    lado = -1 if z > 0 else 1
    a = min(abs(z), 8.0)
    hi, lo = max(H[s:j + 1]), min(L[s:j + 1])
    cruces = 0
    for i in range(s, j):
        if (C[i] - ref) * (C[i + 1] - ref) < 0:
            cruces += 1
    v3 = (V[j] + V[j - 1] + V[j - 2]) / 3
    v60 = sum(V[j - 59:j + 1]) / 60
    hora = ((t_j + 60) % 86400) / 3600
    x = [a, a * a, (15 - m) / 5, sig5 / sig, (r[-1] * lado) / sig, math.log(C[j] / C[j - 3]) * lado / (sig * math.sqrt(3)),
         (hi - lo) / (ref * sig * math.sqrt(m)), cruces / 3, math.log((v3 + 1e-9) / (v60 + 1e-9)),
         math.sin(2 * math.pi * hora / 24), math.cos(2 * math.pi * hora / 24), math.log(a + 0.05)]
    return x, lado


def muestras(vel, desde, hasta):
    """Todas las miradas de los minutos 10 a 14 de las ventanas completas entre desde y hasta: X, y, ventana, minuto."""
    C, H, L, V, O = (vel.A[k, :vel.n].tolist() for k in (3, 1, 2, 4, 0))
    t0 = vel.t0
    a = max(0, -(-(int(desde) - t0) // 900) * 15)
    b = min(vel.n, (int(hasta) - t0) // 60)
    X, y, W, M = [], [], [], []
    for s in range(a, b - 14, 15):
        ref, fin = O[s], C[s + 14]
        if ref != ref or fin != fin or any(c != c for c in C[max(0, s - 61):s + 15]):
            continue
        for m in MINUTOS:
            r = rasgos(C, H, L, V, s, m, ref, t0 + 60 * (s + m - 1))
            if r is None:
                continue
            x, lado = r
            X.append(x)
            y.append(1 if (fin - ref) * lado > 0 else 0)
            W.append(t0 + 60 * s)
            M.append(m)
    return np.array(X), np.array(y, dtype=np.float64), np.array(W, dtype=np.int64), np.array(M, dtype=np.int64)


def ajustar(X, y, iters=25, lam=1.0):
    mu, de = X.mean(axis=0), X.std(axis=0) + 1e-9
    A = np.c_[np.ones(len(X)), (X - mu) / de]
    w = np.zeros(A.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(A @ w, -40, 40)))
        g = A.T @ (p - y) + lam * np.r_[0, w[1:]]
        Hs = (A * (p * (1 - p))[:, None]).T @ A + lam * np.diag(np.r_[0, np.ones(A.shape[1] - 1)])
        w -= np.linalg.solve(Hs, g)
    return {"w": w.tolist(), "mu": mu.tolist(), "de": de.tolist(), "nombres": NOMBRES}


def predecir(modelo, x):
    z = modelo["w"][0]
    for i, v in enumerate(x):
        z += modelo["w"][i + 1] * (v - modelo["mu"][i]) / modelo["de"][i]
    z = max(-40.0, min(40.0, z))
    return 1 / (1 + math.exp(-z))


def calibracion(p, y):
    """Por tramos de probabilidad predicha: n, frecuencia real y promedio predicho."""
    bordes = (0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 1.01)
    out = []
    for lo, hi in zip(bordes[:-1], bordes[1:]):
        m = (p >= lo) & (p < hi)
        n = int(m.sum())
        out.append({"desde": lo, "hasta": hi, "n": n, "real": float(y[m].mean()) if n else None,
                    "predicho": float(p[m].mean()) if n else None})
    return out


def entrenar(vel):
    tramo = {n: (a, b) for n, a, b in TRAMOS}
    Xa, ya, _w, _m = muestras(vel, *tramo["aprende"])
    modelo = ajustar(Xa, ya)
    informe = {"aprende": {"n": int(len(ya)), "base": float(ya.mean())}}
    for nombre in ("elige", "juzga"):
        X, y, _w, _m = muestras(vel, *tramo[nombre])
        p = np.array([predecir(modelo, x) for x in X])
        ll = float(-np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1))))
        informe[nombre] = {"n": int(len(y)), "base": float(y.mean()), "logloss": ll, "calibracion": calibracion(p, y)}
    modelo["informe"] = informe
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=1)
    return modelo


def cargar():
    try:
        return json.load(open(ARCHIVO, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def propuesta(modelo, p, precio=None):
    """Precio máximo con ganancia esperada y, si se conoce el precio real, si conviene comprar."""
    maximo = (1 - COMISION) * p
    return {"p": p, "precio_max": maximo, "compra": precio is not None and 0 < precio < maximo}
