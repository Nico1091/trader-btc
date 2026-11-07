"""Mesa de binarias (04/11/2026): servidor local y motor. Solo biblioteca estándar. http://127.0.0.1:8795

Un hilo mantiene velas, mercado de 15 min, borrador, cinco líneas, arnés y análisis propio, sin IA; el servidor sirve la pantalla (mesa.html).
Las órdenes reales solo nacen de un POST de esa pantalla con su ficha, y se vuelven a evaluar aquí antes de enviarse: la
pantalla nunca decide. Ningún otro proceso tiene la ficha. Parar: crear el archivo PARAR en esta carpeta.
"""
import ctypes
import datetime as dt
import http.server
import json
import math
import os
import secrets
import socketserver
import sys
import threading
import time
import traceback
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "dispositivos"))
import analista  # noqa: E402
import borrador as Bo  # noqa: E402
import conexion as C  # noqa: E402
import graficas  # noqa: E402  (las mismas cinco líneas de la caja y de Pulso)
import reglas as R  # noqa: E402

PUERTO = 8795
ORIGEN = f"http://127.0.0.1:{PUERTO}"
TITULO = "Mesa de binarias"
PARAR = os.path.join(AQUI, "PARAR")
CONFIG = os.path.join(AQUI, "config.json")
REGISTRO = os.path.join(Bo.DATOS, "mesa.log")
REALES = os.path.join(Bo.DATOS, "reales.jsonl")
ESTADOS_FALLIDOS = ("FAILED", "CANCELLED", "CANCELED", "EXPIRED", "REJECTED")
INTENTOS_CONFIRMAR, PAUSA_CONFIRMAR = 6, 0.5
FICHA = secrets.token_hex(24)
ARRANQUE = int(time.time())  # si cambia, la ventana se recarga para traer la ficha nueva
COL = dt.timezone(dt.timedelta(hours=-5))


def log(msg):
    os.makedirs(Bo.DATOS, exist_ok=True)
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def cargar_cfg():
    cfg = dict(R.CFG)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


class Motor:
    def __init__(self):
        self.cfg = cargar_cfg()
        self.bor = Bo.Borrador(self.cfg)
        self.cand = threading.Lock()
        self.orden_cand = threading.Lock()
        self.velas, self.viva, self.lineas, self.mercado = [], None, None, None
        self.saldo, self.wallet, self.pct = 0.0, None, self.cfg["pct_defecto"]
        self.est, self.analisis, self.nivel_prev = None, None, None
        self.error_red, self.t_velas, self.t_libro, self.t_cuenta, self.t_sembrado = None, 0.0, 0.0, 0.0, 0.0
        self.encima = False

    # ------------------------------------------------------------ datos
    def _lineas(self):
        v = self.velas[-150:]
        s = graficas.cinco_lineas(v) if len(v) >= 150 else None
        if not s:
            return None
        n, out = len(v), {}
        for clave in ("techo", "piso", "techo_c", "piso_c", "mitad"):
            r, d = s[clave], s["desde"][clave]
            a, b = r.en(d), r.en(n + 19)
            if math.isfinite(a) and math.isfinite(b):
                out[clave] = {"i0": d, "y0": round(a, 2), "i1": n + 19, "y1": round(b, 2), "ahora": round(r.en(n - 1), 2)}
        return out

    def _refrescar_velas(self):
        cerr, viva = C.velas(170)
        cambio = not self.velas or cerr[-1][0] != self.velas[-1][0]
        self.velas, self.viva = cerr, viva
        if cambio:
            self.lineas = self._lineas()

    def _refrescar_mercado(self, ahora):
        t = int(ahora // 900 * 900)
        m = self.mercado
        if not m or m.get("t") != t:
            m = C.mercado_15m(t)
            if m is None:
                self.mercado = None
                return
            m["ask"], m["bid"] = {}, {}
        for lado in (1, -1):
            m["ask"][lado], m["bid"][lado] = C.libro(m, lado)
        self.mercado = m

    def _refrescar_cuenta(self):
        self.saldo = C.saldo_spot()
        self.wallet = C.billetera()

    def evaluar(self, ahora=None):
        return R.evaluar(self.bor.copia(), ahora or time.time(), self.mercado, self.cfg, bool(self.wallet), self.saldo, self.pct)

    # ------------------------------------------------------------ bucle
    def paso(self):
        ahora = time.time()
        ops = self.bor.ops
        cerca = any(o.get("res") is None and ahora - o["t"] <= 80 for o in ops[-3:])
        if ahora - self.t_sembrado > 900:
            self.t_sembrado = ahora
            n = self.bor.sembrar()
            if n:
                log(f"borrador: {n} operaciones rehechas con velas")
        if ahora - self.t_velas >= 2:
            self.t_velas = ahora
            self._refrescar_velas()
        if ahora - self.t_libro >= (2 if cerca else 5):
            self.t_libro = ahora
            self._refrescar_mercado(ahora)
        if ahora - self.t_cuenta >= 60:
            self.t_cuenta = ahora
            self._refrescar_cuenta()
        self.bor.paso(ahora, self.mercado)
        e = self.evaluar(ahora)
        self.est = e
        if e["nivel"] in ("COMPRE", "VENDA") and e["nivel"] != self.nivel_prev:
            traer_al_frente()
        self.nivel_prev = e["nivel"]
        self.analisis = analista.leer(e, self.velas[-150:], self.lineas, ahora)
        self.error_red = None

    def correr(self):
        log("mesa en marcha")
        while not os.path.exists(PARAR):
            try:
                self.paso()
            except Exception as ex:
                self.error_red = f"{type(ex).__name__}: {str(ex)[:120]}"
                log(f"motor: {self.error_red}")
                time.sleep(3)
            time.sleep(1)
        log("PARAR: salgo")
        os._exit(0)

    # ------------------------------------------------------------ pantalla
    def estado(self):
        ahora = time.time()
        ops = self.bor.copia()
        e = self.est or self.evaluar(ahora)
        m = self.mercado or {}
        v = self.velas[-150:]
        t0 = v[0][0] if v else 0
        flechas = [{"t": o["t"], "dir": o["dir"], "si": bool(o.get("si")), "res": o.get("res")} for o in ops if o["t"] >= t0]
        return {"arranque": ARRANQUE, "ahora": ahora, "hora": dt.datetime.fromtimestamp(ahora, COL).strftime("%H:%M:%S"), "e": e, "velas": v, "viva": self.viva,
                "lineas": self.lineas, "flechas": flechas, "error": self.error_red, "cfg": {k: self.cfg[k] for k in ("ask_max", "pct_tope", "ventana_toque")},
                "mercado": {"t": m.get("t"), "strike": m.get("strike"), "ask": {"1": (m.get("ask") or {}).get(1), "-1": (m.get("ask") or {}).get(-1)}},
                "saldo": self.saldo, "billetera": bool(self.wallet), "pct": self.pct,
                "puede": {str(k): self._puede(k) for k in (1, -1)},
                "analisis": self.analisis, "encima": self.encima,
                "ops": [{k: o.get(k) for k in ("t", "dir", "si", "ask5", "ask30", "ask60", "entra", "res", "neto", "semilla", "aviso", "fuente")} for o in ops[-40:]][::-1],
                "reales": leer_reales()[-10:][::-1]}

    def _puede(self, sentido):
        ask = ((self.mercado or {}).get("ask") or {}).get(sentido)
        return bool(self.mercado and self.mercado.get("abierto") and ask and ask <= self.cfg["precio_max_manual"])

    def ordenar(self, sentido, pct):
        """Su toque, cuando él quiera. Topes que no se saltan: mercado abierto, cuenta, porcentaje máximo, precio y una orden por mercado."""
        with self.orden_cand:
            self.pct = pct
            self._refrescar_mercado(time.time())
            self._refrescar_cuenta()
            m, w, cfg = self.mercado, self.wallet, self.cfg
            if not w:
                return {"ok": False, "msg": "Primero cree la cuenta en la app de Binance: Mercados → Predicción."}
            if not self._puede(sentido):
                return {"ok": False, "msg": "Este mercado no tiene precio para esa opción ahora."}
            usdt = R.importe(self.saldo, pct, cfg)
            if usdt is None:
                return {"ok": False, "msg": "El saldo no alcanza con su tope del 16 %."}
            if any(r.get("t") == m["t"] and not rechazada(r) for r in leer_reales()):
                return {"ok": False, "msg": "Ya tiene una orden en este mercado de 15 min."}
            e = self.evaluar()
            con_senal = bool(e["boton"] and e["sentido"] == sentido)
            q = C.cotizar(w["walletAddress"], m["tokens"][sentido], usdt, cfg["deslizamiento_bps"], cfg["fuente_fondos"])
            precio = float(q.get("averagePrice") or 0)
            if not precio or precio > cfg["precio_max_manual"]:
                return {"ok": False, "msg": f"Cotización a {precio:.3f}: paga casi nada, no se envió."}
            r = C.ordenar(w["walletAddress"], w["walletId"], q["quoteId"], cfg["deslizamiento_bps"], cfg["fuente_fondos"])
            final = confirmar(w["walletAddress"], r.get("orderId"))
            comprado = float((final or {}).get("filledUsdtAmount") or 0)
            estado = (final or {}).get("status") or "SIN CONFIRMAR"
            fila = {"t": m["t"], "dir": sentido, "usdt": usdt, "precio": precio, "orden": r.get("orderId"), "topic": m["topic"], "hora": time.time(), "con_senal": con_senal,
                    "estado": estado, "comprado": comprado}
            with open(REALES, "a", encoding="utf-8") as f:
                f.write(json.dumps(fila) + "\n")
            log(f"orden real por su toque: {'sube' if sentido == 1 else 'baja'} {usdt} USDT a {precio} · con señal: {con_senal} · estado: {estado} · comprado: {comprado}")
            if comprado > 0:
                return {"ok": True, "msg": f"Comprada: {comprado:.2f} USDT a {precio:.3f}.".replace(".", ",")}
            if rechazada(fila):
                return {"ok": False, "msg": f"Binance rechazó la orden ({estado}): no se compró nada y el saldo sigue igual."}
            return {"ok": False, "msg": "Binance recibió la orden pero no confirmó la compra. Revísela en la app antes de repetir."}


def rechazada(fila):
    """Binance la cerró sin comprar nada: no cuenta como la orden de ese mercado."""
    return fila.get("estado") in ESTADOS_FALLIDOS and not fila.get("comprado")


def confirmar(direccion, id_orden):
    """Binance responde a la orden con un número y la resuelve después: «enviada» no es «comprada». Lee cómo quedó."""
    o = None
    for _ in range(INTENTOS_CONFIRMAR):
        try:
            o = C.orden(direccion, id_orden) or o
        except Exception as ex:
            log(f"no pude leer la orden {id_orden}: {type(ex).__name__}")
        if o and (float(o.get("filledUsdtAmount") or 0) > 0 or o.get("status") in ESTADOS_FALLIDOS):
            return o
        time.sleep(PAUSA_CONFIRMAR)
    return o


def leer_reales():
    try:
        with open(REALES, encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]
    except OSError:
        return []


# ---------------------------------------------------------------- ventana encima de todo (Windows)
def _ventanas():
    u, salida = ctypes.windll.user32, []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def ver(h, _):
        b = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, b, 256)
        if b.value.startswith(TITULO):
            salida.append(h)
        return True
    u.EnumWindows(proto(ver), 0)
    return salida


def fijar_encima(si):
    u = ctypes.windll.user32
    for h in _ventanas():
        u.SetWindowPos(h, ctypes.c_void_p(-1 if si else -2), 0, 0, 0, 0, 0x0003)


def traer_al_frente():
    """Encima de todo sin quedarse pegada: mismo truco de abrir-en-primer-plano (Alt simulado, TOPMOST y NOTOPMOST)."""
    try:
        u = ctypes.windll.user32
        for h in _ventanas():
            u.ShowWindow(h, 9)
            u.keybd_event(0x12, 0, 0, 0)
            u.keybd_event(0x12, 0, 2, 0)
            u.SetWindowPos(h, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0003)
            if not MOTOR.encima:
                u.SetWindowPos(h, ctypes.c_void_p(-2), 0, 0, 0, 0, 0x0003)
            u.SetForegroundWindow(h)
    except Exception as ex:
        log(f"al frente: {ex}")


class Web(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _enviar(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _host_ok(self):
        return self.headers.get("Host") == f"127.0.0.1:{PUERTO}"

    def do_GET(self):
        if not self._host_ok():
            return self._enviar(403, b"{}")
        if self.path == "/":
            with open(os.path.join(AQUI, "mesa.html"), encoding="utf-8") as f:
                return self._enviar(200, f.read().replace("__FICHA__", FICHA).encode("utf-8"), "text/html; charset=utf-8")
        if self.path == "/api/estado":
            return self._enviar(200, json.dumps(MOTOR.estado(), ensure_ascii=False).encode("utf-8"))
        self._enviar(404, b"{}")

    def do_POST(self):
        largo = min(int(self.headers.get("Content-Length") or 0), 4096)
        try:
            d = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            return self._enviar(400, b"{}")
        if not self._host_ok() or self.headers.get("Origin") != ORIGEN or not secrets.compare_digest(str(d.get("ficha", "")), FICHA):
            return self._enviar(403, json.dumps({"ok": False, "msg": "Sin permiso."}).encode())
        try:
            r = self._accion(d)
        except C.ErrorBinance as ex:
            log(f"binance: {ex}")
            r = {"ok": False, "msg": f"Binance: {ex.mensaje[:140]}"}
        except Exception as ex:
            log(f"accion: {traceback.format_exc()[-300:]}")
            r = {"ok": False, "msg": f"{type(ex).__name__}: {str(ex)[:120]}"}
        self._enviar(200, json.dumps(r, ensure_ascii=False).encode("utf-8"))

    def _accion(self, d):
        if self.path == "/api/ordenar":
            return MOTOR.ordenar(1 if d.get("sentido") == 1 else -1, float(d.get("pct", MOTOR.pct)))
        if self.path == "/api/pct":
            MOTOR.pct = min(max(float(d.get("pct", 5)), 1.0), float(MOTOR.cfg["pct_tope"]))
            return {"ok": True}
        if self.path == "/api/encima":
            MOTOR.encima = bool(d.get("si"))
            fijar_encima(MOTOR.encima)
            return {"ok": True}
        if self.path == "/api/cobrar":
            w = MOTOR.wallet
            if not w:
                return {"ok": False, "msg": "Aún no tiene cuenta de predicción."}
            tokens = [p["tokenId"] for p in C.posiciones(w["walletAddress"]).get("positions", []) if p.get("canClaim")]
            if not tokens:
                return {"ok": True, "msg": "No hay nada por cobrar."}
            C.cobrar(w["walletAddress"], w["walletId"], tokens)
            return {"ok": True, "msg": f"Cobro enviado: {len(tokens)} posiciones."}
        return {"ok": False, "msg": "Acción desconocida."}


class Servidor(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = False  # en Windows, reutilizar deja levantar dos servidores en el mismo puerto
    daemon_threads = True


def main():
    global MOTOR
    if os.path.exists(PARAR):
        os.remove(PARAR)
    try:
        web = Servidor(("127.0.0.1", PUERTO), Web)
    except OSError:
        return  # ya está corriendo
    MOTOR = Motor()
    threading.Thread(target=MOTOR.correr, daemon=True).start()
    web.serve_forever()


if __name__ == "__main__":
    if sys.stdout is None or sys.stderr is None:  # con pythonw no hay consola
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    try:
        main()
    except Exception:
        log(traceback.format_exc()[-800:])
        ctypes.windll.user32.MessageBoxW(0, "La Mesa de binarias no pudo arrancar. Mire datos\\mesa.log.", TITULO, 0x10)
        raise
