"""A2 (28/10/2026): ¿qué estrategias, solas o combinadas, generan más retorno y más rendimiento por riesgo?

Pedido de Nicolás: «quitas algunas estrategias, pones otras, de a una, de a varias; analizas cuáles son las mejores
combinaciones, cuáles generan más retorno y cuáles más rendimiento».

- 10 piezas: P05b, P05c, P11, N8 y N9 en BTC, y las mismas en las 6 altcoins (ETH, SOL, BNB, XRP, DOGE, ADA) juntas.
- Las 1.023 combinaciones posibles, cada una como cartera con 5 % de riesgo por operación (el óptimo robusto de A1) y hasta
  3 posiciones abiertas; comisión de futuros base (creador 0,02 / tomador 0,05).
- Cada combinación se simula por separado en 2020-2023 (donde se elige) y en 2024-2026 (donde se comprueba, sin volver a elegir).
- Retorno = crecimiento por día del saldo. Rendimiento por riesgo = Sharpe diario anualizado y Calmar (retorno anual / caída máx.).
- N9: su stop es el punto medio del rango de Asia, que no está en ops_*.csv; se aproxima con la mediana de |bruto| de sus
  operaciones que salieron por stop en ese activo (marcado «aprox.»).
Uso: python -I a2_combinaciones.py > a2_combinaciones.txt   (desde investigacion/plan-diario/)"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
OPS = os.path.join(AQUI, "..", "operaciones")
ACTIVOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
ESTR = ["P05b", "P05c", "P11", "N8", "N9"]
CORTE = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
F, MAX_ABIERTAS = 0.05, 3


def cargar():
    t = []
    for a in ACTIVOS:
        x = pd.read_csv(os.path.join(OPS, f"ops_{a}.csv"), parse_dates=["entrada", "salida"])
        for c in ("entrada", "salida"):
            if x[c].dt.tz is None:
                x[c] = x[c].dt.tz_localize("UTC")
        x["activo"] = a
        t.append(x)
    t = pd.concat(t, ignore_index=True)
    cr = t.creador.astype(bool).to_numpy()
    t["neto"] = t.bruto - np.where(cr, 0.02, 0.05) - 0.05
    dist = np.where(t.apertura.notna(), (t.pe - t.apertura).abs() / t.pe, np.where(t.estrategia.isin(["P11", "N8"]), 0.03, np.nan))
    t["dist"] = dist
    for a in ACTIVOS:  # N9: aproximación de la distancia al stop
        m = (t.activo == a) & (t.estrategia == "N9")
        d9 = (t.loc[m & (t.motivo == "stop"), "bruto"].abs() / 100).median()
        t.loc[m, "dist"] = d9
    t["R"] = t.neto / 100 / t.dist
    t["e"] = t.entrada.map(lambda v: int(v.timestamp()))
    t["s"] = t.salida.map(lambda v: int(v.timestamp()))
    t["pieza"] = t.estrategia + np.where(t.activo == "BTC", "·BTC", "·ALT")
    return t


def simular(e, s, R):
    """Saldo relativo, caída máxima y serie diaria de P&L relativo (por fecha de salida)."""
    orden = np.lexsort((np.zeros(len(e)), e))
    ev = sorted([(e[i], 1, i) for i in orden] + [(s[i], 0, i) for i in orden])
    E, pico, cm, abiertas, tam, dia = 1.0, 1.0, 0.0, 0, {}, {}
    for t, tipo, i in ev:
        if tipo == 1:
            if abiertas >= MAX_ABIERTAS or E <= 1e-6:
                continue
            tam[i] = F * E
            abiertas += 1
        elif i in tam:
            g = max(tam.pop(i) * R[i], -E)
            d = t // 86400
            base = dia.setdefault(d, [E, 0.0])
            base[1] += g
            E += g
            abiertas -= 1
            pico = max(pico, E)
            cm = max(cm, 1 - E / pico if pico > 0 else 1)
    return E, cm, dia


def metricas(sub, ini, fin):
    if len(sub) == 0:
        return None
    E, cm, dia = simular(sub.e.to_numpy(), sub.s.to_numpy(), sub.R.to_numpy())
    ndias = (fin - ini) / 86400
    g = E ** (1 / ndias) - 1 if E > 0 else -1
    serie = np.zeros(int(ndias) + 2)
    for d, (b, p) in dia.items():
        k = int(d - ini // 86400)
        if 0 <= k < len(serie) and b > 0:
            serie[k] += p / b
    sharpe = serie.mean() / serie.std() * np.sqrt(365) if serie.std() > 0 else 0.0
    anual = (1 + g) ** 365 - 1
    return {"g": g, "anual": anual, "cm": cm, "sharpe": sharpe, "calmar": anual / cm if cm > 0 else 0.0, "n": len(sub)}


def main():
    t = cargar()
    piezas = sorted(t.pieza.unique(), key=lambda p: (p.split("·")[1], ESTR.index(p.split("·")[0])))
    ini_tr, fin_tr = int(pd.Timestamp("2020-03-01", tz="UTC").timestamp()), CORTE
    ini_te, fin_te = CORTE, int(t.s.max())
    tr, te = t[t.e < CORTE], t[t.e >= CORTE]
    filas = []
    for k in range(1, len(piezas) + 1):
        for comb in itertools.combinations(piezas, k):
            a = metricas(tr[tr.pieza.isin(comb)], ini_tr, fin_tr)
            b = metricas(te[te.pieza.isin(comb)], ini_te, fin_te)
            if a and b:
                filas.append({"comb": " + ".join(comb), "k": k, **{f"tr_{x}": v for x, v in a.items()},
                              **{f"te_{x}": v for x, v in b.items()}})
    R = pd.DataFrame(filas)
    R["rk_tr"] = R.tr_g.rank(ascending=False)
    R["rk_te"] = R.te_g.rank(ascending=False)
    fmt = lambda r: (f"{r.comb[:78]:78s} {r.k:2d} | {r.tr_g * 100:+.3f} %/d {r.tr_cm * 100:3.0f} % Sh {r.tr_sharpe:4.2f} |"
                     f" {r.te_g * 100:+.3f} %/d {r.te_cm * 100:3.0f} % Sh {r.te_sharpe:4.2f} | puesto 24-26: {int(r.rk_te):4d}")
    print(f"A2 · {len(R)} combinaciones de {len(piezas)} piezas, 5 % de riesgo, hasta 3 posiciones. Elegir en 2020-23, comprobar en 2024-26.")
    print("Columnas: combinación, piezas | 2020-23: crecimiento por día, caída máx., Sharpe | 2024-26: lo mismo | puesto en 2024-26 por crecimiento")
    print("\n== CADA PIEZA SOLA ==")
    for r in R[R.k == 1].sort_values("tr_g", ascending=False).itertuples():
        print(fmt(r))
    print("\n== LAS 15 MEJORES POR RETORNO EN 2020-23 (y cómo les fue después) ==")
    for r in R.sort_values("tr_g", ascending=False).head(15).itertuples():
        print(fmt(r))
    print("\n== LAS 15 MEJORES POR RENDIMIENTO (Sharpe) EN 2020-23 ==")
    for r in R.sort_values("tr_sharpe", ascending=False).head(15).itertuples():
        print(fmt(r))
    print("\n== LAS 10 QUE MEJOR SE SOSTIENEN: buen puesto en los dos tramos (suma de puestos) ==")
    R["rk_suma"] = R.rk_tr + R.rk_te
    for r in R.sort_values("rk_suma").head(10).itertuples():
        print(fmt(r))
    rho = R[["rk_tr", "rk_te"]].corr(method="spearman").iloc[0, 1]
    print(f"\n¿Elegir en 2020-23 sirve para 2024-26? Correlación de puestos (Spearman): {rho:+.2f}")
    top = R.sort_values("tr_g", ascending=False).head(50)
    print(f"Las 50 mejores de 2020-23 quedan en 2024-26 en el puesto mediano {top.rk_te.median():.0f} de {len(R)}")
    print("\nCuánto aporta cada pieza (media del crecimiento diario de las combinaciones CON ella menos SIN ella):")
    for p in piezas:
        con = R[R.comb.str.contains(p, regex=False)]
        sin = R[~R.comb.str.contains(p, regex=False)]
        print(f"   {p:9s}  2020-23 {(con.tr_g.mean() - sin.tr_g.mean()) * 100:+.4f} %/d · 2024-26 {(con.te_g.mean() - sin.te_g.mean()) * 100:+.4f} %/d")


if __name__ == "__main__":
    main()
