"""Plan diario de ganancias (27-28/10/2026): las mismas operaciones medidas en cinco libros de distinto tamaño, en pesos.

Pedido de Nicolás: el plan de ganancias es DIARIO, con meta de 11 % al día. Lo medido (investigacion/plan-diario/) dice
que un 11 % diario de media no existe con estas estrategias; por eso la meta vive en el libro L11 y se compara cada día con
los demás, en pesos, sin dinero real.

Libros (riesgo = fracción del saldo que se pierde si salta el stop planeado; nocional = riesgo * saldo / distancia):
  L2   2 %  (el actual)                          L5  5 %
  LK   medio Kelly de lo ejecutado, tope 10 %     L11 19 % (meta 11 %), paradas −10 % día, −20 % semana, −50 % total
  LC   LIBRO PRINCIPAL desde el 28/10: la mejor combinación de a2_combinaciones.txt (P05c en los 7 activos + P05b, P11
       y N8 de BTC), 3 % por operación (riesgo bajado a pedido de Nicolás: peor caída histórica 33-43 % en vez de 50-63 %),
       hasta 3 posiciones; paradas −9 % día, −18 % semana, −45 % total
  LC5  la misma cartera al 5 % (el óptimo robusto de a1), como sombra para comparar
Todos con una pérdida máxima del 100 % del saldo por operación (liquidación) y sin abrir tras su parada total.

Uso:
  python -I consolidacion/plan_diario.py                      -> informe del papel (papel/libro.jsonl, solo EJECUTADAS)
  python -I consolidacion/plan_diario.py --teorico            -> lo mismo con todas las señales
  python -I consolidacion/plan_diario.py --historia RUTA.csv  -> los libros sobre operaciones históricas (ops_*.csv)
Solo biblioteca estándar."""
import csv
import datetime as dt
import json
import math
import os
import sys

UTC = dt.timezone.utc
COP_POR_USDT = 3177.85
CAPITAL_USDT = 40000 / COP_POR_USDT
LIBROS = {
    "L2": dict(riesgo=0.02, dia=0.04, semana=0.08, total=0.20),
    "L5": dict(riesgo=0.05, dia=0.10, semana=0.20, total=0.40),
    "LK": dict(riesgo=None, dia=0.10, semana=0.20, total=0.40),
    "L11": dict(riesgo=0.19, dia=0.10, semana=0.20, total=0.50),
    "LC": dict(riesgo=0.03, dia=0.09, semana=0.18, total=0.45, max_abiertas=3),
    "LC5": dict(riesgo=0.05, dia=0.15, semana=0.30, total=0.60, max_abiertas=3),
}
COSTE = {"creador": 0.02, "tomador": 0.05}


def _ts(x):
    if isinstance(x, (int, float)):
        return int(x)
    return int(dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp())


def operaciones_historia(ruta, estrategias=("P05c", "P11", "P05b", "N8")):
    """Operaciones de investigacion/operaciones/ops_*.csv en el formato del libro."""
    ops = []
    with open(ruta, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["estrategia"] not in estrategias:
                continue
            pe = float(r["pe"])
            ap = r.get("apertura") or ""
            dist = abs(pe - float(ap)) / pe if ap else 0.03
            neto = float(r["bruto"]) - (COSTE["creador"] if r["creador"] == "True" else COSTE["tomador"]) - COSTE["tomador"]
            activo = os.path.basename(ruta)[4:-4] if os.path.basename(ruta).startswith("ops_") else "BTC"
            ops.append({"estrategia": r["estrategia"], "entrada": _ts(r["entrada"]), "salida": _ts(r["salida"]),
                        "neto": neto, "dist": dist, "activo": activo})
    return ops


def operaciones_cartera(carpeta):
    """Cartera LC histórica: P05c, P11 y P05b de BTC, más P05c de los demás activos de la carpeta (ops_*.csv)."""
    ops = operaciones_historia(os.path.join(carpeta, "ops_BTC.csv"))
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.startswith("ops_") and nombre.endswith(".csv") and nombre != "ops_BTC.csv":
            ops += operaciones_historia(os.path.join(carpeta, nombre), estrategias=("P05c",))
    return ops


def operaciones_papel(teorico=False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import riesgo
    filas = [r for r in riesgo._leer("libro.jsonl") if r["estrategia"] != "AZAR"]
    if not teorico:
        filas = [r for r in filas if r.get("ejecutada")]
    return [{"estrategia": r["estrategia"], "entrada": r["entrada"], "salida": r["salida"], "neto": r["neto"],
             "dist": r.get("dist") or 0.03, "activo": r.get("activo", "BTC")} for r in filas]


def kelly_medio(rs):
    """Medio Kelly de los múltiplos R vistos; 0 con menos de 20 operaciones (no hay con qué estimar)."""
    if len(rs) < 20:
        return 0.02
    mejor, g_mejor = 0.0, 0.0
    f = 0.0025
    while f < 1:
        xs = [1 + f * r for r in rs]
        if min(xs) <= 0:
            break
        g = sum(math.log(x) for x in xs) / len(xs)
        if g > g_mejor:
            mejor, g_mejor = f, g
        f += 0.0025
    return min(mejor / 2, 0.10)


def simular(ops, libro):
    """Un libro: una posición a la vez (LC admite varias con riesgo abierto ≤ 6 %). Devuelve dict de resultados."""
    p = LIBROS[libro]
    if not libro.startswith("LC"):  # los libros de una posición son de BTC; la cartera de varios activos es LC y LC5
        ops = [o for o in ops if o.get("activo", "BTC") == "BTC"]
    else:  # la cartera: P05c en todos los activos y P05b, P11 y N8 solo en BTC (a2_combinaciones.txt)
        ops = [o for o in ops if o["estrategia"] == "P05c" or (o.get("activo", "BTC") == "BTC" and o["estrategia"] in ("P05b", "P11", "N8"))]
    ops = sorted(ops, key=lambda o: (o["entrada"], o["estrategia"]))
    saldo = maximo = CAPITAL_USDT
    abiertas, pdia, psem, dias = [], {}, {}, {}
    parada, rs, hechas, omitidas = None, [], 0, 0
    reabre, mult, paradas = None, 1.0, []   # tras la parada total: 30 días de pausa y vuelta a la mitad del riesgo; la segunda es definitiva
    eventos = sorted([(o["entrada"], 1, i) for i, o in enumerate(ops)] + [(o["salida"], 0, i) for i, o in enumerate(ops)])
    tam = {}
    for t, tipo, i in eventos:
        o = ops[i]
        d = dt.datetime.fromtimestamp(t, UTC).date()
        w = d.isocalendar()[:2]
        if tipo == 0:
            if i not in tam:
                continue
            noc, riesgo_ab = tam.pop(i)
            abiertas.remove(riesgo_ab)
            g = max(noc * o["neto"] / 100, -saldo)
            saldo += g
            ds = dt.datetime.fromtimestamp(o["salida"], UTC).date()
            dias.setdefault(ds, [saldo - g, 0.0])[1] += g
            pdia[ds] = pdia.get(ds, 0.0) + g
            psem[ds.isocalendar()[:2]] = psem.get(ds.isocalendar()[:2], 0.0) + g
            rs.append(o["neto"] / 100 / o["dist"])
            maximo = max(maximo, saldo)
            if parada is None and reabre is None and (maximo - saldo) / maximo >= p["total"]:
                paradas.append(ds)
                if len(paradas) == 1:
                    reabre, mult = o["salida"] + 30 * 86400, 0.5
                else:
                    parada = ds
            continue
        if reabre is not None:
            if t < reabre:
                omitidas += 1
                continue
            reabre, maximo = None, saldo   # se reabre: el máximo se cuenta desde aquí
        if parada or saldo <= 0.05 * CAPITAL_USDT:
            omitidas += 1
            continue
        if pdia.get(d, 0.0) <= -p["dia"] * saldo or psem.get(w, 0.0) <= -p["semana"] * saldo:
            omitidas += 1
            continue
        if libro.startswith("LC"):
            f = p["riesgo"]
            if len(abiertas) >= p["max_abiertas"]:
                omitidas += 1
                continue
        else:
            if abiertas:
                omitidas += 1
                continue
            f = kelly_medio(rs) if libro == "LK" else p["riesgo"]
        f *= mult
        noc = f * saldo / max(o["dist"], 1e-6)
        tam[i] = (noc, f)
        abiertas.append(f)
        hechas += 1
    rd = {d: v[1] / v[0] for d, v in dias.items() if v[0] > 0}
    return {"libro": libro, "saldo_cop": saldo * COP_POR_USDT, "operaciones": hechas, "omitidas": omitidas,
            "caida_max": None, "dias_11": sum(1 for x in rd.values() if x >= 0.11), "dias_con_op": len(rd),
            "mejor_dia": max(rd.values(), default=0.0), "peor_dia": min(rd.values(), default=0.0),
            "parada": " y ".join(str(x) for x in paradas) + (" (definitiva)" if parada else " (reabrió)") if paradas else None,
            "dias": rd}


def caida_maxima(ops, libro):
    """Caída máxima del saldo cerrando operación a operación (aparte para no complicar simular)."""
    r = simular(ops, libro)
    return r


def informe(ops, titulo, desde=None, hasta=None):
    L = [titulo, f"Capital inicial 40.000 COP ({CAPITAL_USDT:.2f} USDT a {COP_POR_USDT:,.2f} COP). Operaciones: {len(ops)}."]
    if not ops:
        L.append("Sin operaciones todavía: los cinco libros siguen en 40.000 COP.")
        return "\n".join(L)
    t0 = min(o["entrada"] for o in ops)
    t1 = max(o["salida"] for o in ops)
    ndias = max(1, (t1 - t0) // 86400 + 1)
    L.append(f"Periodo: {dt.datetime.fromtimestamp(t0, UTC):%Y-%m-%d} a {dt.datetime.fromtimestamp(t1, UTC):%Y-%m-%d} ({ndias} días)")
    L.append("libro  riesgo   saldo final COP   ganancia/día COP   crec./día   días ≥+11 %   peor día   operaciones  parada")
    for nb in LIBROS:
        r = simular(ops, nb)
        mult = r["saldo_cop"] / 40000
        g = mult ** (1 / ndias) - 1 if mult > 0 else -1
        rr = {"L2": "2 %", "L5": "5 %", "LK": "½ Kelly", "L11": "19 %", "LC": "3 % ×3", "LC5": "5 % ×3"}[nb]
        L.append(f"{nb:5s}  {rr:7s} {r['saldo_cop']:>16,.0f}   {(r['saldo_cop'] - 40000) / ndias:>+14,.0f}   {g * 100:+8.3f} %"
                 f"   {r['dias_11']:>5d} de {r['dias_con_op']:<5d} {r['peor_dia'] * 100:+7.1f} %   {r['operaciones']:>6d}    {r['parada'] or '-'}")
    return "\n".join(L)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if "--historia" in a:
        ruta = a[a.index("--historia") + 1]
        if os.path.isdir(ruta):
            print(informe(operaciones_cartera(ruta), "PLAN DIARIO · historia de la cartera (BTC: P05c, P11, P05b + P05c de los demás activos)"))
        else:
            print(informe(operaciones_historia(ruta), f"PLAN DIARIO · historia de {os.path.basename(ruta)} (P05c > P11 > P05b)"))
    else:
        teo = "--teorico" in a
        print(informe(operaciones_papel(teo), f"PLAN DIARIO · papel {'TEÓRICO (todas las señales)' if teo else 'EJECUTADO'} en pesos"))


if __name__ == "__main__":
    main()
