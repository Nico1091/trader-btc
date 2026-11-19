"""T17 (29/10/2026): las 42 estrategias y sus mezclas en 7 plazos y 5 preventivas, siempre con el 16 % del saldo y sin stop.

Pedido de Nicolás: «16 % de riesgo sin stop loss», «5, 10, 15, 20 minutos, una hora, un día», «con preventivas y sin preventivas
de cada una», 16 operaciones al día por mezcla, y verlas todas. Pago 0,85, máximo 16 al día, una abierta a la vez.
Por cada plazo y preventiva: todas las estrategias solas, parejas y tríos, 3 caminos de crecimiento hasta las 42 y 30 al azar
por tamaño. Se elige con 2024-26 y se mira el mes 29/09-28/10.
Salida: t17_resumen.txt (lo principal) y t17_mezclas.csv (Excel: todas las solas y parejas de cada plazo y preventiva,
y de las más grandes las 100 mejores de cada periodo y las que ganan en los dos).
Uso: python -I t17_plazos_preventivas.py"""
import ctypes
import importlib.util
import itertools
import math
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
_e = importlib.util.spec_from_file_location("t16", os.path.join(AQUI, "t16_mezclas_todas.py"))
t16 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t16)
t7 = t16.t7
PLAZOS = (5, 10, 15, 20, 30, 60, 1440)
PREV = {"sin preventiva": (False, False, 0),
        "para el día tras 2 fallos seguidos": (False, False, 2),
        "solo a favor de la tendencia del día": (True, False, 0),
        "solo con volatilidad baja": (False, True, 0),
        "tendencia del día + para tras 2 fallos": (True, False, 2)}
TOPE, MIN_AP, MIN_MES = 16, 100, 10
LG, LP = math.log(1 + 0.16 * 0.85), math.log(1 - 0.16)
random.seed(29102026)


def simular(P, sel, prev):
    ctx, vb, seguidas = prev
    m = sel[P["k"]]
    if ctx:
        m = m & P["cx"]
    if vb:
        m = m & P["vb"]
    w = lo = e = 0
    ocupado, dia, n, seg, parado = 0, None, 0, 0, False
    dias = set()
    for a, b, r, d in zip(P["ts"][m].tolist(), P["en"][m].tolist(), P["rs"][m].tolist(), P["dy"][m].tolist()):
        if d != dia:
            dia, n, seg, parado = d, 0, 0, False
        if parado or n >= TOPE or a < ocupado:
            continue
        n += 1
        ocupado = b
        dias.add(d)
        if r > 0:
            w += 1
            seg = 0
        elif r < 0:
            lo += 1
            seg += 1
            if seguidas and seg >= seguidas:
                parado = True
        else:
            e += 1
    return w, lo, e, len(dias)


def lg(x):
    return x[0] * LG + x[1] * LP


def saldo(x):
    return 100000 * math.exp(max(min(lg(x), 25), -50))


def main():
    t_ini = time.time()
    t, o, h, l, c, ext = t7.cargar()
    S, T5, vol5 = t7.senales(t, o, h, l, c, ext)
    ctxd = t7.contexto(t, c)
    S.update(t16.senales_E(t, o, h, l, c))
    CONF = {e["nombre"]: e["conf"] for e in t16.R["estrategias"]}
    t7.APUESTA, t7.CAP = 0.02, 150000.0
    t0, N = int(t[0]), len(c)
    nombres, filas = [], []
    for n, (g, ts, ds) in S.items():
        s = t7.preparar(np.asarray(ts, dtype=np.int64), np.asarray(ds), t, o, c, ctxd, T5, vol5)
        if not len(s["t"]):
            continue
        if n not in CONF:
            CONF[n] = t7.optimizar(n, s)[0]
        m = t7.filtrar(s, CONF[n])
        if not m.any():
            continue
        j = len(nombres)
        nombres.append(n)
        tt, dd = s["t"][m], CONF[n]["sentido"] * s["d"][m]
        cx = np.array([ctxd.get(int(x) // 86400, 0.0) for x in tt]) == dd
        filas += list(zip(tt.tolist(), [j] * len(tt), dd.tolist(), cx.tolist(), (~s["valta"][m]).tolist()))
    filas.sort()
    F = np.array(filas, dtype=np.int64)
    TS, KK, DD, CX, VB = F.T
    kmin = (TS - t0) // 60
    K = len(nombres)
    print(f"{K} estrategias, {len(TS)} señales · carga {time.time() - t_ini:.0f} s", file=sys.stderr)

    filas_csv, resumen, ganan_dos = [], [], []
    for pl in PLAZOS:
        fin = kmin + pl - 1
        ok = fin < N
        RS = np.sign(DD * (c[np.minimum(fin, N - 1)] - o[kmin])).astype(np.int64)
        PER = {}
        for nom, (a, b) in (("ent", (t7.INI, t7.MES0)), ("mes", (t7.MES0, t7.MES1))):
            mm = ok & (TS >= a) & (TS < b)
            PER[nom] = {"ts": TS[mm], "en": TS[mm] + pl * 60, "rs": RS[mm], "k": KK[mm], "dy": (TS[mm] - t7.HCOL) // 86400,
                        "cx": CX[mm].astype(bool), "vb": VB[mm].astype(bool), "dias": (b - a) / 86400}
        for pnom, prev in PREV.items():
            visto = {}

            def probar(mz):
                mz = tuple(sorted(mz))
                if mz not in visto:
                    sel = np.zeros(K, bool)
                    sel[list(mz)] = True
                    visto[mz] = simular(PER["ent"], sel, prev)
                return visto[mz]

            def punt(x):
                return lg(x) if x[0] + x[1] >= MIN_AP else -1e18

            for mz in itertools.chain(((k,) for k in range(K)), itertools.combinations(range(K), 2), itertools.combinations(range(K), 3)):
                probar(mz)
            caminos = sorted((mz for mz in visto if len(mz) == 3), key=lambda mz: -punt(visto[mz]))[:3]
            for tam in range(4, K + 1):
                nuevos = sorted(((punt(probar(mz + (k,))), tuple(sorted(mz + (k,)))) for mz in caminos for k in range(K) if k not in mz), reverse=True)
                caminos = list(dict.fromkeys(mz for _, mz in nuevos))[:3]
                for _ in range(30):
                    probar(random.sample(range(K), tam))
            mes = {}
            for mz in visto:
                sel = np.zeros(K, bool)
                sel[list(mz)] = True
                mes[mz] = simular(PER["mes"], sel, prev)
            por_ent = sorted(visto, key=lambda mz: -punt(visto[mz]))
            por_mes = sorted(mes, key=lambda mz: -(lg(mes[mz]) if mes[mz][0] + mes[mz][1] >= MIN_MES else -1e18))
            dos = [mz for mz in visto if punt(visto[mz]) > 0 and mes[mz][0] + mes[mz][1] >= MIN_MES and lg(mes[mz]) > 0]
            elegidas = set(mz for mz in visto if len(mz) <= 2) | set(por_ent[:100]) | set(por_mes[:100]) | set(dos)
            for mz in elegidas:
                filas_csv.append((pl, pnom, mz, visto[mz], mes[mz], PER["ent"]["dias"], PER["mes"]["dias"], mz in dos))
            for mz in dos:
                ganan_dos.append((lg(mes[mz]), pl, pnom, mz, visto[mz], mes[mz]))
            mejor = por_ent[0]
            resumen.append((pl, pnom, len(visto), mejor, visto[mejor], mes[mejor], len(dos), por_mes[0], visto[por_mes[0]], mes[por_mes[0]]))
            print(f"plazo {pl} · {pnom}: {len(visto)} mezclas, {len(dos)} ganan en los dos · {time.time() - t_ini:.0f} s", file=sys.stderr)

    def nm(mz, largo=200):
        x = " + ".join(nombres[k][:28] for k in mz)
        return x if len(x) <= largo else f"{len(mz)} estrategias"

    def txt(x, dias):
        n = x[0] + x[1]
        return (f"{x[0] + x[1] + x[2]} apuestas ({(x[0] + x[1] + x[2]) / dias:.1f} al día), {x[0]} aciertos y {x[1]} fallos "
                f"({x[0] / n * 100 if n else 0:.1f} %), 100.000 → {saldo(x):,.0f}".replace(",", "."))

    de, dm = (t7.MES0 - t7.INI) / 86400, (t7.MES1 - t7.MES0) / 86400
    with open(os.path.join(AQUI, "t17_resumen.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T17 · {K} estrategias · binarias por tiempo, 16 % del saldo, sin stop, pago 0,85, hasta 16 al día · "
          f"{len(PLAZOS)} plazos × {len(PREV)} preventivas · {sum(r[2] for r in resumen):,} pruebas".replace(",", "."))
        p("Saldos topados en 100.000 × e^25 para que se lean; 0 = la cuenta se acabó.\n")
        p("== POR PLAZO Y PREVENTIVA: la mejor elegida con 2024-26, cómo le fue en el mes, y cuántas ganan en los dos ==")
        for pl, pnom, nv, mz, xe, xm, nd2, mzm, xe2, xm2 in resumen:
            p(f"\n[{pl} min · {pnom}] {nv} mezclas probadas · {nd2} ganan en los dos periodos")
            p(f"   mejor en 2024-26: {nm(mz, 150)}\n      2024-26: {txt(xe, de)}\n      mes:     {txt(xm, dm)}")
            p(f"   mejor del mes:    {nm(mzm, 150)}\n      2024-26: {txt(xe2, de)}\n      mes:     {txt(xm2, dm)}")
        ganan_dos.sort(reverse=True)
        p(f"\n== LAS QUE GANAN EN LOS DOS PERIODOS CON EL 16 % ({len(ganan_dos)} en total; las 60 que más dejan en el mes) ==")
        for _, pl, pnom, mz, xe, xm in ganan_dos[:60]:
            p(f"[{pl} min · {pnom}] {nm(mz, 150)}\n      2024-26: {txt(xe, de)}\n      mes:     {txt(xm, dm)}")
    with open(os.path.join(AQUI, "t17_mezclas.csv"), "w", encoding="utf-8-sig") as f:
        f.write("plazo_min;preventiva;cuantas;estrategias;apuestas_2024_26;por_dia_2024_26;aciertos_2024_26;fallos_2024_26;"
                "acierto_2024_26;saldo_2024_26;apuestas_mes;por_dia_mes;aciertos_mes;fallos_mes;acierto_mes;saldo_mes;gana_en_los_dos\n")
        for pl, pnom, mz, xe, xm, de_, dm_, dos in sorted(filas_csv, key=lambda r: (r[0], r[1], -lg(r[4]))):
            def col(x, d):
                n = x[0] + x[1]
                return [str(x[0] + x[1] + x[2]), f"{(x[0] + x[1] + x[2]) / d:.2f}".replace(".", ","), str(x[0]), str(x[1]),
                        f"{x[0] / n * 100 if n else 0:.1f}".replace(".", ","), f"{saldo(x):.0f}"]
            f.write(";".join([str(pl), pnom, str(len(mz)), " + ".join(nombres[k] for k in mz)] + col(xe, de_) + col(xm, dm_) + ["sí" if dos else "no"]) + "\n")
    print(f"listo: {len(filas_csv)} filas en el CSV · {time.time() - t_ini:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
