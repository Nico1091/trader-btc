"""A5 (28/10/2026): qué pasó en el historial después de cada clase de vela, en cada marco (la «base medida» del lector).

Para BTC (futuros de Binance, 1 m de 2020 a 2026) se arma cada marco (1 m, 5 m, 15 m, 1 h, 4 h, 1 d), se clasifica cada vela
con consolidacion/clases_vela.py (la misma definición que usa el lector en vivo) y se mide el movimiento de las 4 velas
siguientes de ese marco: cuántas veces sube y cuánto, en total y por tramo (2020-2023 / 2024-2026).
Salida: consolidacion/base_velas.json (lo lee lector_velas.py) y este resumen.
Uso: python -I a5_base_velas.py RUTA_BTCUSDT_um_1m.npy > a5_base_velas.txt"""
import json
import os
import random
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "consolidacion"))
import clases_vela as CV  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MARCOS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
CORTE = 1704067200  # 2024-01-01
ADELANTE = 4


def agregar(t, o, h, l, c, v, seg):
    g = t - t % seg
    cortes = np.flatnonzero(np.diff(g)) + 1
    i0 = np.concatenate([[0], cortes])
    i1 = np.concatenate([cortes, [len(t)]])
    return (g[i0], o[i0], np.maximum.reduceat(h, i0), np.minimum.reduceat(l, i0), c[i1 - 1], np.add.reduceat(v, i0))


def main():
    a = np.load(sys.argv[1])
    t = (a[:, 0] // 1000).astype("int64") if a[0, 0] > 1e11 else a[:, 0].astype("int64")
    o, h, l, c, v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    salida = {"fuente": "Binance futuros BTCUSDT 1 m", "adelante": ADELANTE, "marcos": {}}
    print(f"A5 · base medida por clase de vela (BTC, {len(t):,} velas de 1 m). «Sube» = el cierre {ADELANTE} velas después es mayor.")
    for marco, seg in MARCOS.items():
        T, O, H, L, C, V = agregar(t, o, h, l, c, v, seg)
        O, H, L, C, V = (x.tolist() for x in (O, H, L, C, V))
        clases = CV.clasificar_serie(O, H, L, C, V)
        # comprobación: la serie rápida da lo mismo que la definición vela a vela en 200 velas al azar
        for i in random.Random(5).sample(range(40, len(C)), 200):
            atr, vol = CV.referencias(O, H, L, C, V, i)
            assert clases[i] == CV.clase(CV.medidas(O[i], H[i], L[i], C[i], V[i], atr, vol)), (marco, i)
        fut = [(C[i + ADELANTE] / C[i] - 1) * 100 if i + ADELANTE < len(C) else None for i in range(len(C))]
        base_sube = np.mean([x > 0 for x in fut if x is not None])
        filas = {}
        for k, _ in CV.CLASES:
            idx = [i for i in range(40, len(C)) if clases[i] == k and fut[i] is not None]
            if not idx:
                continue
            f = np.array([fut[i] for i in idx])
            ta = np.array([T[i] < CORTE for i in idx])
            filas[k] = {"n": len(idx), "sube": round(float((f > 0).mean()), 4), "media": round(float(f.mean()), 4),
                        "n_a": int(ta.sum()), "sube_a": round(float((f[ta] > 0).mean()), 4) if ta.any() else None,
                        "n_b": int((~ta).sum()), "sube_b": round(float((f[~ta] > 0).mean()), 4) if (~ta).any() else None}
        salida["marcos"][marco] = {"base_sube": round(float(base_sube), 4), "clases": filas}
        print(f"\n== {marco}: {len(C):,} velas · base: sube el {base_sube * 100:.1f} % ==")
        for k, d in sorted(filas.items(), key=lambda kv: -kv[1]["sube"]):
            print(f"   {CV.TEXTO[k]:46s} n={d['n']:8,d}  sube {d['sube'] * 100:5.1f} %  media {d['media']:+.3f} %"
                  f"  [2020-23 {d['sube_a'] * 100 if d['sube_a'] is not None else float('nan'):4.1f} · 2024-26 {d['sube_b'] * 100 if d['sube_b'] is not None else float('nan'):4.1f}]")
    ruta = os.path.join(AQUI, "..", "..", "consolidacion", "base_velas.json")
    json.dump(salida, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nGuardado: consolidacion/base_velas.json")


if __name__ == "__main__":
    main()
