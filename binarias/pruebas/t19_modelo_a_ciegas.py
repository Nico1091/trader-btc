"""T19 (29/10/2026): modelo a ciegas, mes a mes, en los plazos de Binance (10, 30 y 60 min). PLAN.md v2, sección 4 (P3).

En cada cierre de vela de 5 min, una regresión logística propia (numpy, sin librerías nuevas) estima la probabilidad de que el
precio suba en el plazo. Rasgos, todos con datos anteriores a la entrada: rendimientos de 1 a 240 min sobre la volatilidad,
volatilidades y sus razones, volumen, posición en el rango de 4 y 24 h, distancia y pendiente de medias, forma de la última
vela, hora, fin de semana, contexto diario y las 27 señales del grupo A (sus libros). Por cada mes M: se normaliza y se ajusta
con los meses M-12 a M-4, el umbral de confianza se elige con M-3 a M-1 (solo apuestas vencidas antes de M) y se opera M.
El modelo vive en motor/modelo.py, el mismo que usa el centinela.
Operación como T18: una abierta a la vez, hasta 16 al día, 16 % o 5 USDT, empate = fallo.
Salidas: t19_<SÍMBOLO>.txt, t19_<SÍMBOLO>_apuestas.csv y t19_<SÍMBOLO>.json.
Uso: python -I t19_modelo_a_ciegas.py BTCUSDT|ETHUSDT [archivo de velas]"""
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
_e = importlib.util.spec_from_file_location("t18", os.path.join(AQUI, "t18_reglas_a_ciegas.py"))
t18 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t18)
from motor import modelo as MOD  # noqa: E402  (t18 ya puso la carpeta raíz en sys.path)

SEN, SEL, es, mes_ini, sumar, HCOL = t18.SEN, t18.SEL, t18.es, t18.mes_ini, t18.sumar, t18.HCOL
SYM, NPY, UTC, PAGOS, MINIMO, Z_BONF = t18.SYM, t18.NPY, t18.UTC, t18.PAGOS, t18.MINIMO, t18.Z_BONF
PLAZOS = (10, 30, 60)
random.seed(29102026)


def auc(p, y):
    orden = np.argsort(p, kind="stable")
    rangos = np.empty(len(p))
    rangos[orden] = np.arange(1, len(p) + 1)
    npos = y.sum()
    nneg = len(y) - npos
    return (rangos[y == 1].sum() - npos * (npos + 1) / 2) / max(1, npos * nneg)


def main():
    t_ini = time.time()
    a = np.load(NPY)
    t = (a[:, 0] // 1000).astype(np.int64)
    o, h, l, c, v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    te, k, X, nombres = MOD.rasgos(t, o, h, l, c, v)
    print(f"{SYM}: {len(te):,} muestras × {X.shape[1]} rasgos · {time.time() - t_ini:.0f} s", file=sys.stderr)
    ultimo = int(t[-1])
    salida, res_json = {}, {}
    for pl in PLAZOS:
        mov = c[k + pl - 1] - o[k]
        mov60 = c[k + pl] - o[k + 1]
        ev, taus, ps, ys = [], [], [], []
        ym = (2021, 1)
        while mes_ini(*ym) < ultimo:
            a_, f_, b_, e_ = mes_ini(*sumar(*ym, -12)), mes_ini(*sumar(*ym, -3)), mes_ini(*ym), mes_ini(*sumar(*ym, 1))
            ib0, ie = (int(x) for x in np.searchsorted(te, [b_, e_]))
            par = MOD.entrenar(te, X, mov, a_, f_, b_, pl)
            pm = MOD.prob(par["w"], MOD.normalizar(X[ib0:ie], par["mu"], par["de"]))
            ps.append(pm)
            ys.append(mov[ib0:ie])
            tau = par["tau"]
            taus.append((ym, tau))
            if tau is not None:
                d = np.where(pm >= tau, 1, np.where(pm <= 1 - tau, -1, 0))
                for i in np.flatnonzero(d).tolist():
                    g = ib0 + i
                    ev.append((int(te[g]), f"modelo {pl} min", int(d[i]), pl, int(np.sign(d[i] * mov[g])), int(np.sign(d[i] * mov60[g])),
                               int(np.sign(mov[g]))))
            ym = sumar(*ym, 1)
        tom = SEL.operar(sorted(ev))
        pall, yall = np.concatenate(ps), np.concatenate(ys)
        nz = yall != 0
        salida[pl] = (tom, taus, auc(pall[nz], (yall[nz] > 0).astype(float)))
        print(f"plazo {pl}: {len(tom)} apuestas · {time.time() - t_ini:.0f} s", file=sys.stderr)

    fecha = lambda ts: dt.datetime.fromtimestamp(ts - HCOL, UTC)

    def tramo(x, y0, y1):
        return [e for e in x if y0 <= fecha(e[0]).year <= y1]

    with open(os.path.join(AQUI, f"t19_{SYM}.txt"), "w", encoding="utf-8") as f:
        p = lambda s="": print(s, file=f)
        p(f"T19 · MODELO A CIEGAS · {SYM} · regresión logística con {X.shape[1]} rasgos, ajustada mes a mes · {fecha(int(t[0])):%d/%m/%Y} a {fecha(ultimo):%d/%m/%Y}")
        p("Se ajusta con 9 meses, el umbral se elige con los 3 siguientes y se opera el mes después. Operación igual que T18.")
        p("Para no perder: 54,1 % con pago 0,85. Para crecer al 16 %: 57,8 %. Límite corregido = Wilson al 99,375 % de una cola.\n")
        for pl, (tom, taus, au) in salida.items():
            dias_op = max(1, (tom[-1][0] - tom[0][0]) / 86400) if tom else 1
            p(f"== PLAZO {pl} MIN · AUC fuera de muestra {es(au, 3)} (0,5 = azar) ==")
            p(t18.linea([e[4] for e in tom], "Todo el periodo: "))
            p(f"   {es(len(tom) / dias_op, 2)} apuestas al día, todos los días")
            for y0, y1 in ((2021, 2023), (2024, 2026)):
                p(t18.linea([e[4] for e in tramo(tom, y0, y1)], f"   {y0}-{str(y1)[2:]}: "))
            for yy in range(2021, 2027):
                p(t18.linea([e[4] for e in tramo(tom, yy, yy)], f"      {yy}: "))
            p(t18.linea([e[5] for e in tom], "Entrando 60 s tarde: "))
            p(t18.linea([e[6] for e in tom], "Siempre arriba, mismas horas: "))
            for pg in PAGOS:
                s = sorted(t18.arranques(tom, pg))
                if s:
                    arriba = sum(1 for x in s if x > 100000) / len(s)
                    p(f"pago {es(pg, 2)}: 30 días desde 100.000 terminan arriba en {es(100 * arriba)} % de {len(s)} arranques · "
                      f"quiebra {es(100 * sum(1 for x in s if x <= 0) / len(s))} % · mediana {es(s[len(s) // 2], 0)}")
            sin = sum(1 for _, tau in taus if tau is None)
            p(f"Meses sin apostar (ningún umbral hacía crecer la cuenta en la calibración): {sin} de {len(taus)}")
            p("Umbral por mes: " + " ".join(f"{y}-{m:02d}:{es(tau, 3) if tau else '-'}" for (y, m), tau in taus))
            p()
            n, w, em = t18.cuenta([e[4] for e in tom])
            res_json[pl] = {"apuestas": n, "aciertos": w, "empates": em, "acierto": w / n if n else None, "auc": au,
                            "lb_corregido": SEL.wilson_lb(w, n, Z_BONF) if n else None, "por_dia": len(tom) / dias_op,
                            "tramos": {f"{y0}-{y1}": t18.cuenta([e[4] for e in tramo(tom, y0, y1)]) for y0, y1 in ((2021, 2023), (2024, 2026))},
                            "tarde_60s": t18.cuenta([e[5] for e in tom]), "siempre_arriba": t18.cuenta([e[6] for e in tom])}
    with open(os.path.join(AQUI, f"t19_{SYM}_apuestas.csv"), "w", encoding="utf-8-sig") as f:
        f.write("fecha_hora_colombia;plazo_min;sentido;resultado;resultado_60s_tarde\n")
        txt = lambda r: "acierta" if r > 0 else "empate" if r == 0 else "falla"
        for pl, (tom, _, _) in salida.items():
            for e in tom:
                f.write(f"{fecha(e[0]):%Y-%m-%d %H:%M};{pl};{'SUBE' if e[2] > 0 else 'BAJA'};{txt(e[4])};{txt(e[5])}\n")
    json.dump({"simbolo": SYM, "rasgos": nombres, "plazos": res_json}, open(os.path.join(AQUI, f"t19_{SYM}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    print(f"listo · {time.time() - t_ini:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
