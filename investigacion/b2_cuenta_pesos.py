"""B2: auditoría de la cuenta de 40.000 pesos y escenarios de riesgo por operación (D3).

1) Modo «consolidado»: reimplementa cuenta() de consolidado.py y debe dar sus mismas cifras (comprobación).
2) Modo «real»: las restricciones del contado de Binance comprobadas hoy (exchangeInfo del 27/10/2026):
   paso de cantidad 0,00001 BTC, nocional mínimo 5 USDT; la comisión de compra (0,10 %) se cobra en BTC y deja
   «polvo» que se arrastra; con BNB (0,075 %) se paga aparte y no deja polvo (se supone saldo de BNB suficiente).
   Capital 12,5871 USDT (config.json: P2P 3.177,85 COP/USDT del 20/10).
3) Riesgo planeado frente a realizado: la pérdida real de cada operación frente a la que se planeó al entrar.
4) Monte Carlo por bloques de meses: distribución de la caída máxima y probabilidad de tocar el −20 %.
Uso: python3 -I b2_cuenta_pesos.py [BTC|ETH] > b2_cuenta_pesos_BTC.txt"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from metricas import cargar, CORTE_PRUEBA  # noqa: E402

ETQ = sys.argv[1] if len(sys.argv) > 1 else "BTC"
COP = 3177.85
CAP0 = 40000 / COP
PASO = {"BTC": 0.00001, "ETH": 0.0001}[ETQ]
T = cargar(ETQ)

# libro de la cuenta en pesos, igual que en la consolidación: P11, P05c final y P05b largo + patrón 1 h
libro = pd.concat([T[T.estrategia == "P11"], T[T.estrategia == "P05c"],
                   T[(T.estrategia == "P05b") & (T.lado > 0) & T.pat1h]])
libro = libro.sort_values("entrada", kind="stable").drop_duplicates(subset=["entrada"]).reset_index(drop=True)
libro["dist"] = np.where(libro.apertura.notna(), (libro.pe - libro.apertura).abs() / libro.pe, 0.03)


def cuenta(t, riesgo, com, modo="consolidado", tope_total=0.20, cap0=CAP0, bnb=True):
    """Devuelve dict con ops, saldo final en COP, caída máxima %, peor racha, omitidas por mínimo y riesgo realizado."""
    tope_d, tope_s = 2 * riesgo, 4 * riesgo
    efectivo, polvo = cap0, 0.0
    maxs, caida_max, libre = cap0, 0.0, None
    dia = sem = None
    pdia = psem = 0.0
    n = racha = peor = omit_min = 0
    perdidas_rel = []
    for r in t.itertuples():
        saldo = efectivo + polvo * r.pe
        if libre is not None and r.entrada < libre:
            continue
        if (maxs - saldo) / maxs >= tope_total:
            break
        d, w = r.entrada.normalize(), r.entrada.isocalendar()[:2]
        if d != dia:
            dia, pdia = d, 0.0
        if w != sem:
            sem, psem = w, 0.0
        if pdia <= -tope_d * saldo or psem <= -tope_s * saldo:
            continue
        noc = min(efectivo, riesgo * saldo / r.dist)
        if modo == "consolidado":
            if noc < 5:
                omit_min += 1
                continue
            g = noc * (r.bruto - 2 * com) / 100
            efectivo += g
        else:
            q = math.floor(noc / r.pe / PASO + 1e-9) * PASO
            if q * r.pe < 5 or q <= 0:
                omit_min += 1
                continue
            coste = q * r.pe
            if bnb:   # comisión en BNB: no toca la cantidad; se descuenta del efectivo
                q_neto = q
                efectivo -= coste * com / 100
            else:     # comisión en BTC: llega menos BTC
                q_neto = q * (1 - com / 100)
            q_venta = math.floor((q_neto + polvo) / PASO + 1e-9) * PASO
            polvo = max(q_neto + polvo - q_venta, 0.0)
            recibido = q_venta * r.px * (1 - (0 if bnb else com / 100))
            if bnb:
                efectivo -= q_venta * r.px * com / 100
            antes = saldo
            efectivo = efectivo - coste + recibido
            g = efectivo + polvo * r.px - antes
        nuevo = efectivo + polvo * r.px
        perdidas_rel.append(-g / saldo * 100 if g < 0 else 0.0)
        pdia += g
        psem += g
        n += 1
        racha = racha + 1 if g <= 0 else 0
        peor = max(peor, racha)
        maxs = max(maxs, nuevo)
        caida_max = max(caida_max, (maxs - nuevo) / maxs * 100)
        libre = r.salida
    final = efectivo + polvo * (t.px.iloc[-1] if len(t) else 0)
    return dict(ops=n, cop=final * COP, caida=caida_max, peor=peor, omit_min=omit_min,
                perdida_max=max(perdidas_rel) if perdidas_rel else 0.0,
                p95_perdida=np.percentile([x for x in perdidas_rel if x > 0], 95) if any(perdidas_rel) else 0.0)


TRAMOS = {"2020-2023": libro[libro.entrada < CORTE_PRUEBA], "2024-2026": libro[libro.entrada >= CORTE_PRUEBA]}


def anual(s, cop):
    anos = (s.entrada.max() - s.entrada.min()).days / 365.25
    return ((cop / 40000) ** (1 / anos) - 1) * 100


print(f"=== {ETQ}: libro de la cuenta en pesos = {len(libro)} operaciones "
      f"({libro.estrategia.value_counts().to_dict()}) · capital {CAP0:.4f} USDT · paso {PASO} ===")

print("\n1) COMPROBACIÓN: reimplementación de cuenta() de consolidado.py (debe coincidir con consolidado_*.txt)")
for riesgo in (0.015, 0.02, 0.025):
    for com in (0.075, 0.15):
        for tr, s in TRAMOS.items():
            r = cuenta(s, riesgo, com)
            print(f"  riesgo {riesgo * 100:.1f} % · comisión {com:.3f} · {tr}: {r['ops']} ops, saldo {r['cop']:,.0f} COP "
                  f"({(r['cop'] / 40000 - 1) * 100:+.1f} %, {anual(s, r['cop']):+.1f} %/año), caída máxima {r['caida']:.1f} %, peor racha {r['peor']}")

print("\n2) ESCENARIOS DE RIESGO CON LAS RESTRICCIONES REALES DEL CONTADO (paso, mínimo 5 USDT, comisión)")
print("   omit = operaciones que no caben por el mínimo de 5 USDT; pérd.máx = mayor pérdida de una operación en % del saldo")
filas = []
for riesgo in (0.0025, 0.005, 0.01, 0.02, 0.025):
    for nombre, com, bnb in (("BNB 0,075", 0.075, True), ("normal 0,10 en BTC", 0.10, False), ("doble 0,15 en BTC", 0.15, False)):
        for tr, s in TRAMOS.items():
            r = cuenta(s, riesgo, com, modo="real", bnb=bnb)
            ideal = cuenta(s, riesgo, com, modo="real", bnb=bnb, cap0=1_000_000 / COP)  # mismo libro, capital grande
            filas.append(dict(riesgo=f"{riesgo * 100:.2f} %", comision=nombre, tramo=tr, ops=r["ops"], omit=r["omit_min"],
                              final_cop=r["cop"], ret=(r["cop"] / 40000 - 1) * 100, anual=anual(s, r["cop"]),
                              caida=r["caida"], perd_max=r["perdida_max"], p95=r["p95_perdida"], racha=r["peor"],
                              anual_cap_grande=anual(s, ideal["cop"] * 40000 / 1_000_000), caida_cap_grande=ideal["caida"]))
tab = pd.DataFrame(filas)
pd.set_option("display.width", 250)
print(tab.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
tab.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"b2_riesgo_{ETQ}.csv"), index=False)

print("\n3) RIESGO PLANEADO FRENTE A REALIZADO (en % del nocional, operaciones que salieron por stop)")
for nb in ("P05b", "P05c", "P11"):
    x = libro[(libro.estrategia == nb) & (libro.motivo == "stop")]
    if len(x):
        real = -(x.bruto - 0.15) / 100
        ratio = real / x.dist
        print(f"  {nb}: {len(x)} stops · distancia planeada media {x.dist.mean() * 100:.2f} % · pérdida real media "
              f"{real.mean() * 100:.2f} % · real/planeada: mediana {ratio.median():.2f}, p90 {ratio.quantile(.9):.2f}, máx {ratio.max():.2f}")
cuota = libro.dist.lt(0.02 / 1.0)
print(f"  Operaciones cuya distancia al stop es menor que el riesgo (el tope «todo el saldo» limita el tamaño): "
      f"con 2 %: {(libro.dist < 0.02).mean() * 100:.0f} %; con 1 %: {(libro.dist < 0.01).mean() * 100:.0f} %")
print(f"  Distancia al stop: mediana {libro.dist.median() * 100:.2f} % · p10 {libro.dist.quantile(.1) * 100:.2f} % · p90 {libro.dist.quantile(.9) * 100:.2f} %")
nmin = {r: (np.minimum(1, r / libro.dist) * CAP0 < 5).mean() * 100 for r in (0.0025, 0.005, 0.01, 0.02)}
print("  Con el saldo inicial (12,59 USDT), % de operaciones cuyo tamaño por riesgo queda bajo 5 USDT: " +
      ", ".join(f"{k * 100:.2f} % de riesgo → {v:.0f} %" for k, v in nmin.items()))

print("\n4) MONTE CARLO (2.000 trayectorias de 2 años, meses de operaciones sorteados de TODO el historial, modo real BNB)")
rng = np.random.default_rng(2710)
libro["mes"] = libro.entrada.dt.strftime("%Y-%m")
meses = [g for _, g in libro.groupby("mes")]
todos_meses = pd.period_range(libro.entrada.min().tz_localize(None), libro.entrada.max().tz_localize(None), freq="M")
vacios = len(todos_meses) - len(meses)
for riesgo in (0.0025, 0.005, 0.01, 0.02, 0.025):
    caidas, finales, toca = [], [], 0
    for _ in range(2000):
        partes, base = [], pd.Timestamp("2030-01-01", tz="UTC")
        for k in range(24):
            j = rng.integers(0, len(meses) + vacios)
            if j >= len(meses):
                continue  # mes sin operaciones
            g = meses[j].copy()
            desplaz = base + pd.DateOffset(months=k) - g.entrada.iloc[0].normalize().replace(day=1)
            g["entrada"] = g.entrada + desplaz
            g["salida"] = g.salida + desplaz
            partes.append(g)
        s = pd.concat(partes).sort_values("entrada", kind="stable") if partes else libro.iloc[:0]
        if len(s) == 0:
            continue
        r = cuenta(s, riesgo, 0.075, modo="real", bnb=True)
        caidas.append(r["caida"])
        finales.append(r["cop"])
        toca += r["caida"] >= 20
    caidas, finales = np.array(caidas), np.array(finales)
    print(f"  riesgo {riesgo * 100:.2f} %: caída máx mediana {np.median(caidas):.1f} %, p95 {np.percentile(caidas, 95):.1f} % · "
          f"P(tocar −20 %) {toca / len(caidas) * 100:.1f} % · saldo a 2 años: p5 {np.percentile(finales, 5):,.0f}, "
          f"mediana {np.median(finales):,.0f}, p95 {np.percentile(finales, 95):,.0f} COP · P(perder) {(finales < 40000).mean() * 100:.0f} %")
