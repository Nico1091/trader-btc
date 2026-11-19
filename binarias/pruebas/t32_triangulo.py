"""T32 (31/10/2026): su triángulo (máximos que bajan y mínimos que suben, con el precio dentro). PLAN.md, sección 18.
E1 rebote dentro (toca el techo → BAJA, el piso → SUBE). E2 ruptura (cierra fuera → a favor; también se informa al revés).
Velas de 1 min, entrada al abrir el minuto siguiente, 10 y 30 min, una abierta a la vez.
Uso: python -I t32_triangulo.py BTCUSDT|ETHUSDT GIRO"""
import datetime as dt
import math
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
GIRO = int(sys.argv[2]) if len(sys.argv) > 2 else 10
NPY = rf"C:\Users\ni109\Ingresos\trader-btc\datos\um\{SYM}_um_1m.npy"
CORTE = int(dt.datetime(2024, 1, 1, 5, tzinfo=dt.timezone.utc).timestamp())
EQ = 1 / 1.85


def wilson(w, n, z=1.959964):
    if n == 0:
        return 0.0
    p = w / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def recta(giros, val, n, sube):
    k = np.searchsorted(giros + GIRO, np.arange(n), side="right") - 1
    ok = k >= 1
    p2 = giros[np.clip(k, 0, len(giros) - 1)]
    p1 = giros[np.clip(k - 1, 0, len(giros) - 1)]
    v1, v2 = val[p1], val[p2]
    with np.errstate(invalid="ignore", divide="ignore"):
        lin = v2 + (v2 - v1) / np.maximum(p2 - p1, 1) * (np.arange(n) - p2)
    ok &= (v2 > v1) if sube else (v2 < v1)
    return np.where(ok, lin, np.nan)


def main():
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    n = len(c)
    w = 2 * GIRO + 1
    mx = np.full(n, np.nan)
    mn = np.full(n, np.nan)
    mx[GIRO:n - GIRO] = sliding_window_view(h, w).max(axis=1)
    mn[GIRO:n - GIRO] = sliding_window_view(l, w).min(axis=1)
    techo = recta(np.flatnonzero(h == mx), h, n, sube=False)
    piso = recta(np.flatnonzero(l == mn), l, n, sube=True)
    with np.errstate(invalid="ignore"):
        dentro = (c < techo) & (c > piso) & (techo > piso)
    d10 = np.r_[np.zeros(10, bool), sliding_window_view(dentro, 10).all(axis=1)[:-1]]  # las 10 velas anteriores dentro
    with np.errstate(invalid="ignore"):
        e1 = np.where(d10 & dentro & (h >= techo), -1, np.where(d10 & dentro & (l <= piso), 1, 0))
        e2 = np.where(d10 & (c > techo), 1, np.where(d10 & (c < piso), -1, 0))
    seguido = np.r_[True, np.diff(t) == 60]
    sano = sliding_window_view(np.r_[seguido, np.ones(80, bool)], 80).all(axis=1)[:n]
    out = [f"T32 · SU TRIÁNGULO · {SYM} · giro {GIRO} · 2021 a octubre de 2026 · regla de la sección 18"]
    veredictos = []
    for nombre, sen, natural in (("E1 rebote dentro", e1, 1), ("E2 ruptura", e2, 1)):
        idx = np.flatnonzero(sen != 0)
        for plazo in (10, 30):
            for sentido, cual in ((natural, "en su sentido"), (-natural, "al revés")):
                ocupado, res = -1, []
                for j in idx.tolist():
                    if j <= ocupado or j + plazo >= n or j < 200 or not sano[max(0, j - 79)]:
                        continue
                    if t[j + plazo] - t[j + 1] != (plazo - 1) * 60:
                        continue
                    d = sen[j] * sentido
                    res.append((int(t[j]) + 60, int(np.sign(d * (c[j + plazo] - o[j + 1])))))
                    ocupado = j + plazo
                todo = [r for _, r in res]
                nuevo = [r for ts, r in res if ts >= CORTE]
                N, W = len(todo), sum(r > 0 for r in todo)
                Nb, Wb = len(nuevo), sum(r > 0 for r in nuevo)
                pasa = Nb >= 300 and Wb / max(1, Nb) >= EQ and wilson(W, N) > EQ
                if sentido == natural and pasa:
                    veredictos.append(f"{nombre} a {plazo} min")
                dias = max(1, (int(t[-1]) - int(t[0])) / 86400)
                out.append(f"{nombre} · {plazo} min · {cual}: {es(N, 0)} apuestas, {es(100 * W / max(1, N))} % (Wilson {es(100 * wilson(W, N))} %) "
                           f"· 2024-26 {es(100 * Wb / max(1, Nb))} % en {es(Nb, 0)} · {es(N / dias, 2)} al día{' · CUMPLE' if pasa else ''}")
    out.append("VEREDICTO: " + ("entra: " + ", ".join(veredictos) if veredictos else "no entra"))
    open(os.path.join(AQUI, f"t32_{SYM}_giro{GIRO}.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
