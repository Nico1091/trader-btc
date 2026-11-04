"""Comprobantes en PDF de las apuestas, sin librerías (04/11/2026). Corre en la caja T95H y en el teléfono.

Pedido suyo (04/11): «facturación»: que al hacer clic en los enlaces lleve al sitio donde se ganó ese dinero, para que
después sea demostrable, que el bot lo haga solo por defecto y que se lo mande a su Telegram.
Cada SÍ cerrado deja un comprobante de una página, y cada día un resumen del papel. Los enlaces abren los datos oficiales
de Binance del minuto exacto (vela de entrada, vela del vencimiento e índice de precio con que liquida los Contratos de
Evento), así que cualquiera puede comprobar el resultado. Cada registro lleva su huella SHA-256.
PDF 1.4 hecho a mano: letras Helvetica y Courier con WinAnsiEncoding (tildes y eñes) y enlaces /URI.
"""
import datetime as dt
import hashlib
import json

COL = dt.timezone(dt.timedelta(hours=-5))
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&startTime={ms}&limit=1"
FIDX = "https://fapi.binance.com/fapi/v1/indexPriceKlines?pair=BTCUSDT&interval=1m&startTime={ms}&limit=11"
MONTO_USDT, COP_POR_USDT = 5.0, 3180.0  # 5 USDT ≈ 15.900 COP, la misma conversión del plan
PAGO = 0.85
ANCHO_PAG, ALTO_PAG, MARGEN = 595, 842, 50


def _txt(s):
    """Texto para PDF en WinAnsiEncoding, con los paréntesis y la barra escapados."""
    s = s.replace("−", "-").replace("→", "->").replace("–", "-")
    b = s.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _ancho(s, fuente, tam):
    if fuente == "F3":  # Courier: 0,6 em por letra
        return len(s) * 0.6 * tam
    return len(s) * (0.55 if fuente == "F2" else 0.5) * tam


class Pdf:
    def __init__(self):
        self.paginas = [[]]  # cada página: lista de (x, y, texto, fuente, tamaño, color, enlace)
        self.y = ALTO_PAG - MARGEN

    def linea(self, texto, fuente="F1", tam=10.5, color=(0, 0, 0), enlace=None, salto=None, x=MARGEN):
        salto = salto or tam * 1.45
        if self.y - salto < MARGEN:
            self.paginas.append([])
            self.y = ALTO_PAG - MARGEN
        self.y -= salto
        self.paginas[-1].append((x, self.y, texto, fuente, tam, color, enlace))

    def espacio(self, pt):
        self.y -= pt

    def bytes(self, titulo):
        objetos = []

        def nuevo(contenido):
            objetos.append(contenido)
            return len(objetos)
        cat = nuevo(None)
        pags = nuevo(None)
        fuentes = {}
        for nombre, base in (("F1", "Helvetica"), ("F2", "Helvetica-Bold"), ("F3", "Courier")):
            fuentes[nombre] = nuevo(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode())
        hijos = []
        for pag in self.paginas:
            flujo, anots = [], []
            for x, y, texto, fuente, tam, color, enlace in pag:
                flujo.append(b"%.3f %.3f %.3f rg BT /%s %.1f Tf %.1f %.1f Td (" % (color[0], color[1], color[2], fuente.encode(), tam, x, y)
                             + _txt(texto) + b") Tj ET")
                if enlace:
                    w = _ancho(texto, fuente, tam)
                    flujo.append(b"%.3f %.3f %.3f RG 0.6 w %.1f %.1f m %.1f %.1f l S" % (color[0], color[1], color[2], x, y - 1.5, x + w, y - 1.5))
                    uri = enlace.encode("ascii", errors="ignore").replace(b"(", b"%28").replace(b")", b"%29")
                    anots.append(nuevo(b"<< /Type /Annot /Subtype /Link /Rect [%.1f %.1f %.1f %.1f] /Border [0 0 0] /A << /S /URI /URI (%s) >> >>"
                                       % (x, y - 3, x + w, y + tam, uri)))
            datos = b"\n".join(flujo)
            cont = nuevo(b"<< /Length %d >>\nstream\n" % len(datos) + datos + b"\nendstream")
            pag_id = nuevo(None)
            objetos[pag_id - 1] = (b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >> /Contents %d 0 R"
                                   % (pags, ANCHO_PAG, ALTO_PAG, fuentes["F1"], fuentes["F2"], fuentes["F3"], cont)
                                   + (b" /Annots [" + b" ".join(b"%d 0 R" % a for a in anots) + b"]" if anots else b"") + b" >>")
            hijos.append(pag_id)
        objetos[cat - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pags
        objetos[pags - 1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % h for h in hijos) + b"] /Count %d >>" % len(hijos)
        info = nuevo(b"<< /Title (" + _txt(titulo) + b") /Producer (centinela de binarias) >>")
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        pos = []
        for i, o in enumerate(objetos, 1):
            pos.append(len(out))
            out += b"%d 0 obj\n" % i + (o if isinstance(o, bytes) else o.encode()) + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
        for p in pos:
            out += b"%010d 00000 n \n" % p
        out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, cat, info, xref)
        return bytes(out)


def _num(x, dec=2, signo=False):
    """Número con punto de miles y coma decimal (formato colombiano)."""
    t = f"{x:+,.{dec}f}" if signo else f"{x:,.{dec}f}"
    return t.replace(",", "§").replace(".", ",").replace("§", ".")


def _precio(x):
    return "–" if x is None else _num(x)


def _hora(ts, seg=True):
    return dt.datetime.fromtimestamp(ts, COL).strftime("%d/%m/%Y %H:%M:%S" if seg else "%H:%M")


def enlaces(a, retraso=60, plazo=600):
    return {"entrada": FAPI.format(ms=(a["t"] + retraso - 60) * 1000),
            "vencimiento": FAPI.format(ms=(a["t"] + retraso + plazo - 60) * 1000),
            "indice": FIDX.format(ms=(a["t"] + retraso - 60) * 1000)}


def huella(a):
    campos = {k: a.get(k) for k in ("t", "dir", "entrada", "salida", "res", "res_indice", "indice_entrada", "indice_salida", "si", "real")}
    return hashlib.sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def comprobante(a, etiqueta, retraso=60, plazo=600):
    """Una página por apuesta SÍ cerrada."""
    p = Pdf()
    azul, gris = (0.10, 0.30, 0.85), (0.35, 0.38, 0.45)
    real = bool(a.get("real"))
    sentido = "SUBE" if a["dir"] == 1 else "BAJA"
    res = {1: "ACIERTO", 0: "FALLO"}.get(a.get("res"), "sin resultado")
    res_i = {1: "ACIERTO", 0: "FALLO"}.get(a.get("res_indice"), "sin dato")
    ganancia = MONTO_USDT * PAGO if a.get("res") == 1 else -MONTO_USDT
    p.linea("Comprobante de apuesta · binaria BTC/USDT a 10 minutos", "F2", 15, salto=20)
    p.linea(("Apuesta real" if real else "Apuesta de papel (espejo del real): no se movió dinero") + " · Contratos de Evento de Binance", "F1", 10, gris)
    p.espacio(8)
    neto_previo = a.get("neto_previo")
    for t in (f"Decisión: {_hora(a['t'])} (hora de Colombia, UTC-5)",
              "Señal del núcleo: ruptura de 20 velas de 5 min al revés, decidida con la vela de 5 min ya cerrada",
              f"Aviso: SÍ OPERAR · {sentido} a 10 minutos · papel del día antes de la apuesta: {_num(neto_previo, 2, True) if neto_previo is not None else '–'}",
              f"Interés abierto en los 15 min previos: {_num(a['doi'] * 100, 3, True) + ' %' if a.get('doi') is not None else 'sin dato'}",
              f"Entrada ({retraso} s después de la decisión): {_precio(a.get('entrada'))} en futuros · índice {_precio(a.get('indice_entrada'))}",
              f"Vencimiento ({_hora(a['t'] + retraso + plazo)}): {_precio(a.get('salida'))} en futuros · índice {_precio(a.get('indice_salida'))}",
              f"Resultado: {res} con el precio de futuros · {res_i} con el índice con que liquida Binance",
              f"Monto: {_num(MONTO_USDT, 0)} USDT ({_num(MONTO_USDT * COP_POR_USDT, 0)} COP), sin apalancamiento, tope del 16 % del saldo",
              f"Resultado con pago de 0,85: {_num(ganancia, 2, True)} USDT ({_num(ganancia * COP_POR_USDT, 0, True)} COP)"):
        p.linea(t, "F1", 10.5)
    p.espacio(10)
    p.linea("Comprobación pública en Binance (abre los datos oficiales del minuto exacto):", "F2", 11)
    e = enlaces(a, retraso, plazo)
    for rotulo, clave in (("Vela de 1 min de la entrada, futuros BTCUSDT", "entrada"),
                          ("Vela de 1 min del vencimiento, futuros BTCUSDT", "vencimiento"),
                          ("Índice de precio de la entrada al vencimiento (11 velas)", "indice")):
        p.linea(rotulo, "F1", 10.5, azul, e[clave])
        p.linea(e[clave], "F3", 6.6, azul, e[clave], salto=10)
    p.espacio(10)
    p.linea("Cómo leerlo: cada vela trae [hora de apertura, apertura, máximo, mínimo, cierre, ...]; se usa el cierre.", "F1", 9, gris)
    p.linea("La entrada es el cierre de la vela de entrada y la salida, el de la vela del vencimiento.", "F1", 9, gris)
    p.espacio(8)
    p.linea(f"Huella SHA-256 del registro: {huella(a)}", "F3", 7.2, gris)
    p.linea(f"Generado por el centinela [{etiqueta}] el {_hora(dt.datetime.now(COL).timestamp())}.", "F1", 9, gris)
    return p.bytes(f"Comprobante {sentido} {_hora(a['t'])}")


def resumen_dia(apuestas, dia, etiqueta, retraso=60, plazo=600):
    """Todas las apuestas de papel del núcleo de un día, con su enlace de comprobación."""
    p = Pdf()
    azul, gris = (0.10, 0.30, 0.85), (0.35, 0.38, 0.45)
    cerradas = [a for a in apuestas if a.get("res") is not None]
    neto = sum(PAGO if a["res"] else -1.0 for a in cerradas)
    si = [a for a in cerradas if a.get("si")]
    neto_si = sum(PAGO if a["res"] else -1.0 for a in si)
    p.linea(f"Resumen del papel · {dia} · binarias BTC/USDT a 10 minutos", "F2", 15, salto=20)
    p.linea(f"{len(cerradas)} señales del núcleo · acertadas {sum(a['res'] for a in cerradas)} · neto {_num(neto, 2, True)} apuestas"
            f" ({_num(neto * MONTO_USDT, 2, True)} USDT con 5 USDT y pago de 0,85)", "F1", 10.5)
    p.linea(f"SÍ: {len(si)} · acertados {sum(a['res'] for a in si)} · neto {_num(neto_si, 2, True)} apuestas ({_num(neto_si * MONTO_USDT, 2, True)} USDT)", "F1", 10.5)
    p.espacio(6)
    p.linea("Cada fila abre en Binance la vela de 1 min de su entrada; en azul, los SÍ.", "F1", 9, gris)
    p.linea("Hora   Sentido  Aviso  Entrada        Salida         Resultado  Índice", "F3", 7.6, gris)
    for a in cerradas:
        e = enlaces(a, retraso, plazo)
        fila = (f"{_hora(a['t'], False):<6} {('SUBE' if a['dir'] == 1 else 'BAJA'):<8} {('SÍ' if a.get('si') else 'NO'):<6} "
                f"{_precio(a.get('entrada')):<14} {_precio(a.get('salida')):<14} {('acierto' if a['res'] else 'fallo'):<10} "
                f"{({1: 'acierto', 0: 'fallo'}).get(a.get('res_indice'), '–')}")
        p.linea(fila, "F3", 7.6, azul if a.get("si") else (0, 0, 0), e["entrada"], salto=11)
    p.espacio(10)
    p.linea("Papel: ninguna de estas apuestas movió dinero. Las del día antes del 04/11 pueden no traer el resultado con el índice.", "F1", 9, gris)
    p.linea(f"Generado por el centinela [{etiqueta}] el {_hora(dt.datetime.now(COL).timestamp())}.", "F1", 9, gris)
    return p.bytes(f"Resumen del papel {dia}")
