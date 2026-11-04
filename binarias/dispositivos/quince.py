"""Vigía de 15 min en la caja y el teléfono (04/11/2026). Hilo del avisador, sin IA, arranca solo con el equipo.

Pedido suyo: que todo se haga solo, que las líneas salgan cuando el mercado reaccione, que le lleguen a Telegram y que le
avise con voz cuando el mercado se aproxime «por porcentaje de aciertos».
- Papel de los mercados de 15 min (P19): cada cierre de múltiplo de 15 min aplica la misma señal de semaforo.senal y mide con
  velas. Es el mismo conteo de la Mesa del PC, que además anota los precios reales del libro.
- Porcentaje de aciertos: últimas 25 cerradas. 68 % o más: «se está aproximando». 75 % o más: «ya llegó». Si baja del 75 %: «no opere».
  Cada aviso va con nota de voz; Telegram no deja que un bot haga llamadas.
- Señal con 75 % o más: foto con franja verde o roja. Por debajo no se manda nada: esa señal queda solo en el papel.
- Reacción: una vela cerrada rompe o rechaza el techo o el piso azules. Foto con las cinco líneas, una cada 30 min como máximo.
El teléfono calla mientras la caja late (semaforo.avisar). Este programa no apuesta ni toca Binance con su cuenta.
"""
import datetime as dt
import json
import os
import time

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
COL = S.COL


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
    elif nivel == 1 and previo == 0:
        voz("aproximando", f"SE ESTÁ APROXIMANDO · aciertos en {p} % (últimas {VENTANA}); pide {UMBRAL} %.")
    elif previo == 2:
        voz("bajo", f"BAJÓ · aciertos en {p} %. No se están dando los resultados: no opere.")
    log(f"nivel {previo} → {nivel} con {p} %")


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
    e = leer()
    try:
        n = sembrar(e)
        guardar(e)
        log(f"vigía de 15 min en marcha · rol {avisos.ROL} · {len(e['ops'])} operaciones ({n} sembradas) · aciertos {porcentaje(e)[0]} %")
    except Exception as ex:
        log(f"sin sembrar ({type(ex).__name__}: {ex})")
    while not os.path.exists(PARAR):
        try:
            ahora = time.time()
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
