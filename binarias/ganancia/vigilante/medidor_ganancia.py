#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Medidor de ganancia por apuesta para las binarias (solo biblioteca estándar).

Pregunta que responde: ¿cada estrategia GANA DINERO al precio que de verdad se
pagó en cada apuesta, con el ganador oficial? El porcentaje de aciertos solo sirve
si se compara con el equilibrio que fija el precio pagado; por eso aquí se mide el
dinero por apuesta y no el acierto.

Convención (la del bloc y la del registro del operador): al comprar un lado a un
precio p con 1 USDT, si acierta se cobra 0,98 / p; si falla se pierde 1 USDT.
Ganancia por apuesta: r = 0,98/p - 1 si acierta; r = -1 si falla.

No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono y no
escribe nada salvo el JSON que se pida con --json.
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from statistics import NormalDist, mean, stdev

PAGO = 0.98
PRECIO_MIN, PRECIO_MAX = 0.01, 0.99
SI = {"1", "1.0", "true", "si", "sí", "s", "yes", "y", "acierto"}
NO = {"0", "0.0", "false", "no", "n", "fallo"}
ETIQUETAS = {
    "gana": "GANA DINERO (demostrado)",
    "pierde": "PIERDE DINERO (demostrado)",
    "no": "NO DEMOSTRADO",
    "poca": "MUESTRA INSUFICIENTE",
}


def leer_acierto(valor):
    t = str(valor).strip().lower()
    if t in SI:
        return 1
    if t in NO:
        return 0
    return None


def leer_registro(ruta):
    """Devuelve (filas, malas). filas: lista de (estrategia, precio, acierto).
    malas: lista de (linea, motivo). Las filas malas se cuentan, no se descartan en silencio."""
    filas, malas = [], []
    ext = os.path.splitext(ruta)[1].lower()
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        if ext == ".csv":
            origen = ((i, fila) for i, fila in enumerate(csv.DictReader(f), start=2))
        else:
            def _jsonl():
                for i, linea in enumerate(f, start=1):
                    if not linea.strip():
                        continue
                    try:
                        yield i, json.loads(linea)
                    except ValueError:
                        yield i, None
            origen = _jsonl()
        for i, fila in origen:
            if not isinstance(fila, dict):
                malas.append((i, "no es un registro JSON"))
                continue
            est = str(fila.get("estrategia", "")).strip()
            if not est:
                malas.append((i, "sin estrategia"))
                continue
            try:
                p = float(str(fila.get("precio", "")).strip().replace(",", "."))
            except ValueError:
                malas.append((i, "precio no numérico"))
                continue
            if not (PRECIO_MIN <= p <= PRECIO_MAX):
                malas.append((i, "precio fuera de 0,01 a 0,99: %s" % p))
                continue
            w = leer_acierto(fila.get("acierto", ""))
            if w is None:
                malas.append((i, "acierto no es 1/0 ni sí/no"))
                continue
            filas.append((est, p, w))
    return filas, malas


def remuestreo(valores, B, alfa, semilla):
    """Límites bootstrap (percentiles) de la media, unilaterales a `alfa`."""
    rng = random.Random(semilla)
    n = len(valores)
    medias = sorted(sum(rng.choices(valores, k=n)) / n for _ in range(B))
    inf = medias[max(0, int(math.floor(alfa * B)))]
    sup = medias[min(B - 1, int(math.ceil((1 - alfa) * B)) - 1)]
    return inf, sup


def evaluar(pares, k=1, alfa=0.05, minimo=100, pago=PAGO, B=2000, semilla=20261120, apuesta=1.0):
    """pares: lista de (precio, acierto) de UNA estrategia.
    k: número de estrategias comparadas (corrección Bonferroni sobre alfa).
    Devuelve un dict con las cifras y la decisión."""
    n = len(pares)
    aciertos = sum(w for _, w in pares)
    r = [(pago / p - 1.0) if w else -1.0 for p, w in pares]
    por_usdt = mean(r)
    res = {
        "n": n,
        "aciertos": aciertos,
        "tasa": aciertos / n,
        "precio_medio": mean(p for p, _ in pares),
        # Acierto que deja la ganancia en cero a estos precios: 1 / media(pago/p).
        "equilibrio": 1.0 / mean(pago / p for p, _ in pares),
        "usdt_por_apuesta": por_usdt,
        "neto_usdt": apuesta * sum(r),
        "alfa_por_estrategia": alfa / max(1, k),
    }
    if n < minimo:
        res["decision"] = ETIQUETAS["poca"]
        return res
    se = (stdev(r) if n > 1 else 0.0) / math.sqrt(n)
    z = NormalDist().inv_cdf(1 - res["alfa_por_estrategia"])
    res["inf_normal"] = por_usdt - z * se
    res["sup_normal"] = por_usdt + z * se
    res["inf_boot"], res["sup_boot"] = remuestreo(r, B, res["alfa_por_estrategia"], semilla)
    if res["inf_normal"] > 0 and res["inf_boot"] > 0:
        res["decision"] = ETIQUETAS["gana"]
    elif res["sup_normal"] < 0 and res["sup_boot"] < 0:
        res["decision"] = ETIQUETAS["pierde"]
    else:
        res["decision"] = ETIQUETAS["no"]
    return res


def agrupar(filas):
    grupos = {}
    for est, p, w in filas:
        grupos.setdefault(est, []).append((p, w))
    return grupos


def evaluar_registro(filas, alfa=0.05, minimo=100, pago=PAGO, B=2000, semilla=20261120, apuesta=1.0):
    grupos = agrupar(filas)
    k = len(grupos)
    return {est: evaluar(par, k=k, alfa=alfa, minimo=minimo, pago=pago, B=B, semilla=semilla, apuesta=apuesta)
            for est, par in grupos.items()}


def tabla(resultados):
    cab = ("estrategia", "n", "acierto", "equilibrio", "precio", "USDT/apuesta", "IC95 inf-sup (boot)", "decisión")
    lineas = ["  ".join(cab)]
    for est, r in resultados.items():
        ic = "-"
        if "inf_boot" in r:
            ic = "%+.3f ; %+.3f" % (r["inf_boot"], r["sup_boot"])
        lineas.append("  ".join([
            est[:18].ljust(18),
            str(r["n"]).rjust(4),
            ("%.1f %%" % (100 * r["tasa"])).rjust(8),
            ("%.1f %%" % (100 * r["equilibrio"])).rjust(9),
            ("%.3f" % r["precio_medio"]).rjust(6),
            ("%+.3f" % r["usdt_por_apuesta"]).rjust(12),
            ic.rjust(20),
            r["decision"],
        ]))
    return "\n".join(lineas)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mide si cada estrategia gana dinero por apuesta (precio real, ganador oficial).")
    ap.add_argument("--registro", required=True, help="archivo .csv o .jsonl con una fila por apuesta resuelta")
    ap.add_argument("--alfa", type=float, default=0.05, help="error tolerado por el conjunto (antes de dividir entre estrategias)")
    ap.add_argument("--minimo", type=int, default=100, help="apuestas mínimas por estrategia para decidir")
    ap.add_argument("--pago", type=float, default=PAGO, help="cobro por USDT si acierta, sobre el precio (0,98 por defecto)")
    ap.add_argument("--apuesta", type=float, default=1.0, help="USDT por apuesta, solo para el neto en USDT")
    ap.add_argument("--remuestras", type=int, default=2000, help="remuestras bootstrap")
    ap.add_argument("--semilla", type=int, default=20261120)
    ap.add_argument("--json", help="guarda el resultado en este archivo JSON")
    a = ap.parse_args(argv)
    if a.minimo < 2 or not (0 < a.alfa < 1) or a.remuestras < 100:
        ap.error("--minimo debe ser al menos 2, --alfa entre 0 y 1 y --remuestras al menos 100")
    if not os.path.isfile(a.registro):
        ap.error("no existe el registro: %s" % a.registro)

    filas, malas = leer_registro(a.registro)
    print("Filas válidas: %d · filas malas (no entran): %d" % (len(filas), len(malas)))
    for linea, motivo in malas[:5]:
        print("  línea %d: %s" % (linea, motivo))
    if not filas:
        print("Sin filas válidas: no hay nada que medir.")
        return 2

    res = evaluar_registro(filas, alfa=a.alfa, minimo=a.minimo, pago=a.pago,
                           B=a.remuestras, semilla=a.semilla, apuesta=a.apuesta)
    print("Convención: acierta = %.2f / precio - 1 ; falla = -1 (por USDT). Corrección por %d estrategias, alfa %.3f."
          % (a.pago, len(res), a.alfa))
    print(tabla(res))

    # Dónde discrepan el porcentaje de aciertos y el dinero (la regla 18 de 25 mira solo el acierto).
    regla = [e for e, r in res.items() if r["tasa"] >= 0.72 and r["n"] >= 25]
    if regla:
        con_dinero = [e for e in regla if res[e]["usdt_por_apuesta"] > 0]
        print("Estrategias con acierto de 72 %% o más: %d · de ellas con ganancia por USDT positiva: %d"
              % (len(regla), len(con_dinero)))
    ganadoras = [e for e, r in res.items() if r["decision"] == ETIQUETAS["gana"]]
    print("Decisión final: %s" % (", ".join(ganadoras) if ganadoras else "ninguna estrategia demuestra ganancia de dinero"))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"malas": len(malas), "resultados": res}, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
