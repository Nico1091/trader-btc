# binarias_placa.py · la ESP32-S3 dedicada a las binarias (11/11/2026). Solo papel: no compra, no conoce llaves.
#
# Cada minuto pide a Binance (directo, como la caja) las velas de 1 min de BTCUSDT ya cerradas. En cada cierre de 5 min
# calcula los 19 rasgos del laboratorio, con las mismas fórmulas, y las redes que el laboratorio eligió en «elige»
# (a 10 min la red de 19-16-8; a 15 min la neurona de t33 reajustada). Si la confianza llega a 0,56 abre una señal de
# papel: entrada con el cierre del minuto que abre en T (60 s tarde), salida a los 10 o 15 min, empate = fallo y una
# abierta por plazo. Todo queda en su memoria (binarias.json) y se sirve en la red de la casa:
#   GET /estado   -> cómo va (aciertos, últimas 25, señales abiertas, última vela, memoria)
#   GET /senales  -> las últimas 40 señales
#   POST /pesos   -> pesos nuevos de las redes (los manda la caja tras su reajuste diario)
#   POST /acortar -> respuesta vacía al instante: el bot de noticias usa su propio resumen (la placa ya no acorta)
# Arranca sola al encender (main.py), se reconecta al WiFi, el perro guardián la reinicia si se cuelga y retoma lo
# guardado. Los números son de precisión simple: las probabilidades pueden diferir de la caja en la sexta cifra.

import gc
import json
import math
import os
import socket
import ssl
import time
from array import array

import machine
import network

PUERTO = 8080
HOST = "fapi.binance.com"
CAP, GUARDA = 420, 340          # velas de 1 min que se guardan en memoria (los rasgos piden 320)
CONF = 0.56
PLAZOS = (10, 15)
ARCHIVO, PESOS = "binarias.json", "pesos.json"
WDT = None

# ---------------------------------------------------------------- estado
T = array("i")   # apertura (s, Unix)
O = array("f")
H = array("f")
L = array("f")
C = array("f")
V = array("f")
desfase = 0      # segundos que hay que sumarle a time.time() para tener la hora Unix de Binance
hora_ok = False  # 12/11/2026: sin la hora de Binance no se piden velas (tras un corte de corriente el reloj arranca en el año 2000)
inicio = time.time()
errores_red = 0
ultimo_error = ""
est = {"hecho": 0, "abiertas": [], "senales": [], "n": {"10": 0, "15": 0}, "k": {"10": 0, "15": 0},
       "ult": {"10": "", "15": ""}, "ultimo_t": {"10": 0, "15": 0},
       "perdida": {"n": 0, "k": 0, "ult": "", "abierta": None, "vista": 0, "ultimas": []}, "real": None}
MINUTOS = (3, 5, 7, 9, 11, 13, 14)   # las miradas de laboratorio\perdida.py (v2)
UMBRAL_PERDIDA = 1.0
modelos = {}


def ahora():
    return time.time() + desfase


def guardar():
    with open(ARCHIVO + ".tmp", "w") as f:
        json.dump(est, f)
    try:
        os.remove(ARCHIVO)
    except OSError:
        pass
    os.rename(ARCHIVO + ".tmp", ARCHIVO)


def cargar():
    global est
    try:
        with open(ARCHIVO) as f:
            d = json.load(f)
        for k in est:
            if k in d:
                est[k] = d[k]
    except (OSError, ValueError):
        pass


def cargar_pesos():
    global modelos
    with open(PESOS) as f:
        d = json.load(f)
    modelos = d
    gc.collect()


# ---------------------------------------------------------------- red: Binance por TLS, a mano para cuidar la memoria
def https_json(ruta, tope=30000):
    gc.collect()
    dire = socket.getaddrinfo(HOST, 443, 0, socket.SOCK_STREAM)[0][-1]
    s = socket.socket()
    s.settimeout(15)
    try:
        s.connect(dire)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(s, server_hostname=HOST)
        s.write(b"GET " + ruta.encode() + b" HTTP/1.0\r\nHost: " + HOST.encode() +
                b"\r\nUser-Agent: placa-binarias\r\nConnection: close\r\n\r\n")
        buf = bytearray()
        while True:
            trozo = s.read(1024)
            if not trozo:
                break
            buf.extend(trozo)
            if len(buf) > tope:
                raise OSError("respuesta demasiado grande")
    finally:
        s.close()
    i = buf.find(b"\r\n\r\n")
    linea = bytes(buf[:buf.find(b"\r\n")])
    if b" 200" not in linea:
        raise OSError("http " + linea.decode())
    cuerpo = bytes(buf[i + 4:])
    del buf
    gc.collect()
    return json.loads(cuerpo)


def sincronizar_hora():
    global desfase, hora_ok
    d = https_json("/fapi/v1/time")
    servidor = int(d["serverTime"]) // 1000
    if servidor < 1700000000:
        raise OSError("hora de Binance imposible: %d" % servidor)
    desfase = servidor - time.time()
    hora_ok = True


def poner(filas):
    """Agrega velas cerradas en orden; si hay un hueco, se descarta la memoria vieja (los rasgos piden velas seguidas)."""
    nuevas = 0
    limite = (ahora() - 60) * 1000
    for k in filas:
        if int(k[6]) >= (ahora() * 1000):
            continue
        t = int(k[0]) // 1000
        if len(T) and t <= T[-1]:
            continue
        if len(T) and t != T[-1] + 60:
            for a in (T, O, H, L, C, V):
                del a[:]
        T.append(t)
        O.append(float(k[1]))
        H.append(float(k[2]))
        L.append(float(k[3]))
        C.append(float(k[4]))
        V.append(float(k[5]))
        nuevas += 1
    if len(T) > CAP:
        corte = len(T) - GUARDA
        for a in (T, O, H, L, C, V):
            del a[:corte]
    return nuevas


def traer():
    """Velas que faltan: de a 60 si la memoria está vacía o atrasada; si no, las últimas 3."""
    if not hora_ok:
        raise OSError("sin la hora de Binance")
    if not len(T) or ahora() - T[-1] > 200:
        desde = (int(ahora()) // 60) * 60 - 60 * GUARDA if not len(T) else T[-1] + 60
        while desde < ahora() - 120:
            filas = https_json("/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=60&startTime=%d" % (desde * 1000))
            if not filas:
                break
            poner(filas)
            desde = int(filas[-1][0]) // 1000 + 60
            del filas
            gc.collect()
            if WDT:
                WDT.feed()
    filas = https_json("/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=3")
    poner(filas)


# ---------------------------------------------------------------- rasgos (las fórmulas de laboratorio\rasgos.py)
def rms(j, W):
    s = 0.0
    for i in range(j - W + 1, j + 1):
        r = math.log(C[i] / C[i - 1])
        s += r * r
    return math.sqrt(max(s / W, 1e-12))


def b5(j, m):
    """Vela de 5 min número m hacia atrás (0 = la que cierra en T): apertura, máximo, mínimo, cierre."""
    a, b = j - 5 * m - 4, j - 5 * m
    hi, lo = H[a], L[a]
    for i in range(a + 1, b + 1):
        if H[i] > hi:
            hi = H[i]
        if L[i] < lo:
            lo = L[i]
    return O[a], hi, lo, C[b]


def rsi_cutler(cierres):
    """cierres del más nuevo al más viejo (15 valores): RSI con medias simples de 14 subidas y bajadas."""
    g = p = 0.0
    for k in range(14):
        d = cierres[k] - cierres[k + 1]
        if d > 0:
            g += d
        else:
            p -= d
    g, p = g / 14, p / 14
    return 50.0 if g + p == 0 else 100 * g / (g + p)


def rasgos(j):
    s15, s60, s240 = rms(j, 15), rms(j, 60), rms(j, 240)
    x = []
    for m in (1, 5, 15, 60):
        x.append(math.log(C[j] / C[j - m]) / (s60 * math.sqrt(m)))
    x.append(math.log(s15 / s240))
    hi, lo = max(H[j - 239:j + 1]), min(L[j - 239:j + 1])
    x.append((C[j] - lo) / max(hi - lo, 1e-9) if hi > lo else 0.5)
    v15 = v240 = 0.0
    for i in range(j - 239, j + 1):
        v240 += V[i]
        if i > j - 15:
            v15 += V[i]
    x.append(math.log((v15 / 15 + 1e-9) / (v240 / 240 + 1e-9)))
    est3 = 0.0
    for k in (j, j - 5, j - 10):
        hh, ll = max(H[k - 69:k + 1]), min(L[k - 69:k + 1])
        est3 += (C[k] - ll) / (hh - ll) if hh > ll else 0.5
    x.append(est3 / 3)
    hora = ((T[j] + 60) % 86400) / 3600
    x.append(math.sin(2 * math.pi * hora / 24))
    x.append(math.cos(2 * math.pi * hora / 24))
    barras = [b5(j, m) for m in range(51)]
    esc = s60 * math.sqrt(60)
    l5 = math.log(barras[0][3])
    for N in (20, 50):
        mx = max(b[1] for b in barras[1:N + 1])
        mn = min(b[2] for b in barras[1:N + 1])
        x.append((l5 - math.log(mx)) / esc)
        x.append((l5 - math.log(mn)) / esc)
    c20 = [b[3] for b in barras[:20]]
    m = 0.0
    for v in c20:
        m += v
    m /= 20
    var = 0.0
    for v in c20:
        var += (v - m) ** 2
    sd = math.sqrt(var / 20)
    x.append((barras[0][3] - (m - 2 * sd)) / (4 * sd) if sd > 0 else 0.5)
    x.append(rsi_cutler([b[3] for b in barras[:15]]) / 100)
    jq = j - ((T[j] + 60) % 900) // 60
    x.append(rsi_cutler([C[jq - 15 * m] for m in range(15)]) / 100)
    o0, h0, l0, c0 = barras[0]
    x.append((c0 - o0) / (h0 - l0) if h0 > l0 else 0.0)
    s0 = (c0 > o0) - (c0 < o0)
    cuenta = 0
    if s0:
        for b in barras[:7]:
            if ((b[3] > b[0]) - (b[3] < b[0])) == s0:
                cuenta += 1
            else:
                break
    x.append(s0 * min(cuenta, 6) / 6)
    return x


def probabilidad(plazo, x):
    d = modelos[str(plazo)]
    if d["tipo"] == "neurona":
        z = d["w"][0]
        for i in range(10):
            z += d["w"][i + 1] * (x[i] - d["mu"][i]) / d["de"][i]
    else:
        h = [(x[i] - d["mu"][i]) / d["de"][i] for i in range(19)]
        for W, b in zip(d["W"][:-1], d["b"][:-1]):
            h = [math.tanh(max(-40.0, min(40.0, sum_fila(h, W, k) + b[k]))) for k in range(len(b))]
        W, b = d["W"][-1], d["b"][-1]
        z = sum_fila(h, W, 0) + b[0]
    z = max(-40.0, min(40.0, z))
    return 1 / (1 + math.exp(-z))


def sum_fila(h, W, k):
    s = 0.0
    for i in range(len(h)):
        s += h[i] * W[i][k]
    return s


# ---------------------------------------------------------------- señales de papel
def indice(t):
    """Posición de la vela que abre en t, o -1."""
    if not len(T) or t < T[0] or t > T[-1]:
        return -1
    i = (t - T[0]) // 60
    return i if T[i] == t else -1


def decidir():
    """Evalúa cada cierre de 5 min nuevo con al menos 320 velas seguidas detrás."""
    cambio = False
    for j in range(max(320, len(T) - 6), len(T)):
        Td = T[j] + 60
        if Td % 300 or Td <= est["hecho"]:
            continue
        est["hecho"] = Td
        if not modelos or T[j] - T[j - 320] != 320 * 60:
            continue
        x = rasgos(j)
        for p in PLAZOS:
            pr = probabilidad(p, x)
            k = str(p)
            if abs(pr - 0.5) >= CONF - 0.5 and Td >= est["ultimo_t"][k] + 60 + 60 * p:
                est["abiertas"].append({"t": Td, "p": p, "dir": 1 if pr > 0.5 else -1, "prob": round(pr, 5)})
                est["ultimo_t"][k] = Td
                cambio = True
        if WDT:
            WDT.feed()
    return cambio


def cerrar():
    cambio = False
    quedan = []
    for s in est["abiertas"]:
        e, f = indice(s["t"]), indice(s["t"] + 60 * s["p"])
        if e >= 0 and f >= 0:
            s["entrada"], s["salida"] = C[e], C[f]
            s["res"] = 1 if (C[f] - C[e]) * s["dir"] > 0 else 0
            k = str(s["p"])
            est["n"][k] += 1
            est["k"][k] += s["res"]
            est["ult"][k] = (est["ult"][k] + str(s["res"]))[-25:]
            est["senales"] = (est["senales"] + [s])[-40:]
            cambio = True
        elif ahora() - s["t"] > 7200:
            s["res"] = -1  # hueco: se perdieron las velas; no cuenta
            est["senales"] = (est["senales"] + [s])[-40:]
            cambio = True
        else:
            quedan.append(s)
    est["abiertas"] = quedan
    return cambio


# ---------------------------------------------------------------- comprar sobre la pérdida (laboratorio\perdida.py)
def cubo(z):
    a = abs(z)
    for lo, hi, nombre in ((0.5, 1.0, "0.5-1"), (1.0, 1.5, "1-1.5"), (1.5, 2.0, "1.5-2"), (2.0, 3.0, "2-3"), (3.0, 1e9, "3+")):
        if lo <= a < hi:
            return nombre
    return None


def perdida():
    """En cada ventana de 15 min, la primera mirada (minutos 3 a 14) con |z| ≥ 1 es una compra de papel del lado perdedor;
    al cerrar el minuto 15 se anota si ganó. Revisa todas las velas nuevas en orden, para no saltarse minutos."""
    pe = est["perdida"]
    cambio = False
    for j in range(max(61, len(T) - 6), len(T)):
        t = T[j]
        if t <= pe["vista"]:
            continue
        pe["vista"] = t
        ws = t - t % 900
        m = (t - ws) // 60 + 1
        iw = indice(ws)
        if iw < 0:
            continue
        ab = pe["abierta"]
        if ab and ab["ventana"] < ws:
            # quedó de una ventana que la placa no vio cerrar (estuvo apagada o sin red): no cuenta
            pe["abierta"] = ab = None
            cambio = True
        if m == 15 and ab and ab["ventana"] == ws:
            ab["res"] = 1 if (C[j] - O[iw]) * ab["lado"] > 0 else 0
            pe["n"] += 1
            pe["k"] += ab["res"]
            pe["ult"] = (pe["ult"] + str(ab["res"]))[-25:]
            pe["ultimas"] = (pe["ultimas"] + [ab])[-20:]
            pe["abierta"] = None
            cambio = True
        elif m in MINUTOS and (not ab or ab["ventana"] != ws) and j >= 61:
            z = math.log(C[j] / O[iw]) / (rms(j, 60) * math.sqrt(15 - m))
            if abs(z) >= UMBRAL_PERDIDA:
                q = None
                try:
                    q = modelos.get("perdida", {}).get("precio", {}).get(str(m), {}).get(cubo(z))
                except AttributeError:
                    pass
                pe["abierta"] = {"ventana": ws, "m": m, "z": round(z, 3), "lado": -1 if z > 0 else 1, "precio_max": q}
                cambio = True
    return cambio


def rasgos_final(s, m, ref, t_j):
    """Los mismos rasgos de laboratorio\\perdida_red.py: la red que propone comprar el lado perdedor al final."""
    j = s + m - 1
    if j < 61 or ref <= 0:
        return None
    r = [math.log(C[i] / C[i - 1]) for i in range(j - 59, j + 1)]
    sig = math.sqrt(max(sum(v * v for v in r) / 60, 1e-12))
    sig5 = math.sqrt(max(sum(v * v for v in r[-5:]) / 5, 1e-12))
    mov = math.log(C[j] / ref)
    if mov == 0:
        return None
    z = mov / (sig * math.sqrt(15 - m))
    lado = -1 if z > 0 else 1
    a = min(abs(z), 8.0)
    hi, lo = max(H[s:j + 1]), min(L[s:j + 1])
    cruces = 0
    for i in range(s, j):
        if (C[i] - ref) * (C[i + 1] - ref) < 0:
            cruces += 1
    v3 = (V[j] + V[j - 1] + V[j - 2]) / 3
    v60 = sum(V[j - 59:j + 1]) / 60
    hora = ((t_j + 60) % 86400) / 3600
    x = [a, a * a, (15 - m) / 5, sig5 / sig, (r[-1] * lado) / sig, math.log(C[j] / C[j - 3]) * lado / (sig * math.sqrt(3)),
         (hi - lo) / (ref * sig * math.sqrt(m)), cruces / 3, math.log((v3 + 1e-9) / (v60 + 1e-9)),
         math.sin(2 * math.pi * hora / 24), math.cos(2 * math.pi * hora / 24), math.log(a + 0.05)]
    return x, lado


def proponer():
    """En los minutos 10 a 14 de la ventana: probabilidad de que gane el perdedor y precio máximo con ganancia esperada."""
    d = modelos.get("perdida_red")
    if not d or len(T) < 70:
        return
    j = len(T) - 1
    t = T[j]
    ws = t - t % 900
    m = (t - ws) // 60 + 1
    iw = indice(ws)
    if m < 10 or m > 14 or iw < 0:
        return
    r = rasgos_final(iw, m, O[iw], t)
    if r is None:
        return
    x, lado = r
    z = d["w"][0]
    for i in range(len(x)):
        z += d["w"][i + 1] * (x[i] - d["mu"][i]) / d["de"][i]
    z = max(-40.0, min(40.0, z))
    p = 1 / (1 + math.exp(-z))
    est["propuesta"] = {"ventana": ws, "m": m, "lado": lado, "p": round(p, 5), "precio_max": round(0.98 * p, 4)}


# ---------------------------------------------------------------- servidor de la red de la casa
def responder(cli, codigo, datos):
    cuerpo = json.dumps(datos).encode()
    cli.send(("HTTP/1.0 %d OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
              % (codigo, len(cuerpo))).encode())
    for i in range(0, len(cuerpo), 1024):
        cli.send(cuerpo[i:i + 1024])


def resumen():
    gc.collect()
    r = {"ok": True, "dedicada": "binarias", "acortadas": 0, "encendida_s": time.time() - inicio,
         "memoria_libre": gc.mem_free(), "ultima_vela": (T[-1] + 60) if len(T) else 0, "velas": len(T),
         "reloj": hora_ok, "hora": int(ahora()) if hora_ok else 0,
         "errores_red": errores_red, "ultimo_error": ultimo_error, "pesos": modelos.get("t"),
         "modelos": {k: modelos[k]["tipo"] for k in ("10", "15") if k in modelos}, "abiertas": est["abiertas"],
         "binarias": {}}
    for k in ("10", "15"):
        r["binarias"][k] = {"n": est["n"][k], "k": est["k"][k], "ultimas": est["ult"][k]}
    pe = est["perdida"]
    r["perdida"] = {"n": pe["n"], "k": pe["k"], "ultimas": pe["ult"], "abierta": pe["abierta"]}
    r["real"] = est.get("real")
    r["propuesta"] = est.get("propuesta")
    return r


def atender(cli):
    cli.settimeout(10)
    buf = b""
    while b"\r\n\r\n" not in buf:
        trozo = cli.recv(1024)
        if not trozo:
            return
        buf += trozo
        if len(buf) > 8192:
            return
    cab, _, cuerpo = buf.partition(b"\r\n\r\n")
    partes = cab.split(b"\r\n")[0].split(b" ")
    metodo, ruta = partes[0], partes[1] if len(partes) > 1 else b"/"
    largo = 0
    for l in cab.split(b"\r\n")[1:]:
        if l.lower().startswith(b"content-length:"):
            largo = int(l.split(b":")[1])
    if largo > 60000:
        responder(cli, 413, {"error": "demasiado grande"})
        return
    while len(cuerpo) < largo:
        trozo = cli.recv(2048)
        if not trozo:
            break
        cuerpo += trozo
    if ruta == b"/estado":
        responder(cli, 200, resumen())
    elif ruta == b"/senales":
        responder(cli, 200, {"senales": est["senales"], "abiertas": est["abiertas"]})
    elif ruta == b"/pesos" and metodo == b"POST":
        d = json.loads(cuerpo)
        if not all(k in d for k in ("10", "15")):
            responder(cli, 400, {"error": "faltan los modelos de 10 y 15 min"})
            return
        with open(PESOS + ".tmp", "w") as f:
            json.dump(d, f)
        try:
            os.remove(PESOS)
        except OSError:
            pass
        os.rename(PESOS + ".tmp", PESOS)
        cargar_pesos()
        responder(cli, 200, {"ok": True, "pesos": modelos.get("t")})
    elif ruta == b"/real" and metodo == b"POST":
        # el PC (la Mesa, con la llave que no sale de él) manda el papel con el precio real del libro de Predict.fun
        est["real"] = json.loads(cuerpo)
        guardar()
        responder(cli, 200, {"ok": True})
    elif ruta == b"/real":
        responder(cli, 200, est.get("real") or {})
    elif ruta == b"/acortar" and metodo == b"POST":
        try:
            notas = json.loads(cuerpo).get("notas", [])
        except ValueError:
            notas = []
        responder(cli, 200, {"notas": [{"id": n.get("id"), "corto": "", "frases": 0, "ms": 0} for n in notas]})
    else:
        responder(cli, 404, {"error": "no existe"})


_wlan = network.WLAN(network.STA_IF)
_sin_red_desde = None
_ultima_revision = 0


def revisar_wifi():
    """Si se cae el WiFi, reconecta; si en dos minutos no vuelve, reinicia y boot.py conecta de cero."""
    global _sin_red_desde, _ultima_revision
    if time.time() - _ultima_revision < 20:
        return
    _ultima_revision = time.time()
    if _wlan.isconnected():
        _sin_red_desde = None
        return
    if _sin_red_desde is None:
        _sin_red_desde = time.time()
    try:
        _wlan.active(True)
        _wlan.connect()
    except Exception as e:
        print("reconexión falló:", e)
    if time.time() - _sin_red_desde > 120:
        machine.reset()


def correr():
    global WDT, errores_red, ultimo_error
    WDT = machine.WDT(timeout=120000)
    cargar()
    try:
        cargar_pesos()
    except (OSError, ValueError) as e:
        print("sin pesos:", e)
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PUERTO))
    s.listen(2)
    s.settimeout(1)
    print("binarias de la placa en el puerto", PUERTO)
    # 12/11/2026: la hora de Binance se pide en la primera vuelta y después cada hora. Antes se pedía cuando time.time()
    # pasaba de 3.600, y tras un corte de corriente el reloj de la placa arranca en cero (año 2000): pasaba una hora sin
    # hora, descartando todas las velas por «no cerradas» y sin contar ningún error. «pausa» va con el reloj de la placa y
    # «proximo» con la hora de Binance.
    proximo, hora_sync, pausa = 0, None, 0
    while True:
        WDT.feed()
        revisar_wifi()
        try:
            if time.time() >= pausa and _wlan.isconnected():
                if hora_sync is None or time.time() - hora_sync > 3600:
                    try:
                        sincronizar_hora()
                        hora_sync = time.time()
                    except Exception as e:
                        if hora_sync is None:
                            raise                       # sin hora no se piden velas: se reintenta en 15 s
                        hora_sync = time.time() - 3300  # con la hora anterior se sigue; se reintenta en 5 min
                        errores_red += 1
                        ultimo_error = "hora: %s: %s" % (type(e).__name__, e)
                if ahora() >= proximo:
                    traer()
                    cambio = decidir()
                    cambio = cerrar() or cambio
                    cambio = perdida() or cambio
                    proponer()
                    if cambio:
                        guardar()
                    proximo = (int(ahora()) // 60 + 1) * 60 + 4
        except Exception as e:
            errores_red += 1
            ultimo_error = "%s: %s" % (type(e).__name__, e)
            pausa = time.time() + 15
            gc.collect()
        WDT.feed()
        try:
            cli, _ = s.accept()
        except OSError:
            continue
        try:
            atender(cli)
        except Exception as e:
            try:
                responder(cli, 500, {"error": str(e)})
            except Exception:
                pass
        finally:
            cli.close()
            gc.collect()
