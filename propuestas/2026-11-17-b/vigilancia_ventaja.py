#!/usr/bin/env python3
"""Vigilancia de ventaja de las binarias: ¿la ventaja de cada estrategia se mantiene por periodos?

Complementa evaluador_ventaja.py (que mira el conjunto completo). Este programa parte cada
estrategia en periodos (mes, trimestre o año) y dice:
  - en cuántos periodos el acierto supera el equilibrio;
  - si el último periodo sigue por encima o si la ventaja se está gastando;
  - la tendencia del acierto por periodo;
  - cuántas apuestas más harían falta para decidir con el acierto medido.

Solo biblioteca estándar (Python 3.11 o superior). No se conecta a nada, no envía órdenes
y no escribe archivos salvo que se pida (--json, --ejemplo).

Uso:
  python vigilancia_ventaja.py apuestas.csv
  python vigilancia_ventaja.py apuestas.csv --periodo mes --json salida.json --detalle
  python vigilancia_ventaja.py apuestas.csv --grupo sentido,plazo_min     (sin columna estrategia)
  python vigilancia_ventaja.py --ejemplo ejemplo_SINTETICO.csv             (datos inventados)
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import OrderedDict, defaultdict, namedtuple
from datetime import datetime, timedelta
from statistics import NormalDist

ACIERTO_SI = {"acierta", "acierto", "1", "si", "sí", "true", "gana", "win"}
ACIERTO_NO = {"falla", "fallo", "0", "no", "false", "pierde", "loss", "empate", "tie"}
EMPATE = {"empate", "tie"}
COLUMNAS_RESULTADO = ("acierto", "resultado")
COLUMNAS_FECHA = ("fecha", "fecha_hora_colombia", "fecha_hora")
FORMATOS_FECHA = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
)

# Reglas de veredicto. Son criterios de este programa, no de la red ni del bloc: se pueden
# cambiar, pero conviene dejar constancia de cualquier cambio.
MIN_PERIODOS_VALIDOS = 3      # periodos con el mínimo de apuestas para opinar sobre estabilidad
FRACCION_ESTABLE = 0.75       # fracción de periodos válidos que deben superar el equilibrio
POTENCIA = 0.80               # potencia para el cálculo de apuestas necesarias

Fila = namedtuple("Fila", "periodo acierto precio empate")


class ErrorDeDatos(Exception):
    """Archivo o fila que no se puede leer. Nunca se corrige en silencio."""


# ---------------------------------------------------------------- lectura

def _delimitador(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        primera = f.readline()
    return ";" if primera.count(";") > primera.count(",") else ","


def _primera(columnas, candidatas):
    for c in candidatas:
        if c in columnas:
            return c
    return None


def _fecha(texto, linea):
    t = (texto or "").strip()
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(t, formato)
        except ValueError:
            pass
    raise ErrorDeDatos(f"línea {linea}: fecha no reconocida «{texto}»")


def _precio(texto, linea):
    t = (texto or "").strip().replace(",", ".")
    try:
        p = float(t)
    except ValueError:
        raise ErrorDeDatos(f"línea {linea}: precio no numérico «{texto}»")
    if not 0 < p < 1:
        raise ErrorDeDatos(f"línea {linea}: precio fuera de 0 a 1 «{texto}» (use 0,51 o 0.51)")
    return p


def periodo_de(fecha, tipo):
    if fecha is None:
        return "(sin fecha)"
    if tipo == "mes":
        return fecha.strftime("%Y-%m")
    if tipo == "anio":
        return fecha.strftime("%Y")
    return f"{fecha.year}-T{(fecha.month - 1) // 3 + 1}"


def leer(ruta, grupos=None, col_fecha=None, periodo="trimestre"):
    """Devuelve ({grupo: [Fila, ...]}, metadatos). Lanza ErrorDeDatos ante cualquier fila mala."""
    delim = _delimitador(ruta)
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f, delimiter=delim)
        cols = lector.fieldnames or []
        col_res = _primera(cols, COLUMNAS_RESULTADO)
        if col_res is None:
            raise ErrorDeDatos(
                f"no hay columna de resultado (se busca «acierto» o «resultado»); "
                f"columnas del archivo: {', '.join(cols)}"
            )
        if col_fecha is not None and col_fecha not in cols:
            raise ErrorDeDatos(f"la columna de fecha «{col_fecha}» no existe")
        col_f = col_fecha or _primera(cols, COLUMNAS_FECHA)
        col_p = "precio" if "precio" in cols else None
        if grupos is None:
            grupos = ["estrategia"] if "estrategia" in cols else []
        for g in grupos:
            if g not in cols:
                raise ErrorDeDatos(f"la columna de grupo «{g}» no existe")

        por_grupo = defaultdict(list)
        total = 0
        empates = 0
        for fila in lector:
            linea = lector.line_num
            total += 1
            bruto = fila[col_res]
            v = (bruto or "").strip().lower()
            if v in ACIERTO_SI:
                acierto, empate = 1, False
            elif v in ACIERTO_NO:
                acierto, empate = 0, v in EMPATE
            else:
                raise ErrorDeDatos(f"línea {linea}: resultado no reconocido «{bruto}»")
            if empate:
                empates += 1
            per = periodo_de(_fecha(fila[col_f], linea), periodo) if col_f else "(sin fecha)"
            precio = _precio(fila[col_p], linea) if col_p else None
            clave = " | ".join((fila[g] or "").strip() for g in grupos) if grupos else "(todas)"
            por_grupo[clave].append(Fila(per, acierto, precio, empate))

    meta = {
        "filas": total,
        "empates": empates,
        "delimitador": delim,
        "col_fecha": col_f,
        "col_precio": col_p,
        "grupos": grupos,
        "usa_precio": col_p is not None,
    }
    return por_grupo, meta


# ---------------------------------------------------------------- cálculo

def wilson(k, n, z):
    """Intervalo de Wilson para k aciertos de n con el valor z de la confianza."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centro - margen, centro + margen


def z_corregido(k, confianza=0.95):
    """z de dos colas con Bonferroni por la cantidad de grupos mirados (igual que evaluador_ventaja.py)."""
    k = max(1, k)
    alfa = (1 - confianza) / (2 * k)
    return NormalDist().inv_cdf(1 - alfa)


def equilibrio(precios, usa_precio, pago, comision):
    """Acierto mínimo para no perder. Con columna precio: precio medio / (1 - comisión).
    Sin ella: 1 / (1 + pago), la convención del bloc (pago 0,85 → 54,1 %)."""
    if usa_precio:
        return (sum(precios) / len(precios)) / (1 - comision)
    return 1 / (1 + pago)


def n_necesaria(p, be, z, potencia=POTENCIA):
    """Apuestas para que un acierto real p supere el equilibrio be con la potencia dada (normal).
    None si p no supera be: entonces más apuestas no crean una ventaja que no está medida."""
    if p <= be:
        return None
    zb = NormalDist().inv_cdf(potencia)
    n = ((z * math.sqrt(be * (1 - be)) + zb * math.sqrt(p * (1 - p))) / (p - be)) ** 2
    return math.ceil(n)


def _pendiente(valores):
    """Pendiente de mínimos cuadrados del acierto contra el número de periodo (en fracción por periodo)."""
    m = len(valores)
    mx = (m - 1) / 2
    my = sum(valores) / m
    den = sum((x - mx) ** 2 for x in range(m))
    num = sum((x - mx) * (v - my) for x, v in enumerate(valores))
    return num / den


def _veredicto(n, lo, hi, be, validos, sobre_ultimo, min_total):
    if n < min_total:
        return "PRUEBA INSUFICIENTE"
    if hi < be:
        return "SIN VENTAJA"
    if lo > be:
        if len(validos) < MIN_PERIODOS_VALIDOS:
            return "VENTAJA, PERIODOS INSUFICIENTES"
        sobre = sum(p["sobre"] for p in validos)
        if sobre_ultimo and sobre / len(validos) >= FRACCION_ESTABLE:
            return "SOSTENIDA"
        return "VENTAJA NO SOSTENIDA"
    return "INCONCLUSA"


def _analizar_grupo(nombre, filas, z, usa_precio, pago, comision, min_total, min_periodo):
    n = len(filas)
    aciertos = sum(f.acierto for f in filas)
    acc = aciertos / n
    lo, hi = wilson(aciertos, n, z)
    be = equilibrio([f.precio for f in filas] if usa_precio else None, usa_precio, pago, comision)

    por_periodo = OrderedDict()
    for f in filas:
        por_periodo.setdefault(f.periodo, []).append(f)
    periodos = []
    for clave in sorted(por_periodo):
        fs = por_periodo[clave]
        na = len(fs)
        aa = sum(f.acierto for f in fs)
        be_p = equilibrio([f.precio for f in fs] if usa_precio else None, usa_precio, pago, comision)
        periodos.append({
            "periodo": clave,
            "apuestas": na,
            "aciertos": aa,
            "acierto": aa / na,
            "equilibrio": be_p,
            "valido": na >= min_periodo,
            "sobre": aa / na > be_p,
        })

    validos = [p for p in periodos if p["valido"]]
    sobre_ultimo = bool(validos) and validos[-1]["sobre"]
    # Con menos de MIN_PERIODOS_VALIDOS periodos, una «tendencia» no dice nada.
    pendiente = _pendiente([p["acierto"] for p in validos]) \
        if len(validos) >= MIN_PERIODOS_VALIDOS else None
    n_nec = n_necesaria(acc, be, z)
    n_nec_cons = n_necesaria(lo, be, z) if lo > be else None
    veredicto = _veredicto(n, lo, hi, be, validos, sobre_ultimo, min_total)

    return {
        "grupo": nombre,
        "apuestas": n,
        "aciertos": aciertos,
        "acierto": acc,
        "ic_bajo": lo,
        "ic_alto": hi,
        "equilibrio": be,
        "periodos": periodos,
        "periodos_validos": len(validos),
        "periodos_sobre": sum(p["sobre"] for p in validos),
        "ultimo_sobre": sobre_ultimo,
        "pendiente_pp": None if pendiente is None else pendiente * 100,
        "apuestas_necesarias": n_nec,
        "apuestas_faltan": None if n_nec is None else max(0, n_nec - n),
        "apuestas_necesarias_cota_baja": n_nec_cons,
        "veredicto": veredicto,
    }


def analizar(por_grupo, meta, *, pago, comision, confianza, min_total, min_periodo):
    k = len(por_grupo)
    z = z_corregido(k, confianza)
    resultados = [
        _analizar_grupo(nombre, filas, z, meta["usa_precio"], pago, comision, min_total, min_periodo)
        for nombre, filas in sorted(por_grupo.items())
    ]
    return {"k": k, "z": z, "resultados": resultados}


# ---------------------------------------------------------------- salida

def _pct(x):
    return f"{x * 100:.1f} %".replace(".", ",")


def _num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def _entero(x):
    return f"{x:,}".replace(",", ".")  # separador de miles con punto, como en el bloc


def texto(res, meta, opts, detalle=False, archivo=""):
    out = []
    out.append(f"Vigilancia de ventaja · {archivo}")
    out.append(
        f"Filas leídas: {meta['filas']} · empates (cuentan como fallo): {meta['empates']} · "
        f"periodo: {opts['periodo']} · columna de fecha: {meta['col_fecha'] or 'ninguna'}"
    )
    if meta["usa_precio"]:
        out.append(f"Equilibrio: precio medio / (1 - {_pct(opts['comision'])} de comisión), con la columna «precio».")
    else:
        out.append(
            f"Equilibrio: 1 / (1 + pago), con pago {_num(opts['pago'], 2)} "
            "(sin columna «precio»; la comisión se supone dentro del pago)."
        )
    out.append(
        f"Grupos: {res['k']} · confianza {_pct(opts['confianza'])} corregida por Bonferroni "
        f"(z = {_num(res['z'], 2)})"
    )
    out.append(
        f"Mínimos: {opts['min_total']} apuestas en total y {opts['min_periodo']} por periodo "
        "para contar el periodo."
    )
    out.append("")
    for r in res["resultados"]:
        out.append(f"[{r['grupo']}]  VEREDICTO: {r['veredicto']}")
        out.append(
            f"  apuestas {r['apuestas']} · acierto {_pct(r['acierto'])} · "
            f"IC corregido {_pct(r['ic_bajo'])} a {_pct(r['ic_alto'])} · equilibrio {_pct(r['equilibrio'])}"
        )
        if r["periodos_validos"]:
            ult = [p for p in r["periodos"] if p["valido"]][-1]
            pend = "sin tendencia calculable" if r["pendiente_pp"] is None else (
                f"{r['pendiente_pp']:+.2f} pp por periodo".replace(".", ",")
            )
            out.append(
                f"  periodos sobre el equilibrio: {r['periodos_sobre']} de {r['periodos_validos']} · "
                f"último periodo ({ult['periodo']}) {_pct(ult['acierto'])} "
                f"{'sobre' if ult['sobre'] else 'bajo'} el equilibrio · tendencia {pend}"
            )
        else:
            out.append("  periodos: ninguno llega al mínimo por periodo.")
        if r["apuestas_necesarias"] is None:
            out.append("  apuestas que faltan: no hay ventaja medida; más apuestas al ritmo actual no la crean.")
        else:
            extra = f"; con el extremo bajo del IC: {_entero(r['apuestas_necesarias_cota_baja'])}" \
                if r["apuestas_necesarias_cota_baja"] else ""
            out.append(
                f"  apuestas necesarias para decidir con el acierto medido (potencia {int(POTENCIA*100)} %): "
                f"{_entero(r['apuestas_necesarias'])} · faltan {_entero(r['apuestas_faltan'])}{extra}"
            )
        if detalle and r["periodos"]:
            out.append("  periodo      apuestas  acierto  equilibrio  cuenta")
            for p in r["periodos"]:
                cuenta = "sí" if p["valido"] else "no (pocas)"
                out.append(
                    f"  {p['periodo']:<12}{p['apuestas']:>8}  {_pct(p['acierto']):>7}  "
                    f"{_pct(p['equilibrio']):>10}  {cuenta}"
                )
        out.append("")
    out.append(
        "Lectura: un veredicto SOSTENIDA exige que el intervalo corregido esté por encima del equilibrio, "
        "que el último periodo también lo esté y que la mayoría de los periodos lo superen. "
        "Las reglas están en el código (MIN_PERIODOS_VALIDOS, FRACCION_ESTABLE)."
    )
    return "\n".join(out)


def escribir_ejemplo(ruta, semilla=7):
    """Datos INVENTADOS con semilla fija, en el formato estrategia,precio,acierto,fecha."""
    rng = random.Random(semilla)
    inicio = datetime(2024, 1, 1)
    dias = 912  # 1 de enero de 2024 a mediados de 2026
    perfiles = {
        "SINTETICA-A": lambda t: 0.575,                        # ventaja estable
        "SINTETICA-B": lambda t: 0.600 if t < 0.6 else 0.490,  # ventaja que se gasta
        "SINTETICA-C": lambda t: 0.500,                        # sin ventaja
    }
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write("estrategia,precio,acierto,fecha\n")
        for nombre, prob in perfiles.items():
            filas = []
            for _ in range(2400):
                d = rng.randrange(dias)
                precio = round(rng.uniform(0.51, 0.53), 2)
                acierto = 1 if rng.random() < prob(d / dias) else 0
                filas.append((d, precio, acierto))
            filas.sort()
            for d, precio, acierto in filas:
                fecha = (inicio + timedelta(days=d)).strftime("%Y-%m-%d")
                f.write(f"{nombre},{precio:.2f},{acierto},{fecha}\n")
    return ruta


# ---------------------------------------------------------------- línea de comandos

def main(argv=None):
    ap = argparse.ArgumentParser(description="Vigilancia de ventaja de binarias por periodos.")
    ap.add_argument("archivo", nargs="?", help="CSV con una apuesta por fila: resultado y, si hay, fecha y precio")
    ap.add_argument("--periodo", choices=["mes", "trimestre", "anio"], default="trimestre")
    ap.add_argument("--grupo", help="columnas que definen el grupo, separadas por coma "
                                    "(por defecto: estrategia si existe; si no, todas juntas)")
    ap.add_argument("--fecha", help="columna de fecha si no es fecha o fecha_hora_colombia")
    ap.add_argument("--pago", type=float, default=0.85, help="pago neto sin columna precio (0,85 por defecto)")
    ap.add_argument("--comision", type=float, default=0.02, help="comisión con columna precio (0,02 por defecto)")
    ap.add_argument("--confianza", type=float, default=0.95)
    ap.add_argument("--min-total", type=int, default=100, help="apuestas mínimas por grupo (100)")
    ap.add_argument("--min-periodo", type=int, default=30, help="apuestas mínimas por periodo (30)")
    ap.add_argument("--detalle", action="store_true", help="muestra la tabla por periodo")
    ap.add_argument("--json", metavar="SALIDA", help="escribe el resultado en JSON")
    ap.add_argument("--ejemplo", metavar="RUTA", help="escribe un CSV SINTÉTICO de ejemplo y termina")
    args = ap.parse_args(argv)

    try:
        if args.ejemplo:
            escribir_ejemplo(args.ejemplo)
            print(f"Ejemplo SINTÉTICO escrito en {args.ejemplo} (datos inventados, no son apuestas reales).")
            return 0
        if not args.archivo:
            ap.error("indique un archivo CSV o use --ejemplo")
        grupos = [g.strip() for g in args.grupo.split(",")] if args.grupo else None
        por_grupo, meta = leer(args.archivo, grupos=grupos, col_fecha=args.fecha, periodo=args.periodo)
        res = analizar(
            por_grupo, meta,
            pago=args.pago, comision=args.comision, confianza=args.confianza,
            min_total=args.min_total, min_periodo=args.min_periodo,
        )
    except ErrorDeDatos as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"Error al abrir el archivo: {e}", file=sys.stderr)
        return 2

    opts = {
        "periodo": args.periodo, "pago": args.pago, "comision": args.comision,
        "confianza": args.confianza, "min_total": args.min_total, "min_periodo": args.min_periodo,
    }
    print(texto(res, meta, opts, detalle=args.detalle, archivo=os.path.basename(args.archivo)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"opciones": opts, "meta": meta, **res}, f, ensure_ascii=False, indent=2)
        print(f"\nJSON escrito en {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
