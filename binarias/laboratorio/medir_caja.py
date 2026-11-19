"""Mide en la caja el costo del laboratorio (11/11/2026): armar el contexto de pruebas, los rasgos de la red, probar formas
en «elige» y evaluar N formas vivas en un cierre de 5 min (ventana de tres días). Imprime segundos y temperatura.
Uso: python3 -I medir_caja.py [N]"""
import os
import random
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

import formas as F  # noqa: E402
import juez as J  # noqa: E402
import rasgos as RG  # noqa: E402
import velas as VL  # noqa: E402
from comun import DESDE_PRUEBAS, TRAMO, temperatura  # noqa: E402


def main():
    n_formas = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t = time.time()
    vel = VL.Velas(*VL.historia(DESDE_PRUEBAS))
    interes = VL.cargar_interes()
    VL.cargar_indice(vel)
    print(f"velas {vel.n} en {time.time() - t:.1f} s; temperatura {temperatura()}", flush=True)
    t = time.time()
    ctx = RG.Contexto(vel.recorte(DESDE_PRUEBAS, TRAMO["juzga"][1] + 86400), interes)
    print(f"contexto de pruebas ({ctx.nb} barras) en {time.time() - t:.1f} s", flush=True)
    t = time.time()
    X, ok = ctx.rasgos_red()
    print(f"rasgos de la red ({int(ok.sum())} barras) en {time.time() - t:.1f} s; temperatura {temperatura()}", flush=True)
    rng = random.Random(77)
    fichas = [F.aleatoria(rng) for _ in range(20)]
    t = time.time()
    for f in fichas:
        s = F.senal(ctx, f)
        J.apuestas(ctx, s, f["p"])
    print(f"20 formas probadas en la historia en {time.time() - t:.1f} s ({(time.time() - t) / 20:.2f} s cada una); "
          f"temperatura {temperatura()}", flush=True)
    fin = vel.t_ultima() + 60
    t = time.time()
    win = RG.Contexto(vel.recorte(fin - 3 * 86400), interes)
    vivas = [F.aleatoria(rng) for _ in range(n_formas)]
    for f in vivas:
        F.senal(win, f)[-1]
    print(f"{n_formas} formas vivas evaluadas en un cierre de 5 min en {time.time() - t:.1f} s; temperatura {temperatura()}",
          flush=True)


if __name__ == "__main__":
    main()
