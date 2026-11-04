"""T20 (29/10/2026): robustez de lo que salió de T18. PLAN.md v2, sección 4 (P4), y PROMPT-REVISION.md, puntos 1, 3 y 6.

a) «Rompimiento de 20 velas al revés a 10 min» escrito de nuevo, sin motor/ ni t7, sobre futuros (2020-2026): si da lo mismo que
   el banco, el resultado no viene de un error del banco.
b) Lo mismo sobre CONTADO de 1 min (2023-2026): si el efecto solo existiera en futuros, Binance podría liquidar con otro precio.
c) Las apuestas a ciegas de T18 (BTC) medidas con precio de contado: en cuántas coincide el resultado con el de futuros.
d) Retraso real: las apuestas de T18 de mayo a octubre de 2026 y la regla cruda, con velas de 1 s de contado, entrando 0, 5, 10,
   20, 30 y 60 s después del cierre de la vela.
Uso: python -I t20_robustez.py"""
import ctypes
import datetime as dt
import json
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
AQUI = os.path.dirname(os.path.abspath(__file__))
UM = r"C:\Users\ni109\Ingresos\trader-btc\datos\um\BTCUSDT_um_1m.npy"
CACHE = r"C:\Users\ni109\Ingresos\trader-btc\datos\cache"
UTC = dt.timezone.utc
RETRASOS = (0, 5, 10, 20, 30, 60)


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def cache(nombre):
    meta = json.load(open(os.path.join(CACHE, f"{nombre}.json"), encoding="utf-8"))
    out = {}
    for campo in ("t", "o", "h", "l", "c"):
        x = np.fromfile(os.path.join(CACHE, f"{nombre}.{campo}.bin"), dtype=np.int64 if campo == "t" else np.float64)
        out[campo] = x
    t = out["t"]
    if t[0] > 10 ** 11:  # milisegundos
        t = t // 1000
    if not (1.6e9 < t[0] < 1.9e9):  # no era entero: era flotante
        t = np.fromfile(os.path.join(CACHE, f"{nombre}.t.bin"), dtype=np.float64).astype(np.int64)
        t = t // 1000 if t[0] > 10 ** 11 else t
    out["t"] = t
    assert len(t) == meta["n"], (nombre, len(t), meta["n"])
    return out


def rejilla(t, o, c, paso):
    """Arreglos indexados por tiempo exacto (paso de 60 o 1 s), con NaN donde falte la vela."""
    t0 = int(t[0])
    n = int((t[-1] - t0) // paso + 1)
    O, C = np.full(n, np.nan), np.full(n, np.nan)
    i = (t - t0) // paso
    O[i], C[i] = o, c
    return t0, O, C


def rompimientos(t, o, h, l, c):
    """Vela de 5 min alineada a UTC que cierra sobre el máximo de las 20 anteriores (o bajo el mínimo), primera de la racha."""
    i0 = int(np.argmax(t % 300 == 0))
    n = (len(t) - i0) // 5 * 5
    T = t[i0:i0 + n].reshape(-1, 5)[:, 0]
    ok5 = (t[i0:i0 + n].reshape(-1, 5)[:, -1] - T) == 240
    H = h[i0:i0 + n].reshape(-1, 5).max(1)
    L = l[i0:i0 + n].reshape(-1, 5).min(1)
    C = c[i0:i0 + n].reshape(-1, 5)[:, -1]
    hi = np.full(len(C), np.nan)
    lo = np.full(len(C), np.nan)
    from numpy.lib.stride_tricks import sliding_window_view as sw
    hi[20:] = sw(H[:-1], 20).max(1)
    lo[20:] = sw(L[:-1], 20).min(1)
    with np.errstate(invalid="ignore"):
        up = C > hi
        dn = C < lo
    up &= ~np.r_[False, up[:-1]]
    dn &= ~np.r_[False, dn[:-1]]
    up &= ok5
    dn &= ok5
    ts = np.r_[T[up], T[dn]] + 300
    d = np.r_[-np.ones(up.sum()), np.ones(dn.sum())]  # al revés: tras romper arriba se apuesta abajo
    orden = np.argsort(ts)
    return ts[orden], d[orden]


def medir(ts, d, t0, O, C, paso, pl_s, retraso=0):
    """Resultado de cada apuesta entrando `retraso` s después de ts y venciendo `pl_s` s después de la entrada (empate = fallo)."""
    ie = (ts + retraso - t0) // paso
    ix = (ts + retraso + pl_s - t0) // paso - 1
    ok = (ie >= 0) & (ix < len(C))
    ie, ix, d = ie[ok], ix[ok], d[ok]
    pe, px = O[ie], C[ix]
    bien = ~(np.isnan(pe) | np.isnan(px))
    r = np.sign(d[bien] * (px[bien] - pe[bien]))
    return r, ts[ok][bien]


def linea(r, nombre):
    n = len(r)
    w = int((r > 0).sum())
    return f"{nombre}: {es(n, 0)} apuestas, {es(100 * w / n) if n else '-'} % de acierto"


def sin_solapes(ts, pl_s):
    keep, ocupado = [], 0
    for i, x in enumerate(ts.tolist()):
        if x >= ocupado:
            keep.append(i)
            ocupado = x + pl_s
    return np.array(keep, dtype=np.int64)


def main():
    out = []
    p = lambda s="": (out.append(s), print(s, flush=True))
    p("T20 · ROBUSTEZ · empate = fallo · para no perder con pago 0,85 hace falta 54,1 %\n")
    a = np.load(UM)
    tf = (a[:, 0] // 1000).astype(np.int64)
    of, hf, lf, cf = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    t0f, Of, Cf = rejilla(tf, of, cf, 60)
    ts, d = rompimientos(tf, of, hf, lf, cf)
    k = sin_solapes(ts, 600)
    p("== a) Rompimiento de 20 velas al revés, 10 min, escrito de nuevo, FUTUROS, sin filtros y sin solapes ==")
    r, tr = medir(ts[k], d[k], t0f, Of, Cf, 60, 600)
    años = np.array([dt.datetime.fromtimestamp(int(x), UTC).year for x in tr])
    for y in range(2020, 2027):
        p(linea(r[años == y], f"   {y}"))
    p(linea(r, "   Todo") + f" · {es(len(r) / ((tr[-1] - tr[0]) / 86400), 1)} al día")
    p(linea(medir(ts[k], d[k], t0f, Of, Cf, 60, 600, 60)[0], "   Todo, entrando 60 s tarde"))

    s1 = cache("contado-1m")
    t0s, Os, Cs = rejilla(s1["t"], s1["o"], s1["c"], 60)
    tss, dss = rompimientos(s1["t"], s1["o"], s1["h"], s1["l"], s1["c"])
    ks = sin_solapes(tss, 600)
    p("\n== b) La misma regla sobre CONTADO de 1 min (2023-2026) ==")
    r, tr = medir(tss[ks], dss[ks], t0s, Os, Cs, 60, 600)
    años = np.array([dt.datetime.fromtimestamp(int(x), UTC).year for x in tr])
    for y in range(2023, 2027):
        p(linea(r[años == y], f"   {y}"))
    p(linea(r, "   Todo"))
    rf, _ = medir(tss[ks], dss[ks], t0f, Of, Cf, 60, 600)
    p(linea(rf, "   Mismas horas medidas con futuros"))

    p("\n== c) Apuestas a ciegas de T18 (BTC) medidas con contado, 2023 a 19/10/2026 ==")
    filas = []
    for ln in open(os.path.join(AQUI, "t18_BTCUSDT_apuestas.csv"), encoding="utf-8-sig").read().splitlines()[1:]:
        x = ln.split(";")
        f = dt.datetime.strptime(x[0], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        filas.append((int(f.timestamp()) + 5 * 3600, 1 if x[3] == "SUBE" else -1, int(x[4]), x[5]))
    T18 = np.array([f[0] for f in filas], dtype=np.int64)
    D18 = np.array([f[1] for f in filas], dtype=float)
    P18 = np.array([f[2] for f in filas], dtype=np.int64)
    R18 = np.array([1 if f[3] == "acierta" else -1 for f in filas])
    sel = (T18 >= s1["t"][0]) & (T18 + 3700 < s1["t"][-1])
    acuerdo, n_c, w_s, w_f = 0, 0, 0, 0
    for pl in (10, 30, 60):
        m = sel & (P18 == pl)
        rs, _ = medir(T18[m], D18[m], t0s, Os, Cs, 60, pl * 60)
        rfu, _ = medir(T18[m], D18[m], t0f, Of, Cf, 60, pl * 60)
        nn = min(len(rs), len(rfu))
        if nn:
            acuerdo += int((np.sign(rs[:nn]) == np.sign(rfu[:nn])).sum())
            n_c += nn
            w_s += int((rs > 0).sum())
            w_f += int((rfu > 0).sum())
            p(f"   {pl} min: {es(nn, 0)} apuestas · acierto con futuros {es(100 * (rfu > 0).mean())} % · con contado {es(100 * (rs > 0).mean())} %")
    if n_c:
        p(f"   Mismo resultado con los dos precios en {es(100 * acuerdo / n_c)} % de {es(n_c, 0)} apuestas")

    p("\n== d) Retraso real con velas de 1 s de CONTADO (01/05 a 19/10/2026) ==")
    s = cache("contado-1s-BTCUSDT")
    t01, O1, C1 = rejilla(s["t"], s["o"], s["c"], 1)
    m = (T18 >= s["t"][0]) & (T18 + 3700 < s["t"][-1])
    p(f"   Apuestas a ciegas de T18 en ese periodo: {int(m.sum())}")
    for rt in RETRASOS:
        rr = np.concatenate([medir(T18[m & (P18 == pl)], D18[m & (P18 == pl)], t01, O1, C1, 1, pl * 60, rt)[0] for pl in (10, 30, 60)])
        p(linea(rr, f"      entrando {rt:2d} s tarde"))
    mm = (tss >= s["t"][0]) & (tss + 700 < s["t"][-1])
    k1 = sin_solapes(tss[mm], 600)
    p(f"   Regla cruda (rompimiento al revés, 10 min) en ese periodo: {len(k1)} apuestas")
    for rt in RETRASOS:
        rr, _ = medir(tss[mm][k1], dss[mm][k1], t01, O1, C1, 1, 600, rt)
        p(linea(rr, f"      entrando {rt:2d} s tarde"))
    open(os.path.join(AQUI, "t20_robustez.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
