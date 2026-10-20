"""Cliente de Binance: contado y futuros, red de pruebas y real, con candado de dinero real.

Riesgos operativos que este módulo cierra:
- Confundir pruebas con real: cada entorno sabe si mueve dinero; los reales exigen el
  archivo AUTORIZO-DINERO-REAL.txt con la fecha de hoy (hora de Colombia), que solo
  escribe Nicolás.
- Órdenes duplicadas: las órdenes llevan identificador propio y NO se reintentan a ciegas;
  si la red falla después de enviar, se consulta por ese identificador antes de nada.
- Reloj desfasado (error -1021): se mide el desfase con el servidor y se corrige.
- Cantidades inválidas: se redondean con Decimal a los filtros del par (LOT_SIZE,
  PRICE_FILTER, NOTIONAL) antes de enviar.
- Las claves se leen en tiempo de ejecución y nunca se escriben en registros.
"""
import datetime as _dt
import hashlib
import hmac
import json
import os
import time
import urllib.parse
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from zoneinfo import ZoneInfo

from red import Cliente, ErrorRed, Rechazo

BOGOTA = ZoneInfo("America/Bogota")
CARPETA = os.path.dirname(os.path.abspath(__file__))
AUTORIZACION = os.path.join(CARPETA, "AUTORIZO-DINERO-REAL.txt")

ENTORNOS = {
    # nombre: (base REST, prefijo de API, mueve dinero real; None = solo datos públicos, sin claves)
    "testnet_contado": ("https://testnet.binance.vision", "/api/v3", False),
    "demo_futuros": ("https://demo-fapi.binance.com", "/fapi/v1", False),
    "real_contado": ("https://api.binance.com", "/api/v3", True),
    "real_futuros": ("https://fapi.binance.com", "/fapi/v1", True),
    "datos_contado": ("https://data-api.binance.vision", "/api/v3", None),
    "datos_futuros": ("https://fapi.binance.com", "/fapi/v1", None),
}


class DineroRealBloqueado(PermissionError):
    pass


def autorizado_dinero_real():
    """True solo si existe AUTORIZO-DINERO-REAL.txt con 'AUTORIZO' y la fecha de hoy en Bogotá."""
    try:
        with open(AUTORIZACION, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return False
    hoy = _dt.datetime.now(BOGOTA).strftime("%Y-%m-%d")
    return "AUTORIZO" in texto.upper() and hoy in texto


def leer_claves(ruta):
    """Lee BINANCE_API_KEY y BINANCE_API_SECRET de un archivo KEY=VALOR. No imprime nada."""
    valores = {}
    with open(ruta, encoding="utf-8-sig") as f:      # el Bloc de notas puede guardar con BOM
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    clave = valores.get("BINANCE_API_KEY", "")
    secreto = valores.get("BINANCE_API_SECRET", "")
    if len(clave) < 32 or len(secreto) < 32:
        raise ValueError(f"no hay clave/secreto válidos en {os.path.basename(ruta)}")
    return clave, secreto


def _decimal(x):
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _texto(d):
    t = format(d.normalize(), "f")
    return t if "." not in t else t.rstrip("0").rstrip(".") or "0"


class Filtros:
    """Reglas del par según exchangeInfo."""

    def __init__(self, info):
        self.simbolo = info["symbol"]
        self.paso_cantidad = Decimal("0")
        self.cantidad_min = Decimal("0")
        self.paso_precio = Decimal("0")
        self.nocional_min = Decimal("0")
        for f in info["filters"]:
            t = f["filterType"]
            if t == "LOT_SIZE":
                self.paso_cantidad = Decimal(f["stepSize"])
                self.cantidad_min = Decimal(f["minQty"])
            elif t == "PRICE_FILTER":
                self.paso_precio = Decimal(f["tickSize"])
            elif t in ("NOTIONAL", "MIN_NOTIONAL"):
                self.nocional_min = Decimal(f.get("minNotional") or f.get("notional") or "0")

    def cantidad(self, q, arriba=False):
        q = _decimal(q)
        pasos = (q / self.paso_cantidad).to_integral_value(ROUND_UP if arriba else ROUND_DOWN)
        return pasos * self.paso_cantidad

    def precio(self, p, arriba=False):
        p = _decimal(p)
        pasos = (p / self.paso_precio).to_integral_value(ROUND_UP if arriba else ROUND_DOWN)
        return pasos * self.paso_precio

    def valida(self, cantidad, precio):
        cantidad, precio = _decimal(cantidad), _decimal(precio)
        if cantidad < self.cantidad_min:
            return f"cantidad {cantidad} menor que el mínimo {self.cantidad_min}"
        if cantidad * precio < self.nocional_min:
            return f"valor {cantidad * precio:.4f} menor que el mínimo {self.nocional_min}"
        return None


class Binance:
    def __init__(self, entorno, clave=None, secreto=None, plazo=15):
        if entorno not in ENTORNOS:
            raise ValueError(f"entorno desconocido: {entorno}")
        self.entorno = entorno
        self.base, self.prefijo, self.real = ENTORNOS[entorno]
        if self.real is None and (clave or secreto):
            raise ValueError(f"{entorno} es solo de datos públicos: no admite claves")
        if self.real and not autorizado_dinero_real():
            raise DineroRealBloqueado(
                "Entorno de dinero real bloqueado: falta AUTORIZO-DINERO-REAL.txt con la fecha de hoy.")
        self._clave = clave
        self._secreto = secreto.encode() if secreto else None
        self.red = Cliente("directo", plazo=plazo, reintentos=3, etiqueta=f"binance-{entorno}")
        # Las órdenes no se reintentan a ciegas: un solo intento y se consulta después.
        self.red_ordenes = Cliente("directo", plazo=plazo, reintentos=1, etiqueta=f"ordenes-{entorno}")
        self.desfase_ms = 0
        self._ultima_sincronia = 0.0
        self._filtros = {}

    # ---------- tiempo y firma ----------
    def sincronizar_reloj(self):
        antes = time.time() * 1000
        datos = self.publico("time")
        despues = time.time() * 1000
        self.desfase_ms = int(datos["serverTime"] - (antes + despues) / 2)
        self._ultima_sincronia = time.time()
        return self.desfase_ms

    def _firmar(self, params):
        if not self._clave:
            raise PermissionError("este cliente no tiene clave: solo datos públicos")
        if time.time() - self._ultima_sincronia > 600:
            self.sincronizar_reloj()
        p = dict(params or {})
        p["timestamp"] = int(time.time() * 1000) + self.desfase_ms
        p.setdefault("recvWindow", 5000)
        consulta = urllib.parse.urlencode(p)
        firma = hmac.new(self._secreto, consulta.encode(), hashlib.sha256).hexdigest()
        return consulta + "&signature=" + firma

    def _url(self, ruta):
        if ruta.startswith("/"):
            return self.base + ruta
        return f"{self.base}{self.prefijo}/{ruta}"

    # ---------- llamadas ----------
    def publico(self, ruta, params=None):
        return self.red.json(self._url(ruta), params)

    def privado(self, metodo, ruta, params=None, orden=False):
        red = self.red_ordenes if orden else self.red
        for intento in range(2):
            consulta = self._firmar(params)
            cab = {"X-MBX-APIKEY": self._clave}
            try:
                if metodo == "GET":
                    _, _, datos = red.pedir("GET", self._url(ruta) + "?" + consulta, cab)
                else:
                    cab["Content-Type"] = "application/x-www-form-urlencoded"
                    _, _, datos = red.pedir(metodo, self._url(ruta), cab, consulta.encode())
                return json.loads(datos)
            except Rechazo as e:
                try:
                    codigo = json.loads(e.cuerpo).get("code")
                except (ValueError, AttributeError):
                    codigo = None
                if codigo == -1021 and intento == 0:      # reloj fuera de ventana: resincronizar y repetir
                    self.sincronizar_reloj()
                    continue
                raise

    # ---------- mercado ----------
    def filtros(self, simbolo):
        if simbolo not in self._filtros:
            info = self.publico("exchangeInfo", {"symbol": simbolo})
            self._filtros[simbolo] = Filtros(info["symbols"][0])
        return self._filtros[simbolo]

    def precio(self, simbolo):
        return Decimal(self.publico("ticker/price", {"symbol": simbolo})["price"])

    def libro_tope(self, simbolo):
        d = self.publico("ticker/bookTicker", {"symbol": simbolo})
        return Decimal(d["bidPrice"]), Decimal(d["askPrice"])

    # ---------- cuenta ----------
    def cuenta(self):
        return self.privado("GET", "account", {"omitZeroBalances": "true"})

    def saldos(self):
        return {b["asset"]: (Decimal(b["free"]), Decimal(b["locked"])) for b in self.cuenta()["balances"]}

    def comisiones(self, simbolo):
        return self.privado("GET", "account/commission", {"symbol": simbolo})

    def ordenes_abiertas(self, simbolo):
        return self.privado("GET", "openOrders", {"symbol": simbolo})

    def consultar(self, simbolo, id_propio):
        return self.privado("GET", "order", {"symbol": simbolo, "origClientOrderId": id_propio})

    # ---------- órdenes ----------
    @staticmethod
    def nuevo_id(prefijo="nab"):
        return f"{prefijo}-{int(time.time() * 1000)}-{os.urandom(3).hex()}"

    def _orden(self, ruta, params):
        """Envía una orden una sola vez. Si la red falla tras enviar, averigua si entró."""
        try:
            return self.privado("POST", ruta, params, orden=True)
        except ErrorRed as e:
            if isinstance(e, Rechazo):
                raise
            id_propio = params.get("newClientOrderId") or params.get("listClientOrderId")
            time.sleep(1.5)
            try:
                if ruta == "order":
                    return self.consultar(params["symbol"], id_propio)
            except Rechazo:
                pass
            raise ErrorRed(f"estado de la orden {id_propio} desconocido tras fallo de red: revisar a mano") from e

    def probar_orden(self, simbolo, lado, cantidad, precio):
        """Valida una orden en el servidor sin crearla (POST order/test)."""
        f = self.filtros(simbolo)
        params = {"symbol": simbolo, "side": lado, "type": "LIMIT", "timeInForce": "GTC",
                  "quantity": _texto(f.cantidad(cantidad)), "price": _texto(f.precio(precio))}
        return self.privado("POST", "order/test", params, orden=True)

    def limite(self, simbolo, lado, cantidad, precio, solo_creador=True):
        f = self.filtros(simbolo)
        q, p = f.cantidad(cantidad), f.precio(precio, arriba=(lado == "SELL"))
        error = f.valida(q, p)
        if error:
            raise ValueError(error)
        params = {"symbol": simbolo, "side": lado, "quantity": _texto(q), "price": _texto(p),
                  "newClientOrderId": self.nuevo_id(), "newOrderRespType": "FULL"}
        if solo_creador:
            params["type"] = "LIMIT_MAKER"            # se rechaza si fuese a cruzar: comisión de creador
        else:
            params.update({"type": "LIMIT", "timeInForce": "GTC"})
        return self._orden("order", params)

    def mercado(self, simbolo, lado, cantidad=None, cotizado=None):
        f = self.filtros(simbolo)
        params = {"symbol": simbolo, "side": lado, "type": "MARKET",
                  "newClientOrderId": self.nuevo_id(), "newOrderRespType": "FULL"}
        if cotizado is not None:
            params["quoteOrderQty"] = _texto(_decimal(cotizado).quantize(Decimal("0.01"), ROUND_DOWN))
        else:
            params["quantity"] = _texto(f.cantidad(cantidad))
        return self._orden("order", params)

    def oco_venta(self, simbolo, cantidad, toma_ganancia, disparo_perdida, limite_perdida=None):
        """Protege una compra en el propio servidor: si el portátil se apaga, el stop sigue vivo."""
        f = self.filtros(simbolo)
        params = {"symbol": simbolo, "side": "SELL", "quantity": _texto(f.cantidad(cantidad)),
                  "aboveType": "LIMIT_MAKER", "abovePrice": _texto(f.precio(toma_ganancia, arriba=True)),
                  "belowStopPrice": _texto(f.precio(disparo_perdida)),
                  "listClientOrderId": self.nuevo_id("oco"), "newOrderRespType": "FULL"}
        if limite_perdida is None:
            params["belowType"] = "STOP_LOSS"
        else:
            params.update({"belowType": "STOP_LOSS_LIMIT", "belowTimeInForce": "GTC",
                           "belowPrice": _texto(f.precio(limite_perdida))})
        return self._orden("orderList/oco", params)

    def cancelar(self, simbolo, id_propio):
        return self.privado("DELETE", "order", {"symbol": simbolo, "origClientOrderId": id_propio}, orden=True)

    def cancelar_oco(self, simbolo, id_lista):
        return self.privado("DELETE", "orderList", {"symbol": simbolo, "listClientOrderId": id_lista}, orden=True)

    def cancelar_todo(self, simbolo):
        return self.privado("DELETE", "openOrders", {"symbol": simbolo}, orden=True)
