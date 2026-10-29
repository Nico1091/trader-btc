"""T1 (29/10/2026): prueba total de las estrategias del sistema consolidado, con y sin preventivas, por horarios, zonas y márgenes.

Pedido de Nicolás: «pruebas totales por tiempos, con mezclas de estrategias; las estrategias más funcionales con y sin
preventivas; preventivas acorde a horarios, zonas y márgenes; un cuadro de margen operativo de resultados; y el último
agente a nivel de consolidación».

Datos: investigacion/operaciones/ops_<ACTIVO>.csv (motor sin tocar, velas de 1 min de futuros de Binance, 2020-2026) de
12 monedas: BTC; viejas ETH, SOL, BNB, XRP, DOGE, ADA; nuevas (nunca usadas para diseñar) LINK, AVAX, LTC, DOT, TRX.
Estrategias: P05b, P05c, P11, N8 y N9 (definiciones en consolidacion/sistema.py).

Reglas fijadas ANTES de mirar resultados:
1. Preventivas (filtros causales, todo se conoce al dar la señal):
   horario  H17 señal antes de las 17:00 UTC · ASIA 00-07 · EUROPA 07-13 · AMERICA 13-21 · SEMANA sin sábado ni domingo
   zonas    CERCA |distancia del cierre de ayer a la SMA 50| ≤ 5 % · LEJOS > 10 % · VBAJA ATR14/precio ≤ 3 % · VALTA > 5 %
   tiempos  C1 1 h a favor · C2 1 h y 1 d a favor · C3 1 h, 4 h y 1 d a favor · PAT patrón de 1 h a favor
   Se adopta una preventiva para una estrategia solo si mejora la media neta con comisión doble en TODAS las celdas con 20 o
   más operaciones (2020-23 y 2024-26 × BTC, monedas viejas y monedas nuevas) y conserva ≥ 30 % de las operaciones.
2. Márgenes: riesgo por operación 2, 3, 5, 8 o 10 % (nocional = riesgo × saldo / distancia al stop); hasta 1, 3 o 5
   posiciones a la vez; apalancamiento total de la cuenta tope 3×, 5×, 10× o 20× (si una posición no cabe, se achica).
   Paradas: −15 % en el día, −30 % en la semana; con −60 % desde el máximo, 30 días de pausa y vuelta a la mitad del riesgo;
   la segunda parada es definitiva. La pérdida de una operación nunca pasa del saldo.
3. Costos: creador 0,02 %, tomador 0,05 % y financiación media 0,017 % por operación (medida el 27/10); «doble» = el doble.
4. Elección del agente consolidado: la mezcla y el margen con mayor crecimiento diario en la PEOR de las dos mitades
   (cada mitad simulada desde 150.000 COP), con caída máxima ≤ 60 % en las dos; con empate, la de menor caída.
Salidas: t1_prueba_total.txt (informe), t1_cuadro.json (cuadro de margen operativo), t1_replay.json (operaciones del agente
elegido, para verlas en tiempo real) y consolidacion/agente_consolidado.json (configuración del agente).
Uso: python -I t1_prueba_total.py > t1_prueba_total.txt"""
import csv
import re
import datetime as dt
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
OPS = os.path.join(AQUI, "..", "operaciones")
CONS = os.path.join(AQUI, "..", "..", "consolidacion")
UTC = dt.timezone.utc
COP = 3177.85
CAPITAL = 150000 / COP
CORTE = int(dt.datetime(2024, 1, 1, tzinfo=UTC).timestamp())
VIEJAS = ["ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
NUEVAS = ["LINK", "AVAX", "LTC", "DOT", "TRX"]
ACTIVOS = ["BTC"] + VIEJAS + NUEVAS
ESTRATEGIAS = ["P05b", "P05c", "P11", "N8", "N9"]
COSTO = {"normal": {"creador": 0.02, "tomador": 0.05, "fin": 0.017}, "doble": {"creador": 0.04, "tomador": 0.10, "fin": 0.034}}


def es(s):
    """Números a la colombiana (1.234,5) sin tocar las comas del texto."""
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s))


def ts(x):
    return int(dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp())


def cargar():
    ops = []
    for a in ACTIVOS:
        with open(os.path.join(OPS, f"ops_{a}.csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["estrategia"] not in ESTRATEGIAS:
                    continue
                pe = float(r["pe"])
                ap = r.get("apertura") or ""
                senal = ts(r["senal"])
                hora = dt.datetime.fromtimestamp(senal, UTC)
                ops.append({
                    "activo": a, "grupo": "BTC" if a == "BTC" else "VIEJAS" if a in VIEJAS else "NUEVAS",
                    "estrategia": r["estrategia"], "lado": int(r["lado"]), "entrada": ts(r["entrada"]), "salida": ts(r["salida"]),
                    "senal": senal, "hora": hora.hour + hora.minute / 60, "dow": hora.weekday(), "pe": pe, "px": float(r["px"]),
                    "bruto": float(r["bruto"]), "creador": r["creador"] == "True", "motivo": r["motivo"],
                    "dist": abs(pe - float(ap)) / pe if ap else 0.03,
                    "ctx": abs(float(r["ctx_dist"] or 0)), "vol": float(r["atr14"]) / float(r["precio_dia"]) * 100,
                    "e1h": r["e1h"] == "True", "e4h": r["e4h"] == "True", "e1d": r["e1d"] == "True", "pat": r["pat1h"] == "True"})
    return ops


def costo(o, tipo="normal"):
    c = COSTO[tipo]
    return (c["creador"] if o["creador"] else c["tomador"]) + c["tomador"] + c["fin"]


PREVENTIVAS = {
    "H17": ("señal antes de las 17 UTC", lambda o: o["hora"] < 17),
    "ASIA": ("señal en Asia (00-07 UTC)", lambda o: o["hora"] < 7),
    "EUROPA": ("señal en Europa (07-13 UTC)", lambda o: 7 <= o["hora"] < 13),
    "AMERICA": ("señal en América (13-21 UTC)", lambda o: 13 <= o["hora"] < 21),
    "SEMANA": ("sin sábado ni domingo", lambda o: o["dow"] < 5),
    "CERCA": ("cierre de ayer a ≤ 5 % de la SMA 50", lambda o: o["ctx"] <= 5),
    "LEJOS": ("cierre de ayer a > 10 % de la SMA 50", lambda o: o["ctx"] > 10),
    "VBAJA": ("volatilidad baja (ATR ≤ 3 % del precio)", lambda o: o["vol"] <= 3),
    "VALTA": ("volatilidad alta (ATR > 5 % del precio)", lambda o: o["vol"] > 5),
    "C1": ("1 h a favor", lambda o: o["e1h"]),
    "C2": ("1 h y 1 día a favor", lambda o: o["e1h"] and o["e1d"]),
    "C3": ("1 h, 4 h y 1 día a favor", lambda o: o["e1h"] and o["e4h"] and o["e1d"]),
    "PAT": ("patrón de 1 h a favor", lambda o: o["pat"]),
}


def media(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def cribar(ops):
    """Paso 1: cada preventiva en cada estrategia, por periodo y grupo de monedas (media neta con comisión doble)."""
    L, adoptadas = ["PASO 1 · PREVENTIVAS, UNA POR UNA (media neta por operación con comisión doble; n entre paréntesis)", ""], {}
    celdas = [(p, g) for p in ("A", "B") for g in ("BTC", "VIEJAS", "NUEVAS")]
    for e in ESTRATEGIAS:
        base = [o for o in ops if o["estrategia"] == e]
        def celda(xs, p, g):
            return [o["bruto"] - costo(o, "doble") for o in xs if o["grupo"] == g and (o["entrada"] < CORTE) == (p == "A")]
        b = {c: celda(base, *c) for c in celdas}
        L.append(f"== {e} sin preventiva: " + " · ".join(f"{p}-{g} {media(v):+.3f} ({len(v)})" for (p, g), v in b.items()))
        adoptadas[e] = []
        for k, (nombre, f) in PREVENTIVAS.items():
            sel = [o for o in base if f(o)]
            if not sel:
                continue
            v = {c: celda(sel, *c) for c in celdas}
            validas = [c for c in celdas if len(v[c]) >= 20 and len(b[c]) >= 20]
            mejora = [c for c in validas if media(v[c]) > media(b[c])]
            frac = len(sel) / len(base)
            ok = validas and len(mejora) == len(validas) and frac >= 0.30
            if ok:
                adoptadas[e].append(k)
            L.append(f"   {k:7s} {nombre:42s} conserva {frac * 100:3.0f} % · mejora en {len(mejora)} de {len(validas)} celdas · "
                     + " · ".join(f"{p}-{g} {media(v[(p, g)]):+.3f}" for p, g in celdas if (p, g) in validas)
                     + ("  → SE ADOPTA" if ok else ""))
        L.append("")
    return L, adoptadas


def libro(ops, riesgo, max_ab, apal, desde=None, hasta=None, tipo="normal", registrar=False):
    """Libro en papel desde 150.000 COP. Devuelve las cifras del cuadro de margen operativo (en USDT) y, si se pide, cada operación."""
    sel = sorted((o for o in ops if (desde is None or o["entrada"] >= desde) and (hasta is None or o["entrada"] < hasta)),
                 key=lambda o: (o["entrada"], o["activo"], o["estrategia"]))
    ev = sorted([(o["entrada"], 1, i) for i, o in enumerate(sel)] + [(o["salida"], 0, i) for i, o in enumerate(sel)])
    saldo = maximo = CAPITAL
    abiertas, pdia, psem, dias = {}, {}, {}, {}
    ganado = perdido = costos = 0.0
    hechas = ganadas = 0
    caida = 0.0
    reabre, mult, paradas, definitiva = None, 1.0, [], False
    reg = []
    for t, tipo_ev, i in ev:
        o = sel[i]
        d = dt.datetime.fromtimestamp(t, UTC).date()
        if tipo_ev == 0:
            if i not in abiertas:
                continue
            noc = abiertas.pop(i)
            g_bruto = noc * o["bruto"] / 100
            c = noc * costo(o, tipo) / 100
            g = max(g_bruto - c, -saldo)
            saldo += g
            ganado += max(g_bruto, 0.0)
            perdido += max(-g_bruto, 0.0)
            costos += c
            ganadas += g > 0
            ds = dt.datetime.fromtimestamp(o["salida"], UTC).date()
            dias.setdefault(ds, [saldo - g, 0.0])[1] += g
            pdia[ds] = pdia.get(ds, 0.0) + g
            psem[ds.isocalendar()[:2]] = psem.get(ds.isocalendar()[:2], 0.0) + g
            maximo = max(maximo, saldo)
            caida = max(caida, 1 - saldo / maximo)
            if registrar:
                reg.append({"a": o["activo"], "e": o["estrategia"], "l": o["lado"], "t0": o["entrada"], "t1": o["salida"],
                            "pe": o["pe"], "px": o["px"], "noc": round(noc, 4), "g": round(g, 6), "saldo": round(saldo, 6)})
            if not definitiva and reabre is None and (maximo - saldo) / maximo >= 0.60:
                paradas.append(str(ds))
                if len(paradas) == 1:
                    reabre, mult = o["salida"] + 30 * 86400, 0.5
                else:
                    definitiva = True
            continue
        if reabre is not None:
            if t < reabre:
                continue
            reabre, maximo = None, saldo
        if definitiva or saldo <= 0.05 * CAPITAL or len(abiertas) >= max_ab:
            continue
        if pdia.get(d, 0.0) <= -0.15 * saldo or psem.get(d.isocalendar()[:2], 0.0) <= -0.30 * saldo:
            continue
        noc = riesgo * mult * saldo / max(o["dist"], 1e-6)
        libre = apal * saldo - sum(abiertas.values())
        noc = min(noc, libre)
        if noc < 5:  # mínimo de Binance: 5 USDT de nocional
            continue
        abiertas[i] = noc
        hechas += 1
    t0 = desde or min((o["entrada"] for o in sel), default=CORTE)
    t1 = hasta or max((o["salida"] for o in sel), default=CORTE)
    ndias = max(1.0, (t1 - t0) / 86400)
    crec = (saldo / CAPITAL) ** (1 / ndias) - 1 if saldo > 0 else -1.0
    rd = [v[1] / v[0] for v in dias.values() if v[0] > 0]
    r = {"operaciones": hechas, "aciertos": ganadas / hechas * 100 if hechas else 0.0, "ingresos_cop": ganado * COP,
         "perdidas_cop": perdido * COP, "costos_cop": costos * COP, "resultado_cop": (saldo - CAPITAL) * COP,
         "margen_operativo": (saldo - CAPITAL) / ganado * 100 if ganado else 0.0, "saldo_cop": saldo * COP,
         "crec_dia": crec * 100, "cop_dia": (saldo - CAPITAL) * COP / ndias, "caida_max": caida * 100,
         "peor_dia": min(rd, default=0.0) * 100, "dias_11": sum(1 for x in rd if x >= 0.11), "paradas": paradas, "definitiva": definitiva}
    if registrar:
        r["registro"] = reg
    return r


def mezclas(ops, adoptadas):
    def con_prev(o):
        return all(PREVENTIVAS[k][1](o) for k in adoptadas.get(o["estrategia"], []))
    lc = lambda o: o["estrategia"] == "P05c" or (o["activo"] == "BTC" and o["estrategia"] in ("P05b", "P11", "N8"))  # noqa: E731
    return {
        "LC (actual: P05c en 12 + P05b, P11, N8 de BTC)": [o for o in ops if lc(o)],
        "LC con las preventivas adoptadas": [o for o in ops if lc(o) and con_prev(o)],
        "P05c en las 12 monedas": [o for o in ops if o["estrategia"] == "P05c"],
        "LC + N9 de BTC": [o for o in ops if lc(o) or (o["activo"] == "BTC" and o["estrategia"] == "N9")],
        "Todas las estrategias en las 12 monedas": list(ops),
        "Todas con las preventivas adoptadas": [o for o in ops if con_prev(o)],
    }


def fila(nombre, r):
    return (f"{nombre[:46]:46s} {r['operaciones']:6d} {r['aciertos']:6.1f} % {r['ingresos_cop']:>14,.0f} {r['perdidas_cop']:>14,.0f} "
            f"{r['costos_cop']:>12,.0f} {r['resultado_cop']:>+15,.0f} {r['margen_operativo']:>+8.1f} % {r['crec_dia']:>+7.3f} % "
            f"{r['cop_dia']:>+9,.0f} {r['caida_max']:>5.0f} % {r['peor_dia']:>+6.1f} %")


CAB = (f"{'configuración':46s} {'ops':>6s} {'aciertos':>8s} {'ingresos COP':>14s} {'pérdidas COP':>14s} {'costos COP':>12s} "
       f"{'resultado COP':>15s} {'margen op.':>10s} {'%/día':>8s} {'COP/día':>9s} {'caída':>6s} {'peor día':>8s}")


def main():
    ops = cargar()
    p(f"T1 · PRUEBA TOTAL · {len(ops):,} operaciones de {len(ACTIVOS)} monedas · 2020-2026 · capital 150 mil COP")
    p("A = 2020-2023 (ajuste) · B = 2024-2026 (prueba) · BTC / VIEJAS (ETH, SOL, BNB, XRP, DOGE, ADA) / NUEVAS (LINK, AVAX, LTC, DOT, TRX)\n")
    L, adoptadas = cribar(ops)
    p("\n".join(L))
    p("Preventivas adoptadas: " + "; ".join(f"{e}: {', '.join(v) if v else 'ninguna'}" for e, v in adoptadas.items()) + "\n")
    M = mezclas(ops, adoptadas)
    p("PASO 2 · MEZCLAS × MÁRGENES (riesgo, posiciones a la vez, apalancamiento tope). Mitades simuladas por separado desde 150 mil COP.")
    mejor, resumen = None, {}
    for nombre, xs in M.items():
        filas = []
        for riesgo in (0.02, 0.03, 0.05, 0.08, 0.10):
            for max_ab in (1, 3, 5):
                for apal in (3, 5, 10, 20):
                    a = libro(xs, riesgo, max_ab, apal, hasta=CORTE)
                    b = libro(xs, riesgo, max_ab, apal, desde=CORTE)
                    filas.append((min(a["crec_dia"], b["crec_dia"]), riesgo, max_ab, apal, a, b))
        validas = [f for f in filas if f[4]["caida_max"] <= 60 and f[5]["caida_max"] <= 60 and not f[4]["definitiva"] and not f[5]["definitiva"]]
        elegida = max(validas, key=lambda f: (round(f[0], 4), -max(f[4]["caida_max"], f[5]["caida_max"]))) if validas else max(filas, key=lambda f: f[0])
        _, riesgo, max_ab, apal, a, b = elegida
        resumen[nombre] = {"riesgo": riesgo, "max_ab": max_ab, "apal": apal, "A": a, "B": b}
        p(f"\n== {nombre} ({len(xs):,} operaciones) ==")
        p(f"   mejor margen robusto: riesgo {riesgo * 100:.0f} %, hasta {max_ab} a la vez, tope {apal}× · "
              f"A {a['crec_dia']:+.3f} %/día (caída {a['caida_max']:.0f} %) · B {b['crec_dia']:+.3f} %/día (caída {b['caida_max']:.0f} %)")
        for rr in (0.02, 0.05, 0.08):
            f = next(x for x in filas if x[1] == rr and x[2] == max_ab and x[3] == apal)
            p(f"   con riesgo {rr * 100:.0f} %: A {f[4]['crec_dia']:+.3f} %/día (caída {f[4]['caida_max']:.0f} %) · "
                  f"B {f[5]['crec_dia']:+.3f} %/día (caída {f[5]['caida_max']:.0f} %)")
        if (mejor is None or (elegida[0], -max(a["caida_max"], b["caida_max"])) > (mejor[1][0], -max(mejor[1][4]["caida_max"], mejor[1][5]["caida_max"]))) \
                and elegida in validas:
            mejor = (nombre, elegida)
    p("\nPASO 3 · CUADRO DE MARGEN OPERATIVO (toda la historia 2020-2026 desde 150 mil COP, con el margen robusto de cada mezcla)")
    p("margen operativo = resultado / ingresos brutos · ingresos y pérdidas antes de costos · costos = comisiones + financiación\n")
    p(CAB)
    cuadro = []
    for nombre, xs in M.items():
        s = resumen[nombre]
        r = libro(xs, s["riesgo"], s["max_ab"], s["apal"])
        rd = libro(xs, s["riesgo"], s["max_ab"], s["apal"], tipo="doble")
        p(fila(nombre, r))
        p(fila("   con comisión doble", rd))
        cuadro.append({"mezcla": nombre, "riesgo": s["riesgo"], "max_ab": s["max_ab"], "apal": s["apal"], "normal": r, "doble": rd,
                       "A": s["A"], "B": s["B"]})
    p("\nCada estrategia sola (riesgo 5 %, hasta 3 a la vez, tope 10×; P11 y N8 solo en BTC como en el sistema):")
    p(CAB)
    for e in ESTRATEGIAS:
        xs = [o for o in ops if o["estrategia"] == e and (e not in ("P11", "N8") or o["activo"] == "BTC")]
        r = libro(xs, 0.05, 3, 10)
        p(fila(e, r))
        cuadro.append({"mezcla": f"{e} sola", "riesgo": 0.05, "max_ab": 3, "apal": 10, "normal": r})
    if mejor is None:
        p("NINGUNA mezcla cumple la regla 4 (caída ≤ 60 % en las dos mitades): se elige la de mayor crecimiento en la peor mitad.")
        nombre = max(resumen, key=lambda k: min(resumen[k]["A"]["crec_dia"], resumen[k]["B"]["crec_dia"]))
        s_ = resumen[nombre]
        mejor = (nombre, (0, s_["riesgo"], s_["max_ab"], s_["apal"], s_["A"], s_["B"]))
    nombre, (_, riesgo, max_ab, apal, a, b) = mejor
    p(f"\nAGENTE CONSOLIDADO ELEGIDO (regla 4): {nombre} · riesgo {riesgo * 100:.0f} % · hasta {max_ab} a la vez · tope {apal}×")
    p(f"   A {a['crec_dia']:+.3f} %/día, caída {a['caida_max']:.0f} % · B {b['crec_dia']:+.3f} %/día, caída {b['caida_max']:.0f} %")
    final = libro(M[nombre], riesgo, max_ab, apal, registrar=True)
    with open(os.path.join(AQUI, "t1_cuadro.json"), "w", encoding="utf-8") as f:
        json.dump(cuadro, f, ensure_ascii=False, indent=1)
    with open(os.path.join(AQUI, "t1_replay.json"), "w", encoding="utf-8") as f:
        json.dump({"agente": nombre, "riesgo": riesgo, "max_ab": max_ab, "apal": apal, "capital_cop": 150000, "cop_usdt": COP,
                   "operaciones": final["registro"]}, f, ensure_ascii=False)
    conf = {"fecha": "2026-10-29", "mezcla": nombre, "riesgo": riesgo, "max_abiertas": max_ab, "apal_max": apal,
            "capital_cop": 150000, "preventivas": adoptadas,
            "estrategias_btc": ["P05b", "P11", "N8"] + (["N9"] if "N9" in nombre else []) if "Todas" not in nombre else ESTRATEGIAS,
            "estrategias_resto": ["P05c"] if "Todas" not in nombre else ESTRATEGIAS,
            "paradas": {"dia": 0.15, "semana": 0.30, "total": 0.60}}
    with open(os.path.join(CONS, "agente_consolidado.json"), "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=1)
    p(f"   historia completa: {final['operaciones']} operaciones, 150 mil → {final['saldo_cop']:,.0f} COP, "
          f"{final['crec_dia']:+.3f} %/día, caída máxima {final['caida_max']:.0f} %")


if __name__ == "__main__":
    main()
