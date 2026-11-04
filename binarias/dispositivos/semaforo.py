"""Semáforo papel → real para BTCUSDT (03/11/2026). Corre en la caja T95H y en el teléfono, junto al centinela.

Idea de Nicolás (03/11): cuando el bot de papel va con mucho acierto, ese día se opera de verdad; si pierde, se detiene;
en real sin apalancamiento. Todo unificado en BTC/USDT.
Probado a ciegas en C7 (cuant/c7_semaforo.py, apuestas de 2021 a 2026, entrada 60 s tarde):
- Señal de papel: «ruptura al revés» en BTC. En cada decisión de 10 min, si la última vela de 5 min cierra por encima del
  máximo de las 20 anteriores, BAJA; si cierra por debajo del mínimo, SUBE. Binaria de 10 min, empate = fallo.
- Semáforo S2: al empezar el día de Colombia, VERDE si el acierto de las últimas 100 apuestas de papel es 58 % o más.
- Parada P1: en real, la primera pérdida apaga el modo real hasta el día siguiente.
- C7: con S2 y P1, 59,8 % en 3.292 apuestas (azar con los mismos días: 58,3 %; p = 0,003). Es una pista con 27
  comparaciones hechas: se confirma con días nuevos antes de pesar más.
Ningún código apuesta: en real, el aviso le dice a Nicolás qué tocar en la app (Binance prohíbe bots ahí). 5 USDT por
apuesta, sin apalancamiento (en binarias no existe). Avisos por Tor (avisos.enviar); el teléfono calla si la caja late.
Uso: python3 -I semaforo.py · Parar: crear PARAR.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import avisos  # noqa: E402

ESTADO = os.path.join(AQUI, "semaforo.json")
REGISTRO = os.path.join(AQUI, "semaforo.log")
PARAR = os.path.join(AQUI, "PARAR")
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m"
H = {"User-Agent": "binarias-semaforo"}
VENTANA, UMBRAL, PLAZO = 100, 0.58, 600
COL = dt.timezone(dt.timedelta(hours=-5))


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer():
    try:
        return json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        return {"apuestas": [], "real": {}}


def guardar(e):
    tmp = ESTADO + ".tmp"
    json.dump(e, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, ESTADO)


def velas(desde_ms=None, limite=1500):
    url = FAPI + f"&limit={limite}" + (f"&startTime={desde_ms}" if desde_ms else "")
    x = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20).read())
    ahora = time.time() * 1000
    return [(int(k[0]) // 1000, float(k[2]), float(k[3]), float(k[4])) for k in x if int(k[6]) < ahora]  # (t, alto, bajo, cierre)


def historial(dias):
    out, desde = [], int((time.time() - dias * 86400) * 1000)
    while True:
        x = velas(desde)
        if not x:
            break
        out += x
        desde = (x[-1][0] + 60) * 1000
        if len(x) < 1400:
            break
    vistos, limpio = set(), []
    for v in out:
        if v[0] not in vistos:
            vistos.add(v[0])
            limpio.append(v)
    return limpio


def senal(v1, t_dec):
    """Ruptura al revés en la decisión t_dec (fin de la vela de 1 min que cierra en múltiplo de 600 s)."""
    por5 = {}
    for t, hi, lo, c in v1:
        if t + 60 > t_dec:
            continue
        k = t // 300
        a = por5.setdefault(k, [0, -1e18, 1e18, 0.0, 0])
        a[1], a[2], a[3], a[4] = max(a[1], hi), min(a[2], lo), c, a[4] + 1
    llaves = sorted(k for k, a in por5.items() if a[4] == 5)
    if len(llaves) < 21 or (llaves[-1] + 1) * 300 != t_dec:
        return 0
    ult = por5[llaves[-1]]
    prev = [por5[k] for k in llaves[-21:-1]]
    if ult[3] > max(p[1] for p in prev):
        return -1
    if ult[3] < min(p[2] for p in prev):
        return 1
    return 0


def cierre_en(v1, t_fin):
    for t, hi, lo, c in v1:
        if t + 60 == t_fin:
            return c
    return None


def sembrar(e):
    """Con las velas de los últimos 9 días, rehace las apuestas de papel para que el semáforo tenga sus 100."""
    v1 = historial(9)
    hechas = {a["t"] for a in e["apuestas"]}
    nuevas = 0
    for i, (t, hi, lo, c) in enumerate(v1):
        t_dec = t + 60
        if t_dec % 600 or t_dec in hechas:
            continue
        s = senal(v1[max(0, i - 130):i + 1], t_dec)
        if not s:
            continue
        sal = cierre_en(v1, t_dec + PLAZO)
        if sal is None:
            continue
        res = 1 if (sal - c) * s > 0 else 0
        e["apuestas"].append({"t": t_dec, "dir": s, "entrada": c, "salida": sal, "res": res, "semilla": True})
        nuevas += 1
    e["apuestas"].sort(key=lambda a: a["t"])
    return nuevas


def acierto_reciente(e, antes_de):
    cerradas = [a for a in e["apuestas"] if a.get("res") is not None and a["t"] + PLAZO <= antes_de]
    ult = cerradas[-VENTANA:]
    return (sum(a["res"] for a in ult) / len(ult) if ult else 0.0), len(ult)


def avisar(texto):
    if avisos.ROL == "telefono" and avisos.caja_late():
        log("la caja late: ella avisa")
        return True
    return avisos.enviar(texto)


def main():
    e = leer()
    n = sembrar(e)
    guardar(e)
    log(f"semáforo en marcha · rol {avisos.ROL} · {len(e['apuestas'])} apuestas de papel ({n} sembradas)")
    while not os.path.exists(PARAR):
        try:
            ahora = time.time()
            hoy = dt.datetime.fromtimestamp(ahora, COL).strftime("%Y-%m-%d")
            ini_dia = dt.datetime.strptime(hoy, "%Y-%m-%d").replace(tzinfo=COL).timestamp()
            # 1) semáforo del día
            if e["real"].get("dia") != hoy:
                acc, n = acierto_reciente(e, ini_dia)
                verde = n >= VENTANA and acc >= UMBRAL
                e["real"] = {"dia": hoy, "encendido": verde, "acierto": acc, "n": n, "perdio": False}
                guardar(e)
                txt = (f"Semáforo BTC del {hoy} [{avisos.ETIQUETA}]: {'VERDE' if verde else 'ROJO'} · últimas {n} apuestas de papel: "
                       f"{acc * 100:.1f} % (umbral {UMBRAL * 100:.0f} %). "
                       + ("Hoy hay modo real: cada señal le llegará como «REAL»; la primera pérdida lo apaga hasta mañana. 5 USDT, sin apalancamiento."
                          if verde else "Hoy solo papel: no toque nada en la app."))
                avisar(txt)
                log(txt)
            # 2) decisiones cada 10 min (se espera 3 s tras el cierre de la vela)
            t_dec = int(ahora // 600 * 600)
            if ahora - t_dec >= 3 and not any(a["t"] == t_dec for a in e["apuestas"]) and e.get("ultima_revisada") != t_dec:
                v1 = velas(limite=160)
                e["ultima_revisada"] = t_dec
                s = senal(v1, t_dec) if v1 and v1[-1][0] + 60 == t_dec else 0
                if s:
                    entrada = v1[-1][3]
                    real = bool(e["real"].get("encendido") and not e["real"].get("perdio"))
                    e["apuestas"].append({"t": t_dec, "dir": s, "entrada": entrada, "salida": None, "res": None, "real": real})
                    if real:
                        avisar(f"REAL [semáforo BTC, {avisos.ETIQUETA}]: toque ahora BTC {'SUBE' if s == 1 else 'BAJA'} a 10 min "
                               f"(precio {entrada:,.1f}; vence {dt.datetime.fromtimestamp(t_dec + PLAZO, COL):%H:%M}). 5 USDT, sin apalancamiento.".replace(",", "."))
                    log(f"señal {('SUBE' if s == 1 else 'BAJA')} a las {dt.datetime.fromtimestamp(t_dec, COL):%H:%M} · real {real}")
                guardar(e)
            # 3) cierres
            abiertas = [a for a in e["apuestas"] if a.get("res") is None and a["t"] + PLAZO + 3 <= ahora]
            if abiertas:
                v1 = velas(limite=60)
                for a in abiertas:
                    sal = cierre_en(v1, a["t"] + PLAZO)
                    if sal is None:
                        if ahora - a["t"] > 3600:
                            a["res"] = 0
                            a["salida"] = None
                        continue
                    a["salida"], a["res"] = sal, 1 if (sal - a["entrada"]) * a["dir"] > 0 else 0
                    if a.get("real"):
                        msg = (f"Resultado REAL [semáforo BTC]: {'ACIERTO' if a['res'] else 'FALLO'} · BTC {'SUBE' if a['dir'] == 1 else 'BAJA'} "
                               f"{a['entrada']:,.1f} → {sal:,.1f}.").replace(",", ".")
                        if not a["res"] and e["real"].get("dia") == hoy:
                            e["real"]["perdio"] = True
                            msg += " Primera pérdida: modo real apagado hasta mañana; sigue solo papel."
                        avisar(msg)
                    log(f"cierre {dt.datetime.fromtimestamp(a['t'], COL):%H:%M}: {'acierto' if a['res'] else 'fallo'}")
                e["apuestas"] = e["apuestas"][-3000:]
                guardar(e)
        except Exception as ex:
            log(f"error: {type(ex).__name__}: {ex}")
            time.sleep(10)
        time.sleep(2)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
