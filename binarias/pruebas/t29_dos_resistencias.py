"""T29 (31/10/2026): su estrategia de las dos resistencias, con las líneas trazadas solas. PLAN.md, sección 15, escrita antes.

Velas de 1 min. Resistencia 1: mayor cierre entre 65 y 5 min antes. Resistencia 2: recta por los dos últimos máximos de giro
confirmados (5 velas a cada lado), si van bajando. SUBE cuando la vela cierra sobre las dos y la anterior no; BAJA al revés con
soportes y mínimos de giro que van subiendo. Entrada al abrir el minuto siguiente; plazos de 10 y 30 min; una abierta a la vez.
Salidas: t29_<SÍMBOLO>.txt y t29_<SÍMBOLO>_apuestas.csv. Uso: python -I t29_dos_resistencias.py BTCUSDT|ETHUSDT"""
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
NPY = rf"C:\Users\ni109\Ingresos\trader-btc\datos\um\{SYM}_um_1m.npy"
HCOL = 5 * 3600
GIRO = 5
CORTE = int(dt.datetime(2024, 1, 1, 5, tzinfo=dt.timezone.utc).timestamp())
EQUILIBRIO = 1 / 1.85


def wilson(w, n, z=1.959964):
    if n == 0:
        return 0.0
    p = w / n
    den = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def recta(giros, valores, n, sube):
    """Valor en cada vela de la recta por los dos últimos giros confirmados (a la vela i solo llegan los de i-GIRO o antes)."""
    conf = giros + GIRO
    k = np.searchsorted(conf, np.arange(n), side="right") - 1
    ok = k >= 1
    p2 = giros[np.clip(k, 0, len(giros) - 1)]
    p1 = giros[np.clip(k - 1, 0, len(giros) - 1)]
    v1, v2 = valores[p1], valores[p2]
    with np.errstate(invalid="ignore", divide="ignore"):
        pend = (v2 - v1) / np.maximum(p2 - p1, 1)
        linea = v2 + pend * (np.arange(n) - p2)
    ok &= (v2 > v1) if sube else (v2 < v1)
    return np.where(ok, linea, np.nan)


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
    g_alto = np.flatnonzero(h == mx)
    g_bajo = np.flatnonzero(l == mn)
    tl_baja = recta(g_alto, h, n, sube=False)   # máximos que van bajando: resistencia diagonal
    tl_sube = recta(g_bajo, l, n, sube=True)    # mínimos que van subiendo: soporte diagonal
    r_h = np.full(n, np.nan)
    s_h = np.full(n, np.nan)
    r_h[65:] = sliding_window_view(c, 60)[:n - 65].max(axis=1)
    s_h[65:] = sliding_window_view(c, 60)[:n - 65].min(axis=1)
    with np.errstate(invalid="ignore"):
        techo = np.fmax(r_h, tl_baja)
        piso = np.fmin(s_h, tl_sube)
        arriba = (c > r_h) & (c > tl_baja)
        abajo = (c < s_h) & (c < tl_sube)
    sube = arriba & ~np.r_[False, arriba[:-1]]
    baja = abajo & ~np.r_[False, abajo[:-1]]
    # Minutos contiguos: la recta y las ventanas asumen velas seguidas; se descartan señales junto a huecos de datos.
    seguido = np.r_[True, np.diff(t) == 60]
    ventana_ok = sliding_window_view(np.r_[seguido, np.ones(70, bool)], 70).all(axis=1)[:n]
    senal = np.where(sube, 1, np.where(baja, -1, 0))
    idx = np.flatnonzero(senal != 0)
    out = [f"T29 · SU ESTRATEGIA DE LAS DOS RESISTENCIAS · {SYM} · velas de 1 min de futuros, "
           f"{dt.datetime.fromtimestamp(int(t[0]) - HCOL, dt.timezone.utc):%d/%m/%Y} a {dt.datetime.fromtimestamp(int(t[-1]) - HCOL, dt.timezone.utc):%d/%m/%Y}",
           "Regla fijada antes (PLAN.md, sección 15): 2024-26 ≥ 54,1 % con ≥ 300 apuestas y Wilson 95 % de 2021-26 > 54,1 %, en el sentido que él usa.\n"]
    veredicto = False
    filas = []
    for plazo in (10, 30):
        for sentido, nombre in ((1, "a favor de la ruptura (como él)"), (-1, "contra la ruptura")):
            ocupado = -1
            res = []
            for j in idx.tolist():
                if j <= ocupado or j + plazo >= n or j < 2 * 65 or not ventana_ok[max(0, j - 69)]:
                    continue
                if t[j + plazo] - t[j + 1] != (plazo - 1) * 60:
                    continue
                d = senal[j] * sentido
                r = int(np.sign(d * (c[j + plazo] - o[j + 1])))
                res.append((int(t[j]) + 60, d, r))
                ocupado = j + plazo
            def medida(desde, hasta):
                x = [r for ts, _, r in res if desde <= ts < hasta]
                return len(x), sum(1 for r in x if r > 0)
            n_all, w_all = medida(0, 1 << 62)
            n_b, w_b = medida(CORTE, 1 << 62)
            n_a, w_a = medida(0, CORTE)
            dias = max(1, (int(t[-1]) - int(t[0])) / 86400)
            pasa = n_b >= 300 and w_b / max(1, n_b) >= EQUILIBRIO and wilson(w_all, n_all) > EQUILIBRIO
            if sentido == 1 and pasa:
                veredicto = True
            out.append(f"{plazo} min · {nombre}: 2021-26 {es(n_all, 0)} apuestas, {es(100 * w_all / max(1, n_all))} % "
                       f"(Wilson {es(100 * wilson(w_all, n_all))} %) · 2021-23 {es(100 * w_a / max(1, n_a))} % · "
                       f"2024-26 {es(100 * w_b / max(1, n_b))} % en {es(n_b, 0)} · {es(n_all / dias, 2)} al día"
                       f"{' · CUMPLE' if pasa else ''}")
            if plazo == 10 and sentido == 1:
                filas = res
    out.append(f"\nVEREDICTO: {'entra al banco' if veredicto else 'no entra al banco'} (solo cuenta el sentido que él usa)")
    with open(os.path.join(AQUI, f"t29_{SYM}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(AQUI, f"t29_{SYM}_apuestas.csv"), "w", encoding="utf-8-sig") as f:
        f.write("fecha_hora_colombia;sentido;plazo_min;resultado\n")
        for ts, d, r in filas:
            fe = dt.datetime.fromtimestamp(ts - HCOL, dt.timezone.utc)
            f.write(f"{fe:%Y-%m-%d %H:%M};{'SUBE' if d > 0 else 'BAJA'};10;{'acierta' if r > 0 else 'empate' if r == 0 else 'falla'}\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
