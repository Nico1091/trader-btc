"""Banco de pruebas: sistemas A, B, D contra el azar (C), con tramos separados y todo anotado.

Uso:  python -u -I banco.py
Salidas: datos/experimentos.csv (cada configuración probada, también las que fallan) y
informe-pruebas.md (resumen honesto). El tramo final se evalúa solo con lo elegido.
"""
import csv
import datetime as dt
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import datos  # noqa: E402
import estrategias as es  # noqa: E402
from simulador import Reglas, simular, metricas  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc


def ms(fecha):
    return int(dt.datetime.fromisoformat(fecha).replace(tzinfo=UTC).timestamp() * 1000)


PERIODOS = {
    "desarrollo": (ms("2023-01-01"), ms("2025-07-01")),
    "validacion": (ms("2025-07-01"), ms("2026-04-01")),
    "final": (ms("2026-04-01"), ms("2026-10-19")),
}
MITADES = ((ms("2023-01-01"), ms("2024-04-01")), (ms("2024-04-01"), ms("2025-07-01")))
SEMILLAS = 100


def correr(m, funcion, p, reglas, tramo):
    desde, hasta = tramo
    senales = es.generar(m, funcion, p, desde, hasta)
    res = simular(m_v1, senales, reglas)
    return senales, res, metricas(res)


def puntaje_robusto(ms_mitades):
    """El peor t de las dos mitades del desarrollo: premia lo estable, castiga la suerte de un tramo."""
    ts = []
    for mt in ms_mitades:
        if mt.get("ops", 0) < 30 or mt.get("t_estadistico") is None:
            return -99.0
        ts.append(mt["t_estadistico"])
    return min(ts)


def rejilla_a():
    for tf in (15, 30, 60):
        for w in (48, 96):
            for k_sl in (1.5, 2.5):
                for R in (1.5, 2.5):
                    for H in (16, 48):
                        p = dict(es.A_BASE, w=w, k_sl=k_sl, R=R, H=H)
                        yield tf, p


def rejilla_b():
    for tf in (5, 15):
        for z in (-2.5, -3.5):
            for vz in (1.5, 2.5):
                for oi in (None, -0.3):
                    for R in (1.0, 2.0):
                        for conf in (False, True):
                            yield tf, dict(es.B_BASE, z=z, vz=vz, oi_max=oi, R=R, conf=conf)


def rejilla_d():
    yield 15, dict(es.D_BASE)                                   # tal cual el BTCUSDT.py del curso
    yield 15, dict(es.D_BASE, objetivo=0.02)                   # con el R:R 1:2 del curso de riesgo
    yield 60, dict(es.D_BASE, stop=0.02, objetivo=0.04, H=48)


def main():
    global m_v1
    inicio = time.time()
    v1 = datos.cargar_1m("contado-1m")
    m_v1 = v1
    print("Datos 1m:", json.dumps(v1.calidad, ensure_ascii=False))
    met = datos.cargar_metricas()
    fin = datos.cargar_financiacion()
    print(f"Métricas 5m: {len(met)} puntos; financiación: {len(fin[0])} puntos")
    velas = {k: datos.agregar(v1, k) for k in (5, 15, 30, 60, 240, 1440)}
    for k, v in velas.items():
        print(f"  marco {k} min: {v.calidad}")
    mayores = {60: es.Marco(velas[60], 60), 240: es.Marco(velas[240], 240), 1440: es.Marco(velas[1440], 1440)}
    marcos = {
        5: es.Marco(velas[5], 5, met, fin, mayores[60]),
        15: es.Marco(velas[15], 15, met, fin, mayores[240]),
        30: es.Marco(velas[30], 30, met, fin, mayores[240]),
        60: es.Marco(velas[60], 60, met, fin, mayores[1440]),
    }
    print(f"Indicadores listos en {time.time() - inicio:.0f} s")
    reglas = Reglas(capital=float(os.environ.get("CAPITAL_USDT", "9.7")))

    filas = []
    elegidos = {}
    for sistema, funcion, rejilla in (("A", es.senal_a, rejilla_a), ("B", es.senal_b, rejilla_b),
                                      ("D", es.senal_d, rejilla_d)):
        candidatos = []
        for tf, p in rejilla():
            m = marcos[tf]
            mitades = [correr(m, funcion, p, reglas, tramo)[2] for tramo in MITADES]
            _, _, mdev = correr(m, funcion, p, reglas, PERIODOS["desarrollo"])
            _, _, mval = correr(m, funcion, p, reglas, PERIODOS["validacion"])
            robusto = puntaje_robusto(mitades)
            candidatos.append((robusto, tf, p, mdev, mval))
            filas.append({"sistema": sistema, "marco_min": tf, "parametros": json.dumps(p, ensure_ascii=False),
                          "robusto": robusto, **{f"dev_{k}": v for k, v in mdev.items() if k != "motivos"},
                          **{f"val_{k}": v for k, v in mval.items() if k != "motivos"}})
        candidatos.sort(key=lambda x: x[0], reverse=True)
        elegidos[sistema] = candidatos[:5]
        mejor = candidatos[0]
        print(f"Sistema {sistema}: {len(candidatos)} configuraciones; mejor robusto={mejor[0]} tf={mejor[1]} "
              f"dev={mejor[3]} val={mejor[4]}")

    os.makedirs(os.path.join(CARPETA, "datos"), exist_ok=True)
    columnas = sorted({k for f in filas for k in f}, key=lambda k: (k not in ("sistema", "marco_min", "parametros", "robusto"), k))
    with open(os.path.join(CARPETA, "datos", "experimentos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)

    # Tramo final + control de azar, solo para el mejor de cada sistema.
    resumen = {}
    for sistema, funcion in (("A", es.senal_a), ("B", es.senal_b), ("D", es.senal_d)):
        robusto, tf, p, mdev, mval = elegidos[sistema][0]
        m = marcos[tf]
        por_tramo = {}
        for nombre, tramo in PERIODOS.items():
            senales, res, mt = correr(m, funcion, p, reglas, tramo)
            azar_ret, azar_media = [], []
            for semilla in range(SEMILLAS):
                sa = es.azar(m, senales, semilla, *tramo)
                ma = metricas(simular(v1, sa, reglas))
                if ma.get("ops"):
                    azar_ret.append(ma["retorno_compuesto_pct"])
                    azar_media.append(ma["media_pct"])
            percentil = (sum(1 for x in azar_media if x < mt.get("media_pct", -1e9)) / len(azar_media) * 100
                         if azar_media and mt.get("ops") else None)
            i0 = next((i for i, t in enumerate(v1.t) if t >= tramo[0]), 0)
            i1 = next((i for i in range(len(v1.t) - 1, -1, -1) if v1.t[i] < tramo[1]), len(v1.t) - 1)
            por_tramo[nombre] = {
                **mt, "capital_final_usdt": round(res["capital_final"], 4), "polvo_btc": res["polvo_btc"],
                "omitidas": res["omitidas"],
                "azar_media_mediana": round(statistics.median(azar_media), 4) if azar_media else None,
                "azar_retorno_mediana": round(statistics.median(azar_ret), 2) if azar_ret else None,
                "azar_retorno_p90": round(sorted(azar_ret)[int(len(azar_ret) * 0.9)], 2) if azar_ret else None,
                "percentil_vs_azar": round(percentil, 1) if percentil is not None else None,
                "btc_comprar_y_mantener_pct": round((v1.c[i1] / v1.o[i0] - 1) * 100, 2),
            }
        resumen[sistema] = {"marco_min": tf, "parametros": p, "robusto_dev": robusto, "tramos": por_tramo,
                            "otros_4_mejores": [{"tf": c[1], "p": c[2], "robusto": c[0], "dev": c[3], "val": c[4]}
                                                for c in elegidos[sistema][1:]]}
        print(f"\n== Sistema {sistema} (tf {tf} min) {json.dumps(p, ensure_ascii=False)}")
        for nombre, d in por_tramo.items():
            print(f"  {nombre}: {json.dumps(d, ensure_ascii=False)}")
    with open(os.path.join(CARPETA, "datos", "resumen-banco.json"), "w", encoding="utf-8") as f:
        json.dump({"generado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).isoformat(timespec="seconds"),
                   "capital_usdt": reglas.capital, "comision": reglas.comision,
                   "configuraciones_probadas": len(filas), "resumen": resumen,
                   "calidad_datos": v1.calidad}, f, ensure_ascii=False, indent=1, default=str)
    print(f"\nListo en {time.time() - inicio:.0f} s. {len(filas)} configuraciones anotadas.")


if __name__ == "__main__":
    main()
