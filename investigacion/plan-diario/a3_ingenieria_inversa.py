"""A3 (28/10/2026): ingeniería inversa de la lógica del trade.

Pedido de Nicolás: «aplica ingeniería inversa, en el sentido de que la aplicas a la lógica del trade».

1. AL REVÉS: cada estrategia operada en el lado contrario, con las mismas horas de entrada y salida y comisión de tomador en
   las dos puntas (0,05 + 0,05): ¿alguna pierde tanto que al revés gana, en los dos tramos?
2. QUÉ TIENEN LAS GANADORAS: reglas de una o dos condiciones medidas al entrar (1 h, 4 h y 1 d sobre su EMA 20, patrón de
   1 h, lado, volatilidad alta, contexto lejos de la SMA 50, hora, día de la semana). Se eligen en 2020-2023 con todos los
   activos y se comprueban en 2024-2026 y activo por activo. Una regla vale si conserva al menos el 30 % de las operaciones,
   mejora la media neta en los dos tramos y en 5 de 7 activos o más.
3. RIESGO de la mejor combinación de A2 (P05c en 7 activos + P05b, P11 y N8 de BTC), de 1 a 8 %, en los dos tramos.
Uso: python -I a3_ingenieria_inversa.py > a3_ingenieria_inversa.txt   (desde investigacion/plan-diario/)"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_combinaciones as A2  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def condiciones(t):
    """Columnas booleanas medidas al entrar (sin mirar el futuro: e1h/e4h/e1d/pat1h salen de velas ya cerradas)."""
    c = pd.DataFrame(index=t.index)
    for k in ("e1h", "e4h", "e1d", "pat1h"):
        c[k] = t[k].astype(bool)
    c["largo"] = t.lado > 0
    vol = t.atr14 / t.precio_dia
    c["vol_alta"] = vol > vol.groupby([t.activo, t.estrategia]).transform("median")
    c["ctx_lejos"] = t.ctx_dist.abs() > t.ctx_dist.abs().groupby([t.activo, t.estrategia]).transform("median")
    h = t.entrada.dt.hour
    c["hora_0_7"], c["hora_7_13"], c["hora_13_17"], c["hora_17_24"] = h < 7, (h >= 7) & (h < 13), (h >= 13) & (h < 17), h >= 17
    c["fin_semana"] = t.entrada.dt.dayofweek >= 5
    return c


def main():
    t = A2.cargar()
    tr = t.e < A2.CORTE
    print("A3 · ingeniería inversa de la lógica del trade (comisión de futuros base)\n")
    print("1) CADA ESTRATEGIA AL REVÉS (media neta por operación, %; al revés paga tomador en las dos puntas)")
    print("   estrategia·universo   normal 2020-23 / 2024-26     al revés 2020-23 / 2024-26   ¿al revés gana en los dos?")
    for p in sorted(t.pieza.unique()):
        s = t[t.pieza == p]
        inv = -s.bruto - 0.10
        a, b = s[s.e < A2.CORTE], s[s.e >= A2.CORTE]
        ia, ib = inv[s.e < A2.CORTE], inv[s.e >= A2.CORTE]
        print(f"   {p:10s}  {a.neto.mean():+7.3f} / {b.neto.mean():+7.3f}          {ia.mean():+7.3f} / {ib.mean():+7.3f}"
              f"          {'SÍ' if ia.mean() > 0 and ib.mean() > 0 else 'no'}")
    c = condiciones(t)
    print("\n2) REGLAS QUE SEPARAN GANADORAS DE PERDEDORAS (elegidas en 2020-23, comprobadas en 2024-26 y por activo)")
    for e in A2.ESTR:
        s = t.estrategia == e
        base_a, base_b = t.loc[s & tr, "neto"].mean(), t.loc[s & ~tr, "neto"].mean()
        reglas = []
        cols = list(c.columns)
        candidatas = [(x,) for x in cols] + list(itertools.combinations(cols, 2))
        for comb in candidatas:
            for signo in itertools.product((True, False), repeat=len(comb)):
                m = s.copy()
                for col, v in zip(comb, signo):
                    m &= c[col] == v
                na, nb = (m & tr).sum(), (m & ~tr).sum()
                if na < 0.3 * (s & tr).sum() or nb < 0.3 * (s & ~tr).sum():
                    continue
                ma, mb = t.loc[m & tr, "neto"].mean(), t.loc[m & ~tr, "neto"].mean()
                if ma <= base_a:
                    continue
                por_activo = [t.loc[m & (t.activo == a), "neto"].mean() > t.loc[s & (t.activo == a), "neto"].mean()
                              for a in A2.ACTIVOS if (m & (t.activo == a)).sum() >= 10]
                txt = " y ".join(f"{col}={'sí' if v else 'no'}" for col, v in zip(comb, signo))
                reglas.append((ma - base_a, txt, ma, mb, sum(por_activo), len(por_activo), na, nb))
        reglas.sort(reverse=True)
        print(f"\n   {e}: base {base_a:+.3f} % (2020-23) / {base_b:+.3f} % (2024-26)")
        validas = [r for r in reglas if r[3] > base_b and r[4] >= 5]
        for r in reglas[:3]:
            print(f"     mejor en 2020-23: {r[1]:40s} {r[2]:+.3f} / {r[3]:+.3f} % · mejora en {r[4]} de {r[5]} activos · n {r[6]}/{r[7]}")
        if validas:
            r = validas[0]
            print(f"     ** SE SOSTIENE: {r[1]:36s} {r[2]:+.3f} / {r[3]:+.3f} % · {r[4]} de {r[5]} activos · n {r[6]}/{r[7]}")
        else:
            print("     ninguna regla mejora en los dos tramos y en 5 de 7 activos")
    print("\n3) RIESGO DE LA MEJOR COMBINACIÓN (P05c en 7 activos + P05b, P11 y N8 de BTC; hasta 3 posiciones)")
    combo = ["P05c·ALT", "P05c·BTC", "P05b·BTC", "P11·BTC", "N8·BTC"]
    sub = t[t.pieza.isin(combo)]
    ini_tr, ini_te, fin = int(pd.Timestamp("2020-03-01", tz="UTC").timestamp()), A2.CORTE, int(t.s.max())
    for f in (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08):
        A2.F = f
        a = A2.metricas(sub[sub.e < A2.CORTE], ini_tr, A2.CORTE)
        b = A2.metricas(sub[sub.e >= A2.CORTE], ini_te, fin)
        print(f"   {f * 100:3.0f} %: 2020-23 {a['g'] * 100:+.3f} %/día (caída {a['cm'] * 100:3.0f} %, Sharpe {a['sharpe']:.2f})"
              f" · 2024-26 {b['g'] * 100:+.3f} %/día (caída {b['cm'] * 100:3.0f} %, Sharpe {b['sharpe']:.2f})")


if __name__ == "__main__":
    main()
