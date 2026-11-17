# -*- coding: utf-8 -*-
"""Nodo puente de las binarias (17/11/2026). Solo biblioteca estándar y sin IA propia.

Pedidos del dueño del 17/11/2026:
- 09:45: «un nodo puente en el cual se manda todo»; que una los puntos de los programas que ya existen (Centro de estrategias,
  vigía de 15 min y operador de Fable 5.2), que los mande rápido, y que si solo un equipo está conectado se envíe lo de ese.
- 10:00: «el nodo central debe ser el teléfono»; «el teléfono no debe necesitar de nadie: que haga todo solo y suba todo directo
  a la gente de arriba, que lo apruebe o no». La caja también puede hacer de central, pero solo de respaldo.
- Rutina constructora (12:42): Claude Opus 5.5 decide COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR sobre cada punto alto; el
  operador de Fable 5.2 solo compra de verdad con una decisión COMPRAR vigente de este nodo (operador/aprobacion.py).

Qué hace, sin tocar a los demás programas (solo LEE sus archivos, y solo lo nuevo):
- Cada 10 s mira las fuentes de su equipo: datos/centro.json (E1 a E5 del Centro) y quince.json (vigía de 15 min) se leen
  solo si cambiaron; del registro del operador (un archivo por día) se leen solo las líneas nuevas. De cada estrategia
  calcula las últimas 25 cerradas, la racha y el fondo (empate = fallo, como en el resto de las binarias).
- Un PUNTO es una señal nueva (abierta) de una estrategia, ya puesta en su mercado de Binance: el de 15 min que la contiene
  para el Centro y el vigía; el de 5 o 15 min de la compra de papel para el operador. Es ALTO si esa estrategia lleva UMBRAL o
  más de sus últimas 25. Los puntos del mismo mercado, ventana y sentido se juntan en un grupo.
- Antes de subir un grupo espera 20 s a que lleguen los demás y, si el operador corre en el equipo, hasta 90 s a que mire ese
  mercado: así Claude ve el vector de ganancia del operador (probabilidad, precio real y ganancia esperada de cada lado)
  aunque el punto venga solo del Centro. También ve los puntos en contra de la misma ventana.
- El TELÉFONO es el nodo central: junta sus puntos con los que le lleguen de la caja y sube los grupos con algún punto alto.
  La CAJA es respaldo: entrega sus puntos al teléfono; si el teléfono no late (cada 30 s) o no los recibe, sube lo suyo.
- Subir: a Claude en la nube (si existe ~/.config/binarias/claude, línea 1 = clave de la API; Opus 5.5 con el contexto fijo
  CONTEXTO-NODO.md en caché de 1 h y salida en JSON forzada) y a Telegram por Tor (la clave y el camino de avisos.py).
  Queda en puntos.jsonl y decisiones.jsonl (mercado W, ventana, sentido, decisión, motivo, tokens, costo y segundos); la
  decisión se copia también al otro equipo. Falla cerrado: sin clave, sin respuesta, error, respuesta ilegible o cortada,
  negativa o el sentido contrario al punto = no hay compra. El nodo NO compra: compra el operador con sus frenos.

Uso:  python3 -I nodo.py            (bucle; lo lanza arrancar_nodo.sh con su vigía)
      python3 -I nodo.py --una      (una vuelta y sale; para probar)
Parar: crear el archivo PARAR en esta carpeta.
"""

import hashlib
import hmac
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(HOME, ".config", "binarias")
TELEGRAM = os.path.join(CONF_DIR, "telegram")      # línea 1: clave del bot, línea 2: chat (la misma de avisos.py)
SECRETO = os.path.join(CONF_DIR, "nodo")           # secreto compartido caja-teléfono (firma de lo que se pasan)
CLAUDE = os.path.join(CONF_DIR, "claude")          # línea 1: clave de la API de Claude (la pone el dueño)
TOR = "127.0.0.1:9050"
PUERTO = 8799
CAJA_IP = "192.168.20.45"
TELEFONO_IP = "192.168.20.158"   # solo el primer valor: la caja aprende la IP real del latido del teléfono
UMBRAL = 19            # de las últimas 25 (76 %): «si los porcentajes de los aciertos son altos»
VENTANA = 25
ESPERA_JUNTAR = 20     # segundos que el central espera a que lleguen los demás puntos del mismo mercado y sentido
ESPERA_OPERADOR = 90   # segundos que un grupo espera la mirada del operador de su mercado (el vector de ganancia)
VUELTA = 10            # segundos entre lecturas
LATIDO = 30            # cada cuánto el teléfono le avisa a la caja que está vivo
SIN_LATIDO = 90        # sin latido en este tiempo, la caja hace de central
CADUCIDAD_S = 600      # lo mismo que operador/aprobacion.py: una aprobación vale 10 min y nunca más allá de su ventana
# Claude (API de mensajes, revisada con la documentación oficial el 17/11/2026)
MODELO = "claude-opus-5-5"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
ESFUERZO = "low"       # Opus 5.5 piensa siempre (no se puede apagar); el esfuerzo bajo basta para esta decisión y gasta poco
MAX_TOKENS = 2048      # tope de pensamiento + respuesta; si se alcanza, la respuesta queda cortada y no se compra
CACHE_TTL = "1h"       # el contexto fijo queda en caché una hora: con consultas cada pocos minutos se paga casi solo la lectura
PRECIOS = {"entrada": 4.0, "cache_5m": 5.0, "cache_1h": 8.0, "cache_leida": 0.20, "salida": 20.0}  # USD por millón (Opus 5.5)
# «--noproxy ""» obliga a usar Tor aunque el equipo tenga una lista de excepciones de proxy (no_proxy)
RUTAS_CLAUDE = (("directa", ["--noproxy", "*"]), ("tor", ["--noproxy", "", "--socks5-hostname", "{usuario}@" + TOR]))
SIN_LLEGAR = (5, 6, 7, 35, 97)   # curl no llegó a conectar (DNS, conexión, TLS o proxy): se prueba la ruta siguiente
REINTENTAR = (429, 500, 502, 503, 529)
DECISIONES = ("COMPRAR SUBE", "COMPRAR BAJA", "NO COMPRAR")
COMPRAR = {1: "COMPRAR SUBE", -1: "COMPRAR BAJA"}
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["decision", "motivo"],
           "properties": {"decision": {"type": "string", "enum": list(DECISIONES)}, "motivo": {"type": "string"}}}
NOMBRES = {"E1": "E1 · ruptura de 20 velas al revés", "E2": "E2 · ruptura de 50 velas al revés",
           "E3": "E3 · Gemini 1 al revés", "E4": "E4 · Gemini 3 al revés", "E5": "E5 · rechazo en techo o piso",
           "quince": "vigía de 15 min", "operador": "operador de Fable 5.2",
           "operador15": "operador de Fable 5.2 (15 min)", "operador5": "operador de Fable 5.2 (5 min)"}
COL = -5 * 3600


def ruta(n):
    return os.path.join(AQUI, n)


def log(texto):
    linea = f"{hora(time.time())} {texto}"
    try:
        n = ruta("nodo.log")
        if os.path.exists(n) and os.path.getsize(n) > 2_000_000:
            os.replace(n, n + ".1")
        with open(n, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:
        pass
    if "--una" in sys.argv:
        print(linea)


def hora(t):
    return time.strftime("%d/%m %H:%M:%S", time.gmtime(t + COL))


def hhmm(t):
    return time.strftime("%H:%M", time.gmtime(t + COL))


def leer_json(n, defecto):
    try:
        with open(n, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def escribir_json(n, datos):
    tmp = n + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(tmp, n)


def anexar(n, fila):
    with open(n, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def config():
    """Rol (telefono o caja), carpetas, red y Claude; todo se puede fijar en config.json del nodo."""
    c = leer_json(ruta("config.json"), {})
    rol = c.get("rol")
    cent = c.get("centinela")
    if not cent:
        for d in (os.path.join(HOME, "centinela"), "/data/local/tmp/centinela"):
            if os.path.isdir(d):
                cent = d
                break
    if not rol:
        rol = (open(os.path.join(cent, "rol"), encoding="utf-8").read().strip() if cent and os.path.exists(
            os.path.join(cent, "rol")) else "telefono")
    oper = c.get("operador") or next((d for d in (os.path.join(HOME, "operador"), "/data/local/tmp/operador")
                                      if os.path.isdir(d)), os.path.join(HOME, "operador"))
    rutas = [r for r in RUTAS_CLAUDE if r[0] in (c.get("rutas_claude") or [x[0] for x in RUTAS_CLAUDE])]
    return {"rol": rol, "centinela": cent or AQUI, "operador": oper, "umbral": int(c.get("umbral", UMBRAL)),
            "preferido": c.get("preferido", "telefono"),
            "par_ip": c.get("par_ip") or (CAJA_IP if rol == "telefono" else TELEFONO_IP),
            "puerto": int(c.get("puerto", PUERTO)), "par_puerto": int(c.get("par_puerto", PUERTO)),
            "carpeta": c.get("carpeta", AQUI), "rutas_claude": rutas or list(RUTAS_CLAUDE),
            "esfuerzo": c.get("esfuerzo", ESFUERZO) if c.get("esfuerzo") in ("low", "medium", "high", "xhigh", "max") else ESFUERZO}


def en(c, n):
    return os.path.join(c["carpeta"], n)


# ---------------------------------------------------------------- fuentes (solo lectura, solo lo nuevo)
def resumen(ops):
    """Últimas 25 cerradas, racha de aciertos al final, fondo, lo vivo (sin las rehechas con velas) y la señal abierta más nueva.
    Cerrada es res 0, 1 o 0,5 (empate del vigía); solo res 1 es acierto: el empate cuenta como fallo."""
    cerradas = [o for o in ops if o.get("res") in (0, 1, 0.5)]
    ult = cerradas[-VENTANA:]
    aciertos = 0
    for o in ult:            # en bucle, no sum(): igual en 3.11 y 3.14
        if o["res"] == 1:
            aciertos += 1
    racha = 0
    for o in reversed(cerradas):
        if o["res"] == 1:
            racha += 1
        else:
            break
    total = vivas = vivas_k = 0
    for o in cerradas:
        if o["res"] == 1:
            total += 1
        if not o.get("semilla"):
            vivas += 1
            if o["res"] == 1:
                vivas_k += 1
    abiertas = [o for o in ops if o.get("res") is None]
    return {"aciertos": aciertos, "de": len(ult), "racha": racha,
            "fondo": round(100 * total / len(cerradas), 1) if cerradas else None,
            "vivo": [vivas_k, vivas], "abierta": abiertas[-1] if abiertas else None}


def mercado_de(fuente, op, W=None):
    """(W, ventana, minuto, alineado): el mercado «BTC Up or Down» al que apunta una señal. El Centro y el vigía miden 15 min
    desde su vela: van al mercado de 15 min que contiene la señal (alineado si la señal cae justo en su apertura). El
    operador ya trae su mercado (W) y su ventana."""
    t = int(op.get("t") or 0)
    if fuente == "operador":
        return int(W or op.get("W") or 15), t, int(op.get("m") or 0), True
    v = t - t % 900
    return 15, v, (t - v) // 60, t % 900 == 0


class Cola:
    """Las líneas nuevas del registro del operador (un archivo AAAAMMDD.jsonl por día), sin releer lo ya leído.
    Solo se descifran las filas que sirven (llenado, resultado y las miradas de la última media hora)."""
    UTILES = (b'"tipo": "llenado"', b'"tipo": "resultado"')
    MIRADA = b'"tipo": "mirada"'
    T_RE = re.compile(rb'"t": (\d+)')

    def __init__(self, carpeta, dias=3):
        self.carpeta, self.dias, self.pos, self.leidos = carpeta, dias, {}, 0

    def nuevas(self, ahora=None):
        ahora = ahora or time.time()
        try:
            nombres = sorted(n for n in os.listdir(self.carpeta) if n.endswith(".jsonl"))[-self.dias:]
        except OSError:
            return []
        out = []
        for n in nombres:
            r = os.path.join(self.carpeta, n)
            try:
                tam = os.path.getsize(r)
            except OSError:
                continue
            p = self.pos.get(n, 0)
            if tam < p:          # el archivo se rehizo más corto: se lee de nuevo
                p = 0
            if tam == p:
                continue
            with open(r, "rb") as f:
                f.seek(p)
                datos = f.read(tam - p)
            corte = datos.rfind(b"\n")
            if corte < 0:        # una línea a medio escribir: se espera a la próxima vuelta
                continue
            self.pos[n] = p + corte + 1
            self.leidos += corte + 1
            for linea in datos[:corte].split(b"\n"):
                if any(u in linea for u in self.UTILES):
                    pass
                elif self.MIRADA in linea:
                    m = self.T_RE.search(linea)
                    if not m or int(m.group(1)) < ahora - 1800:
                        continue
                else:
                    continue
                try:
                    out.append(json.loads(linea))
                except ValueError:
                    pass
        for n in list(self.pos):
            if n not in nombres:
                del self.pos[n]
        return out


class Fuentes:
    """Lo que hay en este equipo: el Centro, el vigía y el operador. Guarda lo leído y solo vuelve a leer lo que cambió."""

    def __init__(self, c):
        self.c = c
        self.cache = {}           # ruta -> (mtime, tamaño, datos)
        self.cola = Cola(os.path.join(c["operador"], "registro"))
        self.llenados = {}        # (W, t, lado) -> {"t", "dir", "base", "m"}: compras de papel del operador (libro A, 5 s)
        self.ganadores = {}       # (W, t) -> ganador oficial
        self.miradas = {}         # (W, t) -> la última mirada del operador en esa ventana
        self.leidos = 0           # bytes leídos en la última vuelta
        self.t_operador = 0.0     # última fila útil del operador

    def _resumenes(self, n, fuente):
        """Los resúmenes de un archivo del Centro o del vigía; solo se rehacen si el archivo cambió."""
        try:
            st = os.stat(n)
        except OSError:
            self.cache.pop(n, None)
            return []
        marca = (st.st_mtime, st.st_size)
        hay = self.cache.get(n)
        if hay and hay[0] == marca:
            return hay[1]
        datos = leer_json(n, None)
        self.leidos += st.st_size
        out = []
        if fuente == "centro" and isinstance(datos, dict):
            for e, ops in sorted((datos.get("ops") or {}).items()):
                if isinstance(ops, list):
                    out.append(("centro", e, 15, resumen(ops)))
        elif fuente == "quince" and isinstance(datos, dict) and isinstance(datos.get("ops"), list):
            out.append(("quince", "quince", 15, resumen(datos["ops"])))
        self.cache[n] = (marca, out)
        return out

    def _registro(self, ahora):
        antes = self.cola.leidos
        for r in self.cola.nuevas(ahora):
            tipo, W, t = r.get("tipo"), r.get("W"), r.get("t")
            if W not in (5, 15) or not isinstance(t, (int, float)):
                continue
            t = int(t)
            if isinstance(r.get("hora"), (int, float)):
                self.t_operador = max(self.t_operador, float(r["hora"]))
            if tipo == "llenado":
                # compra de papel con precio real y llenado honesto (libro A, 5 s); las escapadas y la sombra no cuentan
                if r.get("compra") and not r.get("sombra") and r.get("llenado") == 5 and r.get("lado") in (1, -1):
                    self.llenados.setdefault((W, t, r["lado"]), {"t": t, "dir": r["lado"], "base": r.get("q"), "m": r.get("m")})
            elif tipo == "resultado":
                if r.get("serie", "papel") == "papel" and r.get("ganador") in (1, -1, 0):
                    self.ganadores[(W, t)] = r["ganador"]
            elif tipo == "mirada":
                self.miradas[(W, t)] = r
        self.leidos += self.cola.leidos - antes
        for d, n in ((self.llenados, 600), (self.ganadores, 600), (self.miradas, 8)):
            if len(d) > n:
                for k in sorted(d, key=lambda k: k[1])[:len(d) - n]:
                    del d[k]

    def operador_vivo(self, ahora=None):
        """El operador anotó algo útil en los últimos 5 minutos (si no, no se espera su vector)."""
        return (ahora or time.time()) - self.t_operador < 300

    def vector(self, W, t):
        return self.miradas.get((W, t))

    def leer(self, ahora=None):
        """Lista de (fuente, estrategia, W, resumen) con lo que haya en este equipo."""
        ahora = ahora or time.time()
        self.leidos = 0
        out = list(self._resumenes(os.path.join(self.c["centinela"], "datos", "centro.json"), "centro"))
        out += self._resumenes(os.path.join(self.c["centinela"], "quince.json"), "quince")
        if os.path.isdir(os.path.join(self.c["operador"], "registro")):
            self._registro(ahora)
            for W in (15, 5):
                ops = []
                for (w, t, lado), o in sorted(self.llenados.items(), key=lambda kv: kv[1]["t"]):
                    if w != W:
                        continue
                    g = self.ganadores.get((w, t))
                    ops.append(dict(o, res=None if g is None else (1 if g == lado else 0)))
                if ops:
                    out.append(("operador", f"operador{W}", W, resumen(ops)))
        return out


def leer_fuentes(c):
    """Compatibilidad: una lectura completa (para probar a mano)."""
    return [(f, e, r) for f, e, _W, r in Fuentes(c).leer()]


def puntos_nuevos(c, estado, fuentes):
    """Señales abiertas nuevas de cada estrategia, ya puestas en su mercado. Marca vistas para no repetir."""
    vistos = set(estado.get("vistos", []))
    nuevos = []
    primera = not estado.get("iniciado")
    for fuente, est, W, r in fuentes.leer():
        o = r["abierta"]
        if not o:
            continue
        clave = f"{c['rol']}|{fuente}|{est}|{o.get('t')}|{o.get('dir')}"
        if clave in vistos:
            continue
        vistos.add(clave)
        estado["_cambio"] = True
        if primera:
            continue                     # al arrancar no se reenvía lo que ya estaba abierto
        Wm, ventana, minuto, alineado = mercado_de(fuente, o, W)
        p = {"clave": clave, "equipo": c["rol"], "fuente": fuente, "estrategia": est, "nombre": NOMBRES.get(est, est),
             "t": o.get("t"), "dir": o.get("dir"), "base": o.get("base"), "W": Wm, "ventana": ventana, "minuto": minuto,
             "alineado": alineado, "aciertos": r["aciertos"], "de": r["de"], "racha": r["racha"], "fondo": r["fondo"],
             "vivo": r["vivo"], "alto": r["de"] >= VENTANA and r["aciertos"] >= c["umbral"], "visto": int(time.time())}
        if fuente == "centro":
            p["si_regla"], p["oi_no_sube"] = o.get("si"), (None if o.get("doi") is None else o["doi"] <= 0.00022)
        nuevos.append(p)
    if primera or estado.get("_cambio"):
        estado["vistos"] = sorted(vistos)[-3000:]
    estado["iniciado"] = True
    return nuevos


# ---------------------------------------------------------------- firma y red entre equipos
def secreto():
    try:
        return open(SECRETO, encoding="utf-8").read().strip().encode()
    except OSError:
        return b""


def firmar(cuerpo):
    return hmac.new(secreto(), cuerpo, hashlib.sha256).hexdigest()


def enviar_par(c, ip, camino, datos):
    """POST firmado al otro equipo. True solo si respondió 200."""
    if not ip:
        return False
    cuerpo = json.dumps(datos, ensure_ascii=False).encode()
    pet = (f"POST {camino} HTTP/1.0\r\nHost: {ip}\r\nContent-Type: application/json\r\n"
           f"X-Firma: {firmar(cuerpo)}\r\nContent-Length: {len(cuerpo)}\r\n\r\n").encode() + cuerpo
    try:
        with socket.create_connection((ip, c["par_puerto"]), timeout=4) as s:
            s.sendall(pet)
            resp = s.recv(200)
        return resp.split(b" ")[1:2] == [b"200"]
    except OSError:
        return False


# ---------------------------------------------------------------- subir: Telegram y Claude
def comillas(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


def telegram(texto):
    try:
        lineas = open(TELEGRAM, encoding="utf-8").read().split()
        token, chat = lineas[0], lineas[1]
    except Exception:
        log("falta ~/.config/binarias/telegram: no se puede avisar")
        return False
    conf = "\n".join(["url = " + comillas(f"https://api.telegram.org/bot{token}/sendMessage"),
                      "form-string = " + comillas(f"chat_id={chat}"),
                      "form-string = " + comillas(f"text={texto[:4000]}")]) + "\n"
    usuario = f"nodo{int(time.time()) % 100000}:x"
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "60", "--socks5-hostname", f"{usuario}@{TOR}", "-K", "-"],
                           input=conf, capture_output=True, text=True, timeout=90)
        ok = '"ok":true' in (r.stdout or "")
        if not ok:
            log(f"Telegram sin confirmar (curl {r.returncode})")
        return ok
    except Exception as e:
        log(f"Telegram falló ({type(e).__name__})")
        return False


def costo(uso):
    """Dólares de una consulta según su uso (precios de Opus 5.5 por millón de tokens)."""
    uso = uso or {}
    cc = uso.get("cache_creation") or {}
    w1, w5 = cc.get("ephemeral_1h_input_tokens"), cc.get("ephemeral_5m_input_tokens")
    if w1 is None and w5 is None:
        w = uso.get("cache_creation_input_tokens") or 0
        w1, w5 = (w, 0) if CACHE_TTL == "1h" else (0, w)
    x = ((uso.get("input_tokens") or 0) * PRECIOS["entrada"] + (w1 or 0) * PRECIOS["cache_1h"] + (w5 or 0) * PRECIOS["cache_5m"]
         + (uso.get("cache_read_input_tokens") or 0) * PRECIOS["cache_leida"] + (uso.get("output_tokens") or 0) * PRECIOS["salida"])
    return round(x / 1e6, 6)


def interpretar(texto):
    """Primera línea exacta; cualquier otra cosa cuenta como NO COMPRAR (falla cerrado)."""
    lineas = [x.strip() for x in (texto or "").splitlines() if x.strip()]
    if not lineas:
        return None, "respuesta vacía de Claude: NO COMPRAR"
    primera = lineas[0].upper().replace("Í", "I").replace("*", "").strip("«»\"'`. ")
    motivo = lineas[1] if len(lineas) > 1 else ""
    if primera in DECISIONES:
        return primera, motivo
    return "NO COMPRAR", "respuesta ilegible de Claude (cuenta como NO COMPRAR)"


def leer_decision(texto):
    """La respuesta llega en JSON por el esquema; si no, se lee como dos líneas. Lo que no se entienda es NO COMPRAR."""
    try:
        d = json.loads(texto)
    except ValueError:
        return interpretar(texto)
    if isinstance(d, dict) and d.get("decision") in DECISIONES:
        return d["decision"], str(d.get("motivo") or "")[:300]
    return "NO COMPRAR", "respuesta ilegible de Claude (cuenta como NO COMPRAR)"


ERRORES = {401: "autenticacion", 403: "permiso", 402: "facturacion", 404: "modelo", 400: "peticion", 413: "peticion",
           429: "limite", 500: "servidor", 502: "servidor", 503: "servidor", 529: "servidor"}


def _curl(conf, archivo, extra, plazo):
    usuario = f"claude{int(time.time()) % 100000}:x"
    args = ["curl", "-s", "--max-time", str(plazo), "-w", "\n%{http_code}", "-K", "-", "--data-binary", "@" + archivo]
    args += [a.replace("{usuario}", usuario) for a in extra]
    r = subprocess.run(args, input=conf, capture_output=True, text=True, timeout=plazo + 30)
    cuerpo, _sep, codigo = (r.stdout or "").rpartition("\n")
    return r.returncode, int(codigo) if codigo.strip().isdigit() else 0, cuerpo


def decision_claude(paquete, c=None, plazo=90):
    """Claude Opus 5.5 decide sobre un punto. Devuelve un dict: decision (COMPRAR SUBE, COMPRAR BAJA, NO COMPRAR o None si
    no hubo decisión), motivo, uso, costo_usd, segundos, ruta y error. Todo lo que no sea una decisión legible deja None o
    NO COMPRAR: nunca una compra."""
    c = c or {}
    out = {"decision": None, "motivo": "", "uso": None, "costo_usd": 0.0, "segundos": 0.0, "ruta": None, "error": None}
    try:
        clave = open(CLAUDE, encoding="utf-8").read().split()[0]
    except Exception:
        out.update(motivo="pendiente (falta la clave de Claude en el equipo)", error="sin_clave")
        return out
    try:
        contexto = open(ruta("CONTEXTO-NODO.md"), encoding="utf-8").read()
    except OSError:
        contexto = ("Binarias BTC Up or Down de Binance. Solo devolución. Decida COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR; "
                    "ante la duda, NO COMPRAR.")
    pedido = ("Punto de los programas (JSON):\n" + json.dumps(paquete, ensure_ascii=False, separators=(",", ":")) +
              "\nDecida con el contexto. «decision»: COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR; «motivo»: una línea en español.")
    cuerpo = {"model": MODELO, "max_tokens": MAX_TOKENS,
              "system": [{"type": "text", "text": contexto, "cache_control": {"type": "ephemeral", "ttl": CACHE_TTL}}],
              "messages": [{"role": "user", "content": pedido}],
              "output_config": {"effort": c.get("esfuerzo", ESFUERZO), "format": {"type": "json_schema", "schema": ESQUEMA}}}
    archivo = ruta("peticion_claude.json")
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(cuerpo, f, ensure_ascii=False)
    conf = "\n".join(["url = " + comillas(c.get("api_url", API_URL)), "header = " + comillas("x-api-key: " + clave),
                      "header = " + comillas("anthropic-version: " + API_VERSION),
                      'header = "content-type: application/json"']) + "\n"
    t0 = time.time()
    try:
        rc = codigo = 0
        texto = ""
        for nombre, extra in c.get("rutas_claude") or RUTAS_CLAUDE:
            out["ruta"] = nombre
            rc, codigo, texto = _curl(conf, archivo, extra, plazo)
            if rc == 0 and codigo in REINTENTAR:            # Claude ocupado: una sola vez más por la misma ruta
                time.sleep(5)
                rc, codigo, texto = _curl(conf, archivo, extra, plazo)
            if rc not in SIN_LLEGAR:
                break
        out["segundos"] = round(time.time() - t0, 2)
        if rc != 0:
            out.update(error="red", motivo=f"sin respuesta de Claude (curl {rc}): NO COMPRAR")
            return out
        try:
            resp = json.loads(texto)
        except ValueError:
            out.update(error="ilegible", motivo=f"respuesta ilegible de Claude (HTTP {codigo}): NO COMPRAR")
            return out
        if codigo != 200 or not isinstance(resp, dict) or resp.get("type") == "error":
            err = (resp.get("error") or {}) if isinstance(resp, dict) else {}
            out.update(error=ERRORES.get(codigo, "http"),
                       motivo=f"Claude respondió error {codigo} ({err.get('type', '?')}: {str(err.get('message', ''))[:120]}): NO COMPRAR")
            return out
        out["uso"] = {k: resp.get("usage", {}).get(k) for k in ("input_tokens", "cache_creation_input_tokens",
                                                                 "cache_read_input_tokens", "output_tokens")}
        out["costo_usd"] = costo(resp.get("usage"))
        parada = resp.get("stop_reason")
        if parada == "refusal":
            cat = (resp.get("stop_details") or {}).get("category")
            out.update(decision="NO COMPRAR", motivo=f"Claude declinó responder ({cat or 'sin categoría'}): NO COMPRAR")
            return out
        if parada == "max_tokens":
            out.update(decision="NO COMPRAR", motivo="la respuesta de Claude quedó cortada (max_tokens): NO COMPRAR")
            return out
        texto = "".join(b.get("text", "") for b in resp.get("content", []) if isinstance(b, dict) and b.get("type") == "text")
        out["decision"], out["motivo"] = leer_decision(texto.strip())
        return out
    except Exception as e:
        out.update(error="excepcion", motivo=f"sin respuesta de Claude ({type(e).__name__}): NO COMPRAR",
                   segundos=round(time.time() - t0, 2))
        return out
    finally:
        try:
            os.remove(archivo)
        except OSError:
            pass


def flecha(d):
    return "▲ SUBE" if d == 1 else "▼ BAJA"


def pct(x):
    return "—" if x is None else f"{round(100 * x)} %"


def precio(x):
    return "—" if x is None else f"{x:.2f}".replace(".", ",")


def vector_corto(v):
    """El vector de ganancia del operador, en pocos números, para Claude."""
    if not v:
        return None
    lados = {}
    for k, nombre in (("1", "SUBE"), ("-1", "BAJA")):
        d = (v.get("lados") or {}).get(k) or {}
        lados[nombre] = {c: (round(d[c], 3) if isinstance(d.get(c), float) else d.get(c)) for c in ("papel", "p", "p_prud", "q", "G_prud", "limite")}
    return {"minuto": v.get("m"), "serie": v.get("serie"), "resta_s": v.get("resta_s"), "z": v.get("z"),
            "decide": {1: "SUBE", -1: "BAJA"}.get(v.get("decide")), "motivo": v.get("motivo"), "lados": lados}


def paquete(clave, puntos, en_contra, vector):
    """Lo que Claude recibe de un grupo: el mercado, los puntos, los que van en contra y el vector del operador."""
    W, ventana, d = clave
    campos = ("fuente", "estrategia", "nombre", "equipo", "alto", "aciertos", "de", "racha", "fondo", "vivo", "minuto",
              "alineado", "si_regla", "oi_no_sube")

    def corto(p):
        x = {k: p.get(k) for k in campos if p.get(k) is not None}
        x["senal"] = hhmm(p["t"]) if p.get("t") else None
        return x
    return {"mercado": f"BTC Up or Down de {W} min", "W": W, "ventana": f"{hhmm(ventana)} a {hhmm(ventana + 60 * W)}",
            "sentido": "SUBE" if d == 1 else "BAJA", "puntos": [corto(p) for p in puntos],
            "en_contra": [corto(p) for p in en_contra], "operador": vector_corto(vector)}


def mensaje(clave, grupo, r, quien, en_contra=(), vector=None, hoy=None):
    W, ventana, d = clave
    altos = [p for p in grupo if p["alto"]]
    lineas = [f"[Nodo] PUNTO {'ALTO' if altos else 'bajo'} · BTC · {flecha(d)} · mercado de {W} min de las {hhmm(ventana)} "
              f"a las {hhmm(ventana + 60 * W)}",
              f"Coinciden {len(grupo)} · equipos: {', '.join(sorted({p['equipo'] for p in grupo}))}"]
    for p in grupo:
        pc = round(100 * p["aciertos"] / p["de"]) if p["de"] else 0
        extra = f", fondo {str(p['fondo']).replace('.', ',')} %" if p.get("fondo") is not None else ""
        lineas.append(f"- {p['nombre']} ({p['equipo']}): {p['aciertos']} de {p['de']} ({pc} %), racha {p['racha']}{extra} · "
                      f"señal {hhmm(p['t']) if p.get('t') else '?'}" + ("" if p.get("alineado", True) else " (a mitad de ventana)"))
    if en_contra:
        lineas.append("En contra en la misma ventana: " + ", ".join(f"{p['nombre']} {flecha(p['dir'])}" for p in en_contra))
    v = vector_corto(vector)
    if v:
        s, b = v["lados"]["SUBE"], v["lados"]["BAJA"]
        lineas.append(f"Operador, minuto {v['minuto']} ({'sin libro' if v['serie'] == 'sin_llave' else 'con libro'}): "
                      f"SUBE {pct(s['p_prud'])} prudente a {precio(s['q'])} · BAJA {pct(b['p_prud'])} prudente a {precio(b['q'])}")
    dec = r.get("decision")
    lineas.append(f"Decisión de Claude: {dec or r.get('motivo')}" + (f" · {r['motivo']}" if dec and r.get("motivo") else ""))
    if r.get("uso"):
        lineas.append(f"Consulta: {r['segundos']:.0f} s, {r['costo_usd'] * 100:.2f} centavos de dólar".replace(".", ",")
                      + (f" (hoy {hoy[0]} consultas, {hoy[1]:.2f} USD)".replace(".", ",") if hoy else ""))
    lineas.append(f"Sube: {quien}. El nodo no compra: compra el operador si está ARMADO, si su ganancia esperada llega al "
                  f"margen y si esta decisión sigue vigente ({CADUCIDAD_S // 60} min).")
    return "\n".join(lineas)


# ---------------------------------------------------------------- el central (el teléfono; la caja solo de respaldo)
class Central:
    def __init__(self, c, estado, vector_de=None, operador_vivo=None):
        self.c = c
        self.lock = threading.Lock()
        self.grupos = {}          # (W, ventana, dir) -> {"desde": t, "puntos": [...], "pendiente": bool, "envios": n}
        self.par = estado.setdefault("par", {"ip": c["par_ip"], "visto": 0})
        self.estado = estado
        self.vector_de = vector_de or (lambda W, t: None)
        self.operador_vivo = operador_vivo or (lambda: False)
        if c["rol"] == c["preferido"]:
            self.par["ip"] = c["par_ip"]

    def principal(self):
        return self.c["rol"] == self.c["preferido"]

    def activo(self):
        """El teléfono siempre sube; la caja solo si el teléfono no late."""
        return self.principal() or time.time() - self.par.get("visto", 0) > SIN_LATIDO

    def latido_de(self, ip):
        self.par["ip"] = ip
        self.par["visto"] = time.time()

    def recibir(self, p):
        with self.lock:
            if not all(k in p for k in ("W", "ventana")):   # un punto de un nodo viejo: se pone en su mercado aquí
                W, v, mnt, al = mercado_de(p.get("fuente"), p, p.get("W"))
                p = dict(p, W=W, ventana=v, minuto=mnt, alineado=al)
            k = (int(p["W"]), int(p["ventana"]), p["dir"])
            g = self.grupos.setdefault(k, {"desde": time.time(), "puntos": [], "pendiente": True, "envios": 0})
            if all(x["clave"] != p["clave"] for x in g["puntos"]):
                g["puntos"].append(p)
                anexar(en(self.c, "puntos.jsonl"), p)
                if g["envios"] and p.get("alto") and not g["pendiente"]:   # información nueva tras subir: se vuelve a subir
                    g.update(pendiente=True, desde=time.time())

    def _listo(self, k, g, ahora):
        if ahora - g["desde"] < ESPERA_JUNTAR:
            return False
        if ahora - g["desde"] >= ESPERA_OPERADOR or not self.operador_vivo():
            return True
        v = self.vector_de(k[0], k[1])
        minuto = max([p.get("minuto") or 0 for p in g["puntos"]] + [1])
        return bool(v) and (v.get("m") or 0) >= minuto

    def _hoy(self, costo_usd):
        dia = time.strftime("%Y%m%d", time.gmtime(time.time() + COL))
        h = self.estado.get("claude_hoy")
        if not h or h.get("dia") != dia:
            h = {"dia": dia, "consultas": 0, "usd": 0.0}
        h["consultas"] += 1
        h["usd"] = round(h["usd"] + costo_usd, 6)
        self.estado["claude_hoy"] = h
        self.estado["_cambio"] = True
        return h["consultas"], h["usd"]

    def despachar(self):
        ahora = time.time()
        with self.lock:
            listos = [(k, g) for k, g in self.grupos.items() if g["pendiente"] and self._listo(k, g, ahora)]
            for k, g in listos:
                g["pendiente"] = False
                g["envios"] += 1
            for k in [k for k, g in self.grupos.items() if ahora - g["desde"] > 3600 and not g["pendiente"]]:
                del self.grupos[k]
            contra = {k: [p for (W, v, d), g in self.grupos.items() if (W, v) == k[:2] and d != k[2] for p in g["puntos"]]
                      for k, _g in listos}
        quien = "el teléfono (nodo central)" if self.principal() else "la caja (respaldo: el teléfono no respondió)"
        for k, g in listos:
            grupo = list(g["puntos"])
            if not any(p["alto"] for p in grupo):
                continue                       # solo se sube lo de aciertos altos
            vector = self.vector_de(k[0], k[1])
            r = decision_claude(paquete(k, grupo, contra[k], vector), self.c)
            dec = r.get("decision")
            if dec in COMPRAR.values() and dec != COMPRAR[k[2]]:
                r["motivo"] = f"Claude propuso {dec[8:]} sobre un punto de {'SUBE' if k[2] == 1 else 'BAJA'}: no se compra ({r.get('motivo')})"
                dec = r["decision"] = "NO COMPRAR"
            hoy = self._hoy(r.get("costo_usd") or 0.0) if r.get("uso") else None
            fila = {"t": int(ahora), "W": k[0], "ventana": k[1], "dir": k[2], "decision": dec, "detalle": r.get("motivo"),
                    "sube": self.c["rol"], "fuentes": [p["clave"] for p in grupo], "altos": [p["estrategia"] for p in grupo if p["alto"]],
                    "en_contra": [p["clave"] for p in contra[k]], "modelo": MODELO, "uso": r.get("uso"),
                    "costo_usd": r.get("costo_usd"), "segundos": r.get("segundos"), "ruta": r.get("ruta"), "error": r.get("error"),
                    "vence": int(min(ahora + CADUCIDAD_S, k[1] + 60 * k[0]))}
            anexar(en(self.c, "decisiones.jsonl"), fila)
            enviar_par(self.c, self.par.get("ip"), "/decision", fila)   # copia al otro equipo, si está
            telegram(mensaje(k, grupo, r, quien, contra[k], vector, hoy))
            self._alerta(r)
            log(f"subido grupo {k}: {len(grupo)} punto(s), decisión {dec or r.get('motivo')}"
                + (f", {r['segundos']} s, {r['costo_usd']} USD" if r.get("uso") else ""))

    def _alerta(self, r):
        """Una falla de Claude que pide al dueño (clave, saldo o modelo) se le avisa aparte, como mucho cada 6 h."""
        err = r.get("error")
        if err not in ("autenticacion", "permiso", "facturacion", "modelo"):
            return
        a = self.estado.setdefault("alertas", {})
        if time.time() - a.get(err, 0) < 6 * 3600:
            return
        a[err] = int(time.time())
        self.estado["_cambio"] = True
        telegram(f"[Nodo] Claude no está decidiendo: {r.get('motivo')}. Mientras tanto no se compra nada. "
                 "Revise la clave de la API de Claude del teléfono y el saldo de la cuenta.")


def servidor(central):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def responder(self, codigo, cuerpo=b""):
            self.send_response(codigo)
            self.end_headers()
            if cuerpo:
                self.wfile.write(cuerpo)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            cuerpo = self.rfile.read(min(n, 200000))
            if not secreto() or not hmac.compare_digest(self.headers.get("X-Firma", ""), firmar(cuerpo)):
                return self.responder(403)
            try:
                datos = json.loads(cuerpo)
                if self.path == "/puntos":
                    for p in datos:
                        central.recibir(p)
                elif self.path == "/latido":
                    central.latido_de(self.client_address[0])
                elif self.path == "/decision":
                    anexar(en(central.c, "decisiones.jsonl"), dict(datos, copia_de=self.client_address[0]))
                else:
                    return self.responder(404)
            except (ValueError, KeyError, TypeError):
                return self.responder(400)
            self.responder(200, b"ok")

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"nodo": central.c["rol"], "central": central.activo(),
                                         "hora": hora(time.time())}).encode())

    srv = ThreadingHTTPServer(("0.0.0.0", central.c["puerto"]), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def vuelta(c, estado, central, fuentes):
    nuevos = puntos_nuevos(c, estado, fuentes)
    if estado.pop("_cambio", False):
        escribir_json(en(c, "estado.json"), estado)
    if not nuevos:
        return 0
    if not central.activo():                 # caja con el teléfono vivo: se los entrega al teléfono
        if enviar_par(c, central.par.get("ip"), "/puntos", nuevos):
            for p in nuevos:
                anexar(en(c, "puntos.jsonl"), dict(p, entregado="telefono"))
            log(f"{len(nuevos)} punto(s) entregados al teléfono")
            return len(nuevos)
        log("el teléfono no los recibió: la caja hace de central con lo suyo")
        central.par["visto"] = 0
    for p in nuevos:
        central.recibir(p)
    return len(nuevos)


def main():
    c = config()
    estado = leer_json(en(c, "estado.json"), {})
    fuentes = Fuentes(c)
    central = Central(c, estado, fuentes.vector, fuentes.operador_vivo)
    if "--una" not in sys.argv:
        servidor(central)
    log(f"nodo arrancó: rol {c['rol']} ({'central' if central.principal() else 'respaldo'}), "
        f"centinela {c['centinela']}, operador {c['operador']}, umbral {c['umbral']} de {VENTANA}, Claude {MODELO} "
        f"(esfuerzo {c['esfuerzo']}, rutas {', '.join(r[0] for r in c['rutas_claude'])})")
    ultimo_latido, latia = 0.0, None
    medida = {"n": 0, "ms": 0.0, "max_ms": 0.0, "bytes": 0, "max_bytes": 0, "desde": time.time()}
    while not os.path.exists(ruta("PARAR")):
        try:
            t1 = time.perf_counter()
            vuelta(c, estado, central, fuentes)
            ms = (time.perf_counter() - t1) * 1000
            medida.update(n=medida["n"] + 1, ms=medida["ms"] + ms, max_ms=max(medida["max_ms"], ms),
                          bytes=medida["bytes"] + fuentes.leidos, max_bytes=max(medida["max_bytes"], fuentes.leidos))
            if time.time() - medida["desde"] >= 3600:
                log(f"revisiones de la última hora: {medida['n']}, media {medida['ms'] / medida['n']:.1f} ms (máx "
                    f"{medida['max_ms']:.0f} ms), media {medida['bytes'] / medida['n'] / 1024:.1f} KB leídos (máx "
                    f"{medida['max_bytes'] / 1024:.0f} KB)")
                medida.update(n=0, ms=0.0, max_ms=0.0, bytes=0, max_bytes=0, desde=time.time())
            central.despachar()
            if estado.pop("_cambio", False):
                escribir_json(en(c, "estado.json"), estado)
            if central.principal() and time.time() - ultimo_latido >= LATIDO:
                ultimo_latido = time.time()
                ok = enviar_par(c, central.par.get("ip"), "/latido", {"rol": c["rol"], "t": int(ultimo_latido)})
                if ok != latia:
                    log("la caja responde: le paso las decisiones" if ok else "la caja no responde: sigo solo")
                    latia = ok
        except Exception as e:  # el nodo no se cae por una fuente rara
            log(f"vuelta con error: {type(e).__name__}: {e}")
        if "--una" in sys.argv:
            break
        time.sleep(VUELTA)
    log("nodo detenido")


if __name__ == "__main__":
    main()
