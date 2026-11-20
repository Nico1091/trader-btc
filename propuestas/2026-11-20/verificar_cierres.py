#!/usr/bin/env python3
"""Verificador de cierres de las binarias · propuesta del 20/11/2026.

Pregunta que responde: ¿el ganador que calcula el operador con velas de contado (la regla de
papel.py, _ganador_velas: apertura del primer minuto contra cierre del último) coincide con el
ganador OFICIAL de Binance en las mismas ventanas?

Por qué importa: las compras de papel con serie distinta de «papel» se liquidan con esa regla, y las
cifras de acierto de «56 % a 59 %» del bloc salen de velas y de precio supuesto. Si la regla no
coincide con el oficial, esas cifras no miden lo que dicen.

Usa solo la biblioteca estándar de Python (3.8 o superior). Las velas son públicas: no necesita
llaves. No escribe en el registro, no se conecta a la caja ni al teléfono y no envía órdenes.

Uso:
  python verificar_cierres.py --registro registro/ --velas velas.csv
  python verificar_cierres.py --registro registro/ --descargar 2026-11-17 2026-11-19 --guardar velas.csv
  python verificar_cierres.py --registro registro/20261118.jsonl --velas velas.csv --json resultado.json

Códigos de salida: 0 las velas sirven · 1 no sirven, indeciso o muestra insuficiente · 2 error de uso.
"""
import argparse
import calendar
import csv
import datetime as dt
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter

# Criterios fijados ANTES de ver ningún registro real (ver LEEME.md, sección «Criterio»).
MINIMO_VENTANAS = 200      # ventanas oficiales con velas para poder dar veredicto
COTA_SUSTITUTO = 0.02      # límite superior 95 % de la discordancia ≤ 2 %: las velas sirven
COTA_NO_SIRVE = 0.05       # límite inferior 95 % de la discordancia ≥ 5 %: no sirven

DURACIONES_MIN = (5, 15)   # ventanas que opera el operador
URL_VELAS = "https://data-api.binance.vision/api/v3/klines"   # datos públicos de Binance, sin llave
SIMBOLO = "BTCUSDT"
Z95 = 1.959964


class ErrorUso(Exception):
    """La entrada no sirve: ruta inexistente, columnas que faltan o nada que leer."""


# ----------------------------------------------------------------------------- velas

def leer_velas(ruta):
    """CSV con cabecera open_time_ms,open,close (el formato que guarda --guardar).
    Devuelve {inicio_del_minuto_en_segundos: (apertura, cierre)}."""
    velas = {}
    with open(ruta, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        falta = {"open_time_ms", "open", "close"} - set(lector.fieldnames or [])
        if falta:
            raise ErrorUso(f"{ruta}: faltan columnas {sorted(falta)}")
        for num, fila in enumerate(lector, 2):
            try:
                t = int(fila["open_time_ms"]) // 1000
                velas[t] = (float(fila["open"]), float(fila["close"]))
            except (TypeError, ValueError):
                raise ErrorUso(f"{ruta}, línea {num}: valor que no se lee como número")
    return velas


def guardar_velas(velas, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["open_time_ms", "open", "close"])
        for t in sorted(velas):
            o, c = velas[t]
            escritor.writerow([t * 1000, f"{o:.8f}", f"{c:.8f}"])


def descargar_velas(desde_s, hasta_s, simbolo=SIMBOLO, pedir=None):
    """Velas de 1 minuto públicas de [desde_s, hasta_s), en segundos Unix. Pagina de 1.000 en 1.000.
    pedir(url) -> lista de velas crudas de Binance; por defecto usa urllib. Se puede sustituir en pruebas."""
    if pedir is None:
        def pedir(url):
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
    velas = {}
    cursor, fin = desde_s * 1000, hasta_s * 1000
    while cursor < fin:
        consulta = urllib.parse.urlencode({"symbol": simbolo, "interval": "1m", "startTime": cursor,
                                           "endTime": fin - 1, "limit": 1000})
        datos = pedir(f"{URL_VELAS}?{consulta}")
        if not datos:
            break
        for k in datos:
            velas[int(k[0]) // 1000] = (float(k[1]), float(k[4]))
        siguiente = int(datos[-1][0]) + 60_000
        if siguiente <= cursor:       # defensa: la API no avanzó
            break
        cursor = siguiente
    return velas


def ganador_velas(velas, t, W):
    """Regla de papel.py (_ganador_velas). 1 si sube, -1 si baja, 0 si empata; None si falta algún minuto
    de la ventana que empieza en t (segundos Unix)."""
    dur = W * 60
    if any((t + 60 * i) not in velas for i in range(W)):
        return None
    apertura = velas[t][0]
    cierre = velas[t + dur - 60][1]
    return 1 if cierre > apertura else (-1 if cierre < apertura else 0)


# ----------------------------------------------------------------------------- registro

def _archivos(entradas):
    rutas = []
    for e in entradas:
        if os.path.isdir(e):
            rutas += sorted(os.path.join(e, n) for n in os.listdir(e) if n.endswith(".jsonl"))
        elif os.path.isfile(e):
            rutas.append(e)
        else:
            raise ErrorUso(f"no existe: {e}")
    if not rutas:
        raise ErrorUso("no hay archivos .jsonl que leer")
    return rutas


def leer_registro(entradas):
    """Lee las filas tipo «resultado» del registro del operador.
    Devuelve (resultados, cuentas). resultados: dicts con serie, fuente, W, t, ganador.
    Las filas que no se leen se cuentan en cuentas['malas'], no se descartan en silencio."""
    resultados, cuentas = [], Counter()
    for ruta in _archivos(entradas):
        with open(ruta, encoding="utf-8") as f:
            for texto in f:
                if not texto.strip():
                    continue
                try:
                    d = json.loads(texto)
                except json.JSONDecodeError:
                    cuentas["malas"] += 1
                    continue
                if not isinstance(d, dict) or d.get("tipo") != "resultado":
                    continue
                W, t, g = d.get("W"), d.get("t"), d.get("ganador")
                ok_ventana = isinstance(W, int) and isinstance(t, int) and not isinstance(W, bool)
                if not ok_ventana or g not in (1, -1, 0, None):
                    cuentas["malas"] += 1
                    continue
                resultados.append({"serie": d.get("serie", "papel"), "fuente": d.get("fuente", ""),
                                   "W": W, "t": t, "ganador": g})
    return resultados, cuentas


def quitar_conflictos(resultados, cuentas):
    """Una ventana con dos ganadores distintos en el registro no se compara: se cuenta y se deja fuera."""
    vistos, conflictos = {}, set()
    for r in resultados:
        clave = (r["serie"], r["fuente"], r["W"], r["t"])
        if clave in vistos and vistos[clave] != r["ganador"]:
            conflictos.add(clave)
        vistos[clave] = r["ganador"]
    cuentas["conflictos"] = len(conflictos)
    return [r for r in resultados if (r["serie"], r["fuente"], r["W"], r["t"]) not in conflictos]


# ----------------------------------------------------------------------------- análisis

def wilson(x, n, z=Z95):
    """Intervalo de Wilson al 95 % para x aciertos de n."""
    if n == 0:
        return (0.0, 1.0)
    p = x / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def analizar(resultados, velas, cuentas):
    """Compara cada ganador registrado con el que sale de las velas, en la misma ventana."""
    tabla = {W: Counter() for W in DURACIONES_MIN}
    discordancias = []
    for r in resultados:
        W, t, g = r["W"], r["t"], r["ganador"]
        if g is None:
            cuentas["sin_ganador"] += 1
            continue
        if W not in tabla:
            cuentas["otra_duracion"] += 1
            continue
        if t % (W * 60) != 0:
            cuentas["desalineadas"] += 1
            continue
        calc = ganador_velas(velas, t, W)
        if r["fuente"] == "oficial":
            if calc is None:
                tabla[W]["sin_velas"] += 1
            elif calc == g:
                tabla[W]["coinciden"] += 1
            else:
                tabla[W]["difieren"] += 1
                discordancias.append({"W": W, "t": t, "oficial": g, "velas": calc})
        elif r["fuente"] == "velas":
            # Lo que el operador anotó al liquidar con velas: debe ser la misma regla.
            if calc is None:
                cuentas["velas_sin_datos"] += 1
            else:
                cuentas["velas_coinciden" if calc == g else "velas_difieren"] += 1
    return tabla, discordancias


def veredicto(n, discordancias):
    """Veredicto con los criterios fijados al principio. Devuelve (texto, codigo_de_salida)."""
    if n < MINIMO_VENTANAS:
        return (f"MUESTRA INSUFICIENTE: {n} ventanas oficiales con velas (hacen falta {MINIMO_VENTANAS}). "
                "No se puede decidir.", 1)
    lo, hi = wilson(discordancias, n)
    if hi <= COTA_SUSTITUTO:
        return ("LAS VELAS SIRVEN: con 95 % de confianza la regla de velas difiere del oficial en como mucho "
                f"{100 * hi:.1f} % de las ventanas.", 0)
    if lo >= COTA_NO_SIRVE:
        return (f"LAS VELAS NO SIRVEN: con 95 % de confianza la regla de velas difiere del oficial en al menos "
                f"{100 * lo:.1f} % de las ventanas. Las cifras de acierto medidas con velas están sesgadas.", 1)
    return (f"INDECISO: la discordancia está entre {100 * lo:.1f} % y {100 * hi:.1f} % con 95 % de confianza. "
            "Hace falta más muestra.", 1)


def informe(tabla, discordancias, cuentas, velas_n):
    n_total = sum(c["coinciden"] + c["difieren"] for c in tabla.values())
    n_dis = sum(c["difieren"] for c in tabla.values())
    lo, hi = wilson(n_dis, n_total)
    texto, codigo = veredicto(n_total, n_dis)
    lineas = [
        "VERIFICADOR DE CIERRES · velas contra ganador oficial",
        f"Velas leídas: {velas_n} minutos.",
        f"Ventanas oficiales comparadas: {n_total}  (coinciden {n_total - n_dis}, difieren {n_dis})",
        f"Discordancia: {100 * n_dis / n_total if n_total else 0:.2f} %  (IC 95 %: {100 * lo:.2f} a {100 * hi:.2f} %)"
        if n_total else "Discordancia: sin datos",
    ]
    for W in DURACIONES_MIN:
        c = tabla[W]
        n_w = c["coinciden"] + c["difieren"]
        lineas.append(f"  W={W} min: comparadas {n_w}, coinciden {c['coinciden']}, difieren {c['difieren']}, "
                      f"sin velas {c['sin_velas']}")
    lineas += [
        f"Sin ganador oficial (no cuentan): {cuentas['sin_ganador']}",
        f"Ventanas desalineadas (no se comparan): {cuentas['desalineadas']}",
        f"Otra duración de ventana (no se compara): {cuentas['otra_duracion']}",
        f"Conflictos dentro del registro (no se comparan): {cuentas['conflictos']}",
        f"Filas de velas del operador recalculadas: coinciden {cuentas['velas_coinciden']}, "
        f"difieren {cuentas['velas_difieren']}, sin datos {cuentas['velas_sin_datos']}",
        f"Filas malas del registro (no se leyeron): {cuentas['malas']}",
        "",
        "VEREDICTO: " + texto,
    ]
    if discordancias:
        lineas += ["", "Primeras discordancias (W, inicio UTC, oficial, velas):"]
        for d in discordancias[:10]:
            inicio = dt.datetime.fromtimestamp(d["t"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
            lineas.append(f"  W={d['W']}  {inicio}  oficial {d['oficial']:+d}  velas {d['velas']:+d}")
    return "\n".join(lineas), codigo, {"comparadas": n_total, "difieren": n_dis,
                                       "discordancia": (n_dis / n_total) if n_total else None,
                                       "ic95": [lo, hi], "veredicto": texto}


def verificar(registro, velas):
    """Función principal, sin entrada ni salida de pantalla. Devuelve (texto, codigo, datos_json)."""
    resultados, cuentas = leer_registro(registro)
    resultados = quitar_conflictos(resultados, cuentas)
    tabla, discordancias = analizar(resultados, velas, cuentas)
    return informe(tabla, discordancias, cuentas, len(velas))


# ----------------------------------------------------------------------------- línea de comandos

def _fecha_a_segundos(texto):
    try:
        d = dt.datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        raise ErrorUso(f"fecha que no se lee (use AAAA-MM-DD): {texto}")
    return calendar.timegm(d.timetuple())


def principal(argv=None):
    p = argparse.ArgumentParser(description="Compara el ganador de velas con el oficial de cada ventana.")
    p.add_argument("--registro", required=True, nargs="+", help="archivo .jsonl o carpeta con registro/*.jsonl")
    fuente = p.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--velas", help="CSV con open_time_ms,open,close")
    fuente.add_argument("--descargar", nargs=2, metavar=("DESDE", "HASTA"),
                        help="días UTC AAAA-MM-DD; descarga velas públicas de [DESDE, HASTA)")
    p.add_argument("--guardar", help="con --descargar: dónde guardar las velas en CSV")
    p.add_argument("--json", help="escribe el resultado en este archivo JSON")
    a = p.parse_args(argv)
    try:
        if a.descargar:
            velas = descargar_velas(_fecha_a_segundos(a.descargar[0]), _fecha_a_segundos(a.descargar[1]))
            if a.guardar:
                guardar_velas(velas, a.guardar)
        else:
            if a.guardar:
                raise ErrorUso("--guardar solo sirve con --descargar")
            velas = leer_velas(a.velas)
        texto, codigo, datos = verificar(a.registro, velas)
    except (ErrorUso, OSError) as ex:
        print(f"Error: {ex}", file=sys.stderr)
        return 2
    print(texto)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    return codigo


if __name__ == "__main__":
    sys.exit(principal())
