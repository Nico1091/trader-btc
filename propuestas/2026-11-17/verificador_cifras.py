#!/usr/bin/env python3
"""Verificador de cifras de binarias sobre las pruebas reales del repositorio.

Lee las pruebas a ciegas (archivos *_apuestas.csv de binarias/pruebas/) y, para
cada una, calcula con su intervalo de confianza:

  - el acierto (un empate cuenta como fallo, como dice el bloc);
  - el acierto si la entrada llega 60 s tarde, cuando el archivo lo trae;
  - el equilibrio para cada precio de compra supuesto: p / cobro;
  - el valor esperado por USDT apostado: acierto * cobro / p - 1;
  - el precio máximo de compra que aún da ventaja (con centro y con IC 95 %).

Solo usa la biblioteca estándar de Python 3.8 o superior. No se conecta a
Binance, no envía órdenes y no escribe fuera del archivo que se le pida.

Convención de cobro: si acierta, la apuesta paga cobro / precio por cada USDT
(cobro = 0,98 según el bloc, «Ganar» = 0,98 / precio). Por eso el equilibrio
es precio / cobro. Con el pago fijo de 0,85 del bloc, el equilibrio es 54,1 %.

Uso:
    python3 verificador_cifras.py CARPETA_O_ARCHIVOS... [--precio 0.50 0.544 ...]
                                  [--cobro 0.98] [--json salida.json]

Códigos de salida: 0 correcto; 2 algún archivo no se puede leer o trae
valores que no entiende (no se ignoran en silencio).
"""

import argparse
import csv
import glob
import json
import math
import os
import sys

VALORES_VALIDOS = {"acierta", "falla", "empate"}
COLUMNA_RESULTADO = "resultado"
COLUMNA_60S = "resultado_60s_tarde"
Z_95 = 1.96
PRECIOS_POR_DEFECTO = [0.50, 0.544, 0.55, 0.60]
COBRO_POR_DEFECTO = 0.98


class ErrorArchivo(Exception):
    """Un archivo no se puede leer o trae datos que no se entienden."""


def wilson(aciertos, n, z=Z_95):
    """Intervalo de Wilson de una proporción. Devuelve (inferior, superior)."""
    if n == 0:
        return 0.0, 1.0
    p = aciertos / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centro - mitad), min(1.0, centro + mitad)


def equilibrio(precio, cobro):
    """Acierto mínimo para no perder comprando a ese precio."""
    return precio / cobro


def valor_esperado(acierto, precio, cobro):
    """Ganancia esperada por USDT apostado (negativa si pierde)."""
    return acierto * cobro / precio - 1


def veredicto(ic_inf, ic_sup, eq):
    if ic_inf > eq:
        return "ventaja demostrada (IC 95 %)"
    if ic_sup < eq:
        return "pérdida demostrada (IC 95 %)"
    return "sin decidir"


def leer_csv(ruta):
    """Devuelve (filas, tiene_60s). Detecta el separador ; o ,."""
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            cabecera = f.readline()
            f.seek(0)
            delim = ";" if cabecera.count(";") >= cabecera.count(",") else ","
            filas = list(csv.DictReader(f, delimiter=delim))
    except OSError as e:
        raise ErrorArchivo(f"no se puede leer: {e}") from e
    if not filas:
        raise ErrorArchivo("el archivo no tiene filas")
    columnas = set(filas[0].keys())
    if COLUMNA_RESULTADO not in columnas:
        raise ErrorArchivo(f"falta la columna «{COLUMNA_RESULTADO}»")
    tiene_60s = COLUMNA_60S in columnas
    return filas, tiene_60s


def contar(filas, columna):
    """Cuenta aciertos, fallos y empates. Lanza error si hay valores desconocidos."""
    cuenta = {"acierta": 0, "falla": 0, "empate": 0}
    desconocidos = {}
    for fila in filas:
        valor = (fila.get(columna) or "").strip().lower()
        if valor in VALORES_VALIDOS:
            cuenta[valor] += 1
        else:
            desconocidos[valor] = desconocidos.get(valor, 0) + 1
    if desconocidos:
        raise ErrorArchivo(f"valores que no se entienden en «{columna}»: {desconocidos}")
    return cuenta


def analizar_archivo(ruta, precios, cobro):
    filas, tiene_60s = leer_csv(ruta)
    cuenta = contar(filas, COLUMNA_RESULTADO)
    n = len(filas)
    aciertos = cuenta["acierta"]
    acierto = aciertos / n
    ic_inf, ic_sup = wilson(aciertos, n)

    res = {
        "archivo": os.path.basename(ruta),
        "n": n,
        "aciertos": aciertos,
        "fallos": cuenta["falla"],
        "empates": cuenta["empate"],
        "acierto": acierto,
        "ic95": [ic_inf, ic_sup],
        "acierto_60s": None,
        "ic95_60s": None,
        "precios": [],
        "pmax_centro": cobro * acierto,
        "pmax_ic95": cobro * ic_inf,
    }

    if tiene_60s:
        c60 = contar(filas, COLUMNA_60S)
        a60 = c60["acierta"] / n
        i60_inf, i60_sup = wilson(c60["acierta"], n)
        res["acierto_60s"] = a60
        res["ic95_60s"] = [i60_inf, i60_sup]
        res["pmax_ic95_60s"] = cobro * i60_inf

    for p in precios:
        eq = equilibrio(p, cobro)
        entrada = {
            "precio": p,
            "equilibrio": eq,
            "ev": valor_esperado(acierto, p, cobro),
            "veredicto": veredicto(ic_inf, ic_sup, eq),
        }
        if tiene_60s:
            entrada["ev_60s"] = valor_esperado(res["acierto_60s"], p, cobro)
            entrada["veredicto_60s"] = veredicto(i60_inf, i60_sup, eq)
        res["precios"].append(entrada)
    return res


def pct(x):
    return f"{x * 100:.2f} %".replace(".", ",")


def pct1(x):
    return f"{x * 100:+.2f} %".replace(".", ",")


def imprimir(res):
    print(f"\n== {res['archivo']}")
    print(f"   apuestas {res['n']} · aciertos {res['aciertos']} · fallos {res['fallos']} · "
          f"empates {res['empates']} (cuentan como fallo)")
    print(f"   acierto {pct(res['acierto'])}  IC 95 % [{pct(res['ic95'][0])}, {pct(res['ic95'][1])}]")
    if res["acierto_60s"] is not None:
        i = res["ic95_60s"]
        dif = (res["acierto_60s"] - res["acierto"]) * 100
        dif_txt = f"{dif:+.2f}".replace(".", ",")
        print(f"   entrada 60 s tarde: acierto {pct(res['acierto_60s'])}  "
              f"IC 95 % [{pct(i[0])}, {pct(i[1])}]  diferencia {dif_txt} puntos")
    print(f"   precio máximo de compra con el centro: {res['pmax_centro']:.3f} · "
          f"con IC 95 %: {res['pmax_ic95']:.3f}".replace(".", ","))
    if res["acierto_60s"] is not None:
        print(f"   precio máximo con IC 95 % y entrada 60 s tarde: "
              f"{res['pmax_ic95_60s']:.3f}".replace(".", ","))
    cab = f"   {'precio':>7} {'equilibrio':>11} {'EV':>9} {'veredicto':<32}"
    if res["acierto_60s"] is not None:
        cab += f" {'EV 60 s':>9} {'veredicto 60 s':<32}"
    print(cab)
    for e in res["precios"]:
        precio_txt = f"{e['precio']:.3f}".replace(".", ",")
        linea = (f"   {precio_txt:>7} {pct(e['equilibrio']):>11} "
                 f"{pct1(e['ev']):>9} {e['veredicto']:<32}")
        if "ev_60s" in e:
            linea += f" {pct1(e['ev_60s']):>9} {e['veredicto_60s']:<32}"
        print(linea)


def expandir(entradas):
    rutas = []
    for entrada in entradas:
        if os.path.isdir(entrada):
            rutas.extend(sorted(glob.glob(os.path.join(entrada, "*_apuestas.csv"))))
        else:
            rutas.extend(sorted(glob.glob(entrada)) or [entrada])
    return rutas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("entradas", nargs="+", help="carpeta con *_apuestas.csv o archivos")
    ap.add_argument("--precio", nargs="+", type=float, default=PRECIOS_POR_DEFECTO,
                    help="precios de compra a evaluar, entre 0 y 1 (por defecto 0,50 0,544 0,55 0,60)")
    ap.add_argument("--cobro", type=float, default=COBRO_POR_DEFECTO,
                    help="cobro por USDT si acierta, sin el precio (por defecto 0,98)")
    ap.add_argument("--json", metavar="ARCHIVO", help="escribir también los resultados en JSON")
    args = ap.parse_args(argv)

    if not (0 < args.cobro <= 1):
        print("el cobro debe estar entre 0 y 1", file=sys.stderr)
        return 2
    for p in args.precio:
        if not (0 < p < 1):
            print(f"precio fuera de rango: {p}", file=sys.stderr)
            return 2

    rutas = expandir(args.entradas)
    if not rutas:
        print("no se encontraron archivos *_apuestas.csv", file=sys.stderr)
        return 2

    resultados, errores = [], []
    for ruta in rutas:
        try:
            resultados.append(analizar_archivo(ruta, args.precio, args.cobro))
        except ErrorArchivo as e:
            errores.append(f"{os.path.basename(ruta)}: {e}")

    for r in resultados:
        imprimir(r)
    for e in errores:
        print(f"ERROR {e}", file=sys.stderr)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"cobro": args.cobro, "precios": args.precio,
                       "resultados": resultados, "errores": errores},
                      f, ensure_ascii=False, indent=2)
    return 2 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
