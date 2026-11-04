"""Patrones de vela del curso en Python puro (sin pandas ni numpy), idénticos a lib.patrones.
Se usa en el motor en vivo (sistema.py), que debe correr en la rutina de la nube sin instalar nada.
La igualdad con lib.patrones se comprueba en pruebas_sistema.py sobre toda la historia de 1 h."""
import math

LADO = {"envolvente_alcista": 1, "envolvente_bajista": -1, "harami_alcista": 1, "harami_bajista": -1,
        "peonza": 0, "doji_piernas_largas": 0, "doji_cuatro_precios": 0, "doji_lapida": -1,
        "doji_libelula": 1, "pinzas_arriba": -1, "pinzas_abajo": 1, "tres_soldados": 1,
        "tres_cuervos": -1, "estrella_manana": 1, "estrella_tarde": -1, "martillo": 1,
        "martillo_invertido": 1, "hombre_colgado": -1, "estrella_fugaz": -1}
NAN = float("nan")


def patrones(o, h, l, c, n_tend=10):
    """o, h, l, c: listas de igual largo. Devuelve dict patrón -> lista de bool (vela i = última vela del patrón)."""
    n = len(c)
    cuerpo = [abs(c[i] - o[i]) for i in range(n)]
    rango = [h[i] - l[i] for i in range(n)]
    sup = [h[i] - max(o[i], c[i]) for i in range(n)]
    inf = [min(o[i], c[i]) - l[i] for i in range(n)]
    alc = [c[i] > o[i] for i in range(n)]
    baj = [c[i] < o[i] for i in range(n)]

    def s(x, i, k=1):
        return x[i - k] if i - k >= 0 else NAN

    def sb(x, i, k=1):
        return x[i - k] if i - k >= 0 else False

    def media_prev(x, i, w=20):  # media de las w velas anteriores (sin la actual), como rolling(20).mean().shift(1)
        return sum(x[i - w:i]) / w if i - w >= 0 else NAN

    def gt(a, b):
        return not (math.isnan(a) or math.isnan(b)) and a > b

    def ge(a, b):
        return not (math.isnan(a) or math.isnan(b)) and a >= b

    def le(a, b):
        return not (math.isnan(a) or math.isnan(b)) and a <= b

    def lt(a, b):
        return not (math.isnan(a) or math.isnan(b)) and a < b

    def var(i, k_fin, k_ini):  # (c[i-k_fin] - c[i-k_ini]) / c[i-k_ini]
        a, b = s(c, i, k_fin), s(c, i, k_ini)
        return NAN if (math.isnan(a) or math.isnan(b)) else (a - b) / b

    cmed = [media_prev(cuerpo, i) for i in range(n)]
    rmed = [media_prev(rango, i) for i in range(n)]
    grande = [gt(cuerpo[i], cmed[i]) for i in range(n)]
    fuerte_a = [alc[i] and cuerpo[i] >= 0.5 * rango[i] for i in range(n)]
    fuerte_b = [baj[i] and cuerpo[i] >= 0.5 * rango[i] for i in range(n)]
    out = {k: [False] * n for k in LADO}
    for i in range(n):
        t = var(i, 1, n_tend + 1)
        abajo, arriba = lt(t, 0), gt(t, 0)
        t3 = var(i, 3, n_tend + 3)
        doji = rango[i] > 0 and cuerpo[i] <= 0.1 * rango[i]
        o1, c1, h1, l1, cu1 = s(o, i), s(c, i), s(h, i), s(l, i), s(cuerpo, i)
        alc1, baj1 = sb(alc, i), sb(baj, i)
        out["envolvente_alcista"][i] = abajo and baj1 and alc[i] and gt(cuerpo[i], cu1) and ge(c[i], o1) and le(o[i], c1)
        out["envolvente_bajista"][i] = arriba and alc1 and baj[i] and gt(cuerpo[i], cu1) and le(c[i], o1) and ge(o[i], c1)
        dentro = (not math.isnan(o1)) and max(o[i], c[i]) <= max(o1, c1) and min(o[i], c[i]) >= min(o1, c1)
        out["harami_alcista"][i] = abajo and baj1 and sb(grande, i) and dentro and lt(cuerpo[i], 0.5 * cu1 if not math.isnan(cu1) else NAN)
        out["harami_bajista"][i] = arriba and alc1 and sb(grande, i) and dentro and lt(cuerpo[i], 0.5 * cu1 if not math.isnan(cu1) else NAN)
        r, cu, su, inf_ = rango[i], cuerpo[i], sup[i], inf[i]
        out["peonza"][i] = r > 0 and cu > 0.1 * r and cu <= 0.3 * r and su >= cu and inf_ >= cu
        out["doji_piernas_largas"][i] = doji and su >= 0.3 * r and inf_ >= 0.3 * r and gt(r, rmed[i])
        out["doji_cuatro_precios"][i] = le(r, 0.1 * rmed[i]) and le(cu, 0.1 * rmed[i])
        out["doji_lapida"][i] = doji and inf_ <= 0.1 * r and su >= 0.6 * r and arriba
        out["doji_libelula"][i] = doji and su <= 0.1 * r and inf_ >= 0.6 * r and abajo
        tol = 0.05 * rmed[i]
        out["pinzas_arriba"][i] = arriba and alc1 and baj[i] and le(abs(h[i] - h1) if not math.isnan(h1) else NAN, tol)
        out["pinzas_abajo"][i] = abajo and baj1 and alc[i] and le(abs(l[i] - l1) if not math.isnan(l1) else NAN, tol)
        c2 = s(c, i, 2)
        out["tres_soldados"][i] = lt(t3, 0) and fuerte_a[i] and sb(fuerte_a, i) and sb(fuerte_a, i, 2) and gt(c[i], c1) and gt(c1, c2)
        out["tres_cuervos"][i] = gt(t3, 0) and fuerte_b[i] and sb(fuerte_b, i) and sb(fuerte_b, i, 2) and lt(c[i], c1) and lt(c1, c2)
        o2, cu2 = s(o, i, 2), s(cuerpo, i, 2)
        mitad = (o2 + c2) / 2 if not (math.isnan(o2) or math.isnan(c2)) else NAN
        lim = 0.3 * cu2 if not math.isnan(cu2) else NAN
        out["estrella_manana"][i] = lt(t3, 0) and sb(baj, i, 2) and sb(grande, i, 2) and le(cu1, lim) and alc[i] and ge(c[i], mitad)
        out["estrella_tarde"][i] = gt(t3, 0) and sb(alc, i, 2) and sb(grande, i, 2) and le(cu1, lim) and baj[i] and le(c[i], mitad)
        mart = cu > 0 and inf_ >= 2 * cu and su <= 0.5 * cu and gt(r, 0.5 * rmed[i] if not math.isnan(rmed[i]) else NAN)
        inv = cu > 0 and su >= 2 * cu and inf_ <= 0.5 * cu and gt(r, 0.5 * rmed[i] if not math.isnan(rmed[i]) else NAN)
        out["martillo"][i] = abajo and mart
        out["martillo_invertido"][i] = abajo and inv
        out["hombre_colgado"][i] = arriba and mart
        out["estrella_fugaz"][i] = arriba and inv
    return out


def a_favor_3(o, h, l, c):
    """Por vela: (hay patrón alcista en las 3 últimas, hay patrón bajista en las 3 últimas)."""
    p = patrones(o, h, l, c)
    n = len(c)
    alc = [any(p[k][i] for k in LADO if LADO[k] > 0) for i in range(n)]
    baj = [any(p[k][i] for k in LADO if LADO[k] < 0) for i in range(n)]
    alc3 = [any(alc[max(0, i - 2):i + 1]) for i in range(n)]
    baj3 = [any(baj[max(0, i - 2):i + 1]) for i in range(n)]
    return alc3, baj3
