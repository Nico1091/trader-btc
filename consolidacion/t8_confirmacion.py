"""Tarea 8 (pedido de Nicolás del 25/10): quedarse solo con las estrategias que ganan y operarlas
únicamente cuando las velas y el impulso del mercado confirman el lado de la señal.

Bases (las que sobrevivieron a la tarea 3): P11, P05b solo largo, P05b con veto 1 h y P05c solo largo.
Filtros de confirmación, todos medidos en el instante de la señal con velas ya cerradas:
  velaN_tf : patrón de vela a favor del lado en las últimas N velas del marco tf
  imp_Xh   : el precio se movió a favor del lado en las últimas X horas (impulso)
  fuerza   : la vela de 15 m de la señal tiene cuerpo >= 50 % de su rango y cierra en el 25 % extremo a favor
  volumen  : esa vela de 15 m tiene más de 1,5 veces el volumen medio de las 20 anteriores
  tend_d   : el cierre diario de ayer está del lado correcto de su SMA 50
Regla de honestidad: cada combinación se elige en el ajuste (2020-2023) y la prueba (2024-2026) se mira una
sola vez. Se dice cuántas combinaciones se probaron."""
import sys
import numpy as np
import pandas as pd
from lib import cargar, remuestrear, patrones, CORTE
from sim import Velas, p11, p05b, VetoVelas, a_tabla, netos, azar

V = Velas(cargar())
m1 = V.df
c15 = remuestrear(m1, 15)
v20 = c15["v"].rolling(20).mean().shift(1)
d1 = remuestrear(m1, 1440)
sma50 = d1["c"].rolling(50).mean()
veto1h = VetoVelas(m1, 60, 3)


class AFavor:
    """Hay un patrón del mismo lado en las últimas n velas cerradas del marco tf."""
    def __init__(self, tf, n):
        df = remuestrear(m1, tf)
        pat, lado = patrones(df)
        alc = pat[[k for k, s in lado.items() if s > 0]].any(axis=1).to_numpy()
        baj = pat[[k for k, s in lado.items() if s < 0]].any(axis=1).to_numpy()
        self.cierre = df.index + pd.Timedelta(minutes=tf)
        self.alc = pd.Series(alc).rolling(n, min_periods=1).max().to_numpy() > 0
        self.baj = pd.Series(baj).rolling(n, min_periods=1).max().to_numpy() > 0

    def __call__(self, t, lado):
        j = self.cierre.searchsorted(t, side="right") - 1
        return j >= 0 and bool(self.alc[j] if lado > 0 else self.baj[j])


def impulso(horas):
    def f(t, lado):
        i1 = V.i(t) - 1
        i0 = V.i(t - pd.Timedelta(hours=horas))
        return i1 > i0 and lado * (V.c[i1] / V.o[i0] - 1) > 0
    return f


def vela_senal(t):
    """Vela de 15 m que cerró justo en t."""
    k = t - pd.Timedelta(minutes=15)
    return c15.loc[k] if k in c15.index else None


def fuerza(t, lado):
    b = vela_senal(t)
    if b is None:
        return False
    r = b.h - b.l
    if r <= 0:
        return False
    pos = (b.c - b.l) / r
    return abs(b.c - b.o) >= 0.5 * r and (pos >= 0.75 if lado > 0 else pos <= 0.25)


def volumen(t, lado):
    k = t - pd.Timedelta(minutes=15)
    return k in v20.index and not np.isnan(v20.loc[k]) and c15.loc[k, "v"] > 1.5 * v20.loc[k]


def tend_d(t, lado):
    ayer = t.normalize() - pd.Timedelta(days=1)
    if ayer not in sma50.index or np.isnan(sma50.loc[ayer]):
        return False
    return lado * (d1.loc[ayer, "c"] - sma50.loc[ayer]) > 0


filtros = {"vela1_15m": AFavor(15, 1), "vela3_15m": AFavor(15, 3), "vela1_1h": AFavor(60, 1),
           "vela3_1h": AFavor(60, 3), "imp_1h": impulso(1), "imp_4h": impulso(4), "imp_24h": impulso(24),
           "fuerza": fuerza, "volumen": volumen, "tend_d": tend_d}


def caida(x):
    eq = np.concatenate([[0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


def medir(t, merc):
    out = {}
    for tramo in ("ajuste", "prueba"):
        s = t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE]
        if merc == "fut":
            n1, n2 = netos(s, 0.05, 0.02), netos(s, 0.10, 0.04)
        else:
            n1, n2 = netos(s, 0.10, 0.10), netos(s, 0.20, 0.20)
        az = azar(V, s, sims=300, com=0.05 if merc == "fut" else 0.10) if len(s) else np.array([0.0])
        out[tramo] = dict(ops=len(s), neto=float(n1.sum()), doble=float(n2.sum()),
                          media=float(n1.mean()) if len(s) else 0.0, acierto=float((n1 > 0).mean() * 100) if len(s) else 0.0,
                          caida=caida(n1), pct=float((az < n1.sum()).mean() * 100))
    return out


# Señales base: se generan sin filtro y se filtran después (la señal y su resultado no cambian)
def senales_p05b(**kw):
    regs = []
    def espia(t, lado):
        regs.append((t, lado))
        return False
    ops = p05b(V, veto=espia, **kw)
    return ops, regs

bases = {}
ops, _ = senales_p05b(lados=(1,))
bases["P05b solo largo (futuros)"] = (ops, "fut")
ops, _ = senales_p05b(lados=(1,))
bases["P05b solo largo (contado)"] = (ops, "spot")
bases["P05b + veto 1h (futuros)"] = (p05b(V, veto=veto1h), "fut")
bases["P05c solo largo (contado)"] = (p05b(V, k=1.0, lados=(1,)), "spot")
bases["P11 (futuros)"] = (p11(V), "fut")
bases["P11 (contado)"] = (p11(V), "spot")


def t_senal(o, nombre):
    """Instante en que se decide: P11 a las 00:00; P05b al cierre de la vela de 15 m de la señal."""
    if nombre.startswith("P11"):
        return o["entrada"]
    # Corregido el 27/10: se decide en el cierre de la vela de 15 m de la SEÑAL (cuando se pone la orden límite),
    # no en el llenado. Antes se usaba entrada.floor("15min"), que podía ver velas cerradas después de la señal.
    return o["senal"] if "senal" in o else o["entrada"].floor("15min")


filas = []
for nombre, (ops, merc) in bases.items():
    t = a_tabla(ops)
    base = medir(t, merc)
    filas.append(dict(base=nombre, filtro="(ninguno)", **{f"{k}_{tr}": v for tr in base for k, v in base[tr].items()}))
    for fn, f in filtros.items():
        if nombre.startswith("P11") and fn in ("fuerza", "volumen"):
            continue  # P11 no tiene vela de señal
        keep = [o for o in ops if f(t_senal(o, nombre), o["lado"])]
        r = medir(a_tabla(keep), merc)
        filas.append(dict(base=nombre, filtro=fn, **{f"{k}_{tr}": v for tr in r for k, v in r[tr].items()}))
    print(nombre, "listo", flush=True)

t = pd.DataFrame(filas)
t.to_csv(sys.argv[1] if len(sys.argv) > 1 else "t8_confirmacion.csv", index=False)
pd.set_option("display.width", 300)
cols = ["base", "filtro", "ops_ajuste", "neto_ajuste", "doble_ajuste", "pct_ajuste",
        "ops_prueba", "neto_prueba", "doble_prueba", "pct_prueba", "media_prueba"]
print(t[cols].to_string(float_format=lambda v: f"{v:.2f}"))

print("\nELECCIÓN EN EL AJUSTE (mejor neto con comisión doble por operación, mínimo 60 ops en el ajuste)")
for nombre in bases:
    s = t[(t.base == nombre) & (t.ops_ajuste >= 60)].copy()
    s["doble_por_op"] = s.doble_ajuste / s.ops_ajuste
    best = s.sort_values("doble_por_op", ascending=False).iloc[0]
    b0 = t[(t.base == nombre) & (t.filtro == "(ninguno)")].iloc[0]
    print(f"{nombre}: elegido «{best.filtro}». Ajuste {int(best.ops_ajuste)} ops, doble {best.doble_ajuste:+.1f} % | "
          f"PRUEBA {int(best.ops_prueba)} ops, neto {best.neto_prueba:+.1f} %, doble {best.doble_prueba:+.1f} %, "
          f"media {best.media_prueba:+.3f} %, pct {best.pct_prueba:.0f} || sin filtro en prueba: "
          f"{int(b0.ops_prueba)} ops, neto {b0.neto_prueba:+.1f} %, doble {b0.doble_prueba:+.1f} %, media {b0.media_prueba:+.3f} %")
