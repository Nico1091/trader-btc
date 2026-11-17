# -*- coding: utf-8 -*-
"""Nodo puente de las binarias (17/11/2026). Solo biblioteca estándar y sin IA propia.

Pedido del dueño del 17/11/2026, 09:45: «un nodo puente en el cual se manda todo»; que una los puntos de los programas que ya
existen (el Centro de estrategias del teléfono y el vigía de 15 min de la caja; el operador de Fable 5.2 cuando corra), que
los mande rápido, y que si solo uno de los dos equipos está conectado se envíe lo de ese.

Qué hace, sin tocar a los demás programas (solo LEE sus archivos):
- Lee cada 10 s las fuentes que haya en el equipo: datos/centro.json (E1 a E5 del Centro), quince.json (vigía de 15 min) y
  el registro del operador de Fable (si existe). De cada estrategia calcula las últimas 25 cerradas, la racha y el fondo.
- Un PUNTO es una señal nueva (abierta) de una estrategia. Es ALTO si esa estrategia lleva UMBRAL o más de sus últimas 25.
- La caja es el nodo central (IP fija y siempre encendida): recibe por la red de la casa los puntos del teléfono, junta los
  de los dos por mercado y sentido (los que coinciden salen en un solo mensaje) y los envía. El teléfono le manda los suyos;
  si la caja no responde, los envía él mismo. Así basta con que uno de los dos esté conectado.
- Envío: Telegram por Tor (la misma clave y el mismo camino que avisos.py), y todo queda en puntos.jsonl.
- Decisión de Claude en la nube: si existe ~/.config/binarias/claude (línea 1: clave de la API de Claude), cada punto ALTO se
  le manda a Claude Opus 5.5 con el contexto fijo (CONTEXTO-NODO.md) y responde COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR; queda
  en decisiones.jsonl y en el mensaje. Sin esa clave, dice «decisión de Claude: pendiente». El nodo NO compra nada: la
  compra la hará el operador de Fable con sus frenos cuando esté armado (ARMADO, por orden del dueño).

Uso:  python3 -I nodo.py            (bucle; lo lanza arrancar_nodo.sh con su vigía)
      python3 -I nodo.py --una      (una vuelta y sale; para probar)
Parar: crear el archivo PARAR en esta carpeta.
"""

import hashlib
import hmac
import json
import os
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
SECRETO = os.path.join(CONF_DIR, "nodo")           # secreto compartido caja-teléfono (firma de los puntos)
CLAUDE = os.path.join(CONF_DIR, "claude")          # línea 1: clave de la API de Claude (la pone el dueño)
TOR = "127.0.0.1:9050"
PUERTO = 8799
CAJA_IP = "192.168.20.45"
UMBRAL = 19            # de las últimas 25 (76 %): «si los porcentajes de los aciertos son altos»
VENTANA = 25
ESPERA_JUNTAR = 20     # segundos que la caja espera a que lleguen los demás puntos del mismo mercado y sentido
VUELTA = 10            # segundos entre lecturas
MODELO = "claude-opus-5-5"
NOMBRES = {"E1": "E1 · ruptura de 20 velas al revés", "E2": "E2 · ruptura de 50 velas al revés",
           "E3": "E3 · Gemini 1 al revés", "E4": "E4 · Gemini 3 al revés", "E5": "E5 · rechazo en techo o piso",
           "quince": "vigía de 15 min", "operador": "operador de Fable 5.2"}
COL = -5 * 3600


def ruta(n):
    return os.path.join(AQUI, n)


def log(texto):
    linea = f"{hora(time.time())} {texto}"
    try:
        with open(ruta("nodo.log"), "a", encoding="utf-8") as f:
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
    """rol (caja o telefono) y carpeta del centinela; se pueden fijar en config.json del nodo."""
    c = leer_json(ruta("config.json"), {})
    rol = c.get("rol")
    cent = c.get("centinela")
    if not cent:
        for d in ("/data/local/tmp/centinela", os.path.join(HOME, "centinela")):
            if os.path.isdir(d):
                cent = d
                break
    if not rol:
        rol = (open(os.path.join(cent, "rol"), encoding="utf-8").read().strip() if cent and os.path.exists(
            os.path.join(cent, "rol")) else "caja")
    return {"rol": rol, "centinela": cent or AQUI, "operador": c.get("operador", "/data/local/tmp/operador"),
            "umbral": int(c.get("umbral", UMBRAL)), "caja_ip": c.get("caja_ip", CAJA_IP)}


# ---------------------------------------------------------------- fuentes (solo lectura)
def resumen(ops):
    """Últimas 25 cerradas (res 0 o 1), racha de aciertos al final, fondo y la señal abierta más nueva."""
    cerradas = [o for o in ops if o.get("res") in (0, 1)]
    ult = cerradas[-VENTANA:]
    aciertos = 0
    for o in ult:            # en bucle, no sum(): igual en 3.11 y 3.14
        aciertos += o["res"]
    racha = 0
    for o in reversed(cerradas):
        if o["res"] == 1:
            racha += 1
        else:
            break
    total = 0
    for o in cerradas:
        total += o["res"]
    abiertas = [o for o in ops if o.get("res") not in (0, 1)]
    return {"aciertos": aciertos, "de": len(ult), "racha": racha,
            "fondo": round(100 * total / len(cerradas), 1) if cerradas else None,
            "abierta": abiertas[-1] if abiertas else None}


def leer_fuentes(c):
    """Lista de (fuente, estrategia, resumen) con lo que haya en este equipo."""
    out = []
    cen = leer_json(os.path.join(c["centinela"], "datos", "centro.json"), None)
    if isinstance(cen, dict):
        for e, ops in sorted((cen.get("ops") or {}).items()):
            if isinstance(ops, list):
                out.append(("centro", e, resumen(ops)))
    q = leer_json(os.path.join(c["centinela"], "quince.json"), None)
    if isinstance(q, dict) and isinstance(q.get("ops"), list):
        out.append(("quince", "quince", resumen(q["ops"])))
    # Operador de Fable 5.2: si corre, deja su registro diario; se toman sus decisiones de compra (papel o real) como señal.
    reg = os.path.join(c["operador"], "registro")
    if os.path.isdir(reg):
        try:
            dias = sorted(n for n in os.listdir(reg) if n.endswith(".jsonl"))
        except OSError:
            dias = []
        # Filas del operador (papel.py y ejecutor.py): «llenado» (compra de papel con precio real) y «orden» (real) con
        # t de la ventana y lado; «resultado» con t y ganador. Una compra acierta si ganador == lado.
        compras, ganadores = {}, {}
        for n in dias[-3:]:
            try:
                with open(os.path.join(reg, n), encoding="utf-8") as f:
                    for linea in f:
                        try:
                            r = json.loads(linea)
                        except ValueError:
                            continue
                        tipo = r.get("tipo")
                        if tipo in ("llenado", "orden") and r.get("lado") in (1, -1) and not r.get("sombra"):
                            compras.setdefault((r.get("t"), r["lado"]), {"t": int(r.get("t") or 0), "dir": r["lado"],
                                                                        "base": r.get("precio") or r.get("q")})
                        elif tipo == "resultado" and r.get("ganador") in (1, -1):
                            ganadores[r.get("t")] = r["ganador"]
            except OSError:
                pass
        ops = []
        for (t, lado), o in sorted(compras.items(), key=lambda kv: kv[1]["t"]):
            g = ganadores.get(t)
            o["res"] = None if g is None else (1 if g == lado else 0)
            ops.append(o)
        if ops:
            out.append(("operador", "operador", resumen(ops)))
    return out


def puntos_nuevos(c, estado):
    """Señales abiertas nuevas de cada estrategia, con su resumen. Marca vistas para no repetir."""
    vistos = set(estado.get("vistos", []))
    nuevos = []
    primera = not estado.get("iniciado")
    for fuente, est, r in leer_fuentes(c):
        o = r["abierta"]
        if not o:
            continue
        clave = f"{c['rol']}|{fuente}|{est}|{o.get('t')}|{o.get('dir')}"
        if clave in vistos:
            continue
        vistos.add(clave)
        if primera:
            continue                     # al arrancar no se reenvía lo que ya estaba abierto
        nuevos.append({"clave": clave, "equipo": c["rol"], "fuente": fuente, "estrategia": est,
                       "nombre": NOMBRES.get(est, est), "t": o.get("t"), "dir": o.get("dir"), "base": o.get("base"),
                       "aciertos": r["aciertos"], "de": r["de"], "racha": r["racha"], "fondo": r["fondo"],
                       "alto": r["de"] >= VENTANA and r["aciertos"] >= c["umbral"], "visto": int(time.time())})
    estado["vistos"] = sorted(vistos)[-3000:]
    estado["iniciado"] = True
    return nuevos


# ---------------------------------------------------------------- firma entre equipos
def secreto():
    try:
        return open(SECRETO, encoding="utf-8").read().strip().encode()
    except OSError:
        return b""


def firmar(cuerpo):
    return hmac.new(secreto(), cuerpo, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------- envíos
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
                      "form-string = " + comillas(f"text={texto}")]) + "\n"
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


def decision_claude(grupo):
    """Claude Opus 5.5 decide si existe la clave del dueño. Devuelve (texto, detalle) o (None, motivo)."""
    try:
        clave = open(CLAUDE, encoding="utf-8").read().split()[0]
    except Exception:
        return None, "pendiente (falta la clave de Claude en el equipo)"
    try:
        contexto = open(ruta("CONTEXTO-NODO.md"), encoding="utf-8").read()
    except OSError:
        contexto = "Binarias BTC Up or Down de Binance. Solo devolución. Responda COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR."
    paquete = json.dumps([{k: p[k] for k in ("equipo", "fuente", "estrategia", "nombre", "t", "dir", "base", "aciertos",
                                              "de", "racha", "fondo")} for p in grupo], ensure_ascii=False)
    cuerpo = json.dumps({"model": MODELO, "max_tokens": 300,
                         "system": [{"type": "text", "text": contexto, "cache_control": {"type": "ephemeral"}}],
                         "messages": [{"role": "user", "content": "Punto de los programas (JSON):\n" + paquete +
                                       "\nResponda en la primera línea solo: COMPRAR SUBE, COMPRAR BAJA o NO COMPRAR. "
                                       "En la segunda, el motivo en una línea."}]})
    conf = "\n".join(["url = \"https://api.anthropic.com/v1/messages\"",
                      "header = " + comillas(f"x-api-key: {clave}"),
                      "header = \"anthropic-version: 2023-06-01\"",
                      "header = \"content-type: application/json\""]) + "\n"
    usuario = f"claude{int(time.time()) % 100000}:x"
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "90", "--socks5-hostname", f"{usuario}@{TOR}", "-K", "-",
                            "--data-binary", cuerpo], input=conf, capture_output=True, text=True, timeout=120)
        resp = json.loads(r.stdout or "{}")
        texto = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text").strip()
    except Exception as e:
        return None, f"sin respuesta de Claude ({type(e).__name__})"
    return interpretar(texto)


def interpretar(texto):
    """Primera línea exacta; cualquier otra cosa cuenta como NO COMPRAR (falla cerrado)."""
    lineas = [x.strip() for x in (texto or "").splitlines() if x.strip()]
    if not lineas:
        return None, "respuesta vacía de Claude: NO COMPRAR"
    primera = lineas[0].upper().replace("Í", "I")
    motivo = lineas[1] if len(lineas) > 1 else ""
    if primera in ("COMPRAR SUBE", "COMPRAR BAJA", "NO COMPRAR"):
        return primera, motivo
    return "NO COMPRAR", "respuesta ilegible de Claude (cuenta como NO COMPRAR)"


def flecha(d):
    return "▲ SUBE" if d == 1 else "▼ BAJA"


def mensaje(grupo, decision, detalle):
    p0 = grupo[0]
    altos = [p for p in grupo if p["alto"]]
    lineas = [f"[Nodo] PUNTO {'ALTO' if altos else 'bajo'} · BTC · {flecha(p0['dir'])} · señal de las {hhmm(p0['t'])}",
              f"Coinciden {len(grupo)} · equipos: {', '.join(sorted({p['equipo'] for p in grupo}))}"]
    for p in grupo:
        pct = round(100 * p["aciertos"] / p["de"]) if p["de"] else 0
        lineas.append(f"- {p['nombre']} ({p['equipo']}): {p['aciertos']} de {p['de']} ({pct} %), racha {p['racha']}"
                      + (f", fondo {str(p['fondo']).replace('.', ',')} %" if p["fondo"] is not None else ""))
    lineas.append(f"Decisión de Claude: {decision or detalle}" + (f" · {detalle}" if decision and detalle else ""))
    lineas.append("El nodo no compra: compra el operador cuando esté armado.")
    return "\n".join(lineas)


# ---------------------------------------------------------------- caja: nodo central
class Central:
    def __init__(self, c):
        self.c = c
        self.lock = threading.Lock()
        self.grupos = {}          # (t//60, dir) -> {"desde": t, "puntos": [...], "enviado": bool}

    def recibir(self, p):
        with self.lock:
            k = (int(p["t"] or 0) // 60, p["dir"])
            g = self.grupos.setdefault(k, {"desde": time.time(), "puntos": [], "enviado": False})
            if all(x["clave"] != p["clave"] for x in g["puntos"]):
                g["puntos"].append(p)
                anexar(ruta("puntos.jsonl"), p)

    def despachar(self):
        ahora = time.time()
        with self.lock:
            listos = [(k, g) for k, g in self.grupos.items()
                      if not g["enviado"] and ahora - g["desde"] >= ESPERA_JUNTAR]
            for k, g in listos:
                g["enviado"] = True
            for k in [k for k, g in self.grupos.items() if ahora - g["desde"] > 3600]:
                del self.grupos[k]
        for k, g in listos:
            grupo = g["puntos"]
            if not any(p["alto"] for p in grupo):
                continue                       # solo se envía lo de aciertos altos
            decision, detalle = decision_claude([p for p in grupo if p["alto"]])
            anexar(ruta("decisiones.jsonl"), {"t": int(ahora), "punto": k, "decision": decision, "detalle": detalle,
                                              "fuentes": [p["clave"] for p in grupo]})
            telegram(mensaje(grupo, decision, detalle))
            log(f"enviado grupo {k}: {len(grupo)} punto(s), decisión {decision or detalle}")


def servidor(central):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            cuerpo = self.rfile.read(min(n, 100000))
            firma = self.headers.get("X-Firma", "")
            if not secreto() or not hmac.compare_digest(firma, firmar(cuerpo)):
                self.send_response(403)
                self.end_headers()
                return
            try:
                for p in json.loads(cuerpo):
                    central.recibir(p)
            except (ValueError, KeyError, TypeError):
                self.send_response(400)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"nodo": "caja", "hora": hora(time.time())}).encode())

    srv = ThreadingHTTPServer(("0.0.0.0", PUERTO), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------------------------------------------------------------- teléfono: remitente
def a_la_caja(c, puntos):
    cuerpo = json.dumps(puntos, ensure_ascii=False).encode()
    pet = (f"POST /puntos HTTP/1.0\r\nHost: {c['caja_ip']}\r\nContent-Type: application/json\r\n"
           f"X-Firma: {firmar(cuerpo)}\r\nContent-Length: {len(cuerpo)}\r\n\r\n").encode() + cuerpo
    try:
        with socket.create_connection((c["caja_ip"], PUERTO), timeout=4) as s:
            s.sendall(pet)
            resp = s.recv(200)
        return resp.split(b" ")[1:2] == [b"200"]
    except OSError:
        return False


def vuelta(c, estado, central=None):
    nuevos = puntos_nuevos(c, estado)
    escribir_json(ruta("estado.json"), estado)
    if not nuevos:
        return 0
    if central is not None:                 # caja
        for p in nuevos:
            central.recibir(p)
        return len(nuevos)
    for p in nuevos:                         # teléfono
        anexar(ruta("puntos.jsonl"), p)
    if a_la_caja(c, nuevos):
        log(f"{len(nuevos)} punto(s) entregados a la caja")
        return len(nuevos)
    # La caja no responde: el teléfono envía lo suyo directo (basta con que uno esté conectado).
    grupos = {}
    for p in nuevos:
        grupos.setdefault((int(p["t"] or 0) // 60, p["dir"]), []).append(p)
    for k, grupo in grupos.items():
        if any(p["alto"] for p in grupo):
            decision, detalle = decision_claude([p for p in grupo if p["alto"]])
            anexar(ruta("decisiones.jsonl"), {"t": int(time.time()), "punto": list(k), "decision": decision,
                                              "detalle": detalle, "fuentes": [p["clave"] for p in grupo]})
            telegram(mensaje(grupo, decision, detalle) + "\n(la caja no respondió: lo envía el teléfono)")
    log(f"caja sin respuesta: {len(nuevos)} punto(s) tratados en el teléfono")
    return len(nuevos)


def main():
    c = config()
    estado = leer_json(ruta("estado.json"), {})
    central = None
    if c["rol"] == "caja":
        central = Central(c)
        if "--una" not in sys.argv:
            servidor(central)
    log(f"nodo arrancó: rol {c['rol']}, centinela {c['centinela']}, umbral {c['umbral']} de {VENTANA}")
    while not os.path.exists(ruta("PARAR")):
        try:
            vuelta(c, estado, central)
            if central is not None:
                central.despachar()
        except Exception as e:  # el nodo no se cae por una fuente rara
            log(f"vuelta con error: {type(e).__name__}: {e}")
        if "--una" in sys.argv:
            break
        time.sleep(VUELTA)
    log("nodo detenido")


if __name__ == "__main__":
    main()
