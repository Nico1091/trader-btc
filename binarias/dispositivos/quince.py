"""Vigía de 15 min en la caja y el teléfono (04/11/2026). Hilo del avisador, sin IA, arranca solo con el equipo.

Pedido suyo: que todo se haga solo, que las líneas salgan cuando el mercado reaccione, que le lleguen a Telegram y que le
avise con voz cuando el mercado se aproxime «por porcentaje de aciertos».
- Papel de los mercados de 15 min (P19): cada cierre de múltiplo de 15 min aplica la misma señal de semaforo.senal y mide con
  velas. Es el mismo conteo de la Mesa del PC, que además anota los precios reales del libro.
- Porcentaje de aciertos: últimas 25 cerradas. 68 % o más: «se está aproximando». 75 % o más: «ya llegó». Si baja del 75 %: «no opere».
  Cada aviso va con nota de voz; Telegram no deja que un bot haga llamadas.
- Señal con 75 % o más: foto con franja verde o roja. Por debajo no se manda nada: esa señal queda solo en el papel.
- Reacción: una vela cerrada rompe o rechaza el techo o el piso azules. Foto con las cinco líneas, una cada 30 min como máximo.
- Llamada: en el teléfono, al llegar al 75 % y en cada señal con 75 % o más le timbra por el canal de alarma, a cualquier hora (llamada.py).
- Latido: cada hora dice que sigue vivo, y si el equipo estuvo detenido lo cuenta con sus horas (los silencios sin señal no son caídas).
- En el teléfono, http://127.0.0.1:8796 muestra el porcentaje, las operaciones y las líneas, sin claves y solo para mirar.
El teléfono calla mientras la caja late (semaforo.avisar). Este programa no apuesta ni toca Binance con su cuenta.
"""
import datetime as dt
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import avisos
import graficas
import semaforo as S

AQUI = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(AQUI, "quince.json")
REGISTRO = os.path.join(AQUI, "quince.log")
AUDIO = os.path.join(AQUI, "audio")
FOTO = os.path.join(AQUI, "quince_ultima.png")
PARAR = S.PARAR
PLAZO, VENTANA, UMBRAL, CERCA = 900, 25, 75, 68
ESPERA_LINEAS = 1800
HUECO_S = 300
PUERTO_PAGINA = 8796
FOTO_PAGINA = os.path.join(AQUI, "quince_pagina.png")
COL = S.COL
ACTUAL = {"ops": []}


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"ops": []}


def guardar(e):
    e["ops"] = e["ops"][-400:]
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False)
    os.replace(tmp, ESTADO)


def porcentaje(e):
    """(porcentaje de aciertos, cerradas) de las últimas 25. Igual que reglas.resumen en la Mesa."""
    u = [o for o in e["ops"] if o.get("res") is not None][-VENTANA:]
    return (round(100 * len([o for o in u if o["res"] == 1]) / len(u)) if u else 0), len(u)


def resultado(base, salida, d):
    m = (salida - base) * d
    return 1 if m > 0 else (0.5 if m == 0 else 0)


def sembrar(e):
    """Rehace con velas lo que el equipo no vio (recién encendido o sin red)."""
    v = S.historial(9)
    cierre = {x[0] + 60: x[3] for x in v}
    hechas, ahora, n = {o["t"] for o in e["ops"]}, time.time(), 0
    for i, x in enumerate(v):
        t = x[0] + 60
        if t % PLAZO or t in hechas or t + PLAZO + 5 > ahora:
            continue
        s = S.senal(v[max(0, i - 130):i + 1], t)
        a, b = cierre.get(t), cierre.get(t + PLAZO)
        if s and a is not None and b is not None:
            e["ops"].append({"t": t, "dir": s, "base": a, "res": resultado(a, b, s), "semilla": True})
            n += 1
    e["ops"].sort(key=lambda o: o["t"])
    return n


def voz(nombre, texto):
    ruta = os.path.join(AUDIO, nombre + ".mp3")
    if not (os.path.exists(ruta) and S.avisar_archivo(ruta, texto, "sendVoice", "voice")):
        S.avisar(texto)


def alertas(e):
    p, n = porcentaje(e)
    if n < VENTANA:
        return
    nivel = 2 if p >= UMBRAL else (1 if p >= CERCA else 0)
    previo = e.get("nivel")
    e["nivel"] = nivel
    if previo is None or previo == nivel:
        return  # al encender no avisa: solo avisa cuando cambia
    if nivel == 2:
        voz("listo", f"YA LLEGÓ · aciertos en {p} % (últimas {VENTANA}). Mire la Mesa y espere la señal.")
        timbrar(f"Las operaciones están acertando: {p} %.", "listo")
    elif nivel == 1 and previo == 0:
        voz("aproximando", f"SE ESTÁ APROXIMANDO · aciertos en {p} % (últimas {VENTANA}); pide {UMBRAL} %.")
    elif previo == 2:
        voz("bajo", f"BAJÓ · aciertos en {p} %. No se están dando los resultados: no opere.")
    log(f"nivel {previo} → {nivel} con {p} %")


def timbrar(texto, audio):
    """Solo el teléfono llama, y en un hilo aparte: la llamada dura minutos y el vigía no se detiene."""
    if avisos.ROL != "telefono":
        return

    def correr():
        try:
            import llamada
            log("llamada: " + llamada.llamar(texto, os.path.join(AUDIO, audio + ".mp3")))
        except Exception as ex:
            log(f"llamada sin hacer ({type(ex).__name__}: {ex})")
    threading.Thread(target=correr, daemon=True).start()


def hora(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%d/%m %H:%M")


class Pagina(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/foto"):
            try:
                with open(FOTO_PAGINA, "rb") as f:
                    c, tipo = f.read(), "image/png"
            except OSError:
                c, tipo = b"", "text/plain"
        else:
            e = ACTUAL
            p, n = porcentaje(e)
            filas = []
            for o in e["ops"][-30:][::-1]:
                r = "abierta" if o.get("res") is None else ("acierto" if o["res"] == 1 else ("empate" if o["res"] == 0.5 else "fallo"))
                filas.append(f"<tr><td>{hora(o['t'])}</td><td>{'▲ Sube' if o['dir'] == 1 else '▼ Baja'}</td><td>{r}</td></tr>")
            ahora = dt.datetime.now(COL).strftime("%H:%M:%S")
            html = (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><meta http-equiv=refresh content=20>"
                    f"<title>Binarias BTC</title><style>body{{background:#0e1117;color:#e7eaf0;font:15px system-ui;margin:0;padding:12px}}h1{{font-size:18px;margin:0}}"
                    f"b{{font-size:34px}}img{{width:100%;border-radius:8px}}td{{padding:4px 10px 4px 0}}a{{color:#6aa0ff}}</style>"
                    f"<h1>Binarias BTC · 15 min · borrador</h1><p>Aciertos, últimas {n}: <b>{p} %</b> (pide {UMBRAL} %)<br>Hora {ahora} · el programa corre solo</p>"
                    f"<img src='/foto?{int(time.time()) // 60}'><p>El teléfono no compra: los botones están en la Mesa del PC.</p><table>{''.join(filas)}</table>")
            c, tipo = html.encode("utf-8"), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(c)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(c)


def foto(v, s5, franja, fondo, pie):
    with open(FOTO, "wb") as f:
        f.write(graficas.grafica_con_franja(v, s5, franja, fondo))
    return S.avisar_archivo(FOTO, pie, "sendPhoto", "photo")


def lineas():
    v = [x for x in S.velas_ohlc(170)][-150:]
    return v, graficas.cinco_lineas(v)


def reaccion(v, s5):
    """(franja, color, pie) si la última vela rompió o rechazó el techo o el piso azules; si no, None."""
    n, (_, _o, h, lo, c) = len(v), v[-1]
    techo, piso = s5["techo"].en(n - 1), s5["piso"].en(n - 1)
    if c > techo:
        return f"RUPTURA DEL TECHO {techo:.0f}", 1, f"El precio {avisos.precio(c)} cerró encima de su techo."
    if h >= techo:
        return f"RECHAZO EN EL TECHO {techo:.0f}", 3, f"La vela tocó su techo y cerró abajo, en {avisos.precio(c)}."
    if c < piso:
        return f"RUPTURA DEL PISO {piso:.0f}", 1, f"El precio {avisos.precio(c)} cerró debajo de su piso."
    if lo <= piso:
        return f"RECHAZO EN EL PISO {piso:.0f}", 2, f"La vela tocó su piso y cerró arriba, en {avisos.precio(c)}."
    return None


def decidir(e, t):
    v1 = S.velas(limite=160)
    if not v1 or v1[-1][0] + 60 != t:
        return
    s = S.senal(v1, t)
    if not s:
        return
    e["ops"].append({"t": t, "dir": s, "base": v1[-1][3], "res": None})
    p, n = porcentaje(e)
    log(f"señal {S.sentido(s)} a las {dt.datetime.fromtimestamp(t, COL):%H:%M} con {p} % de aciertos")
    if n >= VENTANA and p >= UMBRAL:
        v, s5 = lineas()
        accion = "COMPRE" if s == 1 else "VENDA"
        pie = f"{accion} · BTC {S.sentido(s)} a 15 min · aciertos en {p} %. Toque en la Mesa antes de 75 s, si el botón se enciende."
        timbrar(f"{accion}: BTC {S.sentido(s)} a 15 minutos.", "listo")
        if not (s5 and foto(v, s5, f"{accion} · {S.sentido(s)} · 15 MIN · {p} %", 2 if s == 1 else 3, pie)):
            S.avisar(pie)


def cerrar(e, ahora):
    abiertas = [o for o in e["ops"] if o.get("res") is None and o["t"] + PLAZO + 4 <= ahora]
    if not abiertas:
        return
    v1 = S.velas(limite=60)
    for o in abiertas:
        b = S.cierre_en(v1, o["t"] + PLAZO)
        if b is not None:
            o["res"] = resultado(o["base"], b, o["dir"])
        elif ahora - o["t"] > 3000:
            e["ops"].remove(o)  # hueco de datos: no se inventa el resultado
    guardar(e)


def main():
    global ACTUAL
    e = leer()
    ACTUAL = e
    if avisos.ROL == "telefono":
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", PUERTO_PAGINA), Pagina)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        except OSError as ex:
            log(f"página sin servir ({ex})")
    try:
        n = sembrar(e)
        guardar(e)
        log(f"vigía de 15 min en marcha · rol {avisos.ROL} · {len(e['ops'])} operaciones ({n} sembradas) · aciertos {porcentaje(e)[0]} %")
    except Exception as ex:
        log(f"sin sembrar ({type(ex).__name__}: {ex})")
    while not os.path.exists(PARAR):
        try:
            ahora = time.time()
            visto = e.get("vivo", ahora)
            if ahora - visto > HUECO_S:  # el equipo o este programa estuvieron detenidos
                msj = f"Vigía [{avisos.ETIQUETA}]: estuve detenido de {hora(visto)} a {hora(ahora)} ({(ahora - visto) / 60:.0f} min). Ya sigo."
                log(msj)
                S.avisar(msj)
            e["vivo"] = ahora
            if ahora - e.get("t_latido", 0) >= 3600:
                e["t_latido"] = ahora
                p, n = porcentaje(e)
                S.avisar(f"Vigía vivo [{avisos.ETIQUETA}] · aciertos {p} % en las últimas {n} · {hora(ahora)}. Sin señal no hay más mensajes: no es que esté caído.")
                guardar(e)
            t = int(ahora // PLAZO * PLAZO)
            if ahora - t >= 4 and e.get("rev") != t:
                e["rev"] = t
                decidir(e, t)
                guardar(e)
            cerrar(e, ahora)
            alertas(e)
            minuto = int(ahora // 60)
            if ahora % 60 >= 5 and e.get("min") != minuto:
                e["min"] = minuto
                guardar(e)
                if avisos.ROL == "telefono" and minuto % 5 == 0:
                    v, s5 = lineas()
                    if s5:
                        with open(FOTO_PAGINA, "wb") as f:
                            f.write(graficas.grafica(v, s5))
                if ahora - e.get("t_linea", 0) >= ESPERA_LINEAS:
                    v, s5 = lineas()
                    r = reaccion(v, s5) if s5 else None
                    if r:
                        e["t_linea"] = ahora
                        foto(v, s5, r[0], r[1], r[2] + " Sus cinco líneas en 1 min: " + graficas.lectura(v, s5) + ".")
                        guardar(e)
                        log(r[0])
        except Exception as ex:
            log(f"error: {type(ex).__name__}: {ex}")
            time.sleep(10)
        time.sleep(3)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
