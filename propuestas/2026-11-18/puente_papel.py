#!/usr/bin/env python3
"""Puente entre el registro de papel del operador de binarias y el evaluador de ventaja (18/11/2026).

Lee las filas que el operador escribe en registro/AAAAMMDD.jsonl y deja un CSV con las columnas
estrategia, precio, acierto, fecha: el formato que lee evaluador_ventaja.py (propuestas/2026-11-17/).

Qué cuenta como apuesta (leído del código del operador, rama binarias/plan-v7-2026-11-04, operador/papel.py):
- Fila de compra: tipo "llenado", compra true, serie "papel". Su precio es el campo q (lo pagado por el lado).
- Una mirada en sombra (sombra true) no se opera. Sale del conteo, salvo con --con-sombra, y entonces es otra estrategia.
- Una apuesta por ventana (W, t). Los llenados de 5 y 15 s de la misma decisión no son dos apuestas independientes:
  cuenta el de hora más temprana.
- El resultado viene de la fila tipo "resultado" de la misma ventana: ganador 1 (sube), -1 (baja) o 0 (empate).
  El empate cuenta como fallo (convención del bloc: «empate = fallo»). Sin fila de resultado, la apuesta está abierta.
  Ganador nulo (sin resultado oficial en dos horas): la apuesta no cuenta.
- Fecha: día de Colombia (UTC-5) de la apertura de la ventana t.

Lo que no se puede leer no se corrige en silencio: se cuenta y se muestra. Con --estricto no se escribe nada si hay
alguna línea mala.

Uso:
  python puente_papel.py registro/                      (todos los .jsonl de la carpeta)
  python puente_papel.py registro/20261110.jsonl --salida apuestas.csv
  python puente_papel.py --ejemplo ejemplo_registro_SINTETICO.jsonl   (datos inventados, para probar)
"""
import argparse
import csv
import datetime as dt
import json
import os
import random
import sys

COL = dt.timezone(dt.timedelta(hours=-5))   # Colombia no tiene horario de verano
SERIE = "papel"
COLUMNAS = ["estrategia", "precio", "acierto", "fecha"]


class ErrorUso(Exception):
    """La entrada no sirve: ruta inexistente o nada que leer."""


def archivos(entradas):
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


def leer(rutas):
    """Devuelve (filas, malas). filas: (ruta, línea, dict). malas: (ruta, línea, motivo)."""
    filas, malas = [], []
    for ruta in rutas:
        with open(ruta, encoding="utf-8") as f:
            for num, texto in enumerate(f, 1):
                if not texto.strip():
                    continue
                try:
                    d = json.loads(texto)
                except json.JSONDecodeError as ex:
                    malas.append((ruta, num, f"no es JSON: {ex.msg}"))
                    continue
                if not isinstance(d, dict):
                    malas.append((ruta, num, "no es un objeto"))
                    continue
                filas.append((ruta, num, d))
    return filas, malas


def _entero(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _motivo_compra(d):
    """None si la compra está bien formada; si no, el motivo."""
    if not (_entero(d.get("W")) and _entero(d.get("t"))):
        return "compra sin ventana (W o t)"
    if d.get("lado") not in (1, -1):
        return "compra sin lado 1 o -1"
    q = d.get("q")
    if not _numero(q) or not 0 < q < 1:
        return f"precio q fuera de (0, 1): {q!r}"
    if not _numero(d.get("hora")):
        return "compra sin hora"
    return None


def _fecha(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%Y-%m-%d")


def construir(filas, con_sombra=False):
    """Devuelve (apuestas, cuentas, malas). Una apuesta por ventana; solo las resueltas con ganador."""
    cuentas = {"compras": 0, "sombra": 0, "llenados_extra": 0, "abiertas": 0,
               "sin_ganador": 0, "empates": 0, "conflictos": 0}
    malas = []
    compras, resultados, en_conflicto = {}, {}, set()
    for ruta, num, d in filas:
        if d.get("serie") != SERIE:
            continue
        tipo = d.get("tipo")
        if tipo == "resultado":
            W, t, g = d.get("W"), d.get("t"), d.get("ganador")
            if not (_entero(W) and _entero(t)) or g not in (1, -1, 0, None):
                malas.append((ruta, num, "resultado sin ventana o con ganador distinto de 1, -1, 0 o nulo"))
                continue
            clave = (W, t)
            if clave in resultados and resultados[clave] != g:
                en_conflicto.add(clave)
            resultados[clave] = g
        elif tipo == "llenado" and d.get("compra") is True:
            motivo = _motivo_compra(d)
            if motivo:
                malas.append((ruta, num, motivo))
                continue
            cuentas["compras"] += 1
            sombra = bool(d.get("sombra"))
            if sombra:
                cuentas["sombra"] += 1
                if not con_sombra:
                    continue
            clave = (d["W"], sombra, d["t"])
            fila = {"W": d["W"], "t": d["t"], "lado": d["lado"], "q": float(d["q"]),
                    "hora": float(d["hora"]), "sombra": sombra}
            if clave in compras:
                cuentas["llenados_extra"] += 1
                if fila["hora"] < compras[clave]["hora"]:
                    compras[clave] = fila
            else:
                compras[clave] = fila

    apuestas = []
    for clave in sorted(compras, key=lambda c: (compras[c]["t"], c[0], c[1])):
        c = compras[clave]
        W, sombra, t = clave
        if (W, t) in en_conflicto:
            cuentas["conflictos"] += 1
            continue
        if (W, t) not in resultados:
            cuentas["abiertas"] += 1
            continue
        g = resultados[(W, t)]
        if g is None:
            cuentas["sin_ganador"] += 1
            continue
        if g == 0:
            cuentas["empates"] += 1
        apuestas.append({
            "estrategia": f"{'sombra' if sombra else SERIE}-{W}min",
            "precio": c["q"],
            "acierto": 1 if g == c["lado"] else 0,
            "fecha": _fecha(t),
        })
    return apuestas, cuentas, malas


def escribir_csv(ruta, apuestas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        for a in apuestas:
            w.writerow([a["estrategia"], f"{a['precio']:.6g}", a["acierto"], a["fecha"]])


def resumen(apuestas, cuentas, malas, n_archivos, n_lineas):
    out = [
        f"Registro leído: {n_archivos} archivo(s), {n_lineas} línea(s); no se pudieron leer {len(malas)}.",
        f"Compras de papel: {cuentas['compras']} (en sombra: {cuentas['sombra']}); "
        f"llenados extra de una misma ventana, no cuentan: {cuentas['llenados_extra']}.",
        f"Apuestas resueltas que se exportan: {len(apuestas)}.",
        f"Sin contar: abiertas {cuentas['abiertas']} · sin ganador oficial {cuentas['sin_ganador']} · "
        f"resultado en conflicto {cuentas['conflictos']}.",
        f"Empates (cuentan como fallo): {cuentas['empates']}.",
    ]
    for nombre in sorted({a["estrategia"] for a in apuestas}):
        grupo = [a for a in apuestas if a["estrategia"] == nombre]
        k = sum(a["acierto"] for a in grupo)
        precio = sum(a["precio"] for a in grupo) / len(grupo)
        out.append(f"  {nombre}: {len(grupo)} apuestas, {k} aciertos ({100 * k / len(grupo):.1f} %), "
                   f"precio medio pagado {precio:.3f}.")
    for ruta, num, motivo in malas[:10]:
        out.append(f"  línea mala: {os.path.basename(ruta)} línea {num}: {motivo}")
    if len(malas) > 10:
        out.append(f"  ... y {len(malas) - 10} líneas malas más.")
    return "\n".join(out)


def generar_ejemplo(ruta, semilla=7):
    """Registro SINTÉTICO con la forma de operador/papel.py. Moneda justa y precios alrededor de 0,50 a 0,58.
    No son datos reales: sirven para ver la salida y para probar el puente."""
    rnd = random.Random(semilla)
    base = int(dt.datetime(2026, 11, 10, 5, 0, tzinfo=dt.timezone.utc).timestamp())
    filas = []
    for W, paso, n in ((5, 300, 240), (15, 900, 80)):
        for i in range(n):
            t = base + i * paso
            lado = rnd.choice((1, -1))
            if rnd.random() < 0.2:
                filas.append({"tipo": "llenado", "serie": SERIE, "W": W, "t": t, "lado": lado, "compra": True,
                              "sombra": True, "llenado": 5, "q": round(rnd.uniform(0.50, 0.58), 3),
                              "hora": round(t + 70 + rnd.random() * 10, 2)})
            else:
                q = round(rnd.uniform(0.50, 0.58), 3)
                hora = t + 62 + rnd.random() * 10
                filas.append({"tipo": "llenado", "serie": SERIE, "W": W, "t": t, "lado": lado, "compra": True,
                              "sombra": False, "llenado": 5, "q": q, "hora": round(hora, 2)})
                if rnd.random() < 0.3:   # segundo llenado de la misma decisión: no es otra apuesta
                    filas.append({"tipo": "llenado", "serie": SERIE, "W": W, "t": t, "lado": lado, "compra": True,
                                  "sombra": False, "llenado": 15, "q": q, "hora": round(hora + 10, 2)})
            ganador = 0 if rnd.random() < 0.02 else rnd.choice((1, -1))
            filas.append({"tipo": "resultado", "serie": SERIE, "W": W, "t": t, "ganador": ganador,
                          "fuente": "oficial", "hora": round(t + W * 60 + 90, 2)})
    filas.sort(key=lambda d: (d.get("hora", 0), d["W"], d["tipo"]))
    with open(ruta, "w", encoding="utf-8") as f:
        for d in filas:
            d["_SINTETICO"] = True
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exporta las apuestas de papel del operador de binarias al CSV del evaluador.")
    ap.add_argument("entrada", nargs="*", help="carpeta registro/ o archivos .jsonl del operador")
    ap.add_argument("--salida", default="apuestas_papel.csv", help="CSV que se escribe (por defecto apuestas_papel.csv)")
    ap.add_argument("--con-sombra", action="store_true",
                    help="agrega las miradas en sombra como estrategias aparte (sombra-5min, sombra-15min)")
    ap.add_argument("--estricto", action="store_true",
                    help="si alguna línea no se puede leer, no escribe nada y sale con error")
    ap.add_argument("--ejemplo", metavar="SALIDA",
                    help="escribe un registro SINTÉTICO en SALIDA y sale (no son apuestas reales)")
    args = ap.parse_args(argv)
    try:
        if args.ejemplo:
            generar_ejemplo(args.ejemplo)
            print(f"Escrito {args.ejemplo} (datos SINTÉTICOS, inventados, no son apuestas reales).")
            return 0
        if not args.entrada:
            ap.error("indique la carpeta registro/ o los archivos .jsonl")
        rutas = archivos(args.entrada)
        filas, malas = leer(rutas)
        apuestas, cuentas, malas_construccion = construir(filas, args.con_sombra)
        malas += malas_construccion
        n_lineas = len(filas) + len(malas)
        texto = resumen(apuestas, cuentas, malas, len(rutas), n_lineas)
        if malas and args.estricto:
            print(texto)
            print("Modo estricto: hay líneas que no se pueden leer; no se escribió ningún CSV.", file=sys.stderr)
            return 1
        if not apuestas:
            print(texto)
            print("No hay apuestas resueltas que exportar; no se escribió el CSV.", file=sys.stderr)
            return 1
        escribir_csv(args.salida, apuestas)
        print(texto)
        print(f"CSV escrito: {args.salida}")
        return 0
    except ErrorUso as ex:
        print(f"Error: {ex}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as ex:
        print(f"Error al leer: {ex}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
