"""C3: ¿cuánto de la ventaja medida sobrevive a haber buscado mucho? (pruebas múltiples)

- Sharpe probabilístico (PSR) y Sharpe deflactado (DSR, Bailey y López de Prado 2014) sobre la serie DIARIA de cada
  estrategia (P&L de las operaciones que cierran ese día, 0 los días sin operación; futuros base; 1x nocional).
  DSR descuenta el máximo Sharpe que se esperaría por azar tras probar N variantes; se da para varios N porque las
  variantes del proyecto están correladas y el N efectivo no se conoce. V[SR] bajo la hipótesis nula = 1/T.
- Valores p de la media por operación (bootstrap por bloques de meses, una cola) con corrección de Holm en cada tramo.
- Cuenta de variantes registradas en el proyecto (filas de los CSV de las tareas).
Uso: python3 -I c3_pruebas_multiples.py > c3_pruebas_multiples.txt"""
import glob
import os
import sys
from math import erf, sqrt, log, e

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from metricas import cargar, neto, diario, tramo, TRAMOS  # noqa: E402

Phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))  # noqa: E731


def Phi_inv(p):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if Phi(m) < p else (lo, m)
    return (lo + hi) / 2


def psr(r, sr_ref):
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = pd.Series(r).skew()
    g4 = pd.Series(r).kurt() + 3
    return Phi((sr - sr_ref) * sqrt(T - 1) / sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)), sr


def sr0(N, T):
    g = 0.5772156649
    return sqrt(1 / T) * ((1 - g) * Phi_inv(1 - 1 / N) + g * Phi_inv(1 - 1 / (N * e)))


print("VARIANTES REGISTRADAS EN EL PROYECTO (filas de los CSV de consolidacion/; cada fila suele ser variante × tramo)")
tot = 0
for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "consolidacion", "*.csv"))):
    n = len(pd.read_csv(f))
    tot += n
    print(f"  {os.path.basename(f)}: {n}")
print(f"  total {tot} filas → del orden de {tot // 2} variantes distintas, sin contar el banco de alta frecuencia de octubre "
      f"ni las estrategias del curso de junio. Por eso se dan N = 10, 50, 100 y 300.\n")

ORDEN = ["P05b", "P11", "P05c", "N9", "N8"]
for etq in ("BTC", "ETH"):
    T = cargar(etq)
    print(f"=== {etq} ===")
    filas = []
    for tr in TRAMOS:
        pvals = {}
        for nb in ORDEN:
            t = tramo(T[T.estrategia == nb], tr).sort_values("entrada")
            x = neto(t)
            a, b = TRAMOS[tr]
            d = diario(t, x, ini=a.normalize(), fin=min(b, T.salida.max()).normalize()).to_numpy() / 100
            p0, sr = psr(d, 0.0)
            fila = dict(estrategia=nb, tramo=tr, dias=len(d), sharpe_anual=sr * sqrt(365), PSR_vs_0=p0)
            for N in (10, 50, 100, 300):
                fila[f"DSR N={N}"] = psr(d, sr0(N, len(d)))[0]
            # bootstrap por meses de la media por operación (una cola: H0 media <= 0)
            mes = t.entrada.dt.strftime("%Y-%m").to_numpy()
            grupos = [x[mes == m] for m in np.unique(mes)]
            rng = np.random.default_rng(3)
            centr = [g - x.mean() for g in grupos]  # bajo H0: medias centradas
            sims = np.array([np.concatenate([centr[i] for i in rng.integers(0, len(grupos), len(grupos))]).mean() for _ in range(4000)])
            pvals[nb] = (sims >= x.mean()).mean()
            fila["p_media"] = pvals[nb]
            filas.append(fila)
        # Holm dentro del tramo
        orden = sorted(pvals, key=pvals.get)
        m = len(orden)
        ajust, prev = {}, 0.0
        for i, nb in enumerate(orden):
            prev = max(prev, min(1.0, (m - i) * pvals[nb]))
            ajust[nb] = prev
        for f in filas:
            if f["tramo"] == tr:
                f["p_Holm"] = ajust[f["estrategia"]]
    R = pd.DataFrame(filas)
    pd.set_option("display.width", 220)
    print(R.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("  Lectura: PSR/DSR = probabilidad de que el Sharpe verdadero supere al de referencia; ≥ 0,95 sería evidencia fuerte.\n")
