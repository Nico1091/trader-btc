"""Gráfica de la decisión con las cinco líneas, sin librerías (04/11/2026). Corre en la caja T95H y en el teléfono.

Pedido suyo (04/11, 12:00): «quiero 5 líneas bien optimizadas para mis mínimos y máximos y la recta de la mitad». Sustituye
a las seis líneas de la madrugada, de las que solo se veían las dos azules. Es la misma regla y el mismo dibujo de Pulso
(pulso-btc/src/main.rs: optima, cinco_lineas, grafica_lineas y lectura_lineas), con la misma aritmética: un lienzo de
paleta de 900 × 420 y un PNG armado con zlib. La paridad se comprueba píxel a píxel con herramientas/paridad_lineas.py.
- Cada recta pasa por un máximo (techo) o un mínimo (piso) y se ajusta por mínimos cuadrados a todos los demás sin que
  ninguna vela la cruce (ajuste automático de líneas de tendencia, como TrendLineAutomation de neurotrader888, en forma
  cerrada). Se apoya en el punto que más se aleja de la regresión, así que se traza siempre, también cuando el extremo
  es de las últimas velas.
- Azul: techo y piso sobre las velas sin las 2 últimas, que son las que pueden romperlas.
- Ámbar: techo corto desde el inicio de la última caída (el máximo de las últimas 45 velas) y piso corto desde el inicio
  de la última subida (el mínimo); si ese inicio es de las últimas 7 velas, se usan las últimas 20.
- Violeta discontinua: la recta de la mitad, el centro exacto entre el techo y el piso.
Las sumas van en bucle explícito: sum() suma distinto desde Python 3.12 y rompería la paridad entre el PC (3.11), los
equipos (3.14) y Pulso (Rust).
Velas: lista de (t, apertura, máximo, mínimo, cierre) de 1 min, ya cerradas; se usan las 150 últimas.
"""
import math
import struct
import zlib

ANCHO, ALTO = 900, 420
PALETA = [(0x13, 0x17, 0x22), (0x2A, 0x2E, 0x39), (0x26, 0xA6, 0x9A), (0xEF, 0x53, 0x50),
          (0xD1, 0xD4, 0xDC), (0x29, 0x62, 0xFF), (0xFF, 0xB3, 0x00), (0xC0, 0x7C, 0xFF)]
CIFRAS = {"0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7), "2": (7, 1, 7, 4, 7), "3": (7, 1, 7, 1, 7), "4": (5, 5, 7, 1, 1),
          "5": (7, 4, 7, 1, 7), "6": (7, 4, 7, 5, 7), "7": (7, 1, 1, 1, 1), "8": (7, 5, 7, 5, 7), "9": (7, 5, 7, 1, 7),
          ".": (0, 0, 0, 0, 2)}
CORTO, CORTO_MIN, CORTO_FALLA = 45, 8, 20   # tramo corto: el extremo de las últimas 45 velas; si es de las últimas 7, 20 velas
GROSOR = 3


class Recta:
    __slots__ = ("i0", "p0", "pend")

    def __init__(self, i0, p0, pend):
        self.i0, self.p0, self.pend = i0, p0, pend

    def en(self, i):
        return self.p0 + self.pend * (i - self.i0)


def _div(a, b):
    """División entera que trunca hacia cero, como la de Rust con i64."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def _optima(y, techo, off):
    """Recta de techo (o de piso) sobre y. Pasa por el punto que más se aleja de la regresión y, entre las pendientes que no
    dejan ningún punto por fuera, toma la más cercana a la de mínimos cuadrados. Devuelve (recta, índice desde donde se
    dibuja: el primero de los dos puntos que toca)."""
    n = len(y)
    sx = sy = 0.0
    for i in range(n):
        sx += i
        sy += y[i]
    xm, ym = sx / n, sy / n
    sxy = sxx = 0.0
    for i in range(n):
        dx = i - xm
        sxy += dx * (y[i] - ym)
        sxx += dx * dx
    b = sxy / sxx
    p, mejor = 0, y[0] - b * 0.0
    for i in range(1, n):
        d = y[i] - b * i
        if (d > mejor) if techo else (d < mejor):
            p, mejor = i, d
    lo, hi, ilo, ihi = -math.inf, math.inf, p, p
    num = den = 0.0
    for i in range(n):
        if i == p:
            continue
        d = i - p
        s = (y[i] - y[p]) / d
        if (d > 0) == techo:      # cota inferior de la pendiente
            if s > lo:
                lo, ilo = s, i
        elif s < hi:              # cota superior
            hi, ihi = s, i
        num += (y[i] - y[p]) * d
        den += d * d
    s, toque = num / den, p
    if s < lo:
        s, toque = lo, ilo
    elif s > hi:
        s, toque = hi, ihi
    return Recta(p + off, y[p], s), min(p, toque) + off


def cinco_lineas(v):
    """Las cinco líneas sobre las velas cerradas (None si hay menos de 60)."""
    n = len(v)
    if n < 60:
        return None
    base = v[: n - 2]
    m = len(base)
    alto = [x[2] for x in base]
    bajo = [x[3] for x in base]
    techo, d_t = _optima(alto, True, 0)
    piso, d_p = _optima(bajo, False, 0)

    def corto(es_techo):
        y = alto if es_techo else bajo
        a = max(0, m - CORTO)
        for i in range(a + 1, m):
            if (y[i] > y[a]) if es_techo else (y[i] < y[a]):
                a = i
        if m - a < CORTO_MIN:
            a = m - CORTO_FALLA
        return _optima(y[a:], es_techo, a)

    techo_c, d_tc = corto(True)
    piso_c, d_pc = corto(False)
    mitad = Recta(0, (techo.en(0) + piso.en(0)) / 2.0, (techo.pend + piso.pend) / 2.0)
    return {"techo": techo, "piso": piso, "techo_c": techo_c, "piso_c": piso_c, "mitad": mitad,
            "desde": {"techo": d_t, "piso": d_p, "techo_c": d_tc, "piso_c": d_pc, "mitad": min(d_t, d_p)}}


class Lienzo:
    def __init__(self):
        self.px = bytearray(ANCHO * ALTO)

    def punto(self, x, y, c):
        if 0 <= x < ANCHO and 0 <= y < ALTO:
            self.px[y * ANCHO + x] = c

    def linea(self, p0, p1, c, grosor):
        (x0, y0), (x1, y1) = p0, p1
        pasos = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(pasos + 1):
            x = x0 + _div((x1 - x0) * i, pasos)
            y = y0 + _div((y1 - y0) * i, pasos)
            for dx in range(grosor):
                for dy in range(grosor):
                    self.punto(x + dx, y + dy, c)

    def texto(self, x, y, s, c):
        esc = 3
        for k, ch in enumerate(s):
            for fy, fila in enumerate(CIFRAS.get(ch, (0, 0, 0, 0, 0))):
                for fx in range(3):
                    if fila >> (2 - fx) & 1:
                        for a in range(esc):
                            for b in range(esc):
                                self.punto(x + k * 4 * esc + fx * esc + a, y + fy * esc + b, c)

    def png(self):
        crudo = b"".join(b"\x00" + bytes(self.px[y * ANCHO:(y + 1) * ANCHO]) for y in range(ALTO))

        def trozo(tipo, datos):
            return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ANCHO, ALTO, 8, 3, 0, 0, 0))
                + trozo(b"PLTE", bytes(c for rgb in PALETA for c in rgb)) + trozo(b"IDAT", zlib.compress(crudo, 9))
                + trozo(b"IEND", b""))


ORDEN = (("mitad", 7), ("techo", 5), ("piso", 5), ("techo_c", 6), ("piso_c", 6))
CIFRAS_ORDEN = (("techo", 5), ("piso", 5), ("mitad", 7), ("techo_c", 6), ("piso_c", 6))


def grafica(v, s):
    """PNG con las velas y las cinco líneas (mismo dibujo que grafica_lineas de Pulso)."""
    l = Lienzo()
    izq, der, arr, aba = 12, ANCHO - 150, 20, ALTO - 20
    n = len(v)
    total = n + 20  # velas de espacio a la derecha para ver hacia dónde van las líneas
    lo = min(x[3] for x in v)
    hi = max(x[2] for x in v)
    lo_v, hi_v = lo, hi
    for clave, _ in ORDEN:
        r = s[clave]
        for i in (s["desde"][clave], n - 1, total - 1):
            p = r.en(i)
            if math.isfinite(p) and abs(p - v[n - 1][4]) < (hi_v - lo_v) * 1.5:
                lo, hi = min(lo, p), max(hi, p)
    mrg = max((hi - lo) * 0.04, 1.0)
    lo2, hi2 = lo - mrg, hi + mrg

    def y_de(p):
        return aba - int((p - lo2) / (hi2 - lo2) * (aba - arr))
    paso = max((der - izq) / total, 1.0)

    def x_de(i):
        return izq + int(i * paso + paso / 2.0)
    cuerpo = max(int(paso * 0.7), 1)
    for i, (_, o, h, lw, c) in enumerate(v):
        color = 2 if c >= o else 3
        cx = x_de(i)
        l.linea((cx, y_de(h)), (cx, y_de(lw)), color, 1)
        ya = y_de(max(o, c))
        yb = max(y_de(min(o, c)), y_de(max(o, c)) + 1)
        for y in range(ya, yb + 1):
            l.linea((cx - _div(cuerpo, 2), y), (cx - _div(cuerpo, 2) + cuerpo, y), color, 1)
    r, j = s["mitad"], s["desde"]["mitad"]
    while j < total - 1:  # la mitad, discontinua: 3 velas trazadas y 2 en blanco
        j2 = min(j + 3, total - 1)
        l.linea((x_de(j), y_de(r.en(j))), (x_de(j2), y_de(r.en(j2))), 7, GROSOR)
        j += 5
    for clave, c in ORDEN[1:]:
        r, d = s[clave], s["desde"][clave]
        l.linea((x_de(d), y_de(r.en(d))), (x_de(total - 1), y_de(r.en(total - 1))), c, GROSOR)
    ult = v[n - 1]
    y_ult = min(max(y_de(ult[4]) - 7, arr + 25), aba - 40)
    l.texto(der + 12, y_ult, f"{ult[4]:.0f}", 2 if ult[4] >= ult[1] else 3)
    ocupados = [y_ult]
    for clave, c in CIFRAS_ORDEN:
        val = s[clave].en(n - 1)
        y = min(max(y_de(val) - 7, arr), aba - 15)
        if all(abs(o - y) > 18 for o in ocupados):
            l.texto(der + 12, y, f"{val:.0f}", c)
            ocupados.append(y)
    for val, y in ((hi_v, y_de(hi_v)), (lo_v, y_de(lo_v) - 15)):
        y = min(max(y, arr), aba - 15)
        if all(abs(o - y) > 18 for o in ocupados):
            l.texto(der + 12, y, f"{val:.0f}", 4)
            ocupados.append(y)
    return l.png()


def lectura(v, s):
    """Dónde está el precio frente a las cinco líneas, para el texto del aviso (igual que lectura_lineas de Pulso)."""
    n = len(v)
    c = v[n - 1][4]
    t, p, md = s["techo"].en(n - 1), s["piso"].en(n - 1), s["mitad"].en(n - 1)
    if t < p:
        donde = "con el techo y el piso ya cruzados"
    elif c > t:
        donde = "por encima del techo"
    elif c < p:
        donde = "por debajo del piso"
    elif c >= md:
        donde = "dentro del canal, en la mitad alta"
    else:
        donde = "dentro del canal, en la mitad baja"
    txt = (f"precio {_miles(c)} {donde} · techo {_miles(t)} · piso {_miles(p)} · mitad {_miles(md)} · "
           f"techo corto {_miles(s['techo_c'].en(n - 1))} · piso corto {_miles(s['piso_c'].en(n - 1))}")
    tp, pp = s["techo"].pend, s["piso"].pend
    if tp < pp:
        k = (t - p) / (pp - tp)
        if 0.0 < k < 600.0:
            txt += f" · las líneas se juntan en unos {k:.0f} min"
    return txt


def _miles(x):
    """Como miles() de Pulso: valor absoluto redondeado alejándose del cero, con punto de miles."""
    return f"{int(math.floor(abs(x) + 0.5)):,}".replace(",", ".")
