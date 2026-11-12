"""Validación estadística de estrategias de binarias (03/11/2026). Solo numpy y biblioteca estándar.

Incluye: intervalo de Wilson, prueba binomial de una cola, tamaño de muestra necesario, corrección por pruebas
múltiples (Benjamini-Hochberg), acierto máximo esperado por azar al probar N variantes, probabilidad de sobreajuste
(PBO) por validación cruzada simétrica combinatoria (CSCV, Bailey, Borwein, López de Prado y Zhu, 2014), comparación de
dos estrategias sobre las mismas apuestas (McNemar), rachas (Wald-Wolfowitz y acierto tras acertar), expectativa,
Kelly, caída máxima y probabilidad de quiebra por remuestreo.
"""
import itertools
import math

import numpy as np


def equilibrio(pago):
    """Acierto mínimo para no perder con apuestas iguales: 1 / (1 + pago)."""
    return 1.0 / (1.0 + pago)


def expectativa(p, pago):
    """Ganancia esperada por peso apostado: p·pago − (1 − p)."""
    return p * pago - (1 - p)


def kelly(p, pago):
    """Fracción de Kelly para binarias de pago fijo: (p·pago − (1 − p)) / pago."""
    return max(0.0, (p * pago - (1 - p)) / pago)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - m, c + m)


def _norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def binomial_cola(k, n, p0):
    """P(X ≥ k) con X ~ Binomial(n, p0); exacta hasta n = 2000, aproximación normal con corrección después."""
    if n == 0:
        return 1.0
    if n <= 2000:
        lp = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p0) + (n - i) * math.log(1 - p0)
              for i in range(k, n + 1)]
        m = max(lp)
        return min(1.0, math.exp(m) * sum(math.exp(x - m) for x in lp))
    z = (k - 0.5 - n * p0) / math.sqrt(n * p0 * (1 - p0))
    return _norm_sf(z)


def muestra_necesaria(p1, p0, alfa=0.05, potencia=0.8):
    """Apuestas necesarias para distinguir un acierto real p1 de p0 (una cola)."""
    za = -_norm_inv(alfa)
    zb = -_norm_inv(1 - potencia)
    num = za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def _norm_inv(q):
    """Inversa de la normal estándar (Acklam)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if q < pl:
        r = math.sqrt(-2 * math.log(q))
        return (((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]) / ((((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1)
    if q > 1 - pl:
        return -_norm_inv(1 - q)
    r = q - 0.5
    s = r * r
    return (((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * r / (((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1)


def benjamini_hochberg(pvalores, q=0.05):
    """Devuelve la máscara de hipótesis que sobreviven con tasa de falsos descubrimientos q."""
    p = np.asarray(pvalores, float)
    m = len(p)
    if m == 0:
        return np.zeros(0, bool)
    orden = np.argsort(p)
    umbral = q * (np.arange(1, m + 1) / m)
    pasa = p[orden] <= umbral
    k = np.flatnonzero(pasa).max() + 1 if pasa.any() else 0
    mascara = np.zeros(m, bool)
    mascara[orden[:k]] = True
    return mascara


def acierto_maximo_por_azar(n, variantes, p0=0.5):
    """Acierto que daría la mejor de `variantes` estrategias sin ventaja, cada una con n apuestas (aprox. normal)."""
    if variantes <= 1:
        return p0
    z = -_norm_inv(1.0 / variantes)
    return p0 + z * math.sqrt(p0 * (1 - p0) / n)


def pbo_cscv(matriz, bloques=16):
    """Probabilidad de sobreajuste (CSCV). `matriz`: filas = bloques de tiempo, columnas = estrategias, valor = acierto
    del bloque (o ganancia). Para cada mitad de bloques: la mejor dentro de muestra, ¿qué puesto saca fuera?"""
    M = np.asarray(matriz, float)
    S = M.shape[0]
    assert S % 2 == 0
    peores, logits = 0, []
    combos = list(itertools.combinations(range(S), S // 2))
    for dentro in combos:
        fuera = [s for s in range(S) if s not in dentro]
        ins = np.nanmean(M[list(dentro)], axis=0)
        oos = np.nanmean(M[fuera], axis=0)
        mejor = int(np.nanargmax(ins))
        rango = (np.sum(oos < oos[mejor]) + 0.5 * np.sum(oos == oos[mejor])) / M.shape[1]
        rango = min(max(rango, 1e-6), 1 - 1e-6)
        logits.append(math.log(rango / (1 - rango)))
        peores += rango < 0.5
    return peores / len(combos), float(np.median(logits))


def mcnemar(gana_a, gana_b):
    """Compara dos estrategias sobre las mismas apuestas. Devuelve (b, c, p) con b = A acierta y B no, c = al revés."""
    a, b_ = np.asarray(gana_a, bool), np.asarray(gana_b, bool)
    b = int(np.sum(a & ~b_))
    c = int(np.sum(~a & b_))
    if b + c == 0:
        return b, c, 1.0
    z = (abs(b - c) - 1) / math.sqrt(b + c)
    return b, c, 2 * _norm_sf(z)


def rachas(resultados):
    """resultados: 1 acierto, 0 fallo, en orden. Prueba de Wald-Wolfowitz y acierto condicionado a lo anterior."""
    x = np.asarray(resultados, int)
    n = len(x)
    n1, n0 = int(x.sum()), int(n - x.sum())
    r = 1 + int(np.sum(x[1:] != x[:-1])) if n else 0
    mu = 1 + 2 * n1 * n0 / n if n else 0
    var = 2 * n1 * n0 * (2 * n1 * n0 - n) / (n * n * (n - 1)) if n > 1 else 0
    z = (r - mu) / math.sqrt(var) if var > 0 else 0.0
    def cond(k, valor):
        if n <= k:
            return (float("nan"), 0)
        m = np.ones(n - k, bool)
        for j in range(1, k + 1):
            m &= x[k - j:n - j] == valor
        sig = x[k:][m]
        return (float(sig.mean()) if len(sig) else float("nan"), int(len(sig)))
    mayor = 0
    act = 0
    for v in x:
        act = act + 1 if v == 0 else 0
        mayor = max(mayor, act)
    return {"n": n, "acierto": n1 / n if n else float("nan"), "rachas": r, "rachas_esperadas": mu, "z": z,
            "tras_1_acierto": cond(1, 1), "tras_1_fallo": cond(1, 0), "tras_3_aciertos": cond(3, 1), "tras_3_fallos": cond(3, 0),
            "peor_racha_de_fallos": mayor}


def curva(resultados, pago, fraccion, capital=100000.0, minimo=15900.0):
    """Saldo apostando una fracción fija (con mínimo de 5 USDT). Devuelve saldo final, caída máxima y si quebró."""
    s, pico, caida = capital, capital, 0.0
    for g in resultados:
        apuesta = max(fraccion * s, minimo)
        if apuesta > s:
            return s, 1.0, True
        s += apuesta * pago if g == 1 else -apuesta
        pico = max(pico, s)
        caida = max(caida, 1 - s / pico)
    return s, caida, False


def remuestreo_quiebra(resultados, pago, fraccion, apuestas=300, veces=2000, semilla=3112026):
    """Probabilidad de quebrar y caída mediana en `apuestas` apuestas, remuestreando por bloques de 20 (conserva rachas)."""
    rng = np.random.default_rng(semilla)
    x = np.asarray(resultados, int)
    if len(x) < 40:
        return float("nan"), float("nan")
    bloque = 20
    quiebras, caidas = 0, []
    for _ in range(veces):
        idx = []
        while len(idx) < apuestas:
            a = int(rng.integers(0, len(x) - bloque))
            idx.extend(range(a, a + bloque))
        _, caida, q = curva(x[idx[:apuestas]], pago, fraccion)
        quiebras += q
        caidas.append(caida)
    return quiebras / veces, float(np.median(caidas))
