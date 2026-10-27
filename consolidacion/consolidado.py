"""Consolidación final (27/10/2026): una sola prueba, con el motor corregido, de todo lo que sigue vivo.

Pedido de Nicolás: quedarse solo con lo positivo; que las velas de los otros tiempos confirmen «un poquito» la
tendencia (sin RSI); arriesgar un poco más; separar los libros por horario; sin una sola falla.

Reglas fijadas ANTES de ver los resultados:
- Contexto = cierre diario de ayer frente a su SMA 50 (manda el lado: largos sobre ella, cortos bajo ella).
- Confirmación suave de los otros tiempos, evaluada en el instante de la SEÑAL con velas ya cerradas:
    para lo que opera en 15 min (P05b, P05c, N9): 1 h, 4 h y 1 día, cada uno «a favor» si su último cierre está del
    lado de la operación respecto de su EMA 20; y el patrón del curso en las 3 últimas velas de 1 h.
    Variantes: e1h, e4h, «suave» (al menos 1 de 1 h y 4 h), «mayoría» (2 de 3), «todos» (3 de 3), pat1h.
    para lo que opera en el día (P11, N8): la semana anterior (lunes 00:00 a domingo 23:59) cerró a favor.
- Elección: en el ajuste (2020-2023), la variante con mejor media neta con comisión doble entre las que conservan al
  menos el 40 % de las operaciones de la base. Se mira la prueba (2024-2026) una sola vez. Se adopta solo si en la
  prueba también mejora la media neta de la base; si no, se queda la base.
- Comisión: futuros tomador 0,05 %/lado, creador 0,02 %; el doble: 0,10 % y 0,04 %. Cuenta en pesos: contado 0,10 %.

Uso: python3 -I consolidado.py [ruta_velas.npy] [etiqueta]"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # con -I el directorio del script no está en la ruta
if len(sys.argv) > 1 and sys.argv[1].endswith(".npy"):  # al importarlo desde otro programa, sus argumentos no son de aquí
    os.environ["DATOS_BTC"] = sys.argv[1]
ETQ = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1].endswith(".npy") else "BTC"

from lib import cargar, remuestrear, patrones, CORTE  # noqa: E402
from sim import Velas, p11, p05b, a_tabla, netos, azar, op  # noqa: E402

V = Velas(cargar())
m1 = V.df
c15 = remuestrear(m1, 15)
rng = np.random.default_rng(2710)


# ---------- indicadores de los otros tiempos (valor disponible al cierre de cada vela) ----------
class Marco:
    def __init__(self, minutos):
        self.tf = pd.Timedelta(minutes=minutos)
        df = remuestrear(m1, minutos)
        self.ape = df.index
        self.c = df.c.to_numpy()
        self.ema = df.c.ewm(span=20, adjust=False).mean().to_numpy()
        pat, lado = patrones(df)
        alc = pat[[k for k, s in lado.items() if s > 0]].any(axis=1)
        baj = pat[[k for k, s in lado.items() if s < 0]].any(axis=1)
        self.alc3 = (alc.rolling(3, min_periods=1).max() > 0).to_numpy()
        self.baj3 = (baj.rolling(3, min_periods=1).max() > 0).to_numpy()

    def j(self, t):
        """Índice de la última vela CERRADA en el instante t."""
        return int(self.ape.searchsorted(t - self.tf, side="right")) - 1

    def a_favor(self, t, lado):
        j = self.j(t)
        return j >= 0 and lado * (self.c[j] - self.ema[j]) > 0

    def patron(self, t, lado):
        j = self.j(t)
        return j >= 0 and bool(self.alc3[j] if lado > 0 else self.baj3[j])


H1, H4, D1 = Marco(60), Marco(240), Marco(1440)
dd = remuestrear(m1, 1440)
sma50 = dd.c.rolling(50).mean()
wk = dd.c  # para la semana: cierre del domingo frente al del domingo anterior


def contexto(t):
    ayer = t.normalize() - pd.Timedelta(days=1)
    if ayer not in sma50.index or np.isnan(sma50.loc[ayer]):
        return 0
    return int(np.sign(dd.c.loc[ayer] - sma50.loc[ayer]))


def semana(t, lado):
    dom = t.normalize() - pd.Timedelta(days=((t.weekday() + 1) % 7) or 7)  # último domingo antes de t
    prev = dom - pd.Timedelta(days=7)
    if dom not in wk.index or prev not in wk.index:
        return False
    return lado * (wk.loc[dom] - wk.loc[prev]) > 0


CONF15 = {
    "(base)": lambda t, l: True,
    "e1h": lambda t, l: H1.a_favor(t, l),
    "e4h": lambda t, l: H4.a_favor(t, l),
    "suave 1 de 1h/4h": lambda t, l: H1.a_favor(t, l) or H4.a_favor(t, l),
    # int(): sumar dos np.bool_ da True (o lógico), no 2. Falla encontrada el 27/10 (daba 0 operaciones).
    "mayoría 2 de 3": lambda t, l: int(H1.a_favor(t, l)) + int(H4.a_favor(t, l)) + int(D1.a_favor(t, l)) >= 2,
    "todos 3 de 3": lambda t, l: H1.a_favor(t, l) and H4.a_favor(t, l) and D1.a_favor(t, l),
    "patrón 1h": lambda t, l: H1.patron(t, l),
}
CONFD = {"(base)": lambda t, l: True, "semana a favor": semana}


# ---------- estrategias (señal registrada en cada operación) ----------
def n9(V, desde_h=7, hasta_h=13):
    """Rango de Asia (00-07 UTC) roto en Londres, en el lado del contexto. Límite 60 min en el nivel; stop con un cierre
    de 15 m que vuelve al punto medio; salida 23:59."""
    ops = []
    for d in pd.date_range(V.t[0].normalize() + pd.Timedelta(days=60), V.t[-1].normalize(), freq="D"):
        lado = contexto(d)
        if lado == 0:
            continue
        a = m1.loc[d: d + pd.Timedelta(hours=6, minutes=59)]
        if len(a) < 400:
            continue
        ah, al = a.h.max(), a.l.min()
        nv, medio = (ah if lado > 0 else al), (ah + al) / 2
        b = c15.loc[d + pd.Timedelta(hours=desde_h): d + pd.Timedelta(hours=hasta_h) - pd.Timedelta(minutes=15)]
        cl = b.c.to_numpy()
        j = next((i for i, x in enumerate(cl) if lado * (x - nv) > 0), None)
        if j is None:
            continue
        ts = b.index[j] + pd.Timedelta(minutes=15)
        a0, a1 = V.i(ts), min(V.i(ts + pd.Timedelta(minutes=60)) - 1, len(V.t) - 1)
        seg = V.l[a0:a1 + 1] < nv if lado > 0 else V.h[a0:a1 + 1] > nv
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        ie = a0 + kk[0]
        fin = d + pd.Timedelta(hours=23, minutes=59)
        ifin = V.i(fin)
        if ifin >= len(V.t) or V.t[ifin] != fin:
            continue
        ix, px, mot = ifin, V.c[ifin], "tiempo"
        for tb, row in c15.loc[V.t[ie].floor("15min"): d + pd.Timedelta(hours=23, minutes=30)].iterrows():
            if lado * (row.c - medio) <= 0:
                ix, px, mot = V.i(tb + pd.Timedelta(minutes=14)), row.c, "stop"; break
        ops.append(op(V, ie, ix, lado, nv, px, mot, creador=True, senal=ts))
    return ops


def con_ctx(ops, solo_largo=False):
    out = []
    for o in ops:
        t = o.get("senal", o["entrada"])
        c = contexto(t)
        if c != 0 and o["lado"] == c and (not solo_largo or o["lado"] > 0):
            out.append(o)
    return out


def hasta21(ops):
    return [o for o in ops if o.get("senal", o["entrada"]).hour < 21 or
            (o.get("senal", o["entrada"]).hour == 21 and o.get("senal", o["entrada"]).minute == 0)]


p11s = p11(V)
for o in p11s:
    o["senal"] = o["entrada"]
n8s = p11(V, dias_semana=(2,))
for o in n8s:
    o["senal"] = o["entrada"]
BASES = {
    "PRINCIPAL P05b por régimen": (hasta21(con_ctx(p05b(V))), CONF15),
    "PRINCIPAL P11 con contexto": (con_ctx(p11s, solo_largo=True), CONFD),
    "PRINCIPAL P05c largo con contexto": (hasta21(con_ctx(p05b(V, k=1.0, lados=(1,)), solo_largo=True)), CONF15),
    "PRUEBA N9 Asia-Londres": (n9(V), CONF15),
    "PRUEBA N8 miércoles con contexto": (con_ctx(n8s, solo_largo=True), CONFD),
}


def medir(t, conf):
    k = np.array([conf(r.senal, r.lado) for r in t.itertuples()]) if len(t) else np.array([], bool)
    out = {}
    for tr in ("aj", "pr"):
        sel = (t.entrada < CORTE).to_numpy() if tr == "aj" else (t.entrada >= CORTE).to_numpy()
        x, x2, kk = t.n.to_numpy()[sel], t.d.to_numpy()[sel], k[sel]
        nk = int(kk.sum())
        pct = np.nan
        if 0 < nk < len(x):
            sims = np.array([x[rng.choice(len(x), nk, replace=False)].mean() for _ in range(2000)])
            pct = (sims < x[kk].mean()).mean() * 100
        out[tr] = dict(ops=nk, base=len(x), neto=x[kk].sum(), doble=x2[kk].sum(),
                       media=x[kk].mean() if nk else np.nan, media2=x2[kk].mean() if nk else np.nan, pct=pct)
    return out, k


def informe():
    pd.set_option("display.width", 260)
    print(f"=== {ETQ}: {len(V.t):,} velas de 1 min, {V.t[0]:%Y-%m-%d} a {V.t[-1]:%Y-%m-%d} ===")
    FINAL = {}
    filas = []
    for nb, (ops, confs) in BASES.items():
        t = a_tabla(ops)
        t["n"] = netos(t, 0.05, 0.02)
        t["d"] = netos(t, 0.10, 0.04)
        res = {}
        for cn, cf in confs.items():
            r, k = medir(t, cf)
            res[cn] = (r, k)
            filas.append(dict(estrategia=nb, confirmación=cn,
                              ops_aj=r["aj"]["ops"], neto_aj=r["aj"]["neto"], doble_aj=r["aj"]["doble"], media2_aj=r["aj"]["media2"], pct_aj=r["aj"]["pct"],
                              ops_pr=r["pr"]["ops"], neto_pr=r["pr"]["neto"], doble_pr=r["pr"]["doble"], media_pr=r["pr"]["media"], pct_pr=r["pr"]["pct"]))
        base = res["(base)"][0]
        cands = [(cn, r) for cn, (r, k) in res.items() if cn != "(base)" and r["aj"]["ops"] >= 0.4 * base["aj"]["ops"]]
        elegida = max(cands, key=lambda x: x[1]["aj"]["media2"]) if cands else ("(base)", base)
        cn, r = elegida
        adopta = cn != "(base)" and r["pr"]["media"] > base["pr"]["media"] and r["aj"]["media2"] > base["aj"]["media2"]
        final = cn if adopta else "(base)"
        FINAL[nb] = (t[res[final][1]].copy(), final)
        print(f"{nb}: candidata elegida en el ajuste «{cn}» (media doble aj {r['aj']['media2']:+.3f} vs base {base['aj']['media2']:+.3f}); "
              f"prueba media {r['pr']['media']:+.3f} vs base {base['pr']['media']:+.3f} -> {'SE ADOPTA' if adopta else 'NO se adopta: queda la base'}")

    tabla = pd.DataFrame(filas)
    tabla.to_csv(f"consolidado_{ETQ}.csv", index=False)
    print("\nTODAS LAS VARIANTES (media2 = media neta con comisión doble; pct = percentil frente a subconjuntos al azar de la base)")
    print(tabla.to_string(float_format=lambda v: f"{v:.2f}"))

    # ---------- resumen final por estrategia y por año ----------
    print("\nSISTEMA CONSOLIDADO: cada estrategia con su versión final, año por año (neto en %, futuros 0,05/0,02)")
    anual = {}
    for nb, (t, final) in FINAL.items():
        t["anio"] = t.entrada.dt.year
        anual[f"{nb} [{final}]"] = t.groupby("anio").n.sum()
    an = pd.DataFrame(anual).fillna(0).round(1)
    print(an.T.to_string())
    for nb, (t, final) in FINAL.items():
        aj, pr = t[t.entrada < CORTE], t[t.entrada >= CORTE]
        az = azar(V, t, sims=400)
        print(f"{nb} [{final}]: {len(t)} ops | ajuste {len(aj)} {aj.n.sum():+.1f} % (doble {aj.d.sum():+.1f}) | prueba {len(pr)} "
              f"{pr.n.sum():+.1f} % (doble {pr.d.sum():+.1f}) | años positivos {(an[[c for c in an.columns if c.startswith(nb)][0]] > 0).sum()}/{len(an)} | "
              f"percentil frente al azar {(az < t.n.sum()).mean() * 100:.0f}")


    # ---------- cuenta de 40.000 pesos: solo lo que sobrevive al CONTADO con comisión doble ----------
    # Contado BTCUSDT: 0,10 %/lado (0,075 % pagando con BNB, binance.com/en/fee/trading, 25/10). Solo largos (sin apalancamiento).
    # Piezas candidatas: los largos de cada estrategia del libro PRINCIPAL, con su versión final, y P05b largo + patrón 1 h.
    def spot(t, com):
        return t.bruto.to_numpy() - 2 * com


    p05_reg = FINAL["PRINCIPAL P05b por régimen"][0]
    pat_mask = np.array([H1.patron(r.senal, r.lado) for r in p05_reg.itertuples()]) if len(p05_reg) else np.array([], bool)
    PIEZAS = {
        "P11 con contexto": FINAL["PRINCIPAL P11 con contexto"][0],
        "P05c largo (final)": FINAL["PRINCIPAL P05c largo con contexto"][0],
        "P05b largo con contexto": p05_reg[p05_reg.lado > 0],
        "P05b largo con contexto + patrón 1h": p05_reg[(p05_reg.lado > 0).to_numpy() & pat_mask],
    }
    print("\nPIEZAS EN CONTADO (solo largos): neto con 0,075 %/lado (BNB) y con el doble 0,15 %/lado")
    validas = []
    for nb, t in PIEZAS.items():
        aj, pr = t[t.entrada < CORTE], t[t.entrada >= CORTE]
        r = {tr: (len(x), spot(x, 0.075).sum(), spot(x, 0.15).sum()) for tr, x in (("aj", aj), ("pr", pr))}
        ok = r["aj"][2] > 0 and r["pr"][2] > 0
        if ok:
            validas.append(nb)
        print(f"  {nb}: ajuste {r['aj'][0]} ops {r['aj'][1]:+.1f} % (doble {r['aj'][2]:+.1f}) | prueba {r['pr'][0]} ops {r['pr'][1]:+.1f} % "
              f"(doble {r['pr'][2]:+.1f}) -> {'ENTRA en la cuenta en pesos' if ok else 'fuera: no resiste el contado con comisión doble'}")


    def cuenta(t, riesgo, com, tope_d, tope_s, tope_total=0.20):
        COP, ini = 3177.85, 40000 / 3177.85
        saldo, maxs, caida_max, libre = ini, ini, 0.0, None
        dia = sem = None
        pdia = psem = 0.0
        n = 0
        racha = peor = 0
        for r in t.sort_values("entrada").itertuples():
            if libre is not None and r.entrada < libre:
                continue
            if (maxs - saldo) / maxs >= tope_total:
                break  # parada total: se vuelve a papel
            d, w = r.entrada.normalize(), r.entrada.isocalendar()[:2]
            if d != dia:
                dia, pdia = d, 0.0
            if w != sem:
                sem, psem = w, 0.0
            if pdia <= -tope_d * saldo or psem <= -tope_s * saldo:
                continue
            ap = getattr(r, "apertura", np.nan)
            dist = abs(r.pe - ap) / r.pe if not (ap is None or np.isnan(ap)) else 0.03
            noc = min(saldo, riesgo * saldo / dist)
            if noc < 5:
                continue
            g = noc * (r.bruto - 2 * com) / 100
            saldo += g; pdia += g; psem += g; n += 1
            racha = racha + 1 if g <= 0 else 0
            peor = max(peor, racha)
            maxs = max(maxs, saldo)
            caida_max = max(caida_max, (maxs - saldo) / maxs * 100)
            libre = r.salida
        return n, saldo * COP, caida_max, peor


    libro = pd.concat([PIEZAS[k] for k in validas]) if validas else pd.DataFrame()
    if "apertura" not in libro.columns:
        libro["apertura"] = np.nan
    libro = libro.sort_values("entrada").drop_duplicates(subset=["entrada"])
    print(f"\nCUENTA DE 40.000 PESOS con {', '.join(validas)} (una posición; topes 2x el riesgo al día, 4x a la semana; parada total con -20 %)")
    for riesgo in (0.015, 0.02, 0.025):
        for com in (0.075, 0.15):
            for tramo, s in (("2020-2023", libro[libro.entrada < CORTE]), ("2024-2026", libro[libro.entrada >= CORTE])):
                n, final_cop, cmax, peor = cuenta(s, riesgo, com, 2 * riesgo, 4 * riesgo)
                anos = (s.entrada.max() - s.entrada.min()).days / 365.25
                print(f"  riesgo {riesgo * 100:.1f} % · comisión {com:.3f} · {tramo}: {n} ops, saldo {final_cop:,.0f} COP "
                      f"({(final_cop / 40000 - 1) * 100:+.1f} %, {((final_cop / 40000) ** (1 / anos) - 1) * 100:+.1f} %/año), "
                      f"caída máxima {cmax:.1f} %, peor racha {peor}")


if __name__ == "__main__":
    informe()
