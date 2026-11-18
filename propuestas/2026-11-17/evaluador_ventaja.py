#!/usr/bin/env python3
"""Evaluador de ventaja para las binarias (solo biblioteca estándar).

Responde una sola pregunta, con la regla fijada antes de ver los datos:
¿el acierto de cada estrategia supera el equilibrio por más de lo que explica el azar?

Entrada: apuestas ya resueltas, una por línea (CSV con encabezado o JSONL):
  estrategia  código o nombre de la estrategia (E1, E2, ...)
  precio      lo pagado por el lado comprado, entre 0 y 1 (0,51 o 0.51)
  acierto     1 si acertó, 0 si falló (en empate, 0)
  fecha       opcional; solo se muestra

Cuentas (las mismas convenciones del bloc: pago neto 0,98 / precio − 1 si acierta,
−1 si falla, equilibrio = precio / 0,98):
  por USDT apostado, la ganancia esperada con acierto p es  p × g/precio − 1,
  con g = 1 − comisión (0,98 por defecto).
  Equilibrio de un grupo = 1 / promedio(g/precio).

Veredicto con intervalo de Wilson al 95 %. Como se mira una estrategia entre muchas,
el nivel se corrige por la cantidad de estrategias (Bonferroni): elegir la mejor de
cien variantes da un número bueno por azar.
  PRUEBA INSUFICIENTE  menos de --min apuestas
  VENTAJA DEMOSTRADA   la cota inferior del acierto supera el equilibrio
  SIN VENTAJA          la cota superior queda por debajo del equilibrio
  NO DEMOSTRADA        el intervalo cruza el equilibrio: puede ser azar

Uso:
  python evaluador_ventaja.py apuestas.csv
  python evaluador_ventaja.py apuestas.jsonl --min 100 --comision 0.02 --json salida.json
"""

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from statistics import NormalDist


class ErrorDatos(Exception):
    """Un dato no se puede leer. Se detiene y dice la línea: no se corrige en silencio."""


@dataclass(frozen=True)
class Apuesta:
    linea: int
    estrategia: str
    precio: float
    acierto: int
    fecha: str


def _numero_precio(valor, linea):
    texto = str(valor).strip().replace(",", ".")
    try:
        precio = float(texto)
    except ValueError:
        raise ErrorDatos(f"línea {linea}: el precio «{valor}» no es un número")
    if not 0 < precio < 1:
        raise ErrorDatos(f"línea {linea}: el precio {precio} debe estar entre 0 y 1 "
                         f"(0,51 se escribe 0.51; 51 centavos no)")
    return precio


def _acierto(valor, linea):
    texto = str(valor).strip().lower()
    if texto in ("1", "true", "si", "sí"):
        return 1
    if texto in ("0", "false", "no"):
        return 0
    raise ErrorDatos(f"línea {linea}: el acierto «{valor}» debe ser 1 o 0")


def _apuesta(d, linea):
    estrategia = str(d.get("estrategia", "")).strip()
    if not estrategia:
        raise ErrorDatos(f"línea {linea}: falta la estrategia")
    return Apuesta(linea=linea,
                   estrategia=estrategia,
                   precio=_numero_precio(d.get("precio", ""), linea),
                   acierto=_acierto(d.get("acierto", ""), linea),
                   fecha=str(d.get("fecha", "") or "").strip())


def leer_apuestas(ruta):
    """Lee CSV (con encabezado) o JSONL. Cualquier fila mala detiene la lectura."""
    apuestas = []
    with open(ruta, encoding="utf-8", newline="") as f:
        if ruta.lower().endswith(".jsonl"):
            for num, linea in enumerate(f, 1):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    d = json.loads(linea)
                except json.JSONDecodeError as e:
                    raise ErrorDatos(f"línea {num}: JSON no válido ({e})")
                apuestas.append(_apuesta(d, num))
        else:
            for num, d in enumerate(csv.DictReader(f), 2):
                apuestas.append(_apuesta(d, num))
    if not apuestas:
        raise ErrorDatos("el archivo no tiene apuestas")
    return apuestas


def wilson(k, n, z):
    """Intervalo de Wilson para k aciertos de n con el valor z de la confianza."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    # Con k = 0 o k = n el borde es exacto (0 o 1); el redondeo no debe sacarlo de [0, 1].
    return max(0.0, centro - mitad), min(1.0, centro + mitad)


def z_corregido(estrategias, confianza=0.95):
    """z de dos colas para cada estrategia, con Bonferroni por la cantidad mirada."""
    k = max(1, estrategias)
    return NormalDist().inv_cdf(1 - (1 - confianza) / (2 * k))


def resumir(nombre, grupo, z, g, minimo):
    n = len(grupo)
    k = sum(a.acierto for a in grupo)
    pago = sum(g / a.precio for a in grupo) / n        # pago bruto medio por USDT
    equilibrio = 1 / pago
    lo, hi = wilson(k, n, z)
    p = k / n
    if n < minimo:
        veredicto = "PRUEBA INSUFICIENTE"
    elif lo > equilibrio:
        veredicto = "VENTAJA DEMOSTRADA"
    elif hi < equilibrio:
        veredicto = "SIN VENTAJA"
    else:
        veredicto = "NO DEMOSTRADA"
    faltan = None  # None: sin margen que medir (el acierto no supera el equilibrio)
    if p > equilibrio + 0.005:  # menos de medio punto de margen: la cifra no tiene sentido
        necesarias = math.ceil(z * z * p * (1 - p) / (p - equilibrio) ** 2)
        faltan = max(0, necesarias - n)
    return {
        "estrategia": nombre,
        "n": n,
        "aciertos": k,
        "acierto": p,
        "intervalo": (lo, hi),
        "precio_medio": sum(a.precio for a in grupo) / n,
        "equilibrio": equilibrio,
        "ganancia_esperada": p * pago - 1,
        "ganancia_inferior": lo * pago - 1,
        "ganancia_superior": hi * pago - 1,
        "veredicto": veredicto,
        "faltan": faltan,
    }


def evaluar(apuestas, minimo=100, comision=0.02):
    g = 1 - comision
    por_estrategia = {}
    for a in apuestas:
        por_estrategia.setdefault(a.estrategia, []).append(a)
    z = z_corregido(len(por_estrategia))
    filas = [resumir(nombre, grupo, z, g, minimo)
             for nombre, grupo in sorted(por_estrategia.items())]
    if len(por_estrategia) > 1:
        filas.append(resumir("TODAS", apuestas, z, g, minimo))
    return {"z": z, "comision": comision, "minimo": minimo, "filas": filas}


def _porcentaje(x):
    return f"{100 * x:.1f} %".replace(".", ",")


def _ganancia(x):
    return f"{100 * x:+.1f} %".replace(".", ",")


def texto_informe(res):
    lineas = [
        f"Evaluador de ventaja · comisión {100 * res['comision']:.0f} % · "
        f"confianza 95 % corregida (z = {res['z']:.2f}) · mínimo {res['minimo']} apuestas",
        "Ganancia esperada: por USDT apostado, con el acierto medido. La cota inferior usa el límite bajo del intervalo.",
        "",
        f"{'estrategia':<12}{'n':>6}{'acierto':>9}{'intervalo 95 %':>18}{'equilibrio':>12}"
        f"{'ganancia':>10}{'cota inf.':>11}  {'veredicto':<22}faltan (aprox.)",
    ]
    for f in res["filas"]:
        lo, hi = f["intervalo"]
        if f["faltan"] is None:
            faltan = "-"
        elif f["faltan"] > 100_000:
            faltan = "más de 100 000"
        else:
            faltan = f"{f['faltan']:,}".replace(",", " ")
        lineas.append(
            f"{f['estrategia']:<12}{f['n']:>6}{_porcentaje(f['acierto']):>9}"
            f"{(_porcentaje(lo) + '–' + _porcentaje(hi)):>18}{_porcentaje(f['equilibrio']):>12}"
            f"{_ganancia(f['ganancia_esperada']):>10}{_ganancia(f['ganancia_inferior']):>11}"
            f"  {f['veredicto']:<22}{faltan}"
        )
    lineas += [
        "",
        "Lectura: «VENTAJA DEMOSTRADA» solo con la cota inferior sobre el equilibrio.",
        "«Faltan» dice cuántas apuestas más hacen falta si el acierto se mantiene; es aproximado.",
        "Un veredicto con pocas apuestas no dice que la estrategia no sirva: dice que no hay prueba.",
    ]
    return "\n".join(lineas)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluador de ventaja de binarias (solo biblioteca estándar).")
    ap.add_argument("archivo", help="apuestas resueltas, en CSV o JSONL")
    ap.add_argument("--min", type=int, default=100, help="apuestas mínimas por estrategia (100 por defecto)")
    ap.add_argument("--comision", type=float, default=0.02, help="comisión sobre la ganancia (0,02 por defecto)")
    ap.add_argument("--json", metavar="SALIDA", help="guarda el resultado también en JSON")
    args = ap.parse_args(argv)
    if not 0 <= args.comision < 1:
        print("error: la comisión debe estar entre 0 y 1", file=sys.stderr)
        return 2
    try:
        apuestas = leer_apuestas(args.archivo)
    except (OSError, ErrorDatos) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    res = evaluar(apuestas, minimo=args.min, comision=args.comision)
    print(texto_informe(res))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
