"""A1 (28/10/2026): ¿cuál es la ganancia DIARIA más alta que se puede sostener, y entra un 8 % o un 11 % al día?

Pedido de Nicolás: «si el 11 % rompe la cuenta, entonces mejor el 8 % diario o el porcentaje más óptimo de ganancia diaria;
analiza aún más esto».

Método:
- Operaciones reales del motor (investigacion/operaciones/ops_*.csv, velas de 1 m de futuros de Binance 2020-2026), con
  comisión de futuros (creador 0,02 / tomador 0,05) o doble.
- Dos carteras:
    BTC: P05c > P11 > P05b, una posición a la vez (el libro actual).
    LC:  P05c en los 7 activos (BTC, ETH, SOL, BNB, XRP, DOGE, ADA) + P11 y P05b de BTC, varias posiciones, riesgo abierto
         total ≤ 3 veces el riesgo por operación.
- Riesgo por operación f (fracción del saldo que se pierde si salta el stop planeado). Pérdida máxima por operación: el saldo.
- Crecimiento por día = (saldo final / saldo inicial)^(1/días) − 1, en días de calendario (cripto opera todos los días).
- Monte Carlo a 12 meses: se sortean meses enteros del historial (respeta las rachas), 3.000 trayectorias, con la ventaja
  medida, la mitad de la ventaja y sin ventaja (se resta a cada operación la parte correspondiente de su media en R).
- «Óptimo robusto»: el f que da la mayor mediana a 12 meses promediando los tres escenarios en logaritmo (no apuesta a que la
  ventaja medida sea la verdadera).
Uso: python -I a1_riesgo_diario.py > a1_riesgo_diario.txt   (desde investigacion/plan-diario/)"""
import os
import sys

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
OPS = os.path.join(AQUI, "..", "operaciones")
ACTIVOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
COP = 3177.85
E0 = 40000 / COP


def cargar(doble=False):
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
    k = 2 if doble else 1
    t["neto"] = t.bruto - k * np.where(cr, 0.02, 0.05) - k * 0.05
    t["dist"] = np.where(t.apertura.notna(), (t.pe - t.apertura).abs() / t.pe, 0.03)
    t["R"] = t.neto / 100 / t.dist
    t["e"] = t.entrada.map(lambda v: int(v.timestamp()))
    t["s"] = t.salida.map(lambda v: int(v.timestamp()))
    return t


def cartera(t, nombre):
    if nombre == "BTC":
        b = t[(t.activo == "BTC") & t.estrategia.isin(["P05c", "P11", "P05b"])].copy()
        b["p"] = b.estrategia.map({"P05c": 0, "P11": 1, "P05b": 2})
        b = b.sort_values(["e", "p"]).drop_duplicates("e")
        keep, libre = [], -1
        for r in b.itertuples():
            if r.e < libre:
                continue
            keep.append(r.Index)
            libre = r.s
        return b.loc[keep].sort_values("e").reset_index(drop=True), 1
    c = t[(t.estrategia == "P05c") | ((t.activo == "BTC") & t.estrategia.isin(["P11", "P05b"]))]
    return c.sort_values("e").reset_index(drop=True), 3


def simular(e, s, R, f, max_abiertas):
    """Saldo relativo final, caída máxima y serie diaria, con varias posiciones a la vez (riesgo f cada una)."""
    ev = sorted([(e[i], 1, i) for i in range(len(e))] + [(s[i], 0, i) for i in range(len(e))])
    E, pico, cm, abiertas, tam = 1.0, 1.0, 0.0, 0, {}
    for t, tipo, i in ev:
        if tipo == 1:
            if abiertas >= max_abiertas or E <= 1e-6:
                continue
            tam[i] = f * E
            abiertas += 1
        elif i in tam:
            E += max(tam.pop(i) * R[i], -E)
            abiertas -= 1
            pico = max(pico, E)
            cm = max(cm, 1 - E / pico if pico > 0 else 1)
    return E, cm


def tabla_historia(t, nombre):
    c, mx = cartera(t, nombre)
    e, s, R = c.e.to_numpy(), c.s.to_numpy(), c.R.to_numpy()
    dias = (s.max() - e.min()) / 86400
    print(f"\n== {nombre}: {len(c)} operaciones en {dias:.0f} días ({len(c) / dias:.2f} por día), R medio {R.mean():+.3f} ==")
    print("riesgo   crec./día   al año    caída máx.   40.000 COP terminan en")
    mejor = (None, -9)
    for f in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.19, 0.25, 0.35, 0.50]:
        E, cm = simular(e, s, R, f, mx)
        g = E ** (1 / dias) - 1 if E > 0 else -1
        if g > mejor[1]:
            mejor = (f, g)
        print(f"{f * 100:5.0f} %  {g * 100:+8.3f} %  {((1 + g) ** 365 - 1) * 100:+8.0f} %  {cm * 100:8.0f} %   {E * 40000:>16,.0f}")
    print(f"MÁXIMO de la curva en la historia: riesgo {mejor[0] * 100:.0f} % -> {mejor[1] * 100:+.3f} % por día")
    return c, mx


def montecarlo(c, mx, recortes=(0.0, 0.5, 1.0), sims=1500, meses=12, semilla=7):
    c = c.copy()
    c["mes"] = pd.to_datetime(c.e, unit="s", utc=True).dt.strftime("%Y-%m")
    lista = sorted(c.mes.unique())
    m = c.R.mean()
    bloques = {k: (g.e.to_numpy() - g.e.min(), g.s.to_numpy() - g.e.min(), g.R.to_numpy()) for k, g in c.groupby("mes")}
    rng = np.random.default_rng(semilla)
    sorteo = rng.integers(0, len(lista), (sims, meses))
    out = {}
    for rec in recortes:
        for f in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.19, 0.25]:
            fin, ruina = [], 0
            for fila in sorteo:
                E_tot = 1.0
                for j in fila:
                    e, s, R = bloques[lista[j]]
                    E, _ = simular(e, s, R - rec * m, f, mx)
                    E_tot *= E
                    if E_tot <= 0.05:
                        break
                fin.append(E_tot)
                ruina += E_tot <= 0.05
            fin = np.array(fin)
            out[(rec, f)] = (np.median(fin), np.percentile(fin, 5), (fin < 1).mean(), ruina / sims)
    return out


def main():
    print("A1 · ganancia diaria sostenible según el riesgo por operación (comisión de futuros base)")
    t = cargar()
    resultados = {}
    for nombre in ("BTC", "LC"):
        c, mx = tabla_historia(t, nombre)
        mc = montecarlo(c, mx)
        resultados[nombre] = mc
        print(f"\n   Monte Carlo 12 meses ({nombre}): mediana de 40.000 COP · p5 · P(perder) · P(ruina)  ->  crecimiento diario de la mediana")
        for rec, nom in ((0.0, "ventaja medida"), (0.5, "mitad de la ventaja"), (1.0, "sin ventaja")):
            print(f"   -- {nom} --")
            for f in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.19, 0.25]:
                med, p5, pp, pr = mc[(rec, f)]
                gd = med ** (1 / 365) - 1 if med > 0 else -1
                print(f"   {f * 100:4.0f} %: {med * 40000:>10,.0f} · {p5 * 40000:>9,.0f} · {pp * 100:4.0f} % · {pr * 100:4.1f} %  ->  {gd * 100:+.3f} %/día")
        # óptimo robusto: media de log(mediana) en los tres escenarios
        mejor = max([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.19, 0.25],
                    key=lambda f: np.mean([np.log(max(mc[(r, f)][0], 1e-9)) for r in (0.0, 0.5, 1.0)]))
        meds = [mc[(r, mejor)][0] for r in (0.0, 0.5, 1.0)]
        print(f"   ÓPTIMO ROBUSTO ({nombre}): riesgo {mejor * 100:.0f} % por operación · medianas a 12 meses "
              f"{meds[0] * 40000:,.0f} / {meds[1] * 40000:,.0f} / {meds[2] * 40000:,.0f} COP (medida / mitad / sin ventaja)")
    print("\nLo que exigiría una meta fija diaria (crecimiento compuesto desde 40.000 COP):")
    for g in (0.11, 0.08, 0.05, 0.03, 0.01, 0.005, 0.002):
        print(f"   {g * 100:5.1f} % diario -> 30 días {40000 * (1 + g) ** 30:>16,.0f} · 365 días {40000 * (1 + g) ** 365:>26,.0f} COP")


if __name__ == "__main__":
    main()
