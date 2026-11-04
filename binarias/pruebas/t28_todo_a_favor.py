"""T28 (31/10/2026): operar solo con todo a favor y solo con estrategias robustas. PLAN.md, sección 14, escrita antes de correrla.

C1 contexto de 1 h (última vela de 1 h cerrada al menos 10 min antes, frente a su EMA de 20); C2 color de la vela de 5 min que
acaba de cerrar; C3 parte del volumen de 15 min en velas verdes (>55 % compra, <45 % venta); C4 el C1 del otro activo.
R: la estrategia acertó más del 54,1 % en días de subida y en días de bajada, con sus apuestas a ciegas de meses anteriores.
La variante se elige con 2021-23 y se juzga con 2024-26.
Salidas: t28_<SÍMBOLO>.txt y t28_<SÍMBOLO>.json. Uso: python -I t28_todo_a_favor.py BTCUSDT|ETHUSDT"""
import datetime as dt
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
SEN, SEL, es, HCOL, SYM, NPY = t18.SEN, t18.SEL, t18.es, t18.HCOL, t18.SYM, t18.NPY
OTRO = "ETHUSDT" if SYM == "BTCUSDT" else "BTCUSDT"
NPY_OTRO = NPY.replace(SYM, OTRO)
CORTE = int(dt.datetime(2024, 1, 1, 5, tzinfo=dt.timezone.utc).timestamp())
UMBRAL = 1 / 1.85


def cargar(ruta):
    a = np.load(ruta)
    return (a[:, 0] // 1000).astype(np.int64), a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]


def contexto_1h(t, o, h, l, c, ts):
    """Signo del cierre de la última vela de 1 h cerrada al menos 10 min antes de cada entrada, frente a su EMA de 20."""
    T60, _, _, _, C60 = SEN.velas(t, o, h, l, c, 3600)
    e20 = SEN.ema(C60, 20)
    k = np.searchsorted(T60 + 3600, ts - 600, side="right") - 1
    s = np.sign(C60[np.clip(k, 0, len(C60) - 1)] - e20[np.clip(k, 0, len(C60) - 1)])
    s[k < 20] = 0
    return s


def medir(tom, desde, hasta):
    sub = [e for e in tom if desde <= e[0] < hasta]
    n = len(sub)
    w = sum(1 for e in sub if e[4] > 0)
    s = t18.arranques(sub, 0.85)
    return {"apuestas": n, "acierto": w / n if n else 0.0, "arriba_30d": sum(1 for x in s if x > 100000) / len(s) if s else 0.0,
            "por_dia": n / max(1, (hasta - desde) / 86400)}


def robustas(tom, dia_sube):
    """Máscara R, a ciegas: para cada apuesta, solo cuentan las apuestas de la misma estrategia de meses anteriores."""
    cuenta = {}
    ok = np.zeros(len(tom), bool)
    mes_de = lambda ts: (dt.datetime.fromtimestamp(ts - HCOL, dt.timezone.utc).year, dt.datetime.fromtimestamp(ts - HCOL, dt.timezone.utc).month)
    pendientes, mes_act = [], None
    for i, e in enumerate(tom):
        m = mes_de(e[0])
        if m != mes_act:
            for x in pendientes:  # las del mes anterior ya están cerradas y su día terminado
                d = dia_sube.get((x[0] - HCOL) // 86400)
                if d is None:
                    continue
                c = cuenta.setdefault(x[1], {True: [0, 0], False: [0, 0]})
                c[d][0] += x[4] > 0
                c[d][1] += 1
            pendientes, mes_act = [], m
        c = cuenta.get(e[1])
        if c and all(c[k][1] >= 30 and c[k][0] / c[k][1] > UMBRAL for k in (True, False)):
            ok[i] = True
        pendientes.append(e)
    return ok


def main():
    t0 = time.time()
    t, o, h, l, c, v = cargar(NPY)
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    if SYM == "BTCUSDT":
        S.update(t18.grupo_B(int(t[-1])))
    P = SEL.preparar(S, T5, vol5, ctxd, t, o, c)
    tom, _ = t18.a_ciegas(P, t18.sumar(2020, 1, 12), int(t[-1]), 12, 3)
    print(f"{SYM}: {len(tom)} apuestas a ciegas · {time.time() - t0:.0f} s", file=sys.stderr)
    ts = np.array([e[0] for e in tom], dtype=np.int64)
    dirs = np.array([e[2] for e in tom], dtype=float)

    c1 = contexto_1h(t, o, h, l, c, ts)
    T5_, O5, _, _, C5 = SEN.velas(t, o, h, l, c, 300)
    j5 = np.clip(np.searchsorted(T5_, ts - 300), 0, len(T5_) - 1)
    c2 = np.where(T5_[j5] == ts - 300, np.sign(C5[j5] - O5[j5]), 0.0)
    verde = np.r_[0.0, np.cumsum(v * (c > o))]
    total = np.r_[0.0, np.cumsum(v)]
    i = np.searchsorted(t, ts)
    i0 = np.maximum(i - 15, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        parte = (verde[i] - verde[i0]) / (total[i] - total[i0])
    c3 = np.where(parte > 0.55, 1.0, np.where(parte < 0.45, -1.0, 0.0))
    to, oo, ho, lo, co, _ = cargar(NPY_OTRO)
    c4 = contexto_1h(to, oo, ho, lo, co, ts)

    dcol = (t - HCOL) // 86400
    cortes = np.r_[0, np.flatnonzero(np.diff(dcol)) + 1, len(t)]
    dia_sube = {int(dcol[a]): bool(c[b - 1] > o[a]) for a, b in zip(cortes[:-1], cortes[1:])}
    R = robustas(tom, dia_sube)

    favor = lambda x: x == dirs
    a1, a3, a4, a2 = favor(c1), favor(c3), favor(c4), favor(c2)
    dos_de_tres = (a1.astype(int) + a3.astype(int) + a4.astype(int)) >= 2
    V = {"V1 robustas": R,
         "V2 C1, C3 y C4 a favor": a1 & a3 & a4,
         "V3 C1, C2, C3 y C4 a favor": a1 & a2 & a3 & a4,
         "V4 al menos 2 de C1, C3 y C4": dos_de_tres,
         "V5 robustas con V2": R & a1 & a3 & a4,
         "V6 robustas con V4": R & dos_de_tres}
    inicio, fin = int(ts[0]), int(t[-1])
    base = (medir(tom, inicio, CORTE), medir(tom, CORTE, fin))
    res = {}
    for nom, m in V.items():
        sub = [e for e, k in zip(tom, m.tolist()) if k]
        res[nom] = (medir(sub, inicio, CORTE), medir(sub, CORTE, fin))
    aptas = [n for n in V if res[n][0]["por_dia"] >= 1]
    elegida = max(aptas, key=lambda n: res[n][0]["acierto"]) if aptas else None
    if elegida:
        b = res[elegida][1]
        cond = [b["acierto"] >= base[1]["acierto"] + 0.01, b["arriba_30d"] >= base[1]["arriba_30d"], b["por_dia"] >= 1]
    else:
        cond = [False, False, False]
    with open(os.path.join(AQUI, f"t28_{SYM}.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T28 · SOLO CON TODO A FAVOR Y ESTRATEGIAS ROBUSTAS · {SYM} (otro activo: {OTRO}) · secuencia a ciegas de la t18, pago 0,85")
        p("Regla fijada antes (PLAN.md, sección 14): en 2024-26, +1,0 punto de acierto, no menos arranques arriba y ≥ 1 apuesta al día.\n")
        lin = lambda nom, m: (f"{nom}: {es(m['apuestas'], 0)} apuestas · {es(100 * m['acierto'])} % · 30 días arriba "
                              f"{es(100 * m['arriba_30d'])} % · {es(m['por_dia'], 2)} al día")
        for k, tramo in ((0, "2021-23 (elección)"), (1, "2024-26 (juicio)")):
            p(f"== {tramo} ==")
            p(lin("Sin filtro", base[k]))
            for nom in V:
                p(lin(nom, res[nom][k]))
            p("")
        p(f"Elegida con 2021-23: {elegida or 'ninguna da 1 apuesta al día'}")
        p(f"Acierto +1 punto: {'sí' if cond[0] else 'no'} · arranques: {'sí' if cond[1] else 'no'} · frecuencia: {'sí' if cond[2] else 'no'}")
        p(f"VEREDICTO: {'ENTRA' if all(cond) else 'no entra'}")
        p("\nCoincidencia de cada indicativo con la apuesta (todo el periodo): " +
          " · ".join(f"{n} {es(100 * x.mean())} %" for n, x in (("C1", a1), ("C2", a2), ("C3", a3), ("C4", a4), ("R", R))))
    json.dump({"simbolo": SYM, "base": base, "variantes": res, "elegida": elegida, "entra": all(cond)},
              open(os.path.join(AQUI, f"t28_{SYM}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"listo · {time.time() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
