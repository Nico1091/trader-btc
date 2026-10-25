"""Tarea 5: cada estrategia vigente y nueva en la semana del lunes 19 al viernes 23 de octubre de 2026,
con velas de 1 minuto de futuros USDⓈ-M BTCUSDT. Resultado neto por operación y por día.
Futuros: tomador 0,05 %/lado, creador 0,02 %. Contado (N1, N2c, N2v): 0,10 %/lado.
Las estrategias corren sobre toda la historia (para que los indicadores y la posición abierta sean los reales)
y luego se filtran las entradas de la semana. Testigo: 2.000 sorteos de entradas al azar en la semana."""
import numpy as np
import pandas as pd
from lib import cargar
from sim import Velas, p11, p05b, n3, mezcla, indicadores_1h, VetoVelas, a_tabla, netos

V = Velas(cargar())
h1, rp, pend = indicadores_1h(V.df)
veto = VetoVelas(V.df, 60, 3)
ini, fin = pd.Timestamp("2026-10-19", tz="UTC"), pd.Timestamp("2026-10-24", tz="UTC")

estr = {
    "P11 (futuros)": (p11(V), "fut"),
    "P05b k0,5 (futuros)": (p05b(V), "fut"),
    "P05b solo largo (futuros)": (p05b(V, lados=(1,)), "fut"),
    "P05b + veto 1h (futuros)": (p05b(V, veto=veto), "fut"),
    "P05c k1,0 (futuros)": (p05b(V, k=1.0), "fut"),
    "MEZCLA reglas (futuros)": (mezcla(V, h1, rp, pend), "fut"),
    "MEZCLA + veto 1h (futuros)": (mezcla(V, h1, rp, pend, veto=veto), "fut"),
    "N1 P11 en contado": (p11(V), "spot"),
    "N2v P05b largo + veto 1h (contado)": (p05b(V, lados=(1,), veto=veto), "spot"),
    "N2c P05c largo (contado)": (p05b(V, k=1.0, lados=(1,)), "spot"),
    "N3 retroceso x0,5 2 días (descartada)": (n3(V, 0.5, True), "spot"),
}

pd.set_option("display.width", 250)
filas = []
print("OPERACIONES DE LA SEMANA 19-23/10/2026")
for nombre, (ops, merc) in estr.items():
    t = a_tabla(ops)
    s = t[(t.entrada >= ini) & (t.entrada < fin)].copy()
    if len(s):
        s["neto"] = netos(s, 0.05, 0.02) if merc == "fut" else netos(s, 0.10, 0.10)
        s["doble"] = netos(s, 0.10, 0.04) if merc == "fut" else netos(s, 0.20, 0.20)
        for _, r in s.iterrows():
            print(f"{nombre:40s} {r.entrada:%a %d %H:%M} -> {r.salida:%a %d %H:%M} "
                  f"{'LARGO' if r.lado > 0 else 'CORTO'} entrada {r.pe:,.1f} salida {r.px:,.1f} "
                  f"{r.motivo:9s} bruto {r.bruto:+.2f} % neto {r.neto:+.2f} %")
            filas.append(dict(estrategia=nombre, dia=r.entrada.strftime("%a %d"), bruto=r.bruto, neto=r.neto, doble=r.doble))
    else:
        print(f"{nombre:40s} sin operaciones en la semana")
        filas.append(dict(estrategia=nombre, dia="-", bruto=0.0, neto=0.0, doble=0.0, vacia=True))

t = pd.DataFrame(filas)
print("\nRESUMEN POR ESTRATEGIA")
g = t[t.get("vacia", False) != True].groupby("estrategia")
res = pd.DataFrame({"ops": g.size(), "aciertos": g["neto"].apply(lambda x: int((x > 0).sum())),
                    "fallos": g["neto"].apply(lambda x: int((x <= 0).sum())),
                    "neto": g["neto"].sum(), "doble": g["doble"].sum()}).reindex(estr.keys()).fillna(0)
print(res.to_string(float_format=lambda v: f"{v:+.2f}"))
print("\nNETO POR DÍA (filas: estrategia; columnas: día de entrada)")
piv = t[t.dia != "-"].pivot_table(index="estrategia", columns="dia", values="neto", aggfunc="sum").reindex(estr.keys())
print(piv.to_string(float_format=lambda v: f"{v:+.2f}", na_rep="·"))

# Testigo al azar: una operación larga o corta al azar por día, de duración 6 h, 0,05 %/lado
rng = np.random.default_rng(1910)
i0, i1 = V.i(ini), V.i(fin) - 361
sumas = []
for _ in range(2000):
    e = rng.integers(i0, i1, 5)
    l = rng.choice([-1, 1], 5)
    sumas.append((l * (V.c[e + 360] / V.o[e] - 1) * 100 - 0.10).sum())
print(f"\nAzar (5 operaciones de 6 h al azar en la semana, 0,05 %/lado): mediana {np.median(sumas):+.2f} %, "
      f"p5 {np.percentile(sumas, 5):+.2f} %, p95 {np.percentile(sumas, 95):+.2f} %")
d = V.df.loc[ini:fin - pd.Timedelta(minutes=1)]
dd = d.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last"})
dd["cambio_%"] = (dd.c / dd.o - 1) * 100
dd["rango_%"] = (dd.h / dd.l - 1) * 100
print("\nBTC en la semana (futuros):\n" + dd.round(2).to_string())
