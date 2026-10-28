"""Lector de velas v2 (28/10/2026): TODAS las velas cerradas de 6 marcos, con su significado y lo que pasó en el
historial después de velas iguales, con el contexto primero. Pedido de Nicolás: «que analice todas las velas, absolutamente
todas, todo lo que significa cada una, muy rápido, muy bien estructurado, ya sabiendo el contexto, para ver cuánto ganamos
en papel».

Qué imprime, en este orden (un solo comando, unos segundos):
  1. CONTEXTO: régimen (cierre de ayer frente a la SMA 50 y días de racha), ATR14 diario, niveles de hoy (apertura, bandas de
     P05b y P05c, rango de Asia de N9), estado de riesgo, señales del motor (sistema.py) y evento macro del día.
  2. ALINEACIÓN de los 6 marcos, de −6 a +6.
  3. Por marco (1 m ×60, 5 m ×36, 15 m ×64, 1 h ×48, 4 h ×42, 1 d ×90): una síntesis (estructura, EMA 20, volatilidad,
     posición en el rango, qué invalida la lectura) y UNA LÍNEA POR CADA VELA CERRADA: cambio, clase y su base medida
     (consolidacion/base_velas.json, de investigacion/plan-diario/a5_base_velas.py), dónde cierra, volumen y rango
     relativos, EMA 20, niveles que toca o rompe, patrones del curso y su relación con la vela anterior.
El lector no decide: describe y mide. Decide Claude, y escribe en qué no está de acuerdo con el lector.

Uso:
  python -I consolidacion/lector_velas.py                    -> BTC, todos los marcos, todas las velas de cada ventana
  python -I consolidacion/lector_velas.py --activo SOL       -> otra moneda (Binance futuros; si falla, Coinbase)
  python -I consolidacion/lector_velas.py --solo-nuevas      -> solo las velas cerradas desde la llamada anterior
  python -I consolidacion/lector_velas.py --marcos 15m,1h --n 20
  python -I consolidacion/lector_velas.py --json             -> lo mismo en JSON
  python -I consolidacion/lector_velas.py --fotos CARPETA    -> además, una foto por marco con ejes, niveles y volumen
Solo biblioteca estándar."""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import struct
import sys
import time
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import clases_vela as CV  # noqa: E402
import patrones_std  # noqa: E402
import riesgo  # noqa: E402
import sistema  # noqa: E402

UTC = dt.timezone.utc
COL = dt.timezone(dt.timedelta(hours=-5))
SEG = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
N_DEF = {"1m": 60, "5m": 36, "15m": 64, "1h": 48, "4h": 42, "1d": 90}
EXTRA = 60  # velas previas para EMA 20, ATR 14 y volumen medio
ESTADO = os.path.join(AQUI, "..", "diario", "lector-estado.json")
EVENTOS = os.path.join(AQUI, "eventos.json")


def p(x):
    """Precio con los decimales que pide su tamaño (BTC sin decimales, DOGE con cinco)."""
    if x >= 1000:
        return f"{x:,.0f}"
    if x >= 10:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:.3f}"
    return f"{x:.5f}"


def base():
    try:
        return json.load(open(os.path.join(AQUI, "base_velas.json"), encoding="utf-8"))["marcos"]
    except Exception:
        return {}


def traer(fuente, marco, n, ahora):
    """Velas cerradas [t, l, h, o, c, v] del marco. Coinbase no tiene 4 h: se arma con 1 h alineadas a 00, 04, 08…"""
    gran = SEG[marco]
    fin = ahora - ahora % gran
    ini = fin - gran * (n + EXTRA)
    if isinstance(fuente, sistema.Coinbase) and marco == "4h":
        h1 = fuente.velas(3600, ini, fin)
        g = {}
        for x in h1:
            g.setdefault(x[0] - x[0] % 14400, []).append(x)
        return [[k, min(b[1] for b in v), max(b[2] for b in v), v[0][3], v[-1][4], sum(b[5] for b in v)]
                for k, v in sorted(g.items()) if len(v) == 4]
    return [x for x in fuente.velas(gran, ini, fin) if x[0] + gran <= ahora]


def ema(xs, n=20):
    a, e, out = 2 / (n + 1), None, []
    for x in xs:
        e = x if e is None else e + a * (x - e)
        out.append(e)
    return out


def pivotes(h, l, k=2):
    altos = [i for i in range(k, len(h) - k) if h[i] == max(h[i - k:i + k + 1])]
    bajos = [i for i in range(k, len(l) - k) if l[i] == min(l[i - k:i + k + 1])]
    return altos, bajos


def leer_marco(marco, v, n, niveles, base_m):
    """Síntesis y una línea por cada una de las últimas n velas de v (cerradas, en orden)."""
    t = [x[0] for x in v]
    lo, hi, o, c, vol = ([x[k] for x in v] for k in (1, 2, 3, 4, 5))
    e20 = ema(c)
    pat = patrones_std.patrones(o, hi, lo, c)
    ini = max(0, len(v) - n)
    atrs = []
    filas = []
    zona = UTC if marco in ("4h", "1d") else COL
    for i in range(ini, len(v)):
        atr, vm = CV.referencias(o, hi, lo, c, vol, i)
        atrs.append(atr)
        m = CV.medidas(o[i], hi[i], lo[i], c[i], vol[i], atr, vm)
        cl = CV.clase(m)
        b = (base_m or {}).get("clases", {}).get(cl)
        btxt = (f"tras velas así sube el {b['sube'] * 100:.0f} % (n={b['n']:,})".replace(",", ".") if b and b["n"] >= 200
                else "base: muestra chica")
        if m:
            tercio = "arriba" if m["pos"] > 2 / 3 else "abajo" if m["pos"] < 1 / 3 else "al medio"
            desc = (f"cierra {tercio} · vol ×{m['v_rel']:.1f} · rango ×{m['r_atr']:.1f} ATR")
        else:
            desc = "sin rango"
        d_ema = (c[i] - e20[i]) / atr if atr > 0 else 0
        cruce = ""
        if i > 0 and (c[i - 1] - e20[i - 1]) * (c[i] - e20[i]) < 0:
            cruce = " (CRUZA al alza)" if c[i] > e20[i] else " (CRUZA a la baja)"
        etxt = f"{'sobre' if d_ema >= 0 else 'bajo'} EMA20 {d_ema:+.1f} ATR{cruce}"
        rel = ""
        if i > 0:
            if hi[i] < hi[i - 1] and lo[i] > lo[i - 1]:
                rel = " · vela interior"
            elif hi[i] > hi[i - 1] and lo[i] < lo[i - 1]:
                rel = " · envuelve a la anterior"
            elif hi[i] > hi[i - 1] and lo[i] >= lo[i - 1]:
                rel = " · máximo y mínimo más altos"
            elif lo[i] < lo[i - 1] and hi[i] <= hi[i - 1]:
                rel = " · máximo y mínimo más bajos"
        ventana = range(max(0, i - 20), i)
        rot = ""
        if ventana and hi[i] > max(hi[k] for k in ventana):
            rot = " · ROMPE el máximo de 20"
        elif ventana and lo[i] < min(lo[k] for k in ventana):
            rot = " · ROMPE el mínimo de 20"
        niv = ""
        if marco in ("1m", "5m", "15m", "1h"):
            toca = [nombre for nombre, x in niveles if x and lo[i] <= x <= hi[i]]
            if toca:
                niv = " · toca " + ", ".join(toca)
        pats = [k + ("↑" if patrones_std.LADO[k] > 0 else "↓" if patrones_std.LADO[k] < 0 else "·")
                for k in patrones_std.LADO if pat[k][i]]
        hora = dt.datetime.fromtimestamp(t[i], zona).strftime("%d %H:%M")
        filas.append({"n": i - ini + 1, "t": t[i], "linea":
                      f"#{i - ini + 1:02d} {hora} {p(o[i])}→{p(c[i])} {m['cambio'] if m else 0:+.2f} % · {CV.TEXTO[cl]} "
                      f"[{btxt}] · {desc} · {etxt}{rel}{rot}{niv}{' · patrón ' + ' '.join(pats) if pats else ''}",
                      "clase": cl})
    # síntesis
    w = range(ini, len(v))
    altos, bajos = pivotes(hi[ini:], lo[ini:])
    if len(altos) >= 2 and len(bajos) >= 2:
        a1, a2 = hi[ini + altos[-2]], hi[ini + altos[-1]]
        b1, b2 = lo[ini + bajos[-2]], lo[ini + bajos[-1]]
        estructura = ("alcista (máximos y mínimos más altos)" if a2 > a1 and b2 > b1 else
                      "bajista (máximos y mínimos más bajos)" if a2 < a1 and b2 < b1 else "lateral o en transición")
        invalida = (f"un cierre bajo {p(b2)}" if a2 > a1 and b2 > b1 else
                    f"un cierre sobre {p(a2)}" if a2 < a1 and b2 < b1 else f"salir de {p(min(b1, b2))}-{p(max(a1, a2))}")
    else:
        estructura, invalida = "sin pivotes suficientes", "-"
    atr_now = atrs[-1] if atrs else 0
    pend = (e20[-1] - e20[-6]) / atr_now if atr_now > 0 and len(e20) > 6 else 0
    pend_txt = "sube" if pend > 0.1 else "cae" if pend < -0.1 else "plana"
    pct = sum(1 for a in atrs if a <= atr_now) / len(atrs) if atrs else 0.5
    vol_txt = "baja" if pct < 0.3 else "alta" if pct > 0.7 else "media"
    rh, rl = max(hi[k] for k in w), min(lo[k] for k in w)
    pos = (c[-1] - rl) / (rh - rl) if rh > rl else 0.5
    alin = 1 if c[-1] > e20[-1] and pend > 0.1 else -1 if c[-1] < e20[-1] and pend < -0.1 else 0
    sintesis = (f"--- {marco} · {len(filas)} velas · estructura {estructura} · EMA20 {pend_txt} · volatilidad {vol_txt} "
                f"(ATR en el percentil {pct * 100:.0f} de la ventana) · posición en el rango {pos:.2f} ({p(rl)}-{p(rh)}) · "
                f"invalida la lectura: {invalida} ---")
    return {"marco": marco, "sintesis": sintesis, "alineacion": alin, "velas": filas, "serie": v[ini:], "e20": e20[ini:]}


def contexto(activo, fuente, nombre, ahora):
    D = 86400
    hoy0 = ahora - ahora % D
    d = [x for x in fuente.velas(D, hoy0 - 130 * D, hoy0) if x[0] + D <= ahora]
    cierres = [x[4] for x in d]
    sma = [sum(cierres[i - 50:i]) / 50 for i in range(50, len(cierres) + 1)]
    ctx = 1 if cierres[-1] > sma[-1] else -1
    racha = 0
    for k in range(1, len(sma) + 1):
        if (cierres[-k] > sma[-k]) == (ctx > 0):
            racha += 1
        else:
            break
    tr = [max(b[2] - b[1], abs(b[2] - a[4]), abs(b[1] - a[4])) for a, b in zip(d[-15:], d[-14:])]
    atr = sum(tr) / 14
    m1 = fuente.velas(60, hoy0, ahora - ahora % 60)
    ap = m1[0][3] if m1 else cierres[-1]
    precio = m1[-1][4] if m1 else cierres[-1]
    asia = [x for x in m1 if x[0] < hoy0 + 7 * 3600]
    niveles = [("apertura", ap), ("P05b↑", ap + 0.5 * atr), ("P05b↓", ap - 0.5 * atr), ("P05c↑", ap + atr)]
    asia_txt = ""
    if ahora >= hoy0 + 7 * 3600 and len(asia) > 400:
        ah, al = max(x[2] for x in asia), min(x[1] for x in asia)
        niveles += [("Asia alto", ah), ("Asia bajo", al)]
        asia_txt = f" · Asia {p(al)}-{p(ah)} (N9 {'↑ ' + p(ah) if ctx > 0 else '↓ ' + p(al)}, 07-13 UTC)"
    L = [f"CONTEXTO: {'ALCISTA' if ctx > 0 else 'BAJISTA'} desde hace {racha} días (cierre de ayer {p(cierres[-1])} frente a "
         f"SMA 50 {p(sma[-1])}, {(cierres[-1] / sma[-1] - 1) * 100:+.2f} %) · ATR14 diario {p(atr)} ({atr / precio * 100:.2f} %)",
         f"NIVELES DE HOY: apertura {p(ap)} · P05b ↑{p(ap + 0.5 * atr)} / ↓{p(ap - 0.5 * atr)} · P05c ↑{p(ap + atr)}{asia_txt}"
         f" · precio {p(precio)} ({(precio / ap - 1) * 100:+.2f} % desde la apertura)"]
    return L, niveles, ctx


def eventos(ahora):
    try:
        ev = json.load(open(EVENTOS, encoding="utf-8"))
    except Exception:
        return []
    hoy = dt.datetime.fromtimestamp(ahora, UTC).date().isoformat()
    return [f"EVENTO: {e['evento']} ({e['hora_utc']} UTC). {e['regla']}" for e in ev if e["fecha"] == hoy]


# ---------------------------------------------------------------- fotos (PNG propio, sin librerías)
FUENTE = {  # 3×5 píxeles por carácter
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111", "4": "101101111001001",
    "5": "111100111001111", "6": "111100111101111", "7": "111001001001001", "8": "111101111101111", "9": "111101111001111",
    ".": "000000000000010", ",": "000000000010100", ":": "000010000010000", "-": "000000111000000", " ": "000000000000000",
}


def png(ruta, f, titulo_niveles, ancho=1100, alto=520):
    serie, e20 = f["serie"], f["e20"]
    img = bytearray([255, 255, 255] * ancho * alto)
    M_IZ, M_DE, M_AR, M_AB, VOL = 10, 90, 12, 30, 70

    def px(x, y, col):
        if 0 <= x < ancho and 0 <= y < alto:
            i = (y * ancho + x) * 3
            img[i:i + 3] = bytes(col)

    def texto(x, y, s, col=(60, 60, 60), esc=2):
        for ch in s:
            g = FUENTE.get(ch, FUENTE[" "])
            for r in range(5):
                for cc in range(3):
                    if g[r * 3 + cc] == "1":
                        for dx in range(esc):
                            for dy in range(esc):
                                px(x + cc * esc + dx, y + r * esc + dy, col)
            x += 4 * esc
    lo = min(x[1] for x in serie)
    hi = max(x[2] for x in serie)
    for _, v in titulo_niveles:
        if v and lo * 0.98 < v < hi * 1.02:
            lo, hi = min(lo, v), max(hi, v)
    alto_p = alto - M_AR - M_AB - VOL
    esc = lambda pr: int(M_AR + (hi - pr) / ((hi - lo) or 1) * alto_p)  # noqa: E731
    n = len(serie)
    paso = (ancho - M_IZ - M_DE) / n
    cw = max(1, int(paso * 0.6))
    for k in range(6):  # rejilla y precios a la derecha
        pr = lo + (hi - lo) * k / 5
        y = esc(pr)
        for x in range(M_IZ, ancho - M_DE, 4):
            px(x, y, (228, 228, 228))
        texto(ancho - M_DE + 6, y - 5, p(pr).replace(",", "."))
    colores = {"apertura": (120, 120, 120), "P05b↑": (230, 140, 20), "P05b↓": (230, 140, 20), "P05c↑": (20, 150, 70),
               "Asia alto": (130, 60, 200), "Asia bajo": (130, 60, 200)}
    for nombre, v in titulo_niveles:  # niveles de hoy, con raya discontinua
        if v and lo <= v <= hi:
            y = esc(v)
            for x in range(M_IZ, ancho - M_DE):
                if (x // 6) % 2 == 0:
                    px(x, y, colores.get(nombre, (150, 150, 150)))
    vmax = max(x[5] for x in serie) or 1
    for i, (t, l, h, o, c, vol) in enumerate(serie):
        x0 = int(M_IZ + i * paso + (paso - cw) / 2)
        col = (22, 150, 80) if c >= o else (205, 45, 45)
        xm = x0 + cw // 2
        for y in range(esc(h), esc(l) + 1):
            px(xm, y, (90, 90, 90))
        ya, yb = sorted((esc(o), esc(c)))
        for y in range(ya, max(yb, ya + 1) + 1):
            for x in range(x0, x0 + cw):
                px(x, y, col)
        alto_v = int(vol / vmax * (VOL - 8))
        for y in range(alto - M_AB - alto_v, alto - M_AB):
            for x in range(x0, x0 + cw):
                px(x, y, (170, 190, 215))
        if i % max(1, n // 8) == 0 or i == n - 1:  # número de vela (igual que en el texto) y hora
            texto(x0, alto - M_AB + 4, f"{i + 1}")
            zona = UTC if f["marco"] in ("4h", "1d") else COL
            texto(x0, alto - M_AB + 16, dt.datetime.fromtimestamp(t, zona).strftime("%H:%M" if f["marco"] != "1d" else "%m-%d"))
    for i in range(1, n):  # EMA 20 en azul, gruesa
        x1 = int(M_IZ + (i - 1) * paso + paso / 2)
        x2 = int(M_IZ + i * paso + paso / 2)
        y1, y2 = esc(e20[i - 1]), esc(e20[i])
        pasos = max(1, abs(x2 - x1), abs(y2 - y1))
        for s in range(pasos + 1):
            for d in (-1, 0, 1):
                px(x1 + (x2 - x1) * s // pasos, y1 + (y2 - y1) * s // pasos + d, (40, 90, 220))
    raw = b"".join(b"\x00" + bytes(img[y * ancho * 3:(y + 1) * ancho * 3]) for y in range(alto))
    trozo = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)  # noqa: E731
    with open(ruta, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
                 + trozo(b"IDAT", zlib.compress(raw, 6)) + trozo(b"IEND", b""))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Lector de velas v2")
    ap.add_argument("--activo", default="BTC")
    ap.add_argument("--fuente", choices=("auto", "binance", "coinbase"), default="auto")
    ap.add_argument("--marcos", default="1m,5m,15m,1h,4h,1d")
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--solo-nuevas", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fotos", default="")
    a = ap.parse_args()
    t0 = time.time()
    ahora = int(time.time())
    activo = a.activo.upper()
    fuente, nombre = sistema.fuente_para(activo, a.fuente)
    marcos = a.marcos.split(",")
    bases = base() if activo == "BTC" else base()  # la base medida es de BTC; en otras monedas se usa como referencia
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        fut_ctx = ex.submit(contexto, activo, fuente, nombre, ahora)
        futs = {m: ex.submit(traer, fuente, m, a.n or N_DEF[m], ahora) for m in marcos}
        fut_sen = ex.submit(lambda: sistema.informe(fuente, dt.datetime.fromtimestamp(ahora, UTC).date(), None, activo)[2])
        ctx_lineas, niveles, ctx = fut_ctx.result()
        velas = {m: f.result() for m, f in futs.items()}
        try:
            senales = fut_sen.result()
        except sistema.LecturaInsuficiente as e:
            senales = f"SEÑALES: lectura insuficiente ({e})"
    marcos_leidos = [leer_marco(m, velas[m], a.n or N_DEF[m], niveles, bases.get(m)) for m in marcos if velas[m]]
    estado = {}
    if a.solo_nuevas and os.path.exists(ESTADO):
        estado = json.load(open(ESTADO, encoding="utf-8"))
    hora = dt.datetime.fromtimestamp(ahora, UTC)
    cab = [f"LECTOR DE VELAS v2 · {activo} · {hora:%Y-%m-%d %H:%M} UTC ({hora.astimezone(COL):%H:%M} Colombia) · fuente {nombre}"]
    cab += ctx_lineas
    cab += [riesgo.texto_estado().splitlines()[0]]
    cab += ["SEÑALES DEL MOTOR: " + " | ".join(x.strip() for x in senales.splitlines()[1:] if x.strip() and not x.strip().startswith("lectura "))]
    cab += eventos(ahora)
    al = sum(f["alineacion"] for f in marcos_leidos)
    cab.append(f"ALINEACIÓN DE MARCOS: {al:+d} de ±{len(marcos_leidos)} ("
               + ", ".join(f"{f['marco']} {'+' if f['alineacion'] > 0 else '−' if f['alineacion'] < 0 else '0'}" for f in marcos_leidos) + ")")
    cab.append("Cada vela: cambio · clase [qué pasó en el historial de BTC en las 4 velas siguientes a velas de esa clase] · "
               "dónde cierra · volumen y rango relativos · EMA 20 · relación con la anterior · rupturas y niveles · patrones del curso")
    salida_json = {"cabecera": cab, "marcos": []}
    cuerpo = []
    for f in marcos_leidos:
        clave = f"{activo}:{f['marco']}"
        filas = [x for x in f["velas"] if x["t"] > estado.get(clave, 0)] if a.solo_nuevas else f["velas"]
        cuerpo.append(f["sintesis"])
        cuerpo += [x["linea"] for x in filas] or ["(sin velas nuevas desde la llamada anterior)"]
        salida_json["marcos"].append({"marco": f["marco"], "sintesis": f["sintesis"], "velas": [x["linea"] for x in filas]})
        if f["velas"]:
            estado[clave] = f["velas"][-1]["t"]
    if a.solo_nuevas or not os.path.exists(ESTADO):
        os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
        json.dump(estado, open(ESTADO, "w", encoding="utf-8"))
    if a.fotos:
        os.makedirs(a.fotos, exist_ok=True)
        for f in marcos_leidos:
            png(os.path.join(a.fotos, f"{activo}_{f['marco']}.png"), f, niveles if f["marco"] in ("1m", "5m", "15m", "1h") else [])
        cuerpo.append(f"Fotos en {a.fotos}: una por marco, numeradas como el texto, con precios, horas, niveles de hoy y volumen.")
    total = sum(len(f["velas"]) for f in marcos_leidos)
    pie = f"Lectura de {total} velas en {len(marcos_leidos)} marcos en {time.time() - t0:.1f} s."
    if a.json:
        salida_json["pie"] = pie
        print(json.dumps(salida_json, ensure_ascii=False, indent=1))
    else:
        print("\n".join(cab + cuerpo + [pie]))


if __name__ == "__main__":
    main()
