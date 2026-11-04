"""Conexión con Binance para la Mesa de binarias (04/11/2026). Solo biblioteca estándar.

Dos puertas: las velas e interés abierto públicos de futuros (los mismos del centinela) y la API oficial de predicción de
Binance Wallet (https://developers.binance.com/en/docs/catalog/web3-wallet-prediction-trading/api/rest-api/).
La clave se lee al ejecutar desde ~/.config/binance/lectura.txt y nunca se escribe en registros ni en pantalla.
Aquí no hay retiros, margen ni futuros: las únicas escrituras son comprar en predicción, cancelar y cobrar lo ganado.
"""
import decimal
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.binance.com"
PRED = "/sapi/v1/w3w/wallet/prediction"
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m"
FOI = "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=12"
CLAVES = os.path.join(os.path.expanduser("~"), ".config", "binance", "lectura.txt")
H = {"User-Agent": "mesa-binarias"}
_claves = None


class ErrorBinance(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo, self.mensaje = codigo, mensaje


def _leer_claves():
    """El archivo lleva «etiqueta=valor» por línea; la que empieza por «secret» es el secreto, en cualquier orden."""
    global _claves
    if _claves is None:
        clave = secreto = None
        with open(CLAVES, encoding="utf-8") as f:
            for linea in f.read().splitlines():
                etiqueta, igual, valor = linea.strip().partition("=")
                if not igual:
                    continue
                if etiqueta.lower().startswith("secret"):
                    secreto = valor.strip()
                else:
                    clave = valor.strip()
        if not clave or not secreto:
            raise ErrorBinance(0, "no encuentro la clave y el secreto en lectura.txt")
        _claves = (clave, secreto)
    return _claves


def _json_publico(url, plazo=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=plazo) as r:
        return json.loads(r.read())


def _firmado(metodo, ruta, **params):
    clave, secreto = _leer_claves()
    params = {k: v for k, v in params.items() if v is not None}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    q = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)  # quote_plus cambia los espacios y daña la firma
    firma = hmac.new(secreto.encode(), q.encode(), hashlib.sha256).hexdigest()
    url, cuerpo = BASE + ruta, None
    cab = {**H, "X-MBX-APIKEY": clave}
    if metodo == "GET":
        url += f"?{q}&signature={firma}"
    else:
        cuerpo = f"{q}&signature={firma}".encode()
        cab["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo, headers=cab, method=metodo), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        texto = e.read()[:300].decode("utf-8", "replace")
        try:
            d = json.loads(texto)
            raise ErrorBinance(d.get("code", e.code), d.get("msg", texto)) from None
        except ValueError:
            raise ErrorBinance(e.code, texto) from None


# ---------------------------------------------------------------- mercado público (lo mismo que mira el centinela)
def velas(limite=170, desde_ms=None):
    """(cerradas, viva): velas de 1 min de futuros como (t, apertura, máximo, mínimo, cierre)."""
    x = _json_publico(FAPI + f"&limit={limite}" + (f"&startTime={desde_ms}" if desde_ms else ""))
    ahora = time.time() * 1000
    cerr, viva = [], None
    for k in x:
        v = (int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        if int(k[6]) < ahora:
            cerr.append(v)
        else:
            viva = v
    return cerr, viva


def historial(dias):
    out, desde = [], int((time.time() - dias * 86400) * 1000)
    while True:
        x, _ = velas(1500, desde)
        if not x:
            break
        out += x
        desde = (x[-1][0] + 60) * 1000
        if len(x) < 1400:
            break
    return sorted({v[0]: v for v in out}.values())


def cambio_interes(t_dec):
    """Igual que semaforo.cambio_interes: instantánea con hora <= t_dec - 300 frente a la de <= t_dec - 1200."""
    x = _json_publico(FOI)
    pts = sorted((int(k["timestamp"]) // 1000, float(k["sumOpenInterest"])) for k in x)
    a = [p for p in pts if p[0] <= t_dec - 300]
    b = [p for p in pts if p[0] <= t_dec - 1200]
    if not a or not b or t_dec - 300 - a[-1][0] > 600 or t_dec - 1200 - b[-1][0] > 600 or b[-1][1] <= 0:
        return None
    return a[-1][1] / b[-1][1] - 1


# ---------------------------------------------------------------- predicción: consultas
def _leer_mercado(topic):
    d = _firmado("GET", PRED + "/market/detail", marketTopicId=topic)
    x = (d.get("markets") or [{}])[0]
    tokens, ganador, precio = {}, None, {}
    for o in x.get("outcomes", []):
        lado = 1 if str(o.get("name")).lower() == "up" else -1
        tokens[lado] = o.get("tokenId")
        precio[lado] = float(o.get("price") or 0)
        if o.get("winner") is True:
            ganador = lado
    return {"topic": topic, "vendor": d.get("vendor"), "marketId": x.get("marketId"), "abierto": x.get("tradingStatus") == "OPEN",
            "tokens": tokens, "precio": precio, "ganador": ganador, "estado": d.get("status"),
            "strike": float((d.get("variantData") or {}).get("startPrice") or 0) or None,
            "comision_bps": int(d.get("feeRateBps") or 200), "pregunta": d.get("question")}


def mercado_15m(t_ini):
    """El mercado «BTC Up or Down» de 15 min que empieza en t_ini, o None si Binance todavía no lo publica."""
    slug = f"btc-updown-15m-{t_ini}"
    d = _firmado("GET", PRED + "/market/list", l1Category="crypto", l2Category="up-down", sortBy="END_DATE", orderBy="ASC", limit=100)
    for t in d.get("marketTopics", []):
        if t.get("slug") == slug:
            m = _leer_mercado(t["marketTopicId"])
            m["t"] = t_ini
            return m
    return None


def resultado(topic):
    """Ganador oficial de un mercado: 1, -1 o None si aún no está resuelto."""
    return _leer_mercado(topic)["ganador"]


def libro(m, lado):
    """(mejor compra para mí = ask, mejor venta = bid) del resultado `lado`."""
    d = _firmado("GET", PRED + "/order-book", vendor=m["vendor"], marketId=m["marketId"], tokenId=m["tokens"][lado])
    asks = sorted(float(a["price"]) for a in d.get("asks", []))
    bids = sorted((float(a["price"]) for a in d.get("bids", [])), reverse=True)
    return (asks[0] if asks else None), (bids[0] if bids else None)


def billetera():
    """La billetera de predicción de su cuenta, o None si aún no la ha creado en la app."""
    w = _firmado("GET", PRED + "/wallet/list").get("wallets", [])
    return w[0] if w else None


def saldo_spot():
    for i in _firmado("GET", PRED + "/balance/payment-options").get("items", []):
        if i.get("accountType") == "SPOT":
            return float(str(i.get("availableBalanceDisplay") or 0).replace(",", ""))
    return 0.0


def posiciones(direccion):
    return _firmado("GET", PRED + "/position/list", walletAddress=direccion, limit=100)


def _wei(usdt):
    return str(int(decimal.Decimal(str(usdt)) * 10 ** 18))


# ---------------------------------------------------------------- predicción: escrituras (solo por su toque)
def cotizar(direccion, token, usdt, deslizamiento, fuente):
    return _firmado("POST", PRED + "/trade/get-quote", walletAddress=direccion, tokenId=token, side="BUY", amountIn=_wei(usdt),
                    orderType="MARKET", slippageBps=deslizamiento, fundingSource=fuente)


def ordenar(direccion, id_billetera, id_cotizacion, deslizamiento, fuente):
    return _firmado("POST", PRED + "/trade/place-order-bundle", walletAddress=direccion, walletId=id_billetera, quoteId=id_cotizacion,
                    timeInForce="FOK", accountType="SPOT", orderType="MARKET", slippageBps=deslizamiento, fundingSource=fuente)


def cobrar(direccion, id_billetera, tokens):
    """Reclama lo ganado de mercados ya liquidados. Sin probar con una posición real: la API pide una lista en tokenIds."""
    return _firmado("POST", PRED + "/batch-redeem", walletAddress=direccion, walletId=id_billetera, tokenIds=",".join(tokens))
