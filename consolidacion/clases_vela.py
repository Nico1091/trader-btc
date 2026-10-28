"""Clase de cada vela y su lectura en palabras (28/10/2026). Solo biblioteca estándar.

Una sola definición para el lector en vivo (lector_velas.py) y para la base medida (investigacion/plan-diario/a5_base_velas.py),
así lo que dice el lector de una vela es exactamente lo que se midió en el historial.

Medidas de una vela (todas con datos anteriores a ella para las referencias):
  cuerpo = |c − o| / rango · posición del cierre = (c − l) / rango · mechas = parte de arriba y de abajo / rango
  rango/ATR = rango frente al ATR14 de las 14 velas anteriores · vol/media = volumen frente a la media de las 20 anteriores"""

CLASES = (  # (clave, texto) en orden de prioridad: la primera que se cumple es la clase de la vela
    ("impulso_alcista_vol", "impulso alcista con volumen"),
    ("impulso_bajista_vol", "impulso bajista con volumen"),
    ("esfuerzo_sin_resultado", "mucho volumen y poco recorrido (absorción)"),
    ("fuerte_alcista", "alcista fuerte que cierra arriba"),
    ("fuerte_bajista", "bajista fuerte que cierra abajo"),
    ("rechazo_abajo", "rechazo abajo (mecha inferior larga: compran)"),
    ("rechazo_arriba", "rechazo arriba (mecha superior larga: venden)"),
    ("doji", "indecisión (doji)"),
    ("sin_interes", "sin interés (poco volumen y poco rango)"),
    ("normal_alcista", "alcista normal"),
    ("normal_bajista", "bajista normal"),
)
TEXTO = dict(CLASES)


def medidas(o, h, l, c, v, atr_prev, vol_prev):
    rango = h - l
    if rango <= 0:
        return None
    return {
        "cuerpo": abs(c - o) / rango, "alcista": c >= o, "pos": (c - l) / rango,
        "m_sup": (h - max(o, c)) / rango, "m_inf": (min(o, c) - l) / rango,
        "r_atr": rango / atr_prev if atr_prev > 0 else 1.0, "v_rel": v / vol_prev if vol_prev > 0 else 1.0,
        "cambio": (c / o - 1) * 100 if o else 0.0,
    }


def clase(m):
    if m is None:
        return "doji"
    if m["v_rel"] > 1.5 and m["r_atr"] > 1.5:
        return "impulso_alcista_vol" if m["alcista"] else "impulso_bajista_vol"
    if m["v_rel"] > 1.5 and m["r_atr"] < 0.8:
        return "esfuerzo_sin_resultado"
    if m["cuerpo"] > 0.6 and m["alcista"] and m["pos"] > 0.8:
        return "fuerte_alcista"
    if m["cuerpo"] > 0.6 and not m["alcista"] and m["pos"] < 0.2:
        return "fuerte_bajista"
    if m["m_inf"] > 0.5:
        return "rechazo_abajo"
    if m["m_sup"] > 0.5:
        return "rechazo_arriba"
    if m["cuerpo"] < 0.1:
        return "doji"
    if m["v_rel"] < 0.6 and m["r_atr"] < 0.6:
        return "sin_interes"
    return "normal_alcista" if m["alcista"] else "normal_bajista"


def referencias(o, h, l, c, v, i):
    """ATR14 y volumen medio de las velas ANTERIORES a i (listas o, h, l, c, v)."""
    a = max(1, i - 14)
    tr = [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(a, i)]
    atr = sum(tr) / len(tr) if tr else (h[i] - l[i])
    vs = v[max(0, i - 20):i]
    return atr, (sum(vs) / len(vs) if vs else v[i])


def clasificar_serie(o, h, l, c, v):
    """Clase de cada vela de la serie con las mismas referencias que `referencias` (solo velas anteriores), con sumas
    móviles para que una serie de millones de velas tarde segundos."""
    out = []
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(1, n)]
    s_tr = s_v = 0.0
    for i in range(n):
        # ventana de TR: k de max(1, i-14) a i-1; ventana de volumen: de max(0, i-20) a i-1
        if i >= 2:
            s_tr += tr[i - 1]
        if i - 15 >= 1:
            s_tr -= tr[i - 15]
        n_tr = i - max(1, i - 14)
        atr = s_tr / n_tr if n_tr > 0 else (h[i] - l[i])
        if i >= 1:
            s_v += v[i - 1]
        if i - 21 >= 0:
            s_v -= v[i - 21]
        n_v = i - max(0, i - 20)
        vol = s_v / n_v if n_v > 0 else v[i]
        out.append(clase(medidas(o[i], h[i], l[i], c[i], v[i], atr, vol)))
    return out
