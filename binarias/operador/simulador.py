"""Binance simulado para probar el operador sin red, sin llave real y sin dinero (16/11/2026). Solo biblioteca estándar.

Habla lo mismo que el Binance real en lo que el operador usa: la hora y las velas públicas de contado, y la API de predicción
de Binance Wallet tal como está en la documentación oficial y como respondió de verdad el 04, 06, 07 y 12/11 (nombres de
campos, estados FILLED, SUBMITTED, FAILED y EXPIRED, errores -2014, -2015, -1021, -1022 y -9000). Revisa la firma HMAC de cada
consulta. Se enchufa en conexion._pedir, de modo que la firma, las rutas y la lectura de respuestas que se prueban son las de
verdad; solo cambia el cable. También puede servir por HTTP en 127.0.0.1 para probar el cable mismo.

Tiene reloj propio (self.t), velas que arma la prueba, mercados «BTC Up or Down» de 5 y 15 min con su libro, una cuenta con
billetera y saldos, órdenes que siguen un guion (comprada, rechazada, abierta que luego cierra, sin respuesta) y cobros."""
import hashlib
import hmac
import http.server
import json
import math
import threading
import time
import urllib.parse

PRED = "/sapi/v1/w3w/wallet/prediction"
ABIERTOS = ("SUBMITTED", "PENDING", "OPENING")


class SinRespuesta(OSError):
    """El cable se cortó: quien llama no sabe si Binance recibió la petición."""


def ruido(t):
    return 0.00028 * math.sin(t / 37.0) + 0.00012 * math.sin(t / 11.0)


class Binance:
    def __init__(self, t0, precio=73500.0):
        self.t = float(t0)
        self.vivo_real = False            # con servir(): el reloj es el de verdad más un desfase
        self.desfase = 0.0
        self.velas, self.precio0, self.vivo = {}, precio, None
        self.llaves = {}                  # clave pública -> {secreto, pasa, operar, permisos}
        self.billetera = {"walletAddress": "0x51d0c0ffee51d0c0ffee51d0c0ffee51d0c0ffee", "walletId": "sim-billetera-1"}
        self.saldo = {"SPOT": 0.0, "FUNDING": 0.0, "CeDeFi": 0.0}
        self.publica = {5, 15}            # mercados que Binance publica
        self.demora_apertura, self.demora_resolucion, self.comision_bps = 2.0, 45.0, 200
        self.libro = lambda t, W, t_ini, lado: [(0.50, 1000.0)]
        self.ganador_forzado = {}         # (W, t_ini) -> 1, -1 o 0 (empate)
        self.guion = "FILLED"             # qué pasa con la próxima orden (ver _ordenar)
        self.guion_cobro = "CONFIRMED"    # CONFIRMED, FAILED o ERROR
        self.demora_cobro = 20.0
        self.cotizaciones, self.ordenes, self.cobros, self.posiciones = {}, {}, {}, {}
        self.n, self.llamadas, self.ip = 1000, [], "203.0.113.7"
        self.corte = {}                   # ruta -> veces que el cable se corta antes de responder
        self.gancho = {}                  # ruta -> función(sim) que la prueba corre justo antes de atenderla
        self.escrituras = 0               # cotizaciones no cuentan: solo órdenes y cobros pedidos

    # ------------------------------------------------------------ reloj, llaves y velas
    def ahora(self):
        return time.time() + self.desfase if self.vivo_real else self.t

    def dar_llave(self, clave, secreto, operar=False, pasa=True, **permisos):
        base = {"ipRestrict": True, "enableReading": True, "enableWithdrawals": False, "enableInternalTransfer": False,
                "enableMargin": False, "enableFutures": False, "permitsUniversalTransfer": False, "enableVanillaOptions": False,
                "enableSpotAndMarginTrading": False, "enablePortfolioMarginTrading": False}
        base.update(permisos)
        self.llaves[clave] = {"secreto": secreto, "pasa": pasa, "operar": operar, "permisos": base}

    def sembrar(self, desde, hasta, pasos=None):
        """Velas de 1 min seguidas entre desde y hasta. pasos = {apertura de la vela: rendimiento}; el resto, ruido suave."""
        pasos = pasos or {}
        previas = [t for t in self.velas if t < desde]
        precio = self.velas[max(previas)][4] if previas else self.precio0
        for t in range(int(desde), int(hasta), 60):   # con los mismos decimales con que Binance las entrega
            nuevo = round(precio * math.exp(pasos.get(t, ruido(t))), 2)
            self.velas[t] = (t, precio, round(max(precio, nuevo) + 1.5, 2), round(min(precio, nuevo) - 1.5, 2), nuevo,
                             round(12.0 + 3 * math.sin(t / 500.0) ** 2, 5))
            precio = nuevo

    def _klines(self, q):
        ahora = self.ahora()
        ts = sorted(t for t in self.velas if t <= ahora)
        if "startTime" in q:
            ts = [t for t in ts if t >= int(q["startTime"]) // 1000]
            ts = ts[:int(q.get("limit", 500))]
        else:
            ts = ts[-int(q.get("limit", 500)):]
        out = []
        for t in ts:
            v = self.velas[t]
            cierre = v[4]
            if ahora < t + 60:   # la vela en curso: su cierre es el último precio
                cierre = self.vivo(ahora) if self.vivo else v[1]
            out.append([t * 1000, f"{v[1]:.2f}", f"{v[2]:.2f}", f"{v[3]:.2f}", f"{cierre:.2f}", f"{v[5]:.5f}", t * 1000 + 59999, "0", 10, "0", "0", "0"])
        return out

    # ------------------------------------------------------------ mercados
    @staticmethod
    def topic(W, t_ini):
        return int(t_ini) * 100 + W

    @staticmethod
    def token(W, t_ini, lado):
        return f"{int(t_ini)}{W:02d}{'1' if lado > 0 else '2'}"

    @staticmethod
    def de_token(tok):
        return int(tok[-3:-1]), int(tok[:-3]), (1 if tok[-1] == "1" else -1)

    def ganador(self, W, t_ini):
        """1, -1, 0 (empate) o None si aún no está resuelto."""
        if self.ahora() < t_ini + 60 * W + self.demora_resolucion:
            return None
        if (W, t_ini) in self.ganador_forzado:
            return self.ganador_forzado[(W, t_ini)]
        a, c = self.velas[t_ini][1], self.velas[t_ini + 60 * W - 60][4]
        return 1 if c > a else (-1 if c < a else 0)

    def _lista(self, q):
        ahora = self.ahora()
        temas = []
        for W in sorted(self.publica):
            t = int(ahora // (60 * W)) * 60 * W
            for k in (0, 1):
                temas.append((t + 60 * W * (k + 1), f"btc-updown-{W}m-{t + 60 * W * k}", self.topic(W, t + 60 * W * k)))
        t15 = int(ahora // 900) * 900
        temas += [(t15 + 900, f"eth-updown-15m-{t15}", 7), (t15 + 3600, f"btc-updown-1h-{t15}", 8)]
        temas.sort()
        return {"marketTopics": [{"slug": s, "marketTopicId": tid} for _fin, s, tid in temas][int(q.get("offset", 0)):][:int(q.get("limit", 20))]}

    def _detalle(self, q):
        tid = int(q["marketTopicId"])
        W, t = tid % 100, tid // 100
        if W not in (5, 15) or t not in self.velas:
            return 400, {"code": -9000, "msg": "market not found"}
        ahora, g = self.ahora(), self.ganador(W, t)
        salidas = []
        for lado, nombre in ((1, "Up"), (-1, "Down")):
            o = {"name": nombre, "tokenId": self.token(W, t, lado), "price": "0.50", "index": 0 if lado > 0 else 1}
            if g is not None:
                o["winner"] = (g == 0) or (g == lado)
                o["price"] = "0.5" if g == 0 else ("1" if g == lado else "0")
            salidas.append(o)
        d = {"marketTopicId": tid, "vendor": "predict_fun", "status": "RESOLVED" if g is not None else "REGISTERED",
             "feeRateBps": self.comision_bps, "question": f"BTC Up or Down - {W}m", "variantData": {"type": "UP_DOWN"},
             "markets": [{"marketId": tid + 1, "tradingStatus": "OPEN" if t <= ahora < t + 60 * W else "CLOSED", "outcomes": salidas}]}
        if ahora >= t + self.demora_apertura:
            d["variantData"]["startPrice"] = f"{self.velas[t][1]:.2f}"
        return 200, d

    def _libro(self, q):
        W, t, lado = self.de_token(q["tokenId"])
        asks = self.libro(self.ahora(), W, t, lado) or []
        return {"outcome": "YES", "tokenId": q["tokenId"], "timestamp": int(self.ahora() * 1000),
                "asks": [{"price": f"{p:.2f}", "size": f"{s:.2f}"} for p, s in asks],
                "bids": [{"price": f"{max(0.01, asks[0][0] - 0.02):.2f}", "size": "50.00"}] if asks else []}

    # ------------------------------------------------------------ cuenta, cotización y órdenes
    def _cotizar(self, b):
        if b.get("walletAddress") != (self.billetera or {}).get("walletAddress"):
            return 400, {"code": -3026, "msg": "Invalid parameter."}
        W, t, lado = self.de_token(b["tokenId"])
        ahora = self.ahora()
        usdt = int(b["amountIn"]) / 1e18
        if not t <= ahora < t + 60 * W:
            return 400, {"code": -9000, "msg": "Market is not open for trading"}
        if usdt < 1.5:
            return 400, {"code": -9000, "msg": "Your order amount is too small"}
        if b.get("fundingSource", "MPC") == "MPC" and self.saldo["CeDeFi"] + 1e-9 < usdt:
            return 400, {"code": -9000, "msg": "Insufficient balance"}
        resta, contratos, ultimo = usdt, 0.0, None
        for p, s in self.libro(ahora, W, t, lado) or []:
            gasto = min(resta, p * s)
            contratos += gasto / p
            resta -= gasto
            ultimo = p
            if resta <= 1e-9:
                break
        if resta > 1e-9 or not contratos:
            return 400, {"code": -9000, "msg": "Insufficient liquidity"}
        self.n += 1
        qid = f"q_sim_{self.n}"
        com = int(b.get("feeRateBps") or self.comision_bps) / 10000
        fuera = contratos * (1 - com)   # la comisión sale de los contratos (cotización real del 04/11)
        c = {"quoteId": qid, "tokenId": b["tokenId"], "side": "BUY", "amountIn": b["amountIn"], "amountOut": str(int(fuera * 1e18)),
             "averagePrice": round(usdt / contratos, 6), "lastPrice": ultimo, "feeRateBps": int(com * 10000), "orderType": "MARKET",
             "slippageBps": int(b["slippageBps"]), "minReceive": str(int(fuera * (1 - int(b["slippageBps"]) / 10000) * 1e18)),
             "expireAt": int((ahora + 30) * 1000), "walletAddress": b["walletAddress"], "vendor": "PREDICT_FUN", "timestamp": int(ahora * 1000)}
        self.cotizaciones[qid] = {**c, "usdt": usdt, "contratos": fuera, "usada": False, "fuente": b.get("fundingSource", "MPC")}
        return 200, c

    def _ordenar(self, b, llave):
        if not llave["operar"]:
            return 400, {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."}
        c = self.cotizaciones.get(b.get("quoteId"))
        ahora = self.ahora()
        if not c or c["usada"] or ahora * 1000 > c["expireAt"] or b.get("walletId") != (self.billetera or {}).get("walletId"):
            return 400, {"code": -9000, "msg": "Quote expired or invalid"}
        guion = self.guion
        if guion == "RECHAZO":
            return 400, {"code": -9000, "msg": "Order rejected by risk control"}
        if guion == "CORTE SIN ORDEN":
            raise SinRespuesta("se cortó antes de llegar")
        c["usada"] = True
        self.n += 1
        self.escrituras += 1
        oid = f"2611{self.n:016d}"
        W, t, lado = self.de_token(c["tokenId"])
        o = {"orderId": oid, "vendorOrderId": f"0xsim{self.n}", "vendor": "PREDICT_FUN", "marketTopicId": self.topic(W, t), "marketId": self.topic(W, t) + 1,
             "marketTitle": "UP" if lado > 0 else "DOWN", "status": "SUBMITTED", "side": "BUY", "orderType": "MARKET",
             "createTime": int(ahora * 1000), "modifyTime": int(ahora * 1000), "makerUsdtAmount": f"{c['usdt']:.2f}",
             "filledUsdtAmount": "0.00", "filledShareQty": "0.00", "price": f"{c['averagePrice']:.4f}",
             "_c": c, "_token": c["tokenId"], "_cierra": None, "_final": None}
        if guion in ("FILLED", "FAILED", "EXPIRED"):
            self._cerrar(o, guion)
        elif isinstance(guion, tuple):          # ("SUBMITTED", segundos, "FILLED" | "EXPIRED" | "FAILED")
            o["status"], o["_cierra"], o["_final"] = guion[0], ahora + guion[1], guion[2]
        elif guion in ("CORTE CON ORDEN", "RESPUESTA ROTA"):
            self._cerrar(o, "FILLED")
        self.ordenes[oid] = o
        if guion == "CORTE CON ORDEN":
            raise SinRespuesta("se cortó después de llegar")
        if guion == "RESPUESTA ROTA":
            return 502, b"<html>Bad Gateway</html>"
        return 200, {"orderId": oid}

    def _cerrar(self, o, estado):
        o["status"], o["modifyTime"], o["terminalTime"] = estado, int(self.ahora() * 1000), int(self.ahora() * 1000)
        if estado == "FILLED":
            c = o["_c"]
            if self.saldo["CeDeFi"] + 1e-9 < c["usdt"]:
                o["status"] = "FAILED"
                return
            self.saldo["CeDeFi"] = round(self.saldo["CeDeFi"] - c["usdt"], 6)
            o["filledUsdtAmount"], o["filledShareQty"] = f"{c['usdt']:.2f}", f"{c['contratos']:.4f}"
            p = self.posiciones.setdefault(o["_token"], {"contratos": 0.0, "costo": 0.0, "estado": "OPEN", "cobro": None})
            p["contratos"] += c["contratos"]
            p["costo"] += c["usdt"]

    def _avanzar(self):
        ahora = self.ahora()
        for o in self.ordenes.values():
            if o["_cierra"] is not None and ahora >= o["_cierra"] and o["status"] in ABIERTOS:
                self._cerrar(o, o["_final"])
        for tx, c in self.cobros.items():
            if c["estado"] == "PENDING" and ahora >= c["cuando"]:
                c["estado"] = c["final"]
                if c["final"] == "CONFIRMED":
                    p = self.posiciones[c["token"]]
                    p["estado"], p["cobro"] = "CLAIMED", "CONFIRMED"
                    self.saldo["CeDeFi"] = round(self.saldo["CeDeFi"] + c["monto"], 6)

    def _ordenes(self, abiertas):
        out = [{k: v for k, v in o.items() if not k.startswith("_")} for o in self.ordenes.values() if (o["status"] in ABIERTOS) == abiertas]
        out.sort(key=lambda o: -o["createTime"])
        return {"total": len(out), "offset": 0, "limit": 20, "orders": out}

    def _pago(self, tok):
        """Lo que paga un resultado ya resuelto por contrato: 1, 0,5 (empate) o 0; None si aún no está resuelto."""
        W, t, lado = self.de_token(tok)
        g = self.ganador(W, t)
        return None if g is None else (0.5 if g == 0 else (1.0 if g == lado else 0.0))

    def _liquidadas(self):
        out = []
        for tok, p in self.posiciones.items():
            pago = self._pago(tok)
            if pago is None:
                continue
            W, t, lado = self.de_token(tok)
            out.append({"tokenId": tok, "marketTopicId": self.topic(W, t), "vendor": "PREDICT_FUN", "shares": f"{p['contratos']:.4f}",
                        "totalCost": f"{p['costo']:.2f}", "isWinner": pago > 0, "positionStatus": p["estado"] if p["estado"] == "CLAIMED" else "ENDED",
                        "redeemStatus": p["cobro"], "claimAmount": f"{p['contratos'] * pago:.4f}", "finalOutcome": "YES",
                        "settledDate": int((t + 60 * W) * 1000)})
        return {"totalCount": len(out), "positions": out}

    def _cobrar(self, b, llave):
        if not llave["operar"]:
            return 400, {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."}
        tok = b.get("tokenIds")
        p = self.posiciones.get(tok)
        pago = self._pago(tok) if p else None
        self.n += 1
        self.escrituras += 1
        if not p or not pago or p["estado"] == "CLAIMED":
            return 200, {"batchId": f"lote_{self.n}", "results": [{"requestId": f"req_{self.n}", "txHash": None, "status": "FAILED", "error": "NOTHING_TO_REDEEM"}]}
        if self.guion_cobro == "ERROR":
            return 200, {"batchId": f"lote_{self.n}", "results": [{"requestId": f"req_{self.n}", "txHash": None, "status": "FAILED", "error": "RPC_BUSY"}]}
        tx = f"0xsim{self.n:060d}"
        self.cobros[tx] = {"token": tok, "estado": "PENDING", "final": self.guion_cobro, "cuando": self.ahora() + self.demora_cobro,
                           "monto": round(p["contratos"] * pago, 6)}
        p["cobro"] = "PENDING"
        return 200, {"batchId": f"lote_{self.n}", "results": [{"requestId": f"req_{self.n}", "txHash": tx, "status": "PENDING", "error": None}]}

    # ------------------------------------------------------------ el cable
    def pedir(self, metodo, url, cuerpo=None, cabeceras=None, plazo=15):
        """Lo mismo que conexion._pedir: (código HTTP, cuerpo en bytes)."""
        u = urllib.parse.urlsplit(url)
        ruta = u.path
        self.llamadas.append((round(self.ahora(), 2), metodo, ruta))
        if self.corte.get(ruta, 0) > 0:
            self.corte[ruta] -= 1
            raise SinRespuesta("sin red")
        self._avanzar()
        if ruta in self.gancho:
            self.gancho[ruta](self)
        if u.netloc.startswith("checkip"):
            return 200, (self.ip + "\n").encode()
        codigo, d = self._atender(metodo, ruta, u.query, cuerpo.decode() if cuerpo else "", cabeceras or {})
        return codigo, d if isinstance(d, bytes) else json.dumps(d).encode()

    def _atender(self, metodo, ruta, consulta, cuerpo, cab):
        if ruta == "/api/v3/time":
            return 200, {"serverTime": int(self.ahora() * 1000)}
        if ruta == "/api/v3/klines":
            return 200, self._klines(dict(urllib.parse.parse_qsl(consulta)))
        # todo lo demás va firmado
        clave = next((v for k, v in cab.items() if k.lower() == "x-mbx-apikey"), None)
        if not clave:
            return 400, {"code": -2014, "msg": "API-key format invalid."}
        llave = self.llaves.get(clave)
        if not llave or not llave["pasa"]:
            return 401, {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."}
        crudo = consulta if metodo == "GET" else cuerpo
        mensaje, _sep, firma = crudo.rpartition("&signature=")
        if not firma or not hmac.compare_digest(firma, hmac.new(llave["secreto"].encode(), mensaje.encode(), hashlib.sha256).hexdigest()):
            return 400, {"code": -1022, "msg": "Signature for this request is not valid."}
        q = dict(urllib.parse.parse_qsl(mensaje))
        if abs(int(q.get("timestamp", 0)) / 1000 - self.ahora()) > int(q.get("recvWindow", 5000)) / 1000:
            return 400, {"code": -1021, "msg": "Timestamp for this request is outside of the recvWindow."}
        if ruta == "/sapi/v1/account/apiRestrictions":
            return 200, dict(llave["permisos"])
        if not ruta.startswith(PRED):
            return 404, {"code": -1, "msg": "ruta desconocida"}
        r = ruta[len(PRED):]
        if metodo == "GET":
            if r == "/market/list":
                return 200, self._lista(q)
            if r == "/market/detail":
                return self._detalle(q)
            if r == "/order-book":
                return 200, self._libro(q)
            if r == "/wallet/list":
                return 200, {"wallets": [self.billetera] if self.billetera else []}
            if r == "/balance/payment-options":
                return 200, {"items": [{"accountType": k, "availableBalanceDisplay": f"{v:,.2f}", "enabled": True} for k, v in self.saldo.items()]}
            if r == "/order/list":
                return 200, self._ordenes(True)
            if r == "/order/history":
                return 200, self._ordenes(False)
            if r == "/position/settled-history":
                return 200, self._liquidadas()
            if r == "/redeem/status":
                c = self.cobros.get(q.get("txHash"))
                return 200, {"txHash": q.get("txHash"), "status": c["estado"] if c else "NOT_FOUND"}
        else:
            if r == "/trade/get-quote":
                return self._cotizar(q)
            if r == "/trade/place-order-bundle":
                return self._ordenar(q, llave)
            if r == "/batch-redeem":
                return self._cobrar(q, llave)
        return 404, {"code": -1, "msg": "ruta desconocida"}


def enchufar(C, sim):
    """Deja al módulo de conexión hablando con el simulador: mismo código de firma y de lectura, otro cable y otro reloj."""
    C._pedir = sim.pedir
    C.ahora = sim.ahora
    C.reloj_dudoso = lambda: False
    C._velas.update(t=-1e9, limite=0, dato=None)
    C._claves.update(ruta=None, mtime=None, par=None, tipo=None)


def servir(sim):
    """Sirve el simulador por HTTP en 127.0.0.1 (puerto libre). Devuelve (servidor, puerto, conexiones abiertas)."""
    conexiones = [0]

    class Puerta(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            conexiones[0] += 1
            super().setup()

        def _responder(self, metodo):
            n = int(self.headers.get("Content-Length") or 0)
            cuerpo = self.rfile.read(n) if n else None
            try:
                codigo, datos = sim.pedir(metodo, "http://sim" + self.path, cuerpo, dict(self.headers.items()))
            except SinRespuesta:
                self.close_connection = True
                self.connection.close()
                return
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            self._responder("GET")

        def do_POST(self):
            self._responder("POST")

        def log_message(self, *a):
            pass

    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Puerta)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, servidor.server_address[1], conexiones
