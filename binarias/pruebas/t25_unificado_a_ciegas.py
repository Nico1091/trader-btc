"""T25 (29/10/2026): modelo unificado a ciegas (PLAN.md, sección 11) y comparación con el procedimiento por historial (H, v4).

U: una regresión logística por activo (BTCUSDT y ETHUSDT) a 10 min (motor/unificado.py), ajustada mes a mes a ciegas; en cada
cierre de 5 min se apuesta el activo más alejado de 0,5 que pase su umbral; una abierta a la vez; hasta 16 al día; empate = fallo.
Sensibilidad (se informa, no se escoge): sin flujo de órdenes, sin el otro activo y sin frecuencia mínima.
Decisión fijada en el plan (enero de 2022 a octubre de 2026, medio Kelly, mínimo 5 USDT): U reemplaza a H si (1) los 30 días desde
100.000 COP terminan arriba en al menos tantos arranques, (2) su acierto en 2024-26 es al menos el de H y (3) el porcentaje de
días con apuestas es al menos el de H.
Salidas: t25_unificado.txt, t25_unificado_apuestas.csv y t25_unificado.json.
Uso: python -I t25_unificado_a_ciegas.py"""
import ctypes
import datetime as dt
import importlib.util
import json
import os
import random
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from motor import historial as HI  # noqa: E402
from motor import seleccion as SEL  # noqa: E402
from motor import unificado as U  # noqa: E402

_e = importlib.util.spec_from_file_location("t21", os.path.join(AQUI, "t21_tamano_y_preventivas.py"))
t21 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t21)
UTC = dt.timezone.utc
HCOL = 5 * 3600
Z_BONF = 2.4977
random.seed(29102026)


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def mes_ini(y, m):
    return int(dt.datetime(y, m, 1, 5, tzinfo=UTC).timestamp())


def sumar(y, m, k):
    i = y * 12 + (m - 1) + k
    return i // 12, i % 12 + 1


def fecha(ts):
    return dt.datetime.fromtimestamp(ts - HCOL, UTC)


def preparar():
    A = np.load(os.path.join(RAIZ, "datos", "BTCUSDT_um_1m_tb.npy"))
    B = np.load(os.path.join(RAIZ, "datos", "ETHUSDT_um_1m_tb.npy"))
    A, B = U.alinear(A, B)
    P = {}
    for act, (X_, Y_) in (("BTCUSDT", (A, B)), ("ETHUSDT", (B, A))):
        te, k, X, nombres = U.rasgos(X_, Y_)
        c, o = X_[:, 4], X_[:, 1]
        P[act] = {"te": te, "X": X, "nombres": nombres, "mov": c[k + U.PLAZO - 1] - o[k], "mov60": c[k + U.PLAZO] - o[k + 1]}
    assert np.array_equal(P["BTCUSDT"]["te"], P["ETHUSDT"]["te"]), "las muestras de BTC y ETH no coinciden"
    return P


def a_ciegas(P, min_dia=U.MIN_DIA, quitar=(), desde=(2021, 1)):
    nombres = P["BTCUSDT"]["nombres"]
    columnas = None
    if quitar:
        columnas = np.array([i for i, n in enumerate(nombres) if not any(n.startswith(q) for q in quitar)])
    te = P["BTCUSDT"]["te"]
    ev, taus = [], []
    ym = desde
    while mes_ini(*ym) < te[-1]:
        a, f, b, e = mes_ini(*sumar(*ym, -12)), mes_ini(*sumar(*ym, -3)), mes_ini(*ym), mes_ini(*sumar(*ym, 1))
        ib0, ie = (int(x) for x in np.searchsorted(te, [b, e]))
        probs = {}
        for act in U.ACTIVOS:
            d = P[act]
            par = U.entrenar(d["te"], d["X"], d["mov"], a, f, b, min_dia, columnas)
            probs[act] = (U.probabilidad(par, d["X"][ib0:ie]), par["tau"])
        taus.append((ym, {x: probs[x][1] for x in probs}))
        for i in range(ie - ib0):
            el = U.elegir_apuesta({x: (probs[x][0][i], probs[x][1]) for x in probs})
            if el:
                act, dd, p = el
                g = ib0 + i
                d = P[act]
                ev.append((int(te[g]), act, int(dd), U.PLAZO, int(np.sign(dd * d["mov"][g])), int(np.sign(dd * d["mov60"][g])), int(np.sign(d["mov"][g]))))
        ym = sumar(*ym, 1)
    return SEL.operar(sorted(ev)), taus


def cuenta(res):
    n = len(res)
    return n, sum(1 for r in res if r > 0), sum(1 for r in res if r == 0)


def linea(res, nombre=""):
    n, w, em = cuenta(res)
    if not n:
        return f"{nombre}sin apuestas"
    return (f"{nombre}{es(n, 0)} apuestas, {es(100 * w / n)} % · empates {em} · límite 95 % {es(100 * SEL.wilson_lb(w, n, 1.959964))} % · "
            f"límite corregido {es(100 * SEL.wilson_lb(w, n, Z_BONF))} %")


def dias_con_apuestas(tom, d0, d1):
    dias = {(e[0] - HCOL) // 86400 for e in tom if d0 <= e[0] < d1}
    total = max(1, (d1 - d0) // 86400)
    return len(dias) / total


def como_t21(tom, nombre):
    """Apuestas en el formato de t21: (día ordinal de Colombia, «AAAA-MM», acierto, procedimiento)."""
    return [(fecha(e[0]).date().toordinal(), f"{fecha(e[0]):%Y-%m}", e[4] > 0, nombre) for e in tom]


def main():
    t_ini = time.time()
    P = preparar()
    print(f"rasgos listos: {len(P['BTCUSDT']['te']):,} muestras × {P['BTCUSDT']['X'].shape[1]} por activo · {time.time() - t_ini:.0f} s", file=sys.stderr)
    variantes = {"U (principal)": {}, "U sin flujo de órdenes": {"quitar": ("compras agresivas",)},
                 "U sin el otro activo": {"quitar": ("otro activo", "relativo al otro", "cuerpo de la vela del otro", "posición del otro", "compras agresivas del otro")},
                 "U sin frecuencia mínima": {"min_dia": 0.0}}
    R = {}
    for nom, kw in variantes.items():
        R[nom] = a_ciegas(P, **kw)
        print(f"{nom}: {len(R[nom][0])} apuestas · {time.time() - t_ini:.0f} s", file=sys.stderr)
    tom, taus = R["U (principal)"]
    d0, d1 = mes_ini(2022, 1), mes_ini(2026, 11)
    lineas = []
    p = lambda x="": lineas.append(x)
    p("T25 · MODELO UNIFICADO A CIEGAS (BTC y ETH a 10 min, una regresión por activo) · empate = fallo · pago 0,85")
    p("Para no perder: 54,1 %. Límite corregido = Wilson al 99,375 % de una cola.\n")
    for nom, (tv, _) in R.items():
        p(f"== {nom} ==")
        p(linea([e[4] for e in tv], "Todo (2021-2026): "))
        dias_tot = max(1, (tv[-1][0] - tv[0][0]) / 86400) if tv else 1
        p(f"   {es(len(tv) / dias_tot, 2)} apuestas al día · días con al menos una apuesta (2022-26): {es(100 * dias_con_apuestas(tv, d0, d1))} %")
        for y0, y1 in ((2021, 2023), (2024, 2026)):
            p(linea([e[4] for e in tv if y0 <= fecha(e[0]).year <= y1], f"   {y0}-{str(y1)[2:]}: "))
        for y in range(2021, 2027):
            p(linea([e[4] for e in tv if fecha(e[0]).year == y], f"      {y}: "))
        for act in U.ACTIVOS:
            p(linea([e[4] for e in tv if e[1] == act], f"   solo {act[:3]}: "))
        p(linea([e[5] for e in tv], "   entrando 60 s tarde: "))
        p(linea([e[6] for e in tv], "   siempre arriba, mismas horas: "))
        az = sorted(sum(1 for e in tv if e[6] * random.choice((-1, 1)) > 0) / max(1, len(tv)) for _ in range(200))
        p(f"   azar en las mismas horas: {es(100 * az[100])} % (de {es(100 * az[5])} a {es(100 * az[194])} %)")
        p()
    p("Umbrales por mes (principal): " + " ".join(f"{y}-{m:02d}:" + "/".join(es(v, 3) if v else "-" for v in t.values()) for (y, m), t in taus))
    # comparación con H en enero de 2022 a octubre de 2026, medio Kelly
    PH = HI.cargar()
    SH = HI.stats_mes(PH)
    apH, _ = t21.por_historial(PH, SH, list(PH))
    apU_todo = como_t21(tom, "U")
    SU = HI.stats_mes({"U": [(d, m, r) for d, m, r, _ in apU_todo]})
    apU = [x for x in apU_todo if x[1] >= "2022-01"]
    mH = t21.medida(t21.simular(apH, SH, "medio Kelly", "ninguna", 30))
    mU = t21.medida(t21.simular(apU, SU, "medio Kelly", "ninguna", 30))
    mU16 = t21.medida(t21.simular(apU, SU, "16 %", "ninguna", 30))
    mU90 = t21.medida(t21.simular(apU, SU, "medio Kelly", "ninguna", 90))
    mH90 = t21.medida(t21.simular(apH, SH, "medio Kelly", "ninguna", 90))
    accH = sum(1 for x in apH if x[1][:4] >= "2024" and x[2]) / max(1, sum(1 for x in apH if x[1][:4] >= "2024"))
    accU = sum(1 for x in apU if x[1][:4] >= "2024" and x[2]) / max(1, sum(1 for x in apU if x[1][:4] >= "2024"))
    diasH = len({x[0] for x in apH}) / max(1, (dt.date(2026, 10, 30).toordinal() - dt.date(2022, 1, 1).toordinal()))
    diasU = len({x[0] for x in apU}) / max(1, (dt.date(2026, 10, 30).toordinal() - dt.date(2022, 1, 1).toordinal()))
    p("\n== DECISIÓN (enero de 2022 a octubre de 2026, medio Kelly, mínimo 5 USDT) ==")
    p(f"H (v4, por historial): 30 días {t21.txt(mH)}")
    p(f"U (unificado):         30 días {t21.txt(mU)}")
    p(f"H a 90 días: {t21.txt(mH90)}")
    p(f"U a 90 días: {t21.txt(mU90)}")
    p(f"U al 16 % (referencia): 30 días {t21.txt(mU16)}")
    p(f"Acierto 2024-26: H {es(100 * accH)} % · U {es(100 * accU)} %")
    p(f"Días con al menos una apuesta: H {es(100 * diasH)} % · U {es(100 * diasU)} %")
    c1, c2, c3 = mU["arriba"] >= mH["arriba"], accU >= accH, diasU >= diasH
    p(f"Condiciones: (1) 30 días arriba {'sí' if c1 else 'no'} · (2) acierto 2024-26 {'sí' if c2 else 'no'} · (3) días con apuestas {'sí' if c3 else 'no'}")
    p("VEREDICTO: " + ("U reemplaza a H." if (c1 and c2 and c3) else "U no reemplaza a H."))
    w, n = HI.ventana(SU, "U", "2026-11", 6)
    p(f"Medio Kelly de U para noviembre de 2026: {w}/{n} = {es(100 * w / max(1, n))} % → {es(100 * HI.fraccion(SU, 'U', '2026-11'), 2)} % del saldo")
    open(os.path.join(AQUI, "t25_unificado.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")
    with open(os.path.join(AQUI, "t25_unificado_apuestas.csv"), "w", encoding="utf-8-sig") as f:
        f.write("fecha_hora_colombia;activo;sentido;resultado;resultado_60s_tarde\n")
        txt = lambda r: "acierta" if r > 0 else "empate" if r == 0 else "falla"
        for e in tom:
            f.write(f"{fecha(e[0]):%Y-%m-%d %H:%M};{e[1]};{'SUBE' if e[2] > 0 else 'BAJA'};{txt(e[4])};{txt(e[5])}\n")
    json.dump({"decision": {"c1": c1, "c2": c2, "c3": c3, "adoptar": c1 and c2 and c3}, "H": mH, "U": mU, "acierto_2024_26": {"H": accH, "U": accU},
               "dias": {"H": diasH, "U": diasU}, "rasgos": P["BTCUSDT"]["nombres"]},
              open(os.path.join(AQUI, "t25_unificado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\n".join(lineas))
    print(f"listo · {time.time() - t_ini:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
