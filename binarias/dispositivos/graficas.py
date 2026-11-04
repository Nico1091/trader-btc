"""Gráfica de la decisión con las seis líneas, sin librerías (04/11/2026). Corre en la caja T95H y en el teléfono.

Pedido suyo (04/11): que cada SÍ o NO llegue a su Telegram con la foto y las líneas, y que las líneas sean seis.
Es la misma regla y el mismo dibujo de Pulso (pulso-btc/src/main.rs: sus_lineas, seis_lineas, tramo_corto y
grafica_lineas), portados a Python puro con la misma aritmética entera: un lienzo de paleta de 900 × 420 y un PNG
armado con zlib. La paridad con Pulso se comprueba píxel a píxel con las mismas velas.
- Techo y piso largos (azul): desde el máximo más alto y el mínimo más bajo, sin cortar los máximos o mínimos siguientes.
- Techo y piso cortos (ámbar): desde el último giro con 3 velas a cada lado, distinto del extremo y con tramo de 6 velas
  o más; si el precio ya rompió ese tramo, se dibujan solo hasta donde lo rompió.
- Dos horizontales (violeta, punteadas): el nivel con más cierres en el 40 % alto y en el 40 % bajo del rango.
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


def _largas(v):
    """Techo y piso largos (None si su extremo es de las últimas 5 velas), horizontal del medio e índices de los extremos."""
    n = len(v)
    if n < 60:
        return None
    base = v[: n - 2]
    m = len(base)
    ip = max(range(m), key=lambda a: (base[a][2], a))   # Rust max_by: el último de los máximos
    iv = min(range(m), key=lambda a: (base[a][3], a))   # Rust min_by: el primero de los mínimos
    techo = piso = None
    if ip + 5 < m:
        pend_t = max((base[j][2] - base[ip][2]) / (j - ip) for j in range(ip + 3, m))
        techo = Recta(ip, base[ip][2], min(pend_t, 0.0))
    if iv + 5 < m:
        pend_p = min((base[j][3] - base[iv][3]) / (j - iv) for j in range(iv + 3, m))
        piso = Recta(iv, base[iv][3], max(pend_p, 0.0))
    cierres = sorted(x[4] for x in base[max(0, m - 60):])
    return techo, piso, cierres[len(cierres) // 2], ip, iv


def sus_lineas(v):
    """Igual que en Pulso: si el máximo o el mínimo es de las últimas 5 velas, no hay líneas."""
    r = _largas(v)
    if not r or r[0] is None or r[1] is None:
        return None
    return r[0], r[1], r[2]


def _tramo_corto(base, j, techo):
    m = len(base)
    alto = (lambda k: base[k][2]) if techo else (lambda k: -base[k][3])
    fin = next((k for k in range(j + 1, m) if alto(k) > alto(j)), m)
    if fin < j + 6:
        return None
    pend = min(max((alto(k) - alto(j)) / (k - j) for k in range(j + 3, fin)), 0.0)
    roto = fin if fin < m else None
    return (Recta(j, base[j][2], pend), roto) if techo else (Recta(j, base[j][3], -pend), roto)


def seis_lineas(v, parcial=False):
    """Con parcial=False, igual que Pulso (None si falta una línea larga). Con parcial=True, para la foto de cada
    decisión: la línea larga cuyo extremo es de las últimas 5 velas queda sin trazar y se dibujan las demás."""
    r = _largas(v)
    if not r:
        return None
    techo, piso, medio, ip, iv = r
    if not parcial and (techo is None or piso is None):
        return None
    base = v[: len(v) - 2]
    m = len(base)

    def corto(es_techo, extremo):
        alto = (lambda k: base[k][2]) if es_techo else (lambda k: -base[k][3])
        for j in range(m - 4, 2, -1):
            if j != extremo and all(alto(k) <= alto(j) for k in range(j - 3, j + 4)):
                t = _tramo_corto(base, j, es_techo)
                if t:
                    return t
        return None

    cierres = [x[4] for x in base]
    lo, hi = min(cierres), max(cierres)
    ancho = max((hi - lo) / 40.0, 1e-9)
    cajas, sumas = [0] * 40, [0.0] * 40
    for c in cierres:
        k = min(int((c - lo) / ancho), 39)
        cajas[k] += 1
        sumas[k] += c

    def nivel(a, b):
        k, mejor = a, -1
        for kk in range(a, b):  # Rust max_by_key: el último de los máximos
            if cajas[kk] >= mejor:
                mejor, k = cajas[kk], kk
        return sumas[k] / cajas[k] if cajas[k] > 0 else lo + ancho * (k + 0.5)

    return {"techo": techo, "piso": piso, "techo_c": corto(True, ip), "piso_c": corto(False, iv),
            "arriba": nivel(24, 40), "abajo": nivel(0, 16), "medio": medio}


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


def grafica(v, s):
    """PNG con las velas y las seis líneas (mismo dibujo que grafica_lineas de Pulso)."""
    l = Lienzo()
    izq, der, arr, aba = 12, ANCHO - 150, 20, ALTO - 20
    n = len(v)
    total = n + 20  # velas de espacio a la derecha para ver hacia dónde van las líneas
    lo = min(x[3] for x in v)
    hi = max(x[2] for x in v)
    lo_v, hi_v = lo, hi

    def hasta(fin):
        return total - 1 if fin is None else fin
    rectas = [(s[k], 5, total - 1) for k in ("techo", "piso") if s[k] is not None]
    for clave in ("techo_c", "piso_c"):
        if s[clave]:
            r, fin = s[clave]
            rectas.append((r, 6, hasta(fin)))
    for r, _, fin in rectas:
        for i in (r.i0, min(fin, n - 1), fin):
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
    for h in (s["arriba"], s["abajo"]):
        yh, x = y_de(h), izq
        while x < der:
            l.linea((x, yh), (min(x + 8, der), yh), 7, 1)
            x += 14
    for r, c, fin in rectas:
        l.linea((x_de(r.i0), y_de(r.en(r.i0))), (x_de(fin), y_de(r.en(fin))), c, 2)
    ult = v[n - 1]
    y_ult = min(max(y_de(ult[4]) - 7, arr + 25), aba - 40)
    l.texto(der + 12, y_de(hi_v), f"{hi_v:.0f}", 4)
    l.texto(der + 12, y_de(lo_v) - 15, f"{lo_v:.0f}", 4)
    l.texto(der + 12, y_ult, f"{ult[4]:.0f}", 2 if ult[4] >= ult[1] else 3)
    ocupados = [y_de(hi_v), y_de(lo_v) - 15, y_ult]
    for h in (s["arriba"], s["abajo"]):
        y = y_de(h) - 7
        if all(abs(o - y) > 18 for o in ocupados):
            l.texto(der + 12, y, f"{h:.0f}", 7)
            ocupados.append(y)
    return l.png()


def lectura(v, s):
    """Las seis líneas en la última vela, para el texto del aviso."""
    n = len(v)

    def corto(t):
        if not t:
            return "sin trazar"
        r, fin = t
        return "roto" if fin is not None else _miles(r.en(n - 1))

    def larga(r, cual):
        return _miles(r.en(n - 1)) if r is not None else f"sin trazar ({cual} de los últimos 5 min)"
    return (f"techo {larga(s['techo'], 'el máximo es')} (corto {corto(s['techo_c'])}), piso {larga(s['piso'], 'el mínimo es')} "
            f"(corto {corto(s['piso_c'])}), horizontales {_miles(s['arriba'])} y {_miles(s['abajo'])}")


def _miles(x):
    """Como miles() de Pulso: valor absoluto redondeado alejándose del cero, con punto de miles."""
    return f"{int(math.floor(abs(x) + 0.5)):,}".replace(",", ".")
