"""Paridad (29/10/2026): motor/senales.py frente a t7 (grupos A y C) y t16 (grupo E) con las mismas velas.

Deben coincidir todas las señales (tiempo y dirección), la volatilidad de 5 min y el contexto diario. El grupo B (motor de la
T95H) no está en el módulo y no entra.
Uso: python -I t18_paridad.py"""
import ctypes
import importlib.util
import os
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from motor import senales as SEN  # noqa: E402

_e = importlib.util.spec_from_file_location("t16", os.path.join(AQUI, "t16_mezclas_todas.py"))
t16 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t16)
t7 = t16.t7


class _SinB(Exception):
    pass


def _sin_b(*a, **k):
    raise _SinB()


t7.sistema.Dia = _sin_b  # el grupo B no entra: cada día lanza y t7 lo deja vacío

EXT = os.path.join(RAIZ, "datos", "BTCUSDT_1m_ext.npy")
a = np.load(EXT)
t = (a[:, 0] // 1000).astype(np.int64)
o, h, l, c = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
t0 = time.time()
S7, T5a, v5a = t7.senales(t, o, h, l, c, EXT)
S7.update(t16.senales_E(t, o, h, l, c))
ctx7 = t7.contexto(t, c)
t1 = time.time()
S, T5b, v5b, ctx = SEN.todas(t, o, h, l, c)
t2 = time.time()
print(f"velas {len(t):,} · t7+t16 {t1 - t0:.0f} s · módulo {t2 - t1:.0f} s".replace(",", "."))
mal = 0
for nom, (g, ts, ds) in S.items():
    if nom not in S7:
        print(f"FALTA EN t7/t16: {nom}")
        mal += 1
        continue
    a1 = set(zip(np.asarray(ts, dtype=np.int64).tolist(), np.asarray(ds, dtype=float).tolist()))
    _, ts7, ds7 = S7[nom]
    a2 = set(zip(np.asarray(ts7, dtype=np.int64).tolist(), np.asarray(ds7, dtype=float).tolist()))
    if a1 != a2:
        mal += 1
        print(f"DISTINTA: {nom} · módulo {len(a1)} · t7/t16 {len(a2)} · solo módulo {len(a1 - a2)} · solo t7/t16 {len(a2 - a1)}")
    else:
        print(f"igual: {nom} ({len(a1)} señales)")
for nom in S7:
    if nom not in S and S7[nom][0] != "B":
        print(f"FALTA EN EL MÓDULO: {nom}")
        mal += 1
if not (np.array_equal(T5a, T5b) and np.array_equal(v5a, v5b)):
    print("DISTINTA: velas de 5 min o volatilidad")
    mal += 1
if ctx7 != ctx:
    print("DISTINTO: contexto diario")
    mal += 1
print("PARIDAD COMPLETA" if mal == 0 else f"PARIDAD ROTA en {mal} puntos")
