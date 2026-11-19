#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba secuencial de ventaja para las binarias (razón de verosimilitud de Wald).

Pregunta que contesta: ¿se puede declarar ventaja de una estrategia si la cuenta
se mira después de cada apuesta? Con los límites de esta prueba sí, porque la
probabilidad de declarar ventaja por azar queda acotada por --alfa aunque se
mire siempre (y, con varias estrategias, la corrección de Bonferroni la reparte).

Compara con la regla que hoy arma el operador (18 aciertos en 25, a cada minuto):
--simular muestra con qué frecuencia cada regla arma dinero real sin ventaja.

Convenciones del bloc: el pago es 0,98 por USDT, así que el equilibrio de una
apuesta a precio p es p / 0,98 (igual que el evaluador del 17/11).

Solo biblioteca estándar de Python 3.11 o superior. No se conecta a nada, no
envía órdenes y no lee ni escribe archivos del operador ni de la caja.
"""
import argparse
import csv
import datetime
import io
import json
import math
import random
import sys
from collections import deque
from statistics import median

COMISION = 0.02   # pago 0,98 por USDT, como en el bloc
DELTA = 0.03      # ventaja mínima que se quiere detectar: 3 puntos sobre el equilibrio
ALFA = 0.05       # probabilidad total de declarar ventaja por azar (todas las estrategias, todas las miradas)
BETA = 0.20       # probabilidad de descartar una ventaja de tamaño DELTA (límite inferior)


class ErrorDatos(Exception):
    """Dato o parámetro que no se puede usar. Siempre dice la línea o el parámetro."""


# ---------------------------------------------------------------- matemáticas

def equilibrio(precio, comision=COMISION):
    """Acierto mínimo para no perder con ese precio: precio / (1 - comisión)."""
    return precio / (1.0 - comision)


def kl(p1, p0):
    """Divergencia de Kullback-Leibler entre dos Bernoulli: información media por apuesta."""
    return p1 * math.log(p1 / p0) + (1.0 - p1) * math.log((1.0 - p1) / (1.0 - p0))


def incremento(precio, acierto, delta, comision=COMISION):
    """Cambio del logaritmo de la razón de verosimilitud (H1 contra H0) por una apuesta.

    H0: la apuesta acierta con la probabilidad del equilibrio (sin ventaja).
    H1: acierta con el equilibrio más delta.
    Si la probabilidad real es menor que la de H0, la esperanza de la razón es
    menor que 1; por eso el límite de Wald vale también para H0 compuesta
    («sin ventaja» = acierto igual o inferior al equilibrio).
    """
    p0 = equilibrio(precio, comision)
    p1 = p0 + delta
    if acierto:
        return math.log(p1 / p0)
    return math.log((1.0 - p1) / (1.0 - p0))


def umbrales(alfa, beta, familia):
    """Límites del logaritmo de la razón.

    Con K estrategias cada una usa alfa/K (Bonferroni): la probabilidad de que
    cualquiera declare ventaja por azar queda por debajo de alfa.
    Devuelve (límite para declarar ventaja, límite para descartarla).
    """
    return math.log(familia / alfa), math.log(beta)


# ---------------------------------------------------------------- lectura

def cargar_apuestas(texto, formato="csv", delta=DELTA, comision=COMISION):
    """Lee apuestas resueltas, en orden cronológico. Cualquier fila mala detiene la lectura."""
    if formato == "jsonl":
        filas = []
        for num, linea in enumerate(io.StringIO(texto), 1):
            if not linea.strip():
                continue
            try:
                filas.append((num, json.loads(linea)))
            except json.JSONDecodeError as e:
                raise ErrorDatos(f"línea {num}: JSON no válido ({e.msg})")
    else:
        lector = csv.DictReader(io.StringIO(texto))
        if not {"estrategia", "precio", "acierto"} <= set(lector.fieldnames or []):
            raise ErrorDatos("el encabezado debe incluir estrategia, precio y acierto")
        filas = [(lector.line_num, fila) for fila in lector]

    apuestas = []
    for num, fila in filas:
        estrategia = str(fila.get("estrategia") or "").strip()
        if not estrategia:
            raise ErrorDatos(f"línea {num}: falta la estrategia")
        try:
            precio = float(str(fila.get("precio")).replace(",", "."))
        except ValueError:
            raise ErrorDatos(f"línea {num}: el precio no es un número")
        if not (0.0 < precio < 1.0):
            raise ErrorDatos(f"línea {num}: el precio debe estar entre 0 y 1 (se leyó {precio}); use 0,51 o 0.51")
        if equilibrio(precio, comision) + delta >= 1.0:
            raise ErrorDatos(f"línea {num}: con precio {precio} no cabe una ventaja de {delta}")
        acierto = fila.get("acierto")
        acierto = str(int(acierto)) if isinstance(acierto, bool) else str(acierto).strip()
        if acierto not in ("0", "1"):
            raise ErrorDatos(f"línea {num}: el acierto debe ser 1 o 0 (se leyó {acierto!r})")
        apuestas.append({
            "estrategia": estrategia,
            "precio": precio,
            "acierto": acierto == "1",
            "fecha": str(fila.get("fecha") or ""),
        })
    return apuestas


# ---------------------------------------------------------------- análisis real

def analizar(apuestas, delta=DELTA, alfa=ALFA, beta=BETA, comision=COMISION):
    """Recorre cada estrategia apuesta a apuesta y para en el primer límite que cruza."""
    por_estrategia = {}
    for a in apuestas:
        por_estrategia.setdefault(a["estrategia"], []).append(a)
    arriba, abajo = umbrales(alfa, beta, len(por_estrategia))

    resultados = []
    for nombre, lista in por_estrategia.items():
        llr = 0.0
        estado = None
        decidida_en = None
        suma_kl = 0.0
        suma_eq = 0.0
        aciertos = 0
        for i, a in enumerate(lista, 1):
            p0 = equilibrio(a["precio"], comision)
            suma_kl += kl(p0 + delta, p0)
            suma_eq += p0
            aciertos += a["acierto"]
            if estado is None:
                llr += incremento(a["precio"], a["acierto"], delta, comision)
                if llr >= arriba:
                    estado, decidida_en = "VENTAJA", i
                elif llr <= abajo:
                    estado, decidida_en = "SIN VENTAJA", i
        n = len(lista)
        kl_medio = suma_kl / n
        falta = None
        if estado is None:
            falta = math.ceil(max(0.0, arriba - llr) / kl_medio)
        resultados.append({
            "estrategia": nombre,
            "apuestas": n,
            "aciertos": aciertos,
            "acierto": aciertos / n,
            "equilibrio": suma_eq / n,
            "log_razon": llr,
            "estado": estado or "ABIERTA",
            "decidida_en": decidida_en,
            "faltan_aprox": falta,
        })
    return {
        "delta": delta,
        "alfa": alfa,
        "beta": beta,
        "estrategias": len(por_estrategia),
        "limite_ventaja": arriba,
        "limite_inutilidad": abajo,
        "resultados": resultados,
    }


# ---------------------------------------------------------------- simulación

def simular(delta=DELTA, alfa=ALFA, beta=BETA, comision=COMISION, K=5, horizonte=1000,
            reps=500, semilla=1, ventaja_real=0.0, pmin=0.45, pmax=0.55,
            ventana=25, minimo=18):
    """Compara la regla actual con la prueba secuencial sobre las mismas apuestas.

    Cada réplica tiene K estrategias independientes con `horizonte` apuestas.
    Regla actual: `minimo` aciertos en las últimas `ventana`, en cualquiera de las K,
    mirado después de cada apuesta. Prueba secuencial: límite superior de
    `umbrales` por estrategia, con alfa repartido entre las K.
    La probabilidad real de cada apuesta es el equilibrio de su precio más
    `ventaja_real` (0 = sin ventaja).
    """
    rnd = random.Random(semilla)
    arriba, abajo = umbrales(alfa, beta, K)
    reglas = ("actual", "secuencial")
    armo = {r: 0 for r in reglas}
    cuando = {r: [] for r in reglas}
    for _ in range(reps):
        primero = {r: None for r in reglas}
        for _k in range(K):
            ventana_q = deque(maxlen=ventana)
            llr = 0.0
            decidida = False
            f = {r: None for r in reglas}
            for n in range(1, horizonte + 1):
                precio = rnd.uniform(pmin, pmax)
                acierto = rnd.random() < equilibrio(precio, comision) + ventaja_real
                ventana_q.append(1 if acierto else 0)
                if f["actual"] is None and len(ventana_q) == ventana and sum(ventana_q) >= minimo:
                    f["actual"] = n
                if not decidida:
                    llr += incremento(precio, acierto, delta, comision)
                    if llr >= arriba:
                        f["secuencial"] = n
                        decidida = True
                    elif llr <= abajo:
                        decidida = True
                if f["actual"] is not None and decidida:
                    break
            for r in reglas:
                if f[r] is not None and (primero[r] is None or f[r] < primero[r]):
                    primero[r] = f[r]
        for r in reglas:
            if primero[r] is not None:
                armo[r] += 1
                cuando[r].append(primero[r])
    return {
        r: {
            "p_armar": armo[r] / reps,
            "mediana_apuestas": median(cuando[r]) if cuando[r] else None,
        }
        for r in reglas
    }


# ---------------------------------------------------------------- salida

def pct(x):
    return "—" if x is None else f"{100 * x:.1f} %".replace(".", ",")


def num(x, dec=2):
    return "—" if x is None else f"{x:.{dec}f}".replace(".", ",")


def imprimir_analisis(res):
    print(f"Prueba secuencial · ventaja a detectar {num(res['delta'], 3)} · alfa total {num(res['alfa'], 2)}"
          f" · {res['estrategias']} estrategia(s)")
    print(f"Límite para declarar VENTAJA: {num(res['limite_ventaja'])} (razón {num(math.exp(res['limite_ventaja']), 1)} a 1)")
    print(f"Límite para descartar: {num(res['limite_inutilidad'])}")
    print()
    print(f"{'Estrategia':<12}{'Apuestas':>9}{'Acierto':>9}{'Equilib.':>9}{'Log-razón':>11}  {'Estado':<14}{'Decidida':>9}{'Faltan*':>9}")
    for r in res["resultados"]:
        print(f"{r['estrategia']:<12}{r['apuestas']:>9}{pct(r['acierto']):>9}{pct(r['equilibrio']):>9}"
              f"{num(r['log_razon']):>11}  {r['estado']:<14}{str(r['decidida_en'] or '—'):>9}"
              f"{str(r['faltan_aprox'] if r['faltan_aprox'] is not None else '—'):>9}")
    print()
    print("* Faltan: apuestas aproximadas que harían falta, si la ventaja real fuera exactamente la que se detecta.")
    print("  Las estrategias con «SIN VENTAJA» o «VENTAJA» ya quedaron decididas en la apuesta indicada.")


def imprimir_simulacion(args, datos):
    print(f"Simulación: {args.reps} réplicas · {args.estrategias} estrategias · {args.horizonte} apuestas cada una"
          f" · semilla {args.semilla} · ventaja a detectar {num(args.delta, 3)} · alfa {num(args.alfa, 2)}")
    print("Las estrategias se simulan independientes (ver LEEME: en el mercado real no lo son).")
    print()
    print(f"{'Ventaja real':<14}{'Regla actual: arma':>20}{'mediana':>10}{'Secuencial: arma':>20}{'mediana':>10}")
    for v, fila in datos:
        print(f"{'+' + num(v, 2) if v else 'ninguna':<14}"
              f"{pct(fila['actual']['p_armar']):>20}{num(fila['actual']['mediana_apuestas'], 0):>10}"
              f"{pct(fila['secuencial']['p_armar']):>20}{num(fila['secuencial']['mediana_apuestas'], 0):>10}")
    print()
    print("«arma» = proporción de réplicas en las que la regla arma en alguna de las K estrategias dentro del horizonte.")
    print("«mediana» = apuestas por estrategia hasta el primer armado (solo réplicas que arman).")


def escribir_ejemplo(ruta, semilla=7):
    """CSV SINTÉTICO: datos inventados con semilla fija. No son apuestas reales."""
    rnd = random.Random(semilla)
    inicio = datetime.date(2026, 10, 1)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["estrategia", "precio", "acierto", "fecha"])
        for ronda in range(60):
            fecha = (inicio + datetime.timedelta(days=ronda)).isoformat()
            for e in range(1, 6):
                nombre = f"E{e}"
                precio = round(rnd.uniform(0.45, 0.55), 2)
                p = equilibrio(precio) + (0.05 if nombre == "E4" else 0.0)
                escritor.writerow([nombre, f"{precio:.2f}", int(rnd.random() < p), fecha])
    return ruta


def validar(args):
    if not (0 < args.alfa < 1):
        raise ErrorDatos("--alfa debe estar entre 0 y 1")
    if not (0 < args.beta < 1):
        raise ErrorDatos("--beta debe estar entre 0 y 1")
    if args.delta <= 0:
        raise ErrorDatos("--delta debe ser mayor que 0")
    if not (0 <= args.comision < 1):
        raise ErrorDatos("--comision debe estar entre 0 y 1")
    if args.simular and (args.reps < 1 or args.horizonte < 25 or args.estrategias < 1):
        raise ErrorDatos("--reps y --estrategias deben ser al menos 1; --horizonte al menos 25")


def main(argv=None):
    p = argparse.ArgumentParser(description="Prueba secuencial de ventaja para las binarias.")
    p.add_argument("archivo", nargs="?", help="CSV (estrategia,precio,acierto,fecha) o JSONL, en orden cronológico")
    p.add_argument("--delta", type=float, default=DELTA, help="ventaja a detectar (por defecto 0,03)")
    p.add_argument("--alfa", type=float, default=ALFA, help="probabilidad total de falsa ventaja (por defecto 0,05)")
    p.add_argument("--beta", type=float, default=BETA, help="probabilidad de descartar una ventaja de delta (por defecto 0,20)")
    p.add_argument("--comision", type=float, default=COMISION, help="comisión; el pago es 1 - comisión (por defecto 0,02)")
    p.add_argument("--json", metavar="SALIDA", help="guarda el resultado en un JSON")
    p.add_argument("--simular", action="store_true", help="compara la regla actual 18 de 25 con la prueba secuencial")
    p.add_argument("--reps", type=int, default=500, help="réplicas de la simulación (por defecto 500)")
    p.add_argument("--horizonte", type=int, default=1000, help="apuestas por estrategia en la simulación (por defecto 1000)")
    p.add_argument("--estrategias", type=int, default=5, help="estrategias en la simulación (por defecto 5)")
    p.add_argument("--semilla", type=int, default=1, help="semilla de la simulación")
    p.add_argument("--ejemplo", metavar="RUTA", help="escribe un CSV SINTÉTICO de ejemplo y termina")
    args = p.parse_args(argv)

    try:
        validar(args)
        if args.ejemplo:
            print(f"Escrito el ejemplo SINTÉTICO (datos inventados): {escribir_ejemplo(args.ejemplo)}")
            return 0
        if args.simular:
            escenarios = (0.0, 0.03, 0.05, 0.10)
            datos = []
            for v in escenarios:
                datos.append((v, simular(delta=args.delta, alfa=args.alfa, beta=args.beta,
                                         comision=args.comision, K=args.estrategias,
                                         horizonte=args.horizonte, reps=args.reps,
                                         semilla=args.semilla, ventaja_real=v)))
            imprimir_simulacion(args, datos)
            if args.json:
                with open(args.json, "w", encoding="utf-8") as f:
                    json.dump([{"ventaja_real": v, **fila} for v, fila in datos], f, ensure_ascii=False, indent=2)
            return 0
        if not args.archivo:
            p.error("indique un archivo, --simular o --ejemplo")
        formato = "jsonl" if args.archivo.lower().endswith(".jsonl") else "csv"
        with open(args.archivo, encoding="utf-8-sig", newline="") as f:
            texto = f.read()
        apuestas = cargar_apuestas(texto, formato, args.delta, args.comision)
        if not apuestas:
            raise ErrorDatos("el archivo no tiene apuestas")
        res = analizar(apuestas, args.delta, args.alfa, args.beta, args.comision)
        imprimir_analisis(res)
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        return 0
    except (ErrorDatos, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
