"""Indicadores sin mirar al futuro: el valor en i usa solo datos hasta i inclusive.

Todos devuelven listas del mismo largo que la entrada, con NaN durante el calentamiento.
"""
import collections
import math

NAN = float("nan")


def ema(x, n):
    a = 2.0 / (n + 1)
    out = [NAN] * len(x)
    valor = None
    for i, xi in enumerate(x):
        valor = xi if valor is None else valor + a * (xi - valor)
        if i >= n - 1:
            out[i] = valor
    return out


def atr(h, l, c, n=14):
    out = [NAN] * len(c)
    valor = None
    suma = 0.0
    for i in range(len(c)):
        tr = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        if i < n:
            suma += tr
            if i == n - 1:
                valor = suma / n
                out[i] = valor
        else:
            valor = (valor * (n - 1) + tr) / n
            out[i] = valor
    return out


def rsi(c, n=14):
    out = [NAN] * len(c)
    sube = baja = 0.0
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]
        g, p = (d, 0.0) if d > 0 else (0.0, -d)
        if i <= n:
            sube += g
            baja += p
            if i == n:
                sube /= n
                baja /= n
                out[i] = 100.0 if baja == 0 else 100 - 100 / (1 + sube / baja)
        else:
            sube = (sube * (n - 1) + g) / n
            baja = (baja * (n - 1) + p) / n
            out[i] = 100.0 if baja == 0 else 100 - 100 / (1 + sube / baja)
    return out


def pendiente_log(c, w):
    """Cambio porcentual de la recta de mínimos cuadrados del log-precio en las últimas w velas.

    Es la «pendiente polyfit» de los .py del curso de Nicolás, en versión deslizante O(1).
    """
    out = [NAN] * len(c)
    y = [math.log(v) for v in c]
    sx = w * (w - 1) / 2.0
    sxx = (w - 1) * w * (2 * w - 1) / 6.0
    den = w * sxx - sx * sx
    s1 = sky = 0.0
    for i in range(len(y)):
        if i < w:
            s1 += y[i]
            sky += i * y[i]
            if i == w - 1:
                b = (w * sky - sx * s1) / den
                out[i] = (math.exp(b * (w - 1)) - 1) * 100
            continue
        saliente = y[i - w]
        sky = sky - (s1 - saliente) + (w - 1) * y[i]
        s1 = s1 - saliente + y[i]
        b = (w * sky - sx * s1) / den
        out[i] = (math.exp(b * (w - 1)) - 1) * 100
    return out


def maximo_minimo(h, l, w):
    """Máximo y mínimo de las últimas w velas (incluida la actual), con colas monótonas."""
    mx, mn = [NAN] * len(h), [NAN] * len(l)
    qmax, qmin = collections.deque(), collections.deque()
    for i in range(len(h)):
        while qmax and h[qmax[-1]] <= h[i]:
            qmax.pop()
        qmax.append(i)
        while qmin and l[qmin[-1]] >= l[i]:
            qmin.pop()
        qmin.append(i)
        if qmax[0] <= i - w:
            qmax.popleft()
        if qmin[0] <= i - w:
            qmin.popleft()
        if i >= w - 1:
            mx[i], mn[i] = h[qmax[0]], l[qmin[0]]
    return mx, mn


def posicion_rango(c, mx, mn):
    out = [NAN] * len(c)
    for i in range(len(c)):
        rango = mx[i] - mn[i]
        if rango > 0:
            out[i] = (c[i] - mn[i]) / rango
    return out


def media_desvio(x, w):
    m, s = [NAN] * len(x), [NAN] * len(x)
    suma = suma2 = 0.0
    for i, xi in enumerate(x):
        suma += xi
        suma2 += xi * xi
        if i >= w:
            suma -= x[i - w]
            suma2 -= x[i - w] * x[i - w]
        if i >= w - 1:
            media = suma / w
            var = max(suma2 / w - media * media, 0.0)
            m[i], s[i] = media, math.sqrt(var)
    return m, s


def zscore(x, w):
    m, s = media_desvio(x, w)
    return [NAN if (s[i] != s[i] or s[i] == 0) else (x[i] - m[i]) / s[i] for i in range(len(x))]


def vwap_diario(t, h, l, c, v):
    """VWAP que se reinicia a las 00:00 UTC."""
    out = [NAN] * len(c)
    dia = None
    pv = vol = 0.0
    for i in range(len(c)):
        d = t[i] // 86_400_000
        if d != dia:
            dia, pv, vol = d, 0.0, 0.0
        tipico = (h[i] + l[i] + c[i]) / 3
        pv += tipico * v[i]
        vol += v[i]
        out[i] = pv / vol if vol > 0 else c[i]
    return out


def retornos(c, k):
    return [NAN if i < k else (c[i] / c[i - k] - 1) * 100 for i in range(len(c))]


def patrones(o, h, l, c, i, bajando, subiendo):
    """Patrones de vela del playbook de Nicolás sobre la vela i (y las dos anteriores).

    bajando / subiendo: si venía una bajada o una subida antes de la vela (contexto).
    Devuelve (puntaje, lista_de_nombres): + alcista, - bajista.
    """
    if i < 2:
        return 0, []
    nombres = []
    cuerpo = abs(c[i] - o[i])
    rango = h[i] - l[i]
    if rango <= 0:
        return 0, []
    mecha_inf = min(o[i], c[i]) - l[i]
    mecha_sup = h[i] - max(o[i], c[i])
    c1, o1 = c[i - 1], o[i - 1]
    cuerpo1 = abs(c1 - o1)
    rango1 = h[i - 1] - l[i - 1]
    verde, roja = c[i] > o[i], c[i] < o[i]
    verde1, roja1 = c1 > o1, c1 < o1
    if cuerpo <= 0.1 * rango:
        nombres.append("doji")
    if bajando and mecha_inf >= 2 * cuerpo and mecha_sup <= 0.35 * rango and cuerpo > 0:
        nombres.append("martillo")
    if subiendo and mecha_sup >= 2 * cuerpo and mecha_inf <= 0.35 * rango and cuerpo > 0:
        nombres.append("estrella_fugaz")
    if verde and roja1 and c[i] >= o1 and o[i] <= c1 and cuerpo > cuerpo1:
        nombres.append("envolvente_alcista")
    if roja and verde1 and c[i] <= o1 and o[i] >= c1 and cuerpo > cuerpo1:
        nombres.append("envolvente_bajista")
    if bajando and roja1 and verde and max(o[i], c[i]) < o1 and min(o[i], c[i]) > c1 and cuerpo1 > 0.6 * rango1:
        nombres.append("harami_alcista")
    if subiendo and verde1 and roja and max(o[i], c[i]) < c1 and min(o[i], c[i]) > o1 and cuerpo1 > 0.6 * rango1:
        nombres.append("harami_bajista")
    if bajando and roja1 and verde and o[i] < c1 and c[i] > (o1 + c1) / 2 and c[i] < o1:
        nombres.append("penetrante")
    if subiendo and verde1 and roja and o[i] > c1 and c[i] < (o1 + c1) / 2 and c[i] > o1:
        nombres.append("nube_oscura")
    c2, o2 = c[i - 2], o[i - 2]
    cuerpo_medio = abs(c1 - o1)
    if bajando and c2 < o2 and cuerpo_medio < 0.35 * abs(c2 - o2) and verde and c[i] > (o2 + c2) / 2:
        nombres.append("estrella_manana")
    if subiendo and c2 > o2 and cuerpo_medio < 0.35 * abs(c2 - o2) and roja and c[i] < (o2 + c2) / 2:
        nombres.append("estrella_tarde")
    if c2 > o2 and verde1 and verde and c[i] > c1 > c2 and cuerpo >= cuerpo1 * 0.8:
        nombres.append("tres_soldados")
    if c2 < o2 and roja1 and roja and c[i] < c1 < c2 and cuerpo >= cuerpo1 * 0.8:
        nombres.append("tres_cuervos")
    valor = {"martillo": 1, "envolvente_alcista": 2, "harami_alcista": 1, "penetrante": 1,
             "estrella_manana": 2, "tres_soldados": 1, "estrella_fugaz": -1, "envolvente_bajista": -2,
             "harami_bajista": -1, "nube_oscura": -1, "estrella_tarde": -2, "tres_cuervos": -1, "doji": 0}
    return sum(valor[n] for n in nombres), nombres


def alinear(t_menor, ancho_menor, t_mayor, ancho_mayor):
    """Para cada vela del marco menor, índice de la última vela del marco mayor YA CERRADA.

    Cierre de la menor = t + ancho_menor; se usa la mayor cuyo cierre <= ese instante.
    """
    out = [-1] * len(t_menor)
    j = -1
    for i, ti in enumerate(t_menor):
        cierre = ti + ancho_menor
        while j + 1 < len(t_mayor) and t_mayor[j + 1] + ancho_mayor <= cierre:
            j += 1
        out[i] = j
    return out


def alinear_puntos(t_menor, ancho_menor, t_puntos):
    """Para cada vela, índice del último dato puntual (métrica, financiación) con t <= cierre."""
    out = [-1] * len(t_menor)
    j = -1
    for i, ti in enumerate(t_menor):
        cierre = ti + ancho_menor
        while j + 1 < len(t_puntos) and t_puntos[j + 1] <= cierre:
            j += 1
        out[i] = j
    return out
