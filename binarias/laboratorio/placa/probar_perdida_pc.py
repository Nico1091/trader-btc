"""Prueba en el PC la pérdida de la placa contra laboratorio\\perdida.py (11/11/2026): velas de a una, como llegan en vivo,
y comparación ventana por ventana (qué lado compra y si ganó). Uso: python -I probar_perdida_pc.py"""
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(AQUI)
sys.path.insert(0, LAB)
sys.path.insert(0, AQUI)
for nombre in ("machine", "network"):
    sys.modules[nombre] = types.ModuleType(nombre)
sys.modules["network"].WLAN = lambda *a: types.SimpleNamespace(isconnected=lambda: True)
sys.modules["network"].STA_IF = 0
import numpy as np  # noqa: E402

import binarias_placa as BP  # noqa: E402
import perdida as PD  # noqa: E402
import velas as VL  # noqa: E402
from comun import utc  # noqa: E402


def main():
    vel = VL.Velas(*VL.historia(utc(2026, 10, 18)))
    x = PD.miradas(vel)
    lab = PD.primeras(x, utc(2026, 10, 19), utc(2026, 11, 1))
    BP.desfase = 0
    BP.ahora = lambda: 4e9
    T = (vel.t0 + 60 * np.arange(vel.n)).tolist()
    placa = {}
    for i in range(vel.n):
        for a, v in ((BP.T, T[i]), (BP.O, vel.O[i]), (BP.H, vel.H[i]), (BP.L, vel.L[i]), (BP.C, vel.C[i]), (BP.V, vel.V[i])):
            a.append(float(v) if a is not BP.T else int(v))
        if len(BP.T) > BP.CAP:
            corte = len(BP.T) - BP.GUARDA  # una sola vez, como en poner(): si no, las listas quedan desalineadas
            for a in (BP.T, BP.O, BP.H, BP.L, BP.C, BP.V):
                del a[:corte]
        antes = BP.est["perdida"]["abierta"]
        BP.perdida()
        pe = BP.est["perdida"]
        if antes and pe["abierta"] is None and pe["ultimas"] and pe["ultimas"][-1]["ventana"] == antes["ventana"]:
            u = pe["ultimas"][-1]
            if utc(2026, 10, 19) <= u["ventana"] < utc(2026, 11, 1):
                placa[u["ventana"]] = u["res"]
    comunes = set(lab) & set(placa)
    iguales = sum(1 for w in comunes if lab[w] == placa[w])
    print(f"ventanas con compra: laboratorio {len(lab)}, placa {len(placa)}, en las dos {len(comunes)}, mismo resultado {iguales}")
    solo_lab, solo_placa = sorted(set(lab) - set(placa))[:5], sorted(set(placa) - set(lab))[:5]
    print("solo en el laboratorio:", solo_lab, "solo en la placa:", solo_placa)
    return 0 if len(comunes) >= 0.99 * max(len(lab), len(placa)) and iguales == len(comunes) else 1


if __name__ == "__main__":
    sys.exit(main())
