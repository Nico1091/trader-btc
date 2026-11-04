"""T18 (29/10/2026): reglas a ciegas, mes a mes, en los plazos de Binance (10, 30 y 60 min). PLAN.md v2, secciones 4 y 5.

Cada mes M (calendario de Colombia) se elige con los 12 meses anteriores (motor/seleccion.py), usando solo señales cuyo
resultado ya se conocía al empezar M, y se opera M sin tocar nada: una apuesta abierta a la vez, hasta 16 al día, 16 % del
saldo o 5 USDT si no alcanza, sin stop. Empate = fallo. Velas de 1 min de futuros de Binance desde 2020; grupos A, C y E
(motor/senales.py) y, en BTC, el B (motor de la T95H) desde 2024.
Variantes de sensibilidad (ventana de 6 y 24 meses, 1 y 5 elegidas): se informan, no se escogen.
Salidas: t18_<SÍMBOLO>.txt, t18_<SÍMBOLO>_apuestas.csv (Excel) y t18_<SÍMBOLO>.json.
Uso: python -I t18_reglas_a_ciegas.py BTCUSDT|ETHUSDT"""
import ctypes
import datetime as dt
import json
import os
import random
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:  # prioridad baja: que no le estorbe al equipo
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from motor import senales as SEN  # noqa: E402
from motor import seleccion as SEL  # noqa: E402

SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
# El segundo argumento, si viene, es un archivo de velas más reciente (el centinela lo escribe cada mes en datos/).
NPY = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BINARIAS_NPY_BASE", r"C:\Users\ni109\Ingresos\trader-btc\datos\um\{}_um_1m.npy").format(SYM)
TB = os.environ.get("BINARIAS_TB", r"C:\Users\ni109\Ingresos\trader-btc\.claude\worktrees\maestro-v2")
UTC = dt.timezone.utc
HCOL = 5 * 3600
PAGOS = (0.80, 0.85, 0.90)
TASA = 3180.0  # COP por USDT (mediana P2P de Binance, 20/10/2026)
MINIMO = 5 * TASA
Z_BONF = 2.4977  # 99,375 % de una cola: 95 % corregido por los 8 procedimientos a ciegas
VARIANTES = {"principal": (12, 3), "ventana de 6 meses": (6, 3), "ventana de 24 meses": (24, 3), "1 elegida": (12, 1), "5 elegidas": (12, 5)}
random.seed(29102026)


def es(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def mes_ini(y, m):
    return int(dt.datetime(y, m, 1, 5, tzinfo=UTC).timestamp())


def sumar(y, m, k):
    i = y * 12 + (m - 1) + k
    return i // 12, i % 12 + 1


def grupo_B(t_fin):
    sys.path.insert(0, os.path.join(TB, "consolidacion"))
    import sistema
    F = sistema.Npy(NPY)
    por = {k: ([], []) for k in ("P05b", "P05c", "P11", "N8", "N9")}
    d, fin = dt.date(2024, 1, 1), dt.datetime.fromtimestamp(t_fin, UTC).date()
    while d <= fin:
        try:
            ops, _ = sistema.Dia(F, d).todo()
        except Exception:
            ops = []
        for op in ops:
            if op["estrategia"] in por:
                por[op["estrategia"]][0].append(int(op["senal"]))
                por[op["estrategia"]][1].append(int(op["lado"]))
        d += dt.timedelta(days=1)
    return {f"{k} (T95H)": ("B", np.array(ts, dtype=np.int64), np.array(ds, dtype=float)) for k, (ts, ds) in por.items()}


def a_ciegas(P, primero, ultimo_ts, ventana, k):
    """Elige cada mes con la ventana anterior (sin señales sin vencer) y junta las señales de los elegidos en ese mes."""
    ev, sel = [], []
    y, m = primero
    while mes_ini(y, m) < ultimo_ts:
        a, b, e = mes_ini(*sumar(y, m, -ventana)), mes_ini(y, m), mes_ini(*sumar(y, m, 1))
        elegidos = SEL.elegir(P, a, b - 61 * 60, k)
        sel.append(((y, m), elegidos))
        ev += SEL.eventos(P, elegidos, b, e)
        y, m = sumar(y, m, 1)
    ev.sort()
    return SEL.operar(ev), sel


def cuenta(res):
    n = len(res)
    w = sum(1 for r in res if r > 0)
    em = sum(1 for r in res if r == 0)
    return n, w, em


def linea(res, nombre=""):
    n, w, em = cuenta(res)
    if not n:
        return f"{nombre}sin apuestas"
    return (f"{nombre}{es(n, 0)} apuestas, {es(w, 0)} aciertos ({es(100 * w / n)} %), {es(em, 0)} empates · "
            f"límite 95 % {es(100 * SEL.wilson_lb(w, n, 1.959964))} % · límite corregido {es(100 * SEL.wilson_lb(w, n, Z_BONF))} %")


def arranques(tomadas, pago, dias=30):
    """Para cada día de arranque: 100.000 COP durante `dias` días. Devuelve los saldos finales."""
    if not tomadas:
        return []
    dcol = np.array([(e[0] - HCOL) // 86400 for e in tomadas])
    res = [e[4] for e in tomadas]
    d0, d1 = int(dcol.min()), int(dcol.max())
    out = []
    for d in range(d0, d1 - dias + 2):
        i0, i1 = np.searchsorted(dcol, [d, d + dias])
        out.append(SEL.saldo(res[i0:i1], pago, minimo=MINIMO))
    return out


def main():
    t_ini = time.time()
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    if SYM == "BTCUSDT":
        S.update(grupo_B(int(t[-1])))
    P = SEL.preparar(S, T5, vol5, ctxd, t, o, c)
    print(f"{SYM}: {len(P)} estrategias, {sum(len(p['t']) for p in P.values()):,} señales · {time.time() - t_ini:.0f} s", file=sys.stderr)
    ultimo = int(t[-1])
    R = {}
    for var, (ventana, k) in VARIANTES.items():
        primero = sumar(2020, 1, ventana)
        R[var] = a_ciegas(P, primero, ultimo, ventana, k)
        print(f"{var}: {len(R[var][0])} apuestas · {time.time() - t_ini:.0f} s", file=sys.stderr)
    tom, sel = R["principal"]
    actual = SEL.elegir(P, mes_ini(*sumar(*dt_mes(ultimo), -11)), ultimo - 61 * 60, 3)

    def tramo(x, y0, y1):
        return [e for e in x if y0 <= dt.datetime.fromtimestamp(e[0] - HCOL, UTC).year <= y1]

    fecha = lambda ts: dt.datetime.fromtimestamp(ts - HCOL, UTC)
    dias_op = max(1, (tom[-1][0] - tom[0][0]) / 86400) if tom else 1
    sal = {p: arranques(tom, p) for p in PAGOS}
    resumen = {}
    with open(os.path.join(AQUI, f"t18_{SYM}.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T18 · REGLAS A CIEGAS · {SYM} · velas de 1 min de futuros de Binance, {fecha(int(t[0])):%d/%m/%Y} a {fecha(ultimo):%d/%m/%Y}")
        p("Cada mes se elige con los 12 meses anteriores y se opera sin tocar nada. 10, 30 y 60 min; una abierta a la vez; hasta 16 al día;")
        p("16 % del saldo o 5 USDT si no alcanza; empate = fallo. Para no perder: 55,6 % (pago 0,80), 54,1 % (0,85), 52,6 % (0,90).")
        p("Para crecer al 16 %: 59,1 %, 57,8 % y 56,4 %. Límite corregido = Wilson al 99,375 % de una cola (8 procedimientos).\n")
        p("== RESULTADO PRINCIPAL ==")
        p(linea([e[4] for e in tom], "Todo el periodo: "))
        p(f"   {es(len(tom) / dias_op, 2)} apuestas al día, todos los días ({es(len(tom), 0)} en {es(dias_op, 0)} días)")
        for y0, y1 in ((2021, 2023), (2024, 2026)):
            p(linea([e[4] for e in tramo(tom, y0, y1)], f"   {y0}-{str(y1)[2:]}: "))
        for y in range(2021, 2027):
            p(linea([e[4] for e in tramo(tom, y, y)], f"      {y}: "))
        p(linea([e[5] for e in tom], "Entrando 60 s tarde: "))
        p(linea([e[6] for e in tom], "Siempre arriba, mismas horas y plazos: "))
        az = []
        for _ in range(200):
            az.append(sum(1 for e in tom if e[6] * random.choice((-1, 1)) > 0) / max(1, len(tom)))
        az.sort()
        p(f"Azar en las mismas horas (200 repeticiones): {es(100 * az[100])} % (de {es(100 * az[5])} a {es(100 * az[194])} %)")
        netos = {}
        for e in tom:
            d = (e[0] - HCOL) // 86400
            netos[d] = netos.get(d, 0) + (1 if e[4] > 0 else -1)
        mejores = set(sorted(netos, key=lambda d: -netos[d])[:5])
        p(linea([e[4] for e in tom if (e[0] - HCOL) // 86400 not in mejores], "Sin los 5 mejores días: "))
        p("\n== EN PESOS: 100.000 COP durante 30 días, arrancando cada día del periodo ==")
        for pg in PAGOS:
            s = sorted(sal[pg])
            if not s:
                continue
            arriba = sum(1 for x in s if x > 100000) / len(s)
            quiebra = sum(1 for x in s if x <= 0) / len(s)
            p(f"pago {es(pg, 2)}: termina arriba en {es(100 * arriba)} % de los {len(s)} arranques · quiebra en {es(100 * quiebra)} % · "
              f"mediana {es(s[len(s) // 2], 0)} · peor 10 % {es(s[len(s) // 10], 0)} · mejor 10 % {es(s[9 * len(s) // 10], 0)}")
            resumen[f"arriba_{pg}"] = arriba
        p("\n== VARIANTES DE SENSIBILIDAD (se informan, no se escogen) ==")
        for var, (tv, _) in R.items():
            p(linea([e[4] for e in tv], f"{var}: "))
        p("\n== MES A MES (principal): elegidas con los 12 meses anteriores y su resultado en el mes ==")
        cuenta_sel = {}
        for (y, m), eleg in sel:
            ini, fin = mes_ini(y, m), mes_ini(*sumar(y, m, 1))
            em = [e for e in tom if ini <= e[0] < fin]
            n, w, _ = cuenta([e[4] for e in em])
            s85 = SEL.saldo([e[4] for e in em], 0.85, minimo=MINIMO)
            nombres = "; ".join(f"{x['nombre']} [{describir(x['conf'])}, {es(100 * x['lb'])} %]" for x in eleg) or "ninguna supera 54,1 %: no se apuesta"
            for x in eleg:
                cuenta_sel[x["nombre"]] = cuenta_sel.get(x["nombre"], 0) + 1
            p(f"{y}-{m:02d}: {n} apuestas, {es(100 * w / n) if n else '-'} % · 100.000 → {es(s85, 0)} · {nombres}")
        p("\n== CUÁNTOS MESES FUE ELEGIDA CADA ESTRATEGIA ==")
        for nom, v in sorted(cuenta_sel.items(), key=lambda x: -x[1]):
            p(f"{v:3d} · {nom}")
        p(f"\n== LO QUE SE ELEGIRÍA HOY (12 meses hasta {fecha(ultimo):%d/%m/%Y}) ==")
        for x in actual:
            p(f"{x['nombre']} [{describir(x['conf'])}] · {x['aciertos']}/{x['apuestas']} en la ventana · límite {es(100 * x['lb'])} %")
        if not actual:
            p("ninguna supera 54,1 %: no se apuesta")
    with open(os.path.join(AQUI, f"t18_{SYM}_apuestas.csv"), "w", encoding="utf-8-sig") as f:
        f.write("fecha_hora_colombia;mes;estrategia;sentido;plazo_min;resultado;resultado_60s_tarde;siempre_arriba;apuesta_cop;ganancia_cop;saldo_del_mes\n")
        mes_act, s = None, 100000.0
        for e in tom:
            fe = fecha(e[0])
            if (fe.year, fe.month) != mes_act:
                mes_act, s = (fe.year, fe.month), 100000.0
            if s < MINIMO:
                apuesta, g = 0.0, 0.0
            else:
                apuesta = max(0.16 * s, MINIMO)
                g = apuesta * 0.85 if e[4] > 0 else -apuesta
                s += g
            txt = lambda r: "acierta" if r > 0 else "empate" if r == 0 else "falla"
            f.write(";".join([f"{fe:%Y-%m-%d %H:%M}", f"{fe:%Y-%m}", e[1], "SUBE" if e[2] > 0 else "BAJA", str(e[3]), txt(e[4]), txt(e[5]),
                              txt(e[6]), es(apuesta, 0), es(g, 0), es(s, 0)]) + "\n")
    n, w, em = cuenta([e[4] for e in tom])
    resumen.update({"simbolo": SYM, "apuestas": n, "aciertos": w, "empates": em, "acierto": w / n if n else None,
                    "lb_corregido": SEL.wilson_lb(w, n, Z_BONF) if n else None,
                    "tramos": {f"{y0}-{y1}": cuenta([e[4] for e in tramo(tom, y0, y1)]) for y0, y1 in ((2021, 2023), (2024, 2026))},
                    "tarde_60s": cuenta([e[5] for e in tom]), "siempre_arriba": cuenta([e[6] for e in tom]),
                    "seleccion_hoy": actual, "por_dia": len(tom) / dias_op})
    json.dump(resumen, open(os.path.join(AQUI, f"t18_{SYM}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"listo · {time.time() - t_ini:.0f} s", file=sys.stderr)


def dt_mes(ts):
    f = dt.datetime.fromtimestamp(ts - HCOL, UTC)
    return f.year, f.month


def describir(conf):
    x = [("al revés" if conf["sentido"] < 0 else "normal"), f"{conf['plazo']} min"]
    if conf.get("zona"):
        x.append("a favor del contexto")
    if conf.get("sesion"):
        x.append(conf["sesion"])
    if conf.get("vol"):
        x.append(f"volatilidad {conf['vol']}")
    return ", ".join(x)


if __name__ == "__main__":
    main()
