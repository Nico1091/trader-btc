"""D4: ¿más operaciones conservan la ventaja o solo suman costes? (PREREGISTRO.md, punto 3, D4)

El mecanismo de P05b llevado a sesiones más cortas: en cada sesión de H horas, banda = apertura de la sesión
± k·ATR14·sqrt(H/24) (ATR de los 14 días previos, k = 0,5); el primer cierre de g minutos fuera de la banda en el lado
del contexto diario da la señal (como P05b: el primer rompimiento a cualquier lado debe ir en el lado del contexto); límite en la banda durante min(60, H·60/2) minutos; stop con un cierre de g minutos de
vuelta a la apertura de la sesión; salida al final de la sesión. g = 5 min para H <= 2, 15 min para H >= 4.
Testigo: en cada sesión, entrar a mercado a la apertura en el lado del contexto y salir al final (sin señal).
Uso: python3 -I d4_frecuencia.py RUTA.npy ETIQUETA"""
import os
import sys

RUTA, ETQ = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], RUTA, ETQ]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "consolidacion"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import consolidado as C  # noqa: E402
from sim import atr_diario  # noqa: E402

V = C.V
T0 = V.t[0]
assert ((V.t[1:] - V.t[:-1]) == pd.Timedelta(minutes=1)).all(), "este experimento supone velas sin huecos"
_, ATR = atr_diario(C.m1)
dd = C.dd
ctx_dia = np.sign(dd.c - C.sma50).shift(1)  # contexto de cada día = cierre de ayer frente a su SMA 50
k = 0.5
filas, ops_todas = [], []
for H in (1, 2, 4, 8, 24):
    g = 5 if H <= 2 else 15
    L = H * 60
    W = min(60, L // 2)
    ops = []
    testigo = []
    for d in pd.date_range(T0.normalize() + pd.Timedelta(days=60), V.t[-1].normalize() - pd.Timedelta(days=1), freq="D"):
        lado = ctx_dia.get(d, np.nan)
        a = ATR.get(d, np.nan)
        if not lado or np.isnan(lado) or np.isnan(a):
            continue
        lado = int(lado)
        i_d = V.i(d)
        for s0 in range(0, 1440, L):
            i0, i1 = i_d + s0, i_d + s0 + L - 1   # minutos de la sesión
            ap = V.o[i0]
            testigo.append((V.t[i0], lado * (V.c[i1] / ap - 1) * 100))
            b = k * a * np.sqrt(H / 24)
            nivel = ap + lado * b
            cierres = V.c[i0 + g - 1: i1 + 1: g][:-1]    # cierres de g minutos (el último es el fin de la sesión)
            jj = np.flatnonzero(np.abs(cierres - ap) > b)  # como P05b: el PRIMER rompimiento, a cualquier lado,
            if not len(jj) or np.sign(cierres[jj[0]] - ap) != lado:  # tiene que ir en el lado del contexto
                continue
            a0 = i0 + (jj[0] + 1) * g                    # minuto siguiente al cierre de la señal
            a1 = min(a0 + W - 1, i1)
            seg = V.l[a0:a1 + 1] < nivel if lado > 0 else V.h[a0:a1 + 1] > nivel
            kk = np.flatnonzero(seg)
            if not len(kk):
                continue
            ie = a0 + kk[0]
            # stop: primer cierre de g minutos (desde la vela del llenado) de vuelta a la apertura de la sesión
            primero = i0 + ((ie - i0) // g) * g + g - 1
            cs = V.c[primero: i1 + 1: g]
            st = np.flatnonzero(lado * (cs - ap) <= 0)
            ix = primero + st[0] * g if len(st) else i1
            px = V.c[ix]
            ops.append((V.t[ie], lado, lado * (px / nivel - 1) * 100, ix - ie))
    t = pd.DataFrame(ops, columns=["entrada", "lado", "bruto", "minutos"])
    w = pd.DataFrame(testigo, columns=["inicio", "bruto"])
    meses = (V.t[-1] - V.t[0]).days / 30.44
    for tramo, sel, selw in (("2020-2023", t.entrada < C.CORTE, w.inicio < C.CORTE), ("2024-2026", t.entrada >= C.CORTE, w.inicio >= C.CORTE)):
        x, y = t[sel], w[selw]
        m_tr = ((C.CORTE - V.t[0]).days if tramo == "2020-2023" else (V.t[-1] - C.CORTE).days) / 30.44
        filas.append(dict(sesion_h=H, tramo=tramo, ops=len(x), ops_mes=len(x) / m_tr, bruto_medio=x.bruto.mean(),
                          neto_fut_base=(x.bruto - 0.07).mean(), neto_fut_doble=(x.bruto - 0.14).mean(),
                          neto_contado_bnb=(x.bruto - 0.15).mean(), neto_contado=(x.bruto - 0.20).mean(),
                          suma_fut_base=(x.bruto - 0.07).sum(), suma_contado_bnb=(x.bruto - 0.15).sum(),
                          t_bruto=x.bruto.mean() / (x.bruto.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan,
                          minutos_medios=x.minutos.mean(), testigo_bruto=y.bruto.mean(), testigo_ops_mes=len(y) / m_tr))
    print(f"sesión {H} h lista: {len(t)} operaciones", flush=True)
R = pd.DataFrame(filas)
pd.set_option("display.width", 250)
print(f"\n=== {ETQ}: mecanismo de P05b por sesiones (k = {k}); costes de ida y vuelta: futuros 0,07 (creador+tomador), "
      f"doble 0,14; contado BNB 0,15; contado 0,20 ===")
print(R.to_string(index=False, float_format=lambda v: f"{v:+.3f}" if abs(v) < 10 else f"{v:,.1f}"))
R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"d4_frecuencia_{ETQ}.csv"), index=False)
