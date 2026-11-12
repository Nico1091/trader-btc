"""Prueba en el PC el programa de la placa contra el laboratorio (11/11/2026): mismas velas, mismos cierres de 5 min.
Compara los 19 rasgos, las probabilidades de los dos plazos y las señales (confianza 0,56). La placa guarda las velas en
precisión simple, como en la ESP32, así que se espera una diferencia pequeña en los rasgos y casi ninguna en las señales.
Uso: python -I probar_placa_pc.py"""
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(AQUI)
sys.path.insert(0, LAB)
sys.path.insert(0, AQUI)
for nombre in ("machine", "network"):
    m = types.ModuleType(nombre)
    sys.modules[nombre] = m
sys.modules["network"].WLAN = lambda *a: types.SimpleNamespace(isconnected=lambda: True)
sys.modules["network"].STA_IF = 0
import numpy as np  # noqa: E402

import binarias_placa as BP  # noqa: E402
import emulador as EM  # noqa: E402
import rasgos as RG  # noqa: E402
import velas as VL  # noqa: E402
from comun import utc  # noqa: E402
from exportar_pesos import pesos_placa  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    vel = VL.Velas(*VL.historia(utc(2026, 10, 20)))
    ctx = RG.Contexto(vel, None)
    motor = EM.MotorRed()
    BP.modelos = pesos_placa(motor)
    X, ok = ctx.rasgos_red()
    pr = motor.prob(ctx)
    for a, b in ((BP.T, (vel.t0 + 60 * np.arange(vel.n)).tolist()), (BP.O, vel.O.tolist()), (BP.H, vel.H.tolist()),
                 (BP.L, vel.L.tolist()), (BP.C, vel.C.tolist()), (BP.V, vel.V.tolist())):
        a.extend(b)
    peor, dif_p, distintas, total = np.zeros(19), 0.0, 0, 0
    for b in range(400, ctx.nb, 3):
        if not ok[b]:
            continue
        j = 5 * b + 4
        x = np.array(BP.rasgos(j))
        rel = np.abs(x - X[b]) / np.maximum(np.abs(X[b]), 1e-3)
        peor = np.maximum(peor, rel)
        for p in (10, 15):
            q = BP.probabilidad(p, list(x))
            dif_p = max(dif_p, abs(q - pr[p][b]))
            total += 1
            s_lab = abs(pr[p][b] - 0.5) >= 0.06
            s_placa = abs(q - 0.5) >= 0.06
            if s_lab != s_placa or (s_lab and (pr[p][b] > 0.5) != (q > 0.5)):
                distintas += 1
    print("peor diferencia relativa por rasgo:", np.round(peor, 6).tolist())
    print(f"mayor diferencia de probabilidad: {dif_p:.2e}; señales distintas: {distintas} de {total}")
    return 0 if distintas <= max(1, total // 1000) and dif_p < 1e-3 else 1


if __name__ == "__main__":
    sys.exit(main())
