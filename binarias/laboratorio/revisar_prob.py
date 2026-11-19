"""Revisa las probabilidades de la red de mercado en una semana fija de la historia (25/10 al 01/11/2026): cuántas son finitas,
su rango y una huella de sus valores redondeados a 12 decimales, para compararla entre el PC y la caja (11/11/2026).
Uso: python -I revisar_prob.py"""
import hashlib
import os
import sys
import warnings

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import numpy as np  # noqa: E402

import emulador as EM  # noqa: E402
import rasgos as RG  # noqa: E402
import velas as VL  # noqa: E402
from comun import utc  # noqa: E402


def main():
    vel = VL.Velas(*VL.historia(utc(2026, 10, 25)))
    ctx = RG.Contexto(vel, None)
    motor = EM.MotorRed()
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        pr = motor.prob(ctx)
    for p in (10, 15):
        a = pr[p]
        ok = np.isfinite(a)
        h = hashlib.sha256(np.round(a[ok], 12).tobytes()).hexdigest()[:16]
        print(f"plazo {p} ({motor.usa[p]}): {int(ok.sum())} finitas de {len(a)}, mínimo {np.nanmin(a):.6f}, máximo {np.nanmax(a):.6f}, "
              f"huella {h}")
    print(f"avisos de numpy: {len(avisos)} {[str(w.message) for w in avisos][:2]}")


if __name__ == "__main__":
    main()
