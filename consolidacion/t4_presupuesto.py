"""Tarea 4: estrategias para 40.000 pesos (12,59 USDT) y plan de riesgo diario.

Restricción que manda (reglas de Binance leídas por la rutina el 25/10): en futuros BTCUSDT la orden mínima es
0,001 BTC (unos 80 USDT a 80.000), o sea 6,4 veces el saldo; con stop del 3 % eso arriesga el 19 % de la cuenta.
Por eso las estrategias nuevas van en CONTADO (BTCUSDT, nocional mínimo 5 USDT), solo largas y sin apalancamiento.
Comisión de contado VIP0: 0,10 % por lado (creador y tomador); se repite con el doble (0,20 %).
Las velas son las de futuros (la base entre contado y perpetuo es de centésimas de punto): es una aproximación.

N1: P11 en contado (largo del lunes UTC, stop 3 %).
N2: P05b solo largo en contado (límite de creador en la banda), con y sin el veto de velas de 1 h.
N3: retroceso de creador en tendencia diaria (curso: «seguir la tendencia»): si el cierre diario está sobre la
    SMA 50 y esta sube, límite de compra en apertura - x·ATR14 (válido hasta las 20:00 UTC), stop 1 ATR por debajo,
    salida al cierre del día (A) o del día siguiente (B). Rejilla x ∈ {0,5; 1,0} × {A, B}, elegida en el ajuste.
"""
import sys
import numpy as np
import pandas as pd
from lib import cargar, CORTE
from sim import Velas, p11, p05b, n3, VetoVelas, a_tabla, netos, azar

V = Velas(cargar())
SP, SP2 = 0.10, 0.20  # contado y el doble


def caida(x):
    eq = np.concatenate([[0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


filas, tablas = [], {}
def evaluar(nombre, ops):
    t = a_tabla(ops)
    tablas[nombre] = t
    for tramo in ("ajuste", "prueba", "total"):
        s = t if tramo == "total" else (t[t.entrada < CORTE] if tramo == "ajuste" else t[t.entrada >= CORTE])
        n1, n2 = netos(s, SP, SP), netos(s, SP2, SP2)
        az = azar(V, s, com=SP) if len(s) else np.array([0.0])
        filas.append(dict(estrategia=nombre, tramo=tramo, ops=len(s),
                          ops_semana=len(s) / max(1, ((s.entrada.max() - s.entrada.min()).days / 7)) if len(s) > 1 else 0,
                          acierto=float((n1 > 0).mean() * 100) if len(s) else np.nan,
                          bruto=float(s["bruto"].sum()) if len(s) else 0.0, neto=float(n1.sum()),
                          doble=float(n2.sum()), media=float(n1.mean()) if len(s) else np.nan,
                          caida=caida(n1), pct_azar=float((az < n1.sum()).mean() * 100)))
    print(nombre, "listo", flush=True)

veto = VetoVelas(V.df, 60, 3)
evaluar("N1 P11 en contado", p11(V))
evaluar("N2 P05b largo contado", p05b(V, lados=(1,)))
evaluar("N2v P05b largo contado + veto 1h", p05b(V, lados=(1,), veto=veto))
evaluar("N2c P05c (k1) largo contado", p05b(V, k=1.0, lados=(1,)))
for x in (0.5, 1.0):
    for dd in (False, True):
        evaluar(f"N3 retroceso x{x} {'2 días' if dd else '1 día'}", n3(V, x, dd))

t = pd.DataFrame(filas)
t.to_csv(sys.argv[1] if len(sys.argv) > 1 else "t4_presupuesto.csv", index=False)
pd.set_option("display.width", 250)
print(t.to_string(float_format=lambda v: f"{v:.2f}"))

# ---------- plan de riesgo: simulación de la cuenta en pesos ----------
# Tamaño: nocional = riesgo / distancia del stop, con tope en el saldo (contado, sin apalancamiento) y
# mínimo de 5 USDT. Riesgo 1,5 % por operación. Tope de pérdida diaria 3 % y semanal 6 %. Una posición a la vez.
COP_USDT = 3177.85
def cuenta(t, riesgo=0.015, tope_dia=0.03, tope_sem=0.06, com=SP, stop_pct=None):
    saldo, ini = 12.5871, 12.5871
    dia_perd, sem_perd, d_act, s_act = 0.0, 0.0, None, None
    hist, minimo, saltadas = [], saldo, 0
    for _, r in t.sort_values("entrada").iterrows():
        d, s = r.entrada.normalize(), r.entrada.isocalendar()[:2]
        if d != d_act: dia_perd, d_act = 0.0, d
        if s != s_act: sem_perd, s_act = 0.0, s
        if dia_perd <= -tope_dia * ini or sem_perd <= -tope_sem * ini:
            saltadas += 1; continue
        dist = (stop_pct or r.get("dist_stop", 3.0)) / 100
        nocional = min(saldo, riesgo * saldo / dist)
        if nocional < 5:
            saltadas += 1; continue
        g = nocional * ((r.bruto - 2 * com) / 100)
        saldo += g; dia_perd += g; sem_perd += g
        minimo = min(minimo, saldo)
        hist.append(saldo)
    return saldo, minimo, saltadas, len(hist)

print("\nCUENTA EN PESOS (40.000 COP, riesgo 1,5 % por operación, topes 3 % día y 6 % semana)")
for nombre, dist in (("N1 P11 en contado", 3.0), ("N2v P05b largo contado + veto 1h", None), ("N2c P05c (k1) largo contado", None)):
    t = tablas[nombre].copy()
    if dist is None:  # distancia real del stop: de la banda a la apertura (k·ATR)
        t["dist_stop"] = np.nan
    for tramo, s in (("2020-2023", t[t.entrada < CORTE]), ("2024-2026", t[t.entrada >= CORTE])):
        s = s.copy()
        if dist is None:
            # la distancia es nivel - apertura; se aproxima con la mediana medida de la pérdida en stop
            perd = -s.loc[s.motivo == "stop", "bruto"]
            s["dist_stop"] = float(perd.median()) if len(perd) else 1.5
        for com in (SP, SP2):
            f, mn, salt, n = cuenta(s, com=com, stop_pct=dist)
            print(f"{nombre} {tramo} com {com:.2f}: {n} ops, saldo final {f * COP_USDT:,.0f} COP "
                  f"({(f / 12.5871 - 1) * 100:+.1f} %), mínimo {mn * COP_USDT:,.0f} COP, saltadas {salt}")
