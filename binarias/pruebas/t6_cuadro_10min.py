"""T6 (29/10/2026): cuadro de margen operativo de la señal del bot con el plazo que tiene Binance (10 min).

Señal: REV15 CTX en BTCUSDT (vela de 15 min con cuerpo ≥ 2 × la media de las 100 anteriores → apuesta en contra, solo a favor
del contexto diario). Vence a los 10 min de la entrada. Empate = se devuelve. Datos: velas de 1 min de futuros, 2020-2026.
Dos entradas: al cierre de la vela (lo que hace el bot, a pocos segundos) y un minuto tarde (lo que haría una persona lenta).
Libro de 150.000 COP; apuesta fija del 1, 2, 5 o 10 % del saldo; pago 0,80, 0,85 o 0,90 (la función libro() es la de T3).
Salidas: cuadro_10min.json y replay_10min.json (apuestas del último trimestre, entrada al cierre) para la pantalla.
Uso: python -I t6_cuadro_10min.py > t6_cuadro_10min.txt"""
import importlib.util
import json
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
T3 = r"C:\Users\ni109\Ingresos\trader-btc\.claude\worktrees\maestro-v2\investigacion\total\t3_binarias_libro.py"
_e = importlib.util.spec_from_file_location("t3", T3)
t3 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t3)
p = t3.p


def main():
    x = np.load(os.path.join(t3.DATOS, "BTCUSDT_um_1m.npy"), mmap_mode="r")
    t = (x[:, 0] // 1000).astype(np.int64)
    o1, c1 = np.asarray(x[:, 1]), np.asarray(x[:, 4])
    ctxd = t3.contexto_diario(t, c1)
    i0 = int(np.argmax(t % 900 == 0))
    n = (len(t) - i0) // 15 * 15
    T = t[i0:i0 + n].reshape(-1, 15)[:, 0]
    O = o1[i0:i0 + n].reshape(-1, 15)[:, 0]
    C = c1[i0:i0 + n].reshape(-1, 15)[:, -1]
    cu = np.abs(C - O)
    d = np.where(cu >= 2 * t3.media_previa(cu, 100), -np.sign(C - O), 0)
    ctx = np.array([ctxd.get(int(v) // 86400, 0.0) for v in T])
    d = np.where(d == ctx, d, 0)
    j = np.flatnonzero(d != 0)
    k = i0 + (j + 1) * 15
    ok = k + 11 < len(c1)
    j, k = j[ok], k[ok]
    dj, ts = d[j].astype(int), T[j] + 900
    entradas = {"al cierre": (o1[k], c1[k + 9]), "un minuto tarde": (c1[k], c1[k + 10])}
    p("T6 · REV15 CTX en BTCUSDT con el plazo de Binance (10 min) · libro de 150 mil COP · 2020-2026")
    p("ingresos = lo cobrado en aciertos · pérdidas = lo apostado en fallos · margen operativo = resultado / ingresos\n")
    cuadro = []
    for nombre, (pe, px) in entradas.items():
        res = np.sign(dj * (px - pe))
        g, l = (res > 0), (res < 0)
        a = ts < t3.CORTE
        p(f"== entrada {nombre}: acierto {g[a].sum() / (g[a].sum() + l[a].sum()) * 100:.2f} % (2020-23) · "
          f"{g[~a].sum() / (g[~a].sum() + l[~a].sum()) * 100:.2f} % (2024-26) · {len(res):,} apuestas ==")
        p(f"{'pago':>5s} {'apuesta':>8s} {'margen op.':>10s} {'%/día':>8s} {'caída máx':>9s} {'peor día':>9s}   2024-26: {'%/día':>8s} {'COP/día al empezar':>18s} {'caída':>6s}")
        for pago in (0.80, 0.85, 0.90):
            for apuesta in (0.01, 0.02, 0.05, 0.10):
                r = t3.libro(ts, res, apuesta, pago)
                rb = t3.libro(ts, res, apuesta, pago, desde=t3.CORTE)
                cuadro.append({"entrada": nombre, "pago": pago, "apuesta": apuesta, "todo": r, "B": rb})
                p(f"{pago:5.2f} {apuesta * 100:7.0f} % {r['margen']:+9.1f} % {r['crec_dia']:+7.3f} % {r['caida']:8.0f} % {r['peor_dia']:+8.1f} %"
                  f"   {rb['crec_dia']:+15.3f} % {150000 * rb['crec_dia'] / 100:+18,.0f} {rb['caida']:5.0f} %")
        p()
    with open(os.path.join(AQUI, "..", "cuadro_10min.json"), "w", encoding="utf-8") as f:
        json.dump(cuadro, f)
    pe, px = entradas["al cierre"]
    sel = ts >= ts.max() - 92 * 86400
    rep = [{"a": "BTC", "t": int(a), "d": int(b), "res": int(r), "pe": float(e), "px": float(s)}
           for a, b, r, e, s in zip(ts[sel], dj[sel], np.sign(dj * (px - pe))[sel], pe[sel], px[sel])]
    with open(os.path.join(AQUI, "..", "replay_10min.json"), "w", encoding="utf-8") as f:
        json.dump({"familia": "REV15 CTX", "preventiva": "CTX", "vencimiento_min": 10, "apuestas": rep}, f)


if __name__ == "__main__":
    main()
