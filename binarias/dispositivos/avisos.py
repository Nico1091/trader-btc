"""Avisos del centinela de binarias a su Telegram (bot Centro nocturno), por Tor. 03/11/2026.

Nicolás (03/11): que funcionen los dos, la caja y el teléfono; si la caja no está funcionando, que funcione el teléfono;
los avisos salen por Tor.
- Rol «caja» (principal): avisa siempre y publica en la red de la casa un latido mínimo (solo la hora, sin operaciones)
  en el puerto 8793.
- Rol «telefono» (respaldo): antes de avisar mira el latido de la caja; si la caja late, calla; si no la ve, avisa él.
- Avisa la apertura y el cierre de las cuentas REGLA y BTC FIJO en BTCUSDT (ETH solo se mide), y si el centinela
  deja de latir o vuelve. Lleva dentro el semáforo papel → real de BTC (semaforo.py).
- La clave del bot se lee al momento de ~/.config/binarias/telegram (línea 1: clave, línea 2: chat) y se le pasa a curl
  por la entrada estándar: no queda en la lista de procesos ni en ningún registro.
Desde el 04/11 también manda fotos y documentos (enviar_archivo) y, si existe ~/.config/binarias/canal, publica los SÍ y NO
en el canal para la gente. Desde el 04/11 a las 13:00, el teléfono mira la caja cada minuto: si lleva 10 min sin latir, le
avisa que toma el relevo, y cuando ella vuelve, que calla otra vez (la noche del 03 al 04/11 la caja se durmió sin aviso).
Uso: AVISOS_ROL=caja|telefono python3 -I avisos.py · Parar: crear PARAR en esta carpeta."""
import datetime as dt
import json
import os
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
ESTADO, APUESTAS = os.path.join(AQUI, "estado.json"), os.path.join(AQUI, "apuestas.jsonl")
AVISADOS, REGISTRO, PARAR = (os.path.join(AQUI, x) for x in ("avisados.json", "avisos.log", "PARAR"))
CLAVE = os.path.expanduser("~/.config/binarias/telegram")
ROL = os.environ.get("AVISOS_ROL", "caja")
ETIQUETA = {"caja": "caja", "telefono": "teléfono"}.get(ROL, ROL)
CAJAS = [x for x in os.environ.get("AVISOS_CAJA", "192.168.20.45,192.168.20.156").split(",") if x]
PUERTO_LATIDO = 8793
# 18/11/2026, orden del dueño: «todo lo de binarias únicamente con mi IP de casa y nada en lo absoluto de Tor».
# Vacío = directo por la IP de la casa (lo normal). Tor solo si alguien lo pidiera en AVISOS_TOR, y ya nada lo pide.
TOR = os.environ.get("AVISOS_TOR", "")


def red(usuario):
    """Cómo sale curl: directo por la IP de la casa, sin proxies del entorno; por Tor solo si AVISOS_TOR lo pidiera."""
    return ["--socks5-hostname", f"{usuario}@{TOR}"] if TOR else ["--noproxy", "*"]


CUENTAS = ("REGLA", "BTC FIJO")
SIMBOLOS_AVISO = ("BTCUSDT",)  # 03/11: Nicolás unificó todo en BTC/USDT; ETH queda solo como medición, sin avisos
CAIDO_S = 180
RELEVO_S = 600          # 04/11: 10 min sin latido de la caja y el teléfono avisa que toma el relevo
RELEVO = ("r", "rv")    # claves de esos dos avisos: el teléfono los manda aunque la caja ya lata
COL = dt.timezone(dt.timedelta(hours=-5))
ESTADO_MEM = {"latido": 0.0}


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto


def guardar(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def hora(ts):
    return dt.datetime.fromtimestamp(ts, COL).strftime("%H:%M")


def cop(x, signo=False):
    t = f"{x:+,.0f}" if signo else f"{x:,.0f}"
    return t.replace(",", ".")


def precio(x):
    if x is None:
        return "–"
    return f"{x:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def activo(sim):
    return {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}.get(sim, sim)


def sentido(d):
    return "SUBE" if d == 1 else "BAJA"


# ---------------------------------------------------------------- Telegram por Tor
def comillas(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


def enviar(texto):
    try:
        lineas = open(CLAVE, encoding="utf-8").read().split()
        token, chat = lineas[0], lineas[1]
    except Exception:
        log("falta ~/.config/binarias/telegram: no se puede avisar")
        return False
    conf = "\n".join([
        "url = " + comillas(f"https://api.telegram.org/bot{token}/sendMessage"),
        "form-string = " + comillas(f"chat_id={chat}"),
        "form-string = " + comillas(f"text={texto}"),
    ]) + "\n"
    usuario = f"binarias{int(time.time()) % 100000}:x"  # circuito propio por aviso
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "90", *red(usuario), "-K", "-"],
                           input=conf, capture_output=True, text=True, timeout=120)
        ok = '"ok":true' in (r.stdout or "")
        if not ok:
            log(f"Telegram sin confirmar (curl {r.returncode}): {(r.stdout or r.stderr or '')[-160:]}")
        return ok
    except Exception as e:
        log(f"Telegram falló ({type(e).__name__})")
        return False


CANAL = os.path.expanduser("~/.config/binarias/canal")  # chat del canal para la gente; si no existe, no se publica nada


def enviar_archivo(ruta, texto="", metodo="sendDocument", campo="document", chat=None):
    """Foto o documento a su Telegram (o al canal) por Tor, con la clave leída al momento. 04/11/2026."""
    try:
        lineas = open(CLAVE, encoding="utf-8").read().split()
        token, chat_suyo = lineas[0], lineas[1]
    except Exception:
        log("falta ~/.config/binarias/telegram: no se puede avisar")
        return False
    conf = "\n".join([
        "url = " + comillas(f"https://api.telegram.org/bot{token}/{metodo}"),
        "form-string = " + comillas(f"chat_id={chat or chat_suyo}"),
        "form-string = " + comillas(f"caption={texto[:1000]}"),
        "form = " + comillas(f"{campo}=@{ruta}"),
    ]) + "\n"
    usuario = f"binarias{int(time.time()) % 100000}:x"
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "60", *red(usuario), "-K", "-"],
                           input=conf, capture_output=True, text=True, timeout=90)
        ok = '"ok":true' in (r.stdout or "")
        if not ok:
            log(f"Telegram ({metodo}) sin confirmar (curl {r.returncode}): {(r.stdout or r.stderr or '')[-160:]}")
        return ok
    except Exception as e:
        log(f"Telegram ({metodo}) falló ({type(e).__name__})")
        return False


def canal():
    """Chat del canal para la gente, si él lo creó y puso al bot como administrador."""
    try:
        c = open(CANAL, encoding="utf-8").read().split()
        return c[0] if c else None
    except Exception:
        return None


# ---------------------------------------------------------------- latido de la caja
class Latido(BaseHTTPRequestHandler):
    def do_GET(self):
        cuerpo = json.dumps({"rol": "caja", "latido": ESTADO_MEM["latido"], "ahora": time.time()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def caja_late():
    """¿La caja está viva y su centinela late? Solo lo usa el teléfono."""
    for ip in CAJAS:
        try:
            d = json.loads(urllib.request.urlopen(f"http://{ip}:{PUERTO_LATIDO}/latido", timeout=3).read())
            if d.get("rol") == "caja" and time.time() - float(d.get("latido") or 0) < CAIDO_S:
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------- textos
def texto_abierta(a):
    return (f"Apuesta en papel [{ETIQUETA}]: {activo(a['sim'])} {sentido(a['dir'])} a {a['plazo']} min · cuenta {a['cuenta']} · "
            f"{cop(a['monto'])} COP · entrada {precio(a.get('pe_toque') or a.get('pe_libro'))} · vence {hora(a['t'] + 60 * a['plazo'])} · "
            f"{a.get('estrategia', '')}. Es papel: nada se apostó con dinero real.")


def texto_cerrada(a):
    res = {1: "ACIERTO", -1: "FALLO", 0: "EMPATE (cuenta como fallo)"}.get(a.get("res"), "sin resultado")
    return (f"Cerrada [{ETIQUETA}]: {activo(a['sim'])} {sentido(a['dir'])} a {a['plazo']} min ({hora(a['t'])}-{hora(a['t'] + 60 * a['plazo'])}) · "
            f"{res} · {cop(a.get('ganancia', 0), True)} COP · saldo {a['cuenta']} {cop(a.get('saldo', 0))} COP.")


# ---------------------------------------------------------------- ciclo
def ids_cerradas():
    vistos = []
    try:
        with open(APUESTAS, encoding="utf-8") as f:
            for lin in f:
                try:
                    a = json.loads(lin)
                    vistos.append(a)
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return vistos


def main():
    if ROL == "caja":
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", PUERTO_LATIDO), Latido)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        except OSError:
            log(f"el puerto {PUERTO_LATIDO} ya está ocupado: otro avisador corre; salgo")
            return
    av = leer(AVISADOS, None)
    if av is None:  # primera vez: lo que ya existe no se avisa, para no inundar
        est = leer(ESTADO, {})
        av = {"abiertas": [a["id"] for a in est.get("abiertas", [])], "cerradas": [a["id"] for a in ids_cerradas()], "caido": False}
        guardar(AVISADOS, av)
    try:  # el semáforo papel → real de BTC corre como hilo de este proceso (dentro de Termux, con su bloqueo de suspensión)
        import sys
        sys.path.insert(0, AQUI)  # con python -I la carpeta del script no entra sola en sys.path
        import semaforo
        threading.Thread(target=semaforo.main, daemon=True).start()
        try:  # vigía de 15 min (04/11): porcentaje de aciertos, reacción de las líneas y voz
            import quince
            threading.Thread(target=quince.main, daemon=True).start()
        except Exception as ex:
            log(f"vigía de 15 min sin arrancar ({type(ex).__name__}: {ex})")
    except Exception as e:
        log(f"no arrancó el semáforo: {type(e).__name__}: {e}")
    log(f"avisador en marcha · rol {ROL} · {len(av['abiertas'])} abiertas y {len(av['cerradas'])} cerradas ya vistas")
    pendientes = []  # (clave, texto, intentos)
    av.setdefault("caja_vista", time.time())
    ultima_mirada = 0.0
    while not os.path.exists(PARAR):
        try:
            est = leer(ESTADO, {})
            ESTADO_MEM["latido"] = float(est.get("latido") or 0)
            nuevos = []
            for a in est.get("abiertas", []):
                if a.get("cuenta") in CUENTAS and a.get("sim") in SIMBOLOS_AVISO and a["id"] not in av["abiertas"]:
                    nuevos.append((("a", a["id"]), texto_abierta(a)))
                    av["abiertas"].append(a["id"])
            for a in ids_cerradas():
                if a["id"] not in av["cerradas"]:
                    av["cerradas"].append(a["id"])
                    if a.get("cuenta") in CUENTAS and a.get("sim") in SIMBOLOS_AVISO:
                        nuevos.append((("c", a["id"]), texto_cerrada(a)))
            if ROL == "caja":  # vigilante de temperatura (la caja llegó a 86,8 °C el 27/10; el chip se protege sobre 85)
                try:
                    grados = int(open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000
                    if grados >= 80 and time.time() - av.get("calor", 0) > 3600:
                        av["calor"] = time.time()
                        nuevos.append((("t", int(time.time())), f"Atención [caja]: la T95H está a {grados:.1f} °C (aviso desde 80; se protege sobre 85)."))
                except Exception:
                    pass
            if ROL == "telefono" and time.time() - ultima_mirada >= 60:  # relevo: ¿la caja sigue latiendo?
                ultima_mirada = time.time()
                if caja_late():
                    av["caja_vista"] = time.time()
                    if av.get("relevo"):
                        av["relevo"] = False
                        nuevos.append((("rv", int(time.time())), f"La caja volvió a latir a las {hora(time.time())}: ella da otra vez los avisos y el teléfono calla."))
                elif not av.get("relevo") and time.time() - av["caja_vista"] > RELEVO_S:
                    av["relevo"] = True
                    nuevos.append((("r", int(time.time())), f"Atención [teléfono]: la caja no late desde las {hora(av['caja_vista'])}. El teléfono sigue con los avisos y el SÍ o NO; revise que la caja esté encendida y conectada."))
            edad = time.time() - ESTADO_MEM["latido"]
            if ESTADO_MEM["latido"] and edad > CAIDO_S and not av.get("caido"):
                av["caido"] = True
                nuevos.append((("x", int(time.time())), f"Atención [{ETIQUETA}]: el centinela no late desde las {hora(ESTADO_MEM['latido'])}."))
            elif edad <= CAIDO_S and av.get("caido"):
                av["caido"] = False
                nuevos.append((("v", int(time.time())), f"El centinela [{ETIQUETA}] volvió a latir."))
            if nuevos:
                av["abiertas"], av["cerradas"] = av["abiertas"][-500:], av["cerradas"][-2000:]
                guardar(AVISADOS, av)
                pendientes += [(k, t, 0) for k, t in nuevos]
            if pendientes:
                if ROL == "telefono" and any(k[0] not in RELEVO for k, _, _ in pendientes) and caja_late():
                    log(f"la caja late: callo {sum(1 for k, _, _ in pendientes if k[0] not in RELEVO)} aviso(s); los da ella")
                    pendientes = [x for x in pendientes if x[0][0] in RELEVO]  # el relevo se avisa siempre
                if pendientes:
                    sigue = []
                    for k, t, n in pendientes:
                        if enviar(t):
                            log(f"avisado {k[0]} {k[1]}")
                        elif n < 6:
                            sigue.append((k, t, n + 1))
                        else:
                            log(f"aviso descartado tras 7 intentos: {k}")
                    pendientes = sigue
                    if pendientes:
                        time.sleep(20)
        except Exception as e:
            log(f"error: {type(e).__name__}: {e}")
            time.sleep(5)
        time.sleep(5)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
