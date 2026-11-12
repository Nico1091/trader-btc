"""El juez del laboratorio (11/11/2026): apuestas de papel con la medida del Centro, cifras por tramo, valla de entrada a
vivo y estados en vivo. Los criterios se escribieron antes de ver resultados (PROMPT-FINAL.md, parte 6)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validacion as V  # noqa: E402
from comun import (DIAS_SIN_LLEGAR, EQUILIBRIO, MIN_APTA, MIN_ELIGE, MIN_OBS, PASO, Q_BH, TRAMOS)  # noqa: E402


def apuestas(ctx, apuesta, plazo, b0=0, b1=None):
    """Una apuesta abierta a la vez (la siguiente desde T + 60 s + plazo, como centro._libre). Entra con el cierre del minuto
    que abre en T (60 s tarde) y sale con el del minuto que abre en T + plazo; empate = fallo. Si falta una de las dos velas,
    no cuenta ni bloquea. Devuelve barras, sentidos, resultados con futuros y con el índice (−1 si falta el índice)."""
    b1 = ctx.nb if b1 is None else min(b1, ctx.nb)
    idx = np.flatnonzero(apuesta[b0:b1]) + b0
    paso = PASO[plazo]
    C1, I1 = ctx.C1, ctx.I1
    n1 = len(C1)
    B, D, R, RI = [], [], [], []
    ultimo = -10 ** 9
    for b in idx.tolist():
        if b - ultimo < paso:
            continue
        e = 5 * b + 5
        s = e + plazo
        if s >= n1:
            break
        ce, cs = C1[e], C1[s]
        if ce != ce or cs != cs:
            continue
        d = int(apuesta[b])
        B.append(b)
        D.append(d)
        R.append(1 if (cs - ce) * d > 0 else 0)
        ie, i_s = I1[e], I1[s]
        RI.append(-1 if (ie != ie or i_s != i_s) else (1 if (i_s - ie) * d > 0 else 0))
        ultimo = b
    return (np.array(B, dtype=np.int64), np.array(D, dtype=np.int8), np.array(R, dtype=np.int8),
            np.array(RI, dtype=np.int8))


def cifra(n, k, plazo):
    wi, ws = V.wilson(k, n)
    p = V.binomial_cola(k, n, EQUILIBRIO[plazo]) if n else 1.0
    return {"n": int(n), "k": int(k), "wi": wi, "ws": ws, "p": float(p)}


def cifras(ctx, B, R, RI, plazo, tramos=TRAMOS):
    """Cifras por tramo con futuros (n, k, Wilson, p frente al equilibrio) y con el índice (n_i, k_i)."""
    T = ctx.T[B] if len(B) else np.zeros(0, dtype=np.int64)
    R64, RI64 = R.astype(np.int64), RI.astype(np.int64)
    out = {}
    for nombre, a, b in tramos:
        m = (T >= a) & (T < b)
        n, k = int(m.sum()), int(R64[m].sum())
        c = cifra(n, k, plazo)
        mi = m & (RI64 >= 0)
        c["n_i"], c["k_i"] = int(mi.sum()), int(RI64[mi].sum())
        out[nombre] = c
    return out


def admitir(lote):
    """lote: [(clave, cifras_de_elige, plazo)]. Entra la que tiene 300 o más en «elige», Wilson inferior sobre el equilibrio y
    pasa Benjamini-Hochberg con q = 0,05 dentro de su tanda. Devuelve el conjunto de claves admitidas."""
    if not lote:
        return set()
    mascara = V.benjamini_hochberg([c["p"] for _k, c, _p in lote], Q_BH)
    return {k for (k, c, p), ok in zip(lote, mascara) if ok and c["n"] >= MIN_ELIGE and c["wi"] > EQUILIBRIO[p]}


def objetivo(c, plazo):
    """Lo que aprende la red de búsqueda: Wilson inferior menos el equilibrio, en puntos, entre −10 y +10."""
    return max(-10.0, min(10.0, 100 * (c["wi"] - EQUILIBRIO[plazo]))) if c["n"] else -10.0


def estado_vivo(n, k, plazo, juzga=None, dias=0.0):
    """Estados del plan: en observación hasta 100 cerradas; prometedora con 100 o más y 1 punto sobre el equilibrio; apta en
    papel con 300 o más, Wilson inferior sobre el equilibrio y «juzga» 1 punto o más sobre el equilibrio; descartada con 100
    o más y Wilson superior bajo el equilibrio, o 30 días sin llegar a 100."""
    eq = EQUILIBRIO[plazo]
    if n >= MIN_OBS:
        wi, ws = V.wilson(k, n)
        if ws < eq:
            return "descartada"
        jz = juzga is not None and juzga.get("n", 0) > 0 and juzga["k"] / juzga["n"] >= eq + 0.01
        if n >= MIN_APTA and wi > eq and jz:
            return "apta en papel"
        if k / n >= eq + 0.01:
            return "prometedora"
        return "en observación"
    if dias >= DIAS_SIN_LLEGAR:
        return "descartada"
    return "en observación"


def maximo_por_azar(n, variantes, plazo):
    return V.acierto_maximo_por_azar(max(n, 1), max(variantes, 1), EQUILIBRIO[plazo])
