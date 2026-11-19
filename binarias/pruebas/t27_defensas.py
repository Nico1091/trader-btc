"""T27 (31/10/2026): defensas sin stop sobre la secuencia a ciegas de la t18. PLAN.md, sección 13, escrita antes de correrla.

D1 volumen de la última hora frente a la mediana de 7 días (bajo < 70 %, alto > 130 %); D2 solo las 2 primeras horas de cada
bloque de 3 h; D3 sin apostar tras un movimiento de 3 h mayor que el percentil 90 de los 30 días anteriores.
La variante de D1 se elige con 2021-23 y todas se juzgan con 2024-26.
Salidas: t27_<SÍMBOLO>.txt y t27_<SÍMBOLO>.json. Uso: python -I t27_defensas.py BTCUSDT|ETHUSDT [archivo de velas]"""
import datetime as dt
import importlib.util
import json
import os
import sys
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("t18", os.path.join(AQUI, "t18_reglas_a_ciegas.py"))
t18 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t18)
SEN, SEL, es, HCOL, SYM, NPY = t18.SEN, t18.SEL, t18.es, t18.HCOL, t18.SYM, t18.NPY
CORTE = int(dt.datetime(2024, 1, 1, 5, tzinfo=dt.timezone.utc).timestamp())


def medir(tom, desde, hasta):
    sub = [e for e in tom if desde <= e[0] < hasta]
    n = len(sub)
    w = sum(1 for e in sub if e[4] > 0)
    s = t18.arranques(sub, 0.85)
    return {"apuestas": n, "acierto": w / n if n else 0.0, "arriba_30d": sum(1 for x in s if x > 100000) / len(s) if s else 0.0,
            "por_dia": n / max(1, (hasta - desde) / 86400)}


def main():
    t0 = time.time()
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c, v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    if SYM == "BTCUSDT":
        S.update(t18.grupo_B(int(t[-1])))
    P = SEL.preparar(S, T5, vol5, ctxd, t, o, c)
    tom, _ = t18.a_ciegas(P, t18.sumar(2020, 1, 12), int(t[-1]), 12, 3)
    print(f"{SYM}: {len(tom)} apuestas a ciegas · {time.time() - t0:.0f} s", file=sys.stderr)

    V = np.r_[0.0, np.cumsum(v)]

    def vol_entre(x0, x1):
        return V[np.searchsorted(t, x1)] - V[np.searchsorted(t, x0)]

    def precio(x):
        return c[np.clip(np.searchsorted(t, x - 60, side="right") - 1, 0, len(c) - 1)]

    g0 = (int(t[0]) // 3600 + 1) * 3600
    G = np.arange(g0, int(t[-1]), 3600, dtype=np.int64)
    vh = vol_entre(G - 3600, G)
    med = np.full(len(G), np.nan)
    med[168:] = np.median(sliding_window_view(vh, 168)[:-1], axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m3 = np.abs(np.log(precio(G) / precio(G - 10800)))
    p90 = np.full(len(G), np.nan)
    p90[720:] = np.percentile(sliding_window_view(m3, 720)[:-1], 90, axis=1)

    ts = np.array([e[0] for e in tom], dtype=np.int64)
    k = np.clip((ts - g0) // 3600, 0, len(G) - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        razon = vol_entre(ts - 3600, ts) / med[k]
        mov = np.abs(np.log(precio(ts) / precio(ts - 10800)))
    D = {"D1 sin volumen bajo": ~(razon < 0.7),
         "D1 sin volumen alto": ~(razon > 1.3),
         "D2 solo 2 primeras horas del bloque de 3 h": (ts % 10800) < 7200,
         "D3 sin movimiento de 3 h extremo": ~(mov > p90[k])}
    fin = int(t[-1])
    inicio = tom[0][0]
    base_a, base_b = medir(tom, inicio, CORTE), medir(tom, CORTE, fin)
    filas, res = [], {}
    for nom, m in D.items():
        sub = [e for e, ok in zip(tom, m.tolist()) if ok]
        res[nom] = (medir(sub, inicio, CORTE), medir(sub, CORTE, fin))
    d1 = max(("D1 sin volumen bajo", "D1 sin volumen alto"), key=lambda x: res[x][0]["acierto"])
    juzgar = [d1, "D2 solo 2 primeras horas del bloque de 3 h", "D3 sin movimiento de 3 h extremo"]
    veredicto = {}
    for nom in juzgar:
        b = res[nom][1]
        cond = [b["acierto"] >= base_b["acierto"] + 0.005, b["arriba_30d"] >= base_b["arriba_30d"], b["por_dia"] >= 4]
        veredicto[nom] = cond
    with open(os.path.join(AQUI, f"t27_{SYM}.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T27 · DEFENSAS SIN STOP · {SYM} · secuencia a ciegas de la t18 (12 meses, 3 elegidas), pago 0,85, 30 días al 16 %")
        p("Regla fijada antes (PLAN.md, sección 13): en 2024-26, +0,5 puntos de acierto, no menos arranques arriba y ≥ 4 al día.\n")
        lin = lambda nom, m: (f"{nom}: {es(m['apuestas'], 0)} apuestas · {es(100 * m['acierto'])} % · 30 días arriba "
                              f"{es(100 * m['arriba_30d'])} % · {es(m['por_dia'], 2)} al día")
        p("== 2021-23 (elección) ==")
        p(lin("Sin defensa", base_a))
        for nom in D:
            p(lin(nom, res[nom][0]))
        p(f"Variante de D1 elegida con 2021-23: {d1}\n")
        p("== 2024-26 (juicio) ==")
        p(lin("Sin defensa", base_b))
        for nom in D:
            p(lin(nom, res[nom][1]) + ("" if nom in juzgar else " · (no elegida, solo informativa)"))
        p("")
        for nom, cond in veredicto.items():
            p(f"{'ENTRA' if all(cond) else 'no entra'} · {nom} · acierto {'sí' if cond[0] else 'no'} · arranques {'sí' if cond[1] else 'no'} · "
              f"frecuencia {'sí' if cond[2] else 'no'}")
    json.dump({"simbolo": SYM, "base": [base_a, base_b], "defensas": res, "d1_elegida": d1,
               "veredicto": {k: all(x) for k, x in veredicto.items()}},
              open(os.path.join(AQUI, f"t27_{SYM}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"listo · {time.time() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
