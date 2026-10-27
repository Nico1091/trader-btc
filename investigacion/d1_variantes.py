"""D1/D2/D6: sensibilidad de parámetros, salidas alternativas y walk-forward (familias del PREREGISTRO.md, punto 3).

P05b (y P05c como caso k=1 solo largo con los 3 tiempos), N9, P11 y N8 se recalculan con el motor de la base
(consolidado.py importado sin cambios) y variantes de parámetros y de salida. La variante «actual» de cada familia debe
reproducir exactamente las operaciones de la base (se comprueba). Todas las variantes se guardan en registro_variantes.csv.
Particiones: entrenamiento 2020-2022, validación 2023, prueba 2024-2026. Comisión: futuros base y doble.
Uso: python3 -I d1_variantes.py RUTA.npy ETIQUETA"""
import os
import sys

RUTA, ETQ = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], RUTA, ETQ]
sys.path.insert(0, "/home/user/trader-btc-investigacion/consolidacion")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import consolidado as C  # noqa: E402
from sim import atr_diario  # noqa: E402

V, c15 = C.V, C.c15
M15 = pd.Timedelta(minutes=15)
_, ATR = atr_diario(C.m1)
C15T = c15.index.tz_localize(None).to_numpy()  # datetime64 sin zona (UTC) para searchsorted
C15C = c15.c.to_numpy()
FIN_DIA = pd.Timedelta(hours=23, minutes=59)
SALIDAS = ("actual", "sin stop", "stop duro", "4 h", "8 h")


def salidas(ie, lado, ref, d):
    """Precio y minuto de salida de cada variante, para una entrada en el minuto ie con referencia de stop ref."""
    ifin = V.i(d + FIN_DIA)
    out = {}
    # actual: primer cierre de 15 m (desde la vela del llenado) que vuelve a ref; si no, 23:59
    a = np.searchsorted(C15T, np.datetime64(V.t[ie].floor("15min").tz_localize(None)))
    b = np.searchsorted(C15T, np.datetime64((d + pd.Timedelta(hours=23, minutes=30)).tz_localize(None)), side="right")
    k = np.flatnonzero(lado * (C15C[a:b] - ref) <= 0)
    stop15 = (V.i(pd.Timestamp(C15T[a + k[0]], tz="UTC") + pd.Timedelta(minutes=14)), C15C[a + k[0]]) if len(k) else None
    out["actual"] = stop15 or (ifin, V.c[ifin])
    out["sin stop"] = (ifin, V.c[ifin])
    # stop duro: desde el minuto siguiente al llenado, el primer minuto que toca ref; si abre más allá, en la apertura
    seg = slice(ie + 1, ifin + 1)
    tq = np.flatnonzero(V.l[seg] <= ref) if lado > 0 else np.flatnonzero(V.h[seg] >= ref)
    if len(tq):
        j = ie + 1 + tq[0]
        px = min(V.o[j], ref) if lado > 0 else max(V.o[j], ref)
        out["stop duro"] = (j, px)
    else:
        out["stop duro"] = (ifin, V.c[ifin])
    for horas in (4, 8):
        j_t = min(ie + horas * 60, ifin)
        out[f"{horas} h"] = stop15 if (stop15 and stop15[0] <= j_t) else (j_t, V.c[j_t])
    return out


def banda(k, W, lados, solo_largo_ctx=False):
    """Operaciones de la familia P05b con banda k·ATR y límite de W minutos (todas las salidas)."""
    ops = []
    for d in C.pd.date_range(V.t[0].normalize() + pd.Timedelta(days=15), V.t[-1].normalize(), freq="D"):
        if d not in ATR.index or np.isnan(ATR.loc[d]):
            continue
        i0 = V.i(d)
        if i0 >= len(V.t) or V.t[i0] != d:
            continue
        ap, a = V.o[i0], ATR.loc[d]
        up, dn = ap + k * a, ap - k * a
        s = np.searchsorted(C15T, np.datetime64(d.tz_localize(None)))
        e = np.searchsorted(C15T, np.datetime64((d + pd.Timedelta(hours=23, minutes=30)).tz_localize(None)), side="right")
        if e - s < 90:
            continue
        cl = C15C[s:e]
        jj = np.flatnonzero((cl > up) | (cl < dn))
        if not len(jj):
            continue
        j = jj[0]
        lado = 1 if cl[j] > up else -1
        if lado not in lados:
            continue
        t_senal = pd.Timestamp(C15T[s + j], tz="UTC") + M15
        ctx = C.contexto(t_senal)
        if ctx == 0 or lado != ctx or (solo_largo_ctx and lado < 0):
            continue
        nivel = up if lado > 0 else dn
        a0 = V.i(t_senal)
        a1 = min(V.i(t_senal + pd.Timedelta(minutes=W)) - 1, len(V.t) - 1)
        seg = V.l[a0:a1 + 1] < nivel if lado > 0 else V.h[a0:a1 + 1] > nivel
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        ie = a0 + kk[0]
        if V.i(d + FIN_DIA) >= len(V.t):
            continue
        for nb, (ix, px) in salidas(ie, lado, ap, d).items():
            ops.append(dict(entrada=V.t[ie], salida=V.t[ix], senal=t_senal, lado=lado, pe=nivel, px=px, creador=True,
                            bruto=lado * (px / nivel - 1) * 100, salida_var=nb))
    return ops


def n9_var(desde_h, hasta_h):
    ops = []
    for d in pd.date_range(V.t[0].normalize() + pd.Timedelta(days=60), V.t[-1].normalize(), freq="D"):
        lado = C.contexto(d)
        if lado == 0:
            continue
        a = C.m1.loc[d: d + pd.Timedelta(hours=6, minutes=59)]
        if len(a) < 400:
            continue
        ah, al = a.h.max(), a.l.min()
        nv, medio = (ah if lado > 0 else al), (ah + al) / 2
        s = np.searchsorted(C15T, np.datetime64((d + pd.Timedelta(hours=desde_h)).tz_localize(None)))
        e = np.searchsorted(C15T, np.datetime64((d + pd.Timedelta(hours=hasta_h) - M15).tz_localize(None)), side="right")
        jj = np.flatnonzero(lado * (C15C[s:e] - nv) > 0)
        if not len(jj):
            continue
        ts = pd.Timestamp(C15T[s + jj[0]], tz="UTC") + M15
        a0, a1 = V.i(ts), min(V.i(ts + pd.Timedelta(minutes=60)) - 1, len(V.t) - 1)
        seg = V.l[a0:a1 + 1] < nv if lado > 0 else V.h[a0:a1 + 1] > nv
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        ie = a0 + kk[0]
        ifin = V.i(d + FIN_DIA)
        if ifin >= len(V.t) or V.t[ifin] != d + FIN_DIA:
            continue
        for nb, (ix, px) in salidas(ie, lado, medio, d).items():
            ops.append(dict(entrada=V.t[ie], salida=V.t[ix], senal=ts, lado=lado, pe=nv, px=px, creador=True,
                            bruto=lado * (px / nv - 1) * 100, salida_var=nb))
    return ops


def dia_largo(dia_sem, stop_pct):
    ops = []
    for o in C.p11(V, stop_pct=stop_pct if stop_pct else 1000.0, dias_semana=(dia_sem,)):
        if C.contexto(o["entrada"]) > 0:
            o["senal"] = o["entrada"]
            o["salida_var"] = f"stop {stop_pct} %" if stop_pct else "sin stop"
            ops.append(o)
    return ops


PART = {"entreno 2020-22": ("2020-01-01", "2023-01-01"), "valida 2023": ("2023-01-01", "2024-01-01"),
        "prueba 2024-26": ("2024-01-01", "2027-01-01")}


def resumir(t):
    t = t.sort_values("entrada")
    cm = np.where(t.creador.to_numpy(bool), 0.02, 0.05)
    t = t.assign(n1=t.bruto - cm - 0.05, n2=t.bruto - 2 * cm - 0.10)
    r = {}
    for p, (a, b) in PART.items():
        x = t[(t.entrada >= pd.Timestamp(a, tz="UTC")) & (t.entrada < pd.Timestamp(b, tz="UTC"))]
        eq = np.cumprod(1 + x.n1.to_numpy() / 100)
        dd = (1 - eq / np.maximum.accumulate(np.concatenate([[1], eq]))[1:]).max() * 100 if len(x) else np.nan
        r[f"{p}|ops"] = len(x)
        r[f"{p}|media2"] = x.n2.mean() if len(x) else np.nan
        r[f"{p}|suma1"] = x.n1.sum()
        r[f"{p}|caida"] = dd
    for y in range(2020, 2027):
        x = t[t.entrada.dt.year == y]
        r[f"año {y}|media2"] = x.n2.mean() if len(x) else np.nan
        r[f"año {y}|ops"] = len(x)
    return r


def main():
    filas = []
    # --- P05b: k x W x hora tope x salida
    for k in (0.3, 0.4, 0.5, 0.6, 0.7):
        for W in (30, 60, 120):
            t = pd.DataFrame(banda(k, W, (1, -1)))
            for hora in (19, 21, 23):
                h = t.senal.dt.hour + t.senal.dt.minute / 60
                th = t[h <= hora]
                for sv in SALIDAS:
                    x = th[th.salida_var == sv]
                    filas.append(dict(familia="P05b", k=k, W=W, hora=hora, salida=sv, **resumir(x)))
        print("P05b k", k, "listo", flush=True)
    # --- P05c: k x salida con los 3 tiempos mayores (solo largo con contexto); W=60, hora 21
    for k in (0.8, 1.0, 1.2):
        t = pd.DataFrame(banda(k, 60, (1,), solo_largo_ctx=True))
        t = t[(t.senal.dt.hour < 21) | ((t.senal.dt.hour == 21) & (t.senal.dt.minute == 0))]
        ok = np.array([C.CONF15["todos 3 de 3"](r.senal, r.lado) for r in t.itertuples()])
        t = t[ok]
        for sv in SALIDAS:
            filas.append(dict(familia="P05c", k=k, W=60, hora=21, salida=sv, **resumir(t[t.salida_var == sv])))
    print("P05c listo", flush=True)
    # --- N9: ventana x salida
    for (dh, hh) in ((7, 13), (7, 11), (7, 16)):
        t = pd.DataFrame(n9_var(dh, hh))
        for sv in SALIDAS:
            filas.append(dict(familia="N9", k=np.nan, W=60, hora=hh, salida=sv, **resumir(t[t.salida_var == sv])))
    print("N9 listo", flush=True)
    # --- P11 y N8: stop
    for fam, dsem in (("P11", 0), ("N8", 2)):
        for st in (2.0, 3.0, 5.0, None):
            t = pd.DataFrame(dia_largo(dsem, st))
            filas.append(dict(familia=fam, k=np.nan, W=np.nan, hora=np.nan, salida=f"stop {st} %" if st else "sin stop", **resumir(t)))
    print("P11/N8 listo", flush=True)

    R = pd.DataFrame(filas)
    R.insert(0, "activo", ETQ)
    R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variantes", f"registro_variantes_{ETQ}.csv"), index=False)
    print(f"{len(R)} variantes guardadas")


if __name__ == "__main__":
    main()
