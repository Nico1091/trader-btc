"""T26 (31/10/2026): su contexto de 3 h, 5 h y 90 días, y las estrategias de binarias más difundidas (MHI, flips, torres
gemelas, BNF), a ciegas con la elección de la t18. PLAN.md, sección 12; la regla de decisión se escribió antes de correrla.

Se corre la elección mensual (12 meses, 3 elegidas) con el banco actual y con el banco ampliado por el grupo N, sobre las
mismas velas, y se aplican las cuatro condiciones de la sección 12.
Salidas: t26_<SÍMBOLO>.txt y t26_<SÍMBOLO>.json.
Uso: python -I t26_contexto_y_difundidas.py BTCUSDT|ETHUSDT [archivo de velas]"""
import importlib.util
import json
import os
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("t18", os.path.join(AQUI, "t18_reglas_a_ciegas.py"))
t18 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t18)

SEN, SEL, es, sumar, mes_ini, HCOL = t18.SEN, t18.SEL, t18.es, t18.sumar, t18.mes_ini, t18.HCOL
SYM, NPY = t18.SYM, t18.NPY
BLOQUE = 3 * 3600


def bloques(t, x, seg_vela, n):
    """Agrupa una serie de velas de `seg_vela` s en bloques de n velas alineados a UTC. Devuelve (inicio de bloque, matriz)."""
    i0 = int(np.argmax(t % (seg_vela * n) == 0))
    nb = (len(t) - i0) // n
    return t[i0:i0 + nb * n:n], x[i0:i0 + nb * n].reshape(nb, n)


def mhi(tb, colores, seg_bloque):
    """Mayoría de las velas 3, 4 y 5 del bloque; la señal es la minoría y entra al cerrar el bloque."""
    s = np.sign(colores[:, 2:5].sum(axis=1))
    f = s != 0
    return tb[f] + seg_bloque, -s[f]


def contexto_3h(t, c, ts):
    """Signo común de los rendimientos de 3 h, 5 h y 90 días, fijado al empezar el bloque de 3 h de cada señal; 0 si no coinciden."""
    b3 = (ts // BLOQUE) * BLOQUE

    def precio(x):
        j = np.searchsorted(t, x - 60, side="right") - 1
        out = c[np.clip(j, 0, len(c) - 1)].astype(float)
        out[j < 0] = np.nan
        return out

    p0 = precio(b3)
    with np.errstate(invalid="ignore"):
        r = [np.sign(p0 / precio(b3 - s) - 1) for s in (3 * 3600, 5 * 3600, 90 * 86400)]
    igual = (r[0] == r[1]) & (r[1] == r[2]) & (r[0] != 0)
    return np.where(igual, r[0], 0.0)


def grupo_N(t, o, h, l, c, S):
    N = {}
    col1 = np.sign(c - o)
    tb, cols = bloques(t, col1, 60, 5)
    N["MHI 1 min"] = mhi(tb, cols, 300)
    T5, O5, H5, L5, C5 = SEN.velas(t, o, h, l, c, 300)
    col5 = np.sign(C5 - O5)
    tb5, cols5 = bloques(T5, col5, 300, 5)
    N["MHI 5 min"] = mhi(tb5, cols5, 1500)
    racha = np.ones(len(col5), dtype=np.int64)
    for i in range(1, len(col5)):
        if col5[i] != 0 and col5[i] == col5[i - 1]:
            racha[i] = racha[i - 1] + 1
    racha[col5 == 0] = 0
    for n, nom in ((5, "five flip"), (7, "seven flip")):
        f = racha == n
        N[nom] = (T5[f] + 300, -col5[f])
    cu = np.abs(C5 - O5)
    with np.errstate(invalid="ignore", divide="ignore"):
        med = SEN.media_previa(cu, 20)
        prev = np.r_[np.nan, cu[:-1]]
        pcol = np.r_[0.0, col5[:-1]]
        f = (col5 != 0) & (pcol == -col5) & (cu > med) & (prev > med) & (np.abs(cu - prev) < 0.1 * np.maximum(cu, prev))
    N["torres gemelas"] = (T5[f] + 300, col5[f])
    m300 = SEN.sma(C5, 300)
    with np.errstate(invalid="ignore", divide="ignore"):
        dv = C5 / m300 - 1
        x = np.nan_to_num(dv)
        cs, cs2 = np.r_[0.0, np.cumsum(x)], np.r_[0.0, np.cumsum(x * x)]
        w = 2016
        sd = np.full(len(x), np.nan)
        mu = (cs[w:-1] - cs[:-w - 1]) / w
        sd[w:] = np.sqrt(np.maximum((cs2[w:-1] - cs2[:-w - 1]) / w - mu * mu, 1e-18))
        z = dv / sd
        abajo, arriba = SEN.transicion(z <= -2.5), SEN.transicion(z >= 2.5)
    N["BNF distancia a la media de 25 h"] = (np.r_[T5[abajo], T5[arriba]] + 300, np.r_[np.ones(abajo.sum()), -np.ones(arriba.sum())])
    base = dict(N)
    for nom in ("REV5", "REV15", "rompimiento de 20 velas"):
        base[nom] = S[nom][1:]
    for nom, (ts, ds) in base.items():
        ts, ds = np.asarray(ts, dtype=np.int64), np.asarray(ds, dtype=float)
        ctx = contexto_3h(t, c, ts)
        if nom in N:
            N[nom] = (ts, ds)
        N[f"{nom} · contexto a favor"] = (ts[ds * ctx > 0], ds[ds * ctx > 0])
        N[f"{nom} · contexto en contra"] = (ts[ds * ctx < 0], ds[ds * ctx < 0])
    return {k: ("N",) + v for k, v in N.items()}


def medir(tom):
    n, w, _ = t18.cuenta([e[4] for e in tom])
    n2, w2, _ = t18.cuenta([e[4] for e in tom if t18.dt.datetime.fromtimestamp(e[0] - HCOL, t18.UTC).year >= 2024])
    dias = max(1, (tom[-1][0] - tom[0][0]) / 86400) if tom else 1
    s = t18.arranques(tom, 0.85)
    return {"apuestas": n, "acierto": w / n if n else 0.0, "acierto_2024_26": w2 / n2 if n2 else 0.0,
            "arriba_30d": sum(1 for x in s if x > 100000) / len(s) if s else 0.0, "por_dia": n / dias}


def main():
    t0 = time.time()
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    if SYM == "BTCUSDT":
        S.update(t18.grupo_B(int(t[-1])))
    Nn = grupo_N(t, o, h, l, c, S)
    print(f"{SYM}: grupo N con {len(Nn)} estrategias · {time.time() - t0:.0f} s", file=sys.stderr)
    P_act = SEL.preparar(S, T5, vol5, ctxd, t, o, c)
    P_amp = dict(P_act)
    P_amp.update(SEL.preparar(Nn, T5, vol5, ctxd, t, o, c))
    ultimo, primero = int(t[-1]), sumar(2020, 1, 12)
    tom_act, sel_act = t18.a_ciegas(P_act, primero, ultimo, 12, 3)
    tom_amp, sel_amp = t18.a_ciegas(P_amp, primero, ultimo, 12, 3)
    print(f"elección a ciegas lista · {time.time() - t0:.0f} s", file=sys.stderr)
    m_act, m_amp = medir(tom_act), medir(tom_amp)
    cond = {"acierto de todo el periodo": m_amp["acierto"] >= m_act["acierto"],
            "acierto 2024-26": m_amp["acierto_2024_26"] >= m_act["acierto_2024_26"],
            "30 días arriba (pago 0,85)": m_amp["arriba_30d"] >= m_act["arriba_30d"],
            "apuestas al día": m_amp["por_dia"] >= m_act["por_dia"]}
    meses = {}
    for _, eleg in sel_amp:
        for x in eleg:
            if x["nombre"] in Nn:
                meses[x["nombre"]] = meses.get(x["nombre"], 0) + 1
    with open(os.path.join(AQUI, f"t26_{SYM}.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T26 · CONTEXTO DE 3 H, 5 H Y 90 DÍAS Y ESTRATEGIAS DIFUNDIDAS · {SYM} · a ciegas, 12 meses, 3 elegidas, pago 0,85")
        p("Regla fijada antes (PLAN.md, sección 12): el banco ampliado entra solo si iguala o mejora las cuatro medidas.\n")
        for nom, m in (("Banco actual", m_act), ("Banco ampliado", m_amp)):
            p(f"{nom}: {es(m['apuestas'], 0)} apuestas · acierto {es(100 * m['acierto'])} % · 2024-26 {es(100 * m['acierto_2024_26'])} % · "
              f"30 días arriba {es(100 * m['arriba_30d'])} % · {es(m['por_dia'], 2)} al día")
        p("")
        for k, v in cond.items():
            p(f"{'cumple' if v else 'NO cumple'} · {k}")
        p(f"\nVEREDICTO: {'el banco ampliado entra' if all(cond.values()) else 'el banco no cambia'}")
        p("\n== ESTRATEGIAS NUEVAS: meses elegidas a ciegas y acierto propio en todo el periodo (10 min, sentido fijo) ==")
        for nom in sorted(Nn):
            pp = P_amp.get(nom)
            if pp is None:
                p(f"   0 · {nom}: sin señales")
                continue
            r = pp["res"][10]
            n = len(r)
            w = int((r > 0).sum())
            wi = int((r < 0).sum())
            p(f"{meses.get(nom, 0):4d} · {nom}: {es(n, 0)} señales · tal cual {es(100 * w / max(1, n))} % · al revés {es(100 * wi / max(1, n))} %")
        p("\n== ELEGIDAS POR MES CON EL BANCO AMPLIADO ==")
        for (y, m), eleg in sel_amp:
            p(f"{y}-{m:02d}: " + ("; ".join(f"{x['nombre']} [{t18.describir(x['conf'])}]" for x in eleg) or "ninguna"))
    json.dump({"simbolo": SYM, "actual": m_act, "ampliado": m_amp, "condiciones": cond, "entra": all(cond.values()),
               "meses_elegidas": meses}, open(os.path.join(AQUI, f"t26_{SYM}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"listo · {time.time() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
