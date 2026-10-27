"""Lectura rápida del mercado en 5 tiempos, en tiempo real, para que Claude decida (pedido de Nicolás del 26/10).

Uso:  python3 -I lectura_mercado.py [carpeta_de_salida]
Lee velas de Coinbase BTC-USD (la API de Binance da 451 desde la nube), comprueba que estén completas y sin huecos,
y deja en la carpeta:
  - resumen.txt: una línea por tiempo (dirección, cambio, rango, posición en el rango, volatilidad frente a su media,
    pendiente y patrón de vela del curso) más el contexto y los niveles de las estrategias vivas.
  - 1_5min.png ... 5_3meses.png: la foto de las velas de cada tiempo, para mirarlas antes de decidir.
Este programa no decide ni abre operaciones: solo lee y resume. Decide Claude.
Solo biblioteca estándar (urllib, zlib, struct): no hace falta instalar nada."""
import datetime as dt
import json
import os
import struct
import sys
import time
import urllib.request
import zlib

API = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

# (nombre, granularidad en segundos, número de velas que se muestran y se resumen)
TIEMPOS = [("5 min", 300, 12), ("3 horas", 300, 36), ("16 horas", 900, 64), ("1 día", 3600, 24), ("3 meses", 86400, 90)]


def velas(gran, n, extra=0):
    """Últimas n + extra velas CERRADAS de la granularidad dada, en orden: [t, low, high, open, close, vol]."""
    ahora = int(time.time())
    fin = ahora - ahora % gran  # inicio de la vela en curso: no se usa (no está cerrada)
    total = n + extra
    out = {}
    t1 = fin
    while len(out) < total and t1 > fin - gran * (total + 300):
        t0 = t1 - gran * 300
        u = f"{API}?granularity={gran}&start={dt.datetime.fromtimestamp(t0, dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}&end={dt.datetime.fromtimestamp(t1 - 1, dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
        for intento in range(3):
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "lectura"}), timeout=30)
                for x in json.loads(r.read()):
                    if x[0] < fin:
                        out[x[0]] = [float(v) for v in x]
                break
            except Exception:
                time.sleep(2)
        t1 = t0
    v = [out[k] for k in sorted(out)][-total:]
    huecos = sum(1 for a, b in zip(v, v[1:]) if b[0] - a[0] != gran)
    return v, huecos


def patron(v):
    """Patrón del curso en la última vela cerrada (forma + contexto de las 10 previas). Devuelve texto o ''."""
    if len(v) < 14:
        return ""
    t, l, h, o, c = v[-1][:5]
    cu, r = abs(c - o), h - l
    sup, inf = h - max(o, c), min(o, c) - l
    prev = v[-2]
    cu1 = abs(prev[4] - prev[3])
    tend = v[-2][4] - v[-12][4]
    rmed = sum(x[2] - x[1] for x in v[-21:-1]) / 20 if len(v) > 21 else r
    p = []
    if r > 0 and cu <= 0.1 * r and sup >= 0.3 * r and inf >= 0.3 * r and r > rmed:
        p.append("doji de piernas largas (indecisión, más movimiento)")
    if tend < 0 and prev[4] < prev[3] and c > o and cu > cu1 and c >= prev[3]:
        p.append("envolvente alcista")
    if tend > 0 and prev[4] > prev[3] and c < o and cu > cu1 and c <= prev[3]:
        p.append("envolvente bajista")
    if cu > 0 and inf >= 2 * cu and sup <= 0.5 * cu and r > 0.5 * rmed:
        p.append("martillo" if tend < 0 else "hombre colgado")
    if cu > 0 and sup >= 2 * cu and inf <= 0.5 * cu and r > 0.5 * rmed:
        p.append("martillo invertido" if tend < 0 else "estrella fugaz")
    if r > 0 and 0.1 * r < cu <= 0.3 * r and sup >= cu and inf >= cu:
        p.append("peonza (indecisión)")
    return ", ".join(p)


def resumir(nombre, v, n):
    w = v[-n:]
    c0, c1 = w[0][3], w[-1][4]
    lo, hi = min(x[1] for x in w), max(x[2] for x in w)
    pos = (c1 - lo) / (hi - lo) if hi > lo else 0.5
    rangos = [(x[2] - x[1]) / x[4] * 100 for x in v]
    r_act = sum(rangos[-n:]) / n
    r_ref = sum(rangos) / len(rangos)
    k = min(n, 20)
    ys = [x[4] for x in w[-k:]]
    xm, ym = (k - 1) / 2, sum(ys) / k
    pend = sum((i - xm) * (y - ym) for i, y in enumerate(ys)) / sum((i - xm) ** 2 for i in range(k)) / c1 * 100
    alcistas = sum(1 for x in w if x[4] > x[3])
    dire = "SUBE" if c1 > c0 * 1.001 else "BAJA" if c1 < c0 * 0.999 else "LATERAL"
    return (f"{nombre:8s} {dire:7s} {(c1 / c0 - 1) * 100:+6.2f} % | rango {lo:,.0f}-{hi:,.0f} ({(hi / lo - 1) * 100:.2f} %) | "
            f"posición {pos:.2f} | vol/vela {r_act:.2f} % ({r_act / r_ref:.1f}x su media) | pendiente {pend:+.3f} %/vela | "
            f"velas alcistas {alcistas}/{n} | última vela: {patron(v) or 'sin patrón'}")


# ---------- foto de las velas en PNG (sin librerías) ----------

def png(ruta, v, titulo_alto=0):
    W, H, M = 900, 420, 20
    img = bytearray([255, 255, 255] * W * H)

    def px(x, y, col):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            img[i:i + 3] = bytes(col)

    lo, hi = min(x[1] for x in v), max(x[2] for x in v)
    esc = lambda p: int(H - M - (p - lo) / (hi - lo or 1) * (H - 2 * M))
    for gy in range(5):  # líneas guía
        y = M + gy * (H - 2 * M) // 4
        for x in range(0, W, 4):
            px(x, y, (225, 225, 225))
    ancho = (W - 2 * M) / len(v)
    cw = max(1, int(ancho * 0.6))
    for i, (t, l, h, o, c, _) in enumerate(v):
        x0 = int(M + i * ancho + (ancho - cw) / 2)
        col = (22, 150, 80) if c >= o else (205, 45, 45)
        xm = x0 + cw // 2
        for y in range(esc(h), esc(l) + 1):
            px(xm, y, (90, 90, 90))
        ya, yb = sorted((esc(o), esc(c)))
        for y in range(ya, max(yb, ya + 1) + 1):
            for x in range(x0, x0 + cw):
                px(x, y, col)
    # media de 20 en azul
    if len(v) >= 20:
        for i in range(19, len(v)):
            m = sum(x[4] for x in v[i - 19:i + 1]) / 20
            xm = int(M + i * ancho + ancho / 2)
            for d in (-1, 0, 1):
                px(xm + d, esc(m), (40, 90, 220))
    raw = b"".join(b"\x00" + bytes(img[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(ruta, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def senales(apertura, atr, alcista, cierre_ayer):
    """Señales de hoy de los dos libros, con el motor comprobado (sistema.py: idéntico al simulador en 2.502 de 2.502
    comparaciones). Solo informa: decide Claude."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sistema
    hoy = dt.datetime.now(dt.timezone.utc).date()
    try:
        D, ops, texto = sistema.informe(sistema.Coinbase(), hoy)
    except sistema.LecturaInsuficiente as e:
        return [f"SEÑALES DE HOY: NO OPERAR, lectura insuficiente ({e})"]
    t = int(time.time())
    conf = (f"CONFIRMACIÓN DE LOS OTROS TIEMPOS (EMA 20, a favor del contexto {'alcista' if D.ctx > 0 else 'bajista'}): "
            f"1 h {'sí' if D.e1h(t, D.ctx) else 'no'} · 4 h {'sí' if D.e4h(t, D.ctx) else 'no'} · 1 día {'sí' if D.e1d(t, D.ctx) else 'no'} · "
            f"patrón del curso a favor en las 3 últimas velas de 1 h: {'sí' if D.patron1h(t, D.ctx) else 'no'}")
    return ["SEÑALES DE HOY (motor sistema.py; el programa no decide: decide Claude)"] + texto.splitlines()[1:] + [conf]


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "lectura"
    os.makedirs(carpeta, exist_ok=True)
    t0 = time.time()
    lineas, ok = [], True
    ahora = dt.datetime.now(dt.timezone.utc)
    lineas.append(f"LECTURA DEL MERCADO BTC-USD (Coinbase) · {ahora:%d/%m/%Y %H:%M} UTC · {(ahora - dt.timedelta(hours=5)):%H:%M} Colombia")
    cache = {}
    for idx, (nombre, gran, n) in enumerate(TIEMPOS, 1):
        clave = (gran, n)
        extra = 60 if gran >= 3600 else 40
        if gran not in cache or len(cache[gran][0]) < n + extra:
            cache[gran] = velas(gran, n, extra)
        v, hue = cache[gran]
        v = v[-(n + extra):]
        completo = len(v) >= n + 20 and hue == 0
        ok &= completo
        lineas.append(resumir(nombre, v, n) + ("" if completo else f"  ¡LECTURA INCOMPLETA: {len(v)} velas, {hue} huecos!"))
        png(os.path.join(carpeta, f"{idx}_{nombre.replace(' ', '')}.png"), v[-n:])
    # contexto y niveles de las estrategias vivas
    d, hue = velas(86400, 60)
    precio = cache[300][0][-1][4]
    sma50 = sum(x[4] for x in d[-50:]) / 50
    tr = [max(b[2] - b[1], abs(b[2] - a[4]), abs(b[1] - a[4])) for a, b in zip(d[-16:], d[-15:])]
    atr = sum(tr[-14:]) / 14
    hoy = int(time.time()) // 86400 * 86400
    m1, _ = velas(60, 2)
    apertura = None
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            f"{API}?granularity=60&start={dt.datetime.fromtimestamp(hoy, dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}&end={dt.datetime.fromtimestamp(hoy + 120, dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
            headers={"User-Agent": "lectura"}), timeout=30)
        apertura = sorted(json.loads(r.read()))[0][3]
    except Exception:
        pass
    regimen = "ALCISTA (solo largos)" if d[-1][4] > sma50 else "BAJISTA (largos de P05b y P11 vetados; P05b solo en corto)"
    lineas.append(f"CONTEXTO: cierre de ayer {d[-1][4]:,.2f} vs SMA 50 diaria {sma50:,.2f} ({(d[-1][4] / sma50 - 1) * 100:+.2f} %) -> {regimen}. ATR14 diario {atr:,.0f} ({atr / precio * 100:.2f} %).")
    if apertura:
        lineas.append(f"NIVELES DE HOY (apertura 00:00 UTC {apertura:,.2f}): P05b largo > {apertura + 0.5 * atr:,.2f} · P05b corto < {apertura - 0.5 * atr:,.2f} · "
                      f"P05c largo > {apertura + atr:,.2f} · precio {precio:,.2f} ({(precio / apertura - 1) * 100:+.2f} % desde la apertura)")
    if apertura:
        lineas += senales(apertura, atr, d[-1][4] > sma50, d[-1][4])
    lineas.append(f"Lectura {'COMPLETA' if ok and hue == 0 else 'INCOMPLETA: NO OPERAR'} en {time.time() - t0:.1f} s. Fotos en {carpeta}/ (verde sube, rojo baja, azul = media de 20).")
    texto = "\n".join(lineas)
    open(os.path.join(carpeta, "resumen.txt"), "w", encoding="utf-8").write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
