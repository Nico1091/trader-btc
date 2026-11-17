"""Conexión con Binance del operador de la caja (16/11/2026). Solo biblioteca estándar.

Es mesa/conexion.py (la que compró de verdad el 12/11) con estos cambios: busca el mercado de 5 o de 15 minutos, usa la llave
propia de este equipo, deja ver por qué una llave no pasa, mantiene abierta la conexión con Binance (las cinco lecturas de cada
minuto caben así en los 5 s de la regla) y lleva la hora de Binance sobre el reloj monótono, que no salta cuando Android pone
en hora la caja (arranca en 2021). Dos puertas: las velas públicas de contado, que no piden llave, y la API oficial de
predicción de Binance Wallet (/sapi/v1/w3w/wallet/prediction), firmada. Sin llave válida Binance no entrega ni el listado de
mercados ni el libro (-2014 sin llave, -2015 con una llave que no pasa: comprobado el 16/11).

Llaves, en ~/.config/binance/ de este equipo, con «etiqueta=valor» por línea como lectura.txt:
  operar.txt   llave propia de la caja con Lectura y Predicción y nada más (la única con la que se compra)
  lectura.txt  llave de solo lectura (papel con precios reales)
La llave nunca se escribe en registros ni en pantalla. Aquí no hay retiros, transferencias, margen ni futuros: las únicas
escrituras son cotizar, comprar en predicción y cobrar lo ganado, y solo las llama ejecutor.py con su candado.
Toda la red sale por _pedir: las pruebas la cambian por el Binance simulado y lo demás corre tal cual."""
import decimal
import hashlib
import hmac
import http.client
import json
import os
import time
import urllib.parse

BASE = "https://api.binance.com"
PRED = "/sapi/v1/w3w/wallet/prediction"
# El mercado abre y liquida con el precio de CONTADO de Binance (12/11: 12 de 12 aperturas iguales al contado, ±0,01).
CONTADO = "/api/v3/klines?symbol=BTCUSDT&interval=1m"
IP = "https://checkip.amazonaws.com"
CARPETA_LLAVES = os.path.join(os.path.expanduser("~"), ".config", "binance")
ARCHIVOS = (("operar", "operar.txt"), ("lectura", "lectura.txt"))
H = {"User-Agent": "operador-binarias"}
ESTADOS_COMPRADA = ("FILLED", "CLOSED", "COMPLETED", "MATCHED")           # 12/11: las dos compras reales quedaron FILLED
ESTADOS_FALLIDOS = ("FAILED", "CANCELLED", "CANCELED", "EXPIRED", "REJECTED")  # 06/11 y 07/11: FAILED y EXPIRED, sin comprar
_claves = {"ruta": None, "mtime": None, "par": None, "tipo": None}
_sinc = {"srv": None, "mono": 0.0, "local": 0.0, "visto": -1e9, "dudoso": True}
_velas = {"t": -1e9, "limite": 0, "dato": None}
_con = {"c": None, "host": None, "uso": 0.0}


class ErrorBinance(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo, self.mensaje = codigo, mensaje


# ---------------------------------------------------------------- red
def cerrar():
    c = _con["c"]
    _con.update(c=None, host=None)
    if c is not None:
        try:
            c.close()
        except Exception:
            pass


def _pedir(metodo, url, cuerpo=None, cabeceras=None, plazo=15):
    """Una petición: (código HTTP, cuerpo en bytes). Reutiliza la conexión abierta con el mismo servidor. Una consulta (GET)
    se repite una sola vez si la conexión guardada ya estaba cerrada. Una escritura (POST) sale siempre por una conexión
    recién abierta y no se repite nunca: si falla a medias no se sabe si Binance la recibió, y eso lo resuelve el ejecutor."""
    u = urllib.parse.urlsplit(url)
    ruta = u.path + ("?" + u.query if u.query else "")
    for intento in (1, 2):
        c = _con["c"]
        nueva = c is None or _con["host"] != u.netloc or metodo != "GET" or time.monotonic() - _con["uso"] > 50
        if nueva:
            cerrar()
            clase = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
            c = clase(u.netloc, timeout=plazo)
            _con.update(c=c, host=u.netloc)
        try:
            if c.sock is not None:
                c.sock.settimeout(plazo)
            c.request(metodo, ruta, body=cuerpo, headers=cabeceras or {})
            r = c.getresponse()
            datos = r.read()
            _con["uso"] = time.monotonic()
            if r.will_close:
                cerrar()
            return r.status, datos
        except (http.client.HTTPException, OSError):
            cerrar()
            if nueva or intento == 2:
                raise
    raise OSError("sin respuesta")


def _json(codigo, datos):
    try:
        d = json.loads(datos)
    except ValueError:
        raise ErrorBinance(codigo, datos[:200].decode("utf-8", "replace")) from None
    if codigo >= 400 or (isinstance(d, dict) and isinstance(d.get("code"), int) and d["code"] < 0 and "msg" in d):
        raise ErrorBinance(d.get("code", codigo) if isinstance(d, dict) else codigo, d.get("msg", "") if isinstance(d, dict) else str(d)[:200])
    return d


def _json_publico(url, plazo=15):
    return _json(*_pedir("GET", url, None, H, plazo))


# ---------------------------------------------------------------- hora de Binance
def _sincronizar():
    a = time.monotonic()
    servidor = _json_publico(BASE + "/api/v3/time", 8)["serverTime"] / 1000
    b = time.monotonic()
    if b - a < 3:
        _sinc.update(srv=servidor + (b - a) / 2, mono=b, local=time.time(), dudoso=False)


def ahora():
    """Hora de Binance: la del servidor en la última medida más lo que avanzó el reloj monótono desde entonces. Se vuelve a
    medir cada 10 min, y enseguida si el reloj del equipo y el monótono dejan de ir juntos (el equipo cambió su hora o
    estuvo dormido): mientras no se mida de nuevo, reloj_dudoso() es verdadero y el operador no mira ni compra.
    Con más de 10 s de diferencia Binance rechaza toda consulta firmada (-1021)."""
    mono, local = time.monotonic(), time.time()
    if _sinc["srv"] is not None and abs((local - _sinc["local"]) - (mono - _sinc["mono"])) > 2.0:
        _sinc["dudoso"] = True
    if (_sinc["dudoso"] or mono - _sinc["mono"] > 600) and mono - _sinc["visto"] >= (5 if _sinc["dudoso"] else 60):
        _sinc["visto"] = mono
        try:
            _sincronizar()
        except Exception:
            pass
    if _sinc["srv"] is None:
        return local
    return _sinc["srv"] + (time.monotonic() - _sinc["mono"])


def reloj_dudoso():
    return bool(_sinc["dudoso"])


# ---------------------------------------------------------------- llaves
def llave():
    """Qué llave hay en este equipo: «operar», «lectura» o None. Se mira el archivo cada vez: si llega una nueva, se usa sin reiniciar."""
    for tipo, nombre in ARCHIVOS:
        ruta = os.path.join(CARPETA_LLAVES, nombre)
        try:
            mt = os.path.getmtime(ruta)
        except OSError:
            continue
        if _claves["ruta"] != ruta or _claves["mtime"] != mt:
            clave = secreto = None
            try:
                with open(ruta, encoding="utf-8") as f:
                    for linea in f.read().splitlines():
                        etiqueta, igual, valor = linea.strip().partition("=")
                        if not igual:
                            continue
                        if etiqueta.lower().startswith("secret"):
                            secreto = valor.strip()
                        else:
                            clave = valor.strip()
            except OSError:
                continue
            if not clave or not secreto:
                continue
            _claves.update(ruta=ruta, mtime=mt, par=(clave, secreto), tipo=tipo)
        return tipo
    _claves.update(ruta=None, mtime=None, par=None, tipo=None)
    return None


def marca_llave():
    """(tipo, fecha del archivo) de la llave en uso, sin la llave: sirve para saber si la cambiaron."""
    return _claves["tipo"], _claves["mtime"]


def _firmado(metodo, ruta, **params):
    if llave() is None:
        raise ErrorBinance(0, "este equipo no tiene llave")
    clave, secreto = _claves["par"]
    params = {k: v for k, v in params.items() if v is not None}
    params["timestamp"] = int(ahora() * 1000)
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
    return _json(*_pedir(metodo, url, cuerpo, cab, 20))


def restricciones():
    """Los permisos de la llave en uso, tal como los da Binance (solo consulta)."""
    return _firmado("GET", "/sapi/v1/account/apiRestrictions")


def ip_publica(plazo=8):
    """La IP con la que este equipo sale a internet (para decirle cuál poner en la llave cuando Binance responde -2015).
    El módem de la casa tiene UPnP apagado y Binance no la dice: se pregunta afuera, solo en ese caso."""
    try:
        codigo, datos = _pedir("GET", IP, None, H, plazo)
        ip = datos.decode("ascii", "replace").strip()
        return ip if codigo == 200 and 6 < len(ip) < 46 and all(ch in "0123456789abcdefABCDEF.:" for ch in ip) else None
    except Exception:
        return None


# ---------------------------------------------------------------- mercado público
def _fila_vela(k):
    return (int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))


def velas_contado(limite=90, plazo=8):
    """(cerradas, viva) de CONTADO, la fuente con la que liquida el mercado: filas (t, apertura, máximo, mínimo, cierre,
    volumen). El cierre de la viva es el último precio negociado. Una lectura sirve a los dos mercados durante 0,7 s."""
    t = ahora()
    if _velas["dato"] is not None and _velas["limite"] >= limite and 0 <= t - _velas["t"] < 0.7:
        return _velas["dato"]
    x = _json_publico(BASE + CONTADO + f"&limit={limite}", plazo)
    ahora_ms = ahora() * 1000
    cerr, viva = [], None
    for k in x:
        if int(k[6]) < ahora_ms:
            cerr.append(_fila_vela(k))
        else:
            viva = _fila_vela(k)
    _velas.update(t=ahora(), limite=limite, dato=(cerr, viva))
    return cerr, viva


def velas_desde(t_ini, minutos):
    """Velas de contado cerradas desde t_ini (para liquidar con velas cuando no hay llave)."""
    x = _json_publico(BASE + CONTADO + f"&startTime={int(t_ini) * 1000}&limit={int(minutos)}", 10)
    ahora_ms = ahora() * 1000
    return [_fila_vela(k) for k in x if int(k[6]) < ahora_ms]


# ---------------------------------------------------------------- predicción: consultas
def _leer_mercado(topic):
    d = _firmado("GET", PRED + "/market/detail", marketTopicId=topic)
    x = (d.get("markets") or [{}])[0]
    tokens, precio, ganan = {}, {}, []
    for o in x.get("outcomes", []):
        lado = 1 if str(o.get("name")).lower() == "up" else -1
        tokens[lado] = o.get("tokenId")
        precio[lado] = float(o.get("price") or 0)
        if o.get("winner") is True:
            ganan.append(lado)
    # Binance marca los dos resultados como ganadores cuando reparte (empate: 0,5 por contrato a cada lado)
    ganador = 0 if len(ganan) > 1 else (ganan[0] if ganan else None)
    return {"topic": topic, "vendor": d.get("vendor"), "marketId": x.get("marketId"), "abierto": x.get("tradingStatus") == "OPEN",
            "tokens": tokens, "precio": precio, "ganador": ganador, "estado": d.get("status"),
            "strike": float((d.get("variantData") or {}).get("startPrice") or 0) or None,
            "comision_bps": int(d.get("feeRateBps") or 200), "pregunta": d.get("question")}


def lista_mercados(buscados=(), paginas=3):
    """Los mercados «Up or Down» de cripto que Binance publica ahora: lista de (slug, marketTopicId), de los que cierran antes
    a los que cierran después. Pide otra página solo si falta alguno de los buscados."""
    out = []
    for i in range(paginas):
        d = _firmado("GET", PRED + "/market/list", l1Category="crypto", l2Category="up-down", sortBy="END_DATE", orderBy="ASC",
                     offset=100 * i if i else None, limit=100)
        lote = d.get("marketTopics", [])
        out += [(t.get("slug"), t.get("marketTopicId")) for t in lote]
        if len(lote) < 100 or all(any(s == b for s, _ in out) for b in buscados):
            break
    return out


def slug(W, t_ini):
    return f"btc-updown-{W}m-{int(t_ini)}"


def mercado(W, t_ini):
    """El mercado «BTC Up or Down» de W minutos (5 o 15) que empieza en t_ini, o None si Binance todavía no lo publica."""
    buscado = slug(W, t_ini)
    for s, topic in lista_mercados((buscado,)):
        if s == buscado:
            m = _leer_mercado(topic)
            m["t"], m["W"] = int(t_ini), W
            return m
    return None


def releer(m):
    """Vuelve a leer apertura, estado y tokens de un mercado que aún no los traía."""
    x = _leer_mercado(m["topic"])
    for k in ("strike", "abierto", "precio", "estado", "tokens", "marketId", "comision_bps", "vendor"):
        m[k] = x.get(k) or m.get(k)
    return m


def resultado(topic):
    """Ganador oficial de un mercado: 1 (sube), -1 (baja), 0 (empate: Binance paga la mitad a cada lado) o None si aún no
    está resuelto."""
    return _leer_mercado(topic)["ganador"]


def libro_completo(m, lado):
    """El libro del resultado `lado`: (ventas, compras), cada una como lista de (precio, contratos); las ventas de la más
    barata a la más cara y las compras al revés. Lo que yo compro sale de las ventas."""
    d = _firmado("GET", PRED + "/order-book", vendor=m["vendor"], marketId=m["marketId"], tokenId=m["tokens"][lado])
    asks = sorted((float(a["price"]), float(a.get("size") or 0)) for a in d.get("asks", []))
    bids = sorted(((float(a["price"]), float(a.get("size") or 0)) for a in d.get("bids", [])), reverse=True)
    return asks, bids


def leer_libros(m):
    """Deja en el mercado el mejor precio de cada lado (ask y bid), las ventas con sus tamaños (asks) y la hora de Binance en
    que se leyó (libro_t)."""
    m.setdefault("ask", {}), m.setdefault("bid", {}), m.setdefault("asks", {})
    for lado in (1, -1):
        asks, bids = libro_completo(m, lado)
        m["ask"][lado], m["bid"][lado] = (asks[0][0] if asks else None), (bids[0][0] if bids else None)
        m["asks"][lado] = asks[:15]
    m["libro_t"] = ahora()
    return m


def billetera():
    """La billetera de predicción de la cuenta, o None si no existe."""
    w = _firmado("GET", PRED + "/wallet/list").get("wallets", [])
    return w[0] if w else None


def saldos():
    """Saldo disponible por cuenta: SPOT, FUNDING y CeDeFi (la billetera de predicción, MPC)."""
    return {i.get("accountType"): float(str(i.get("availableBalanceDisplay") or 0).replace(",", ""))
            for i in _firmado("GET", PRED + "/balance/payment-options").get("items", [])}


def ordenes(direccion, limite=30):
    """Las órdenes recientes de la billetera como las da Binance: (abiertas, cerradas). /order/list trae las que siguen
    vivas y /order/history las que ya terminaron."""
    abiertas = _firmado("GET", PRED + "/order/list", walletAddress=direccion, limit=limite).get("orders", [])
    cerradas = _firmado("GET", PRED + "/order/history", walletAddress=direccion, limit=limite).get("orders", [])
    return abiertas, cerradas


def orden(direccion, id_orden):
    """La orden tal como quedó en Binance, con «_cerrada» verdadero si ya figura en el historial; None si aún no aparece."""
    abiertas, cerradas = ordenes(direccion)
    for cerrada, lote in ((True, cerradas), (False, abiertas)):
        for o in lote:
            if str(o.get("orderId")) == str(id_orden):
                return {**o, "_cerrada": cerrada}
    return None


def liquidadas(direccion, limite=50):
    """Posiciones de mercados ya resueltos, con isWinner, redeemStatus, claimAmount y positionStatus (CLAIMED si ya se cobró)."""
    return _firmado("GET", PRED + "/position/settled-history", walletAddress=direccion, limit=limite).get("positions", [])


def estado_cobro(direccion, tx):
    """Cómo va un cobro ya pedido: PENDING, CONFIRMED, FAILED o NOT_FOUND."""
    return _firmado("GET", PRED + "/redeem/status", walletAddress=direccion, txHash=tx).get("status")


def _wei(usdt):
    return str(int(decimal.Decimal(str(usdt)) * 10 ** 18))


# ---------------------------------------------------------------- predicción: escrituras (solo las llama ejecutor.py)
def cotizar(direccion, token, usdt, deslizamiento, fuente):
    """Pide precio para comprar `usdt` de un lado. No compra nada: la orden es otra llamada."""
    return _firmado("POST", PRED + "/trade/get-quote", walletAddress=direccion, tokenId=token, side="BUY", amountIn=_wei(usdt),
                    orderType="MARKET", slippageBps=deslizamiento, fundingSource=fuente)


def ordenar(direccion, id_billetera, id_cotizacion, deslizamiento, fuente):
    return _firmado("POST", PRED + "/trade/place-order-bundle", walletAddress=direccion, walletId=id_billetera, quoteId=id_cotizacion,
                    timeInForce="FOK", accountType="SPOT", orderType="MARKET", slippageBps=deslizamiento, fundingSource=fuente)


def cobrar(direccion, id_billetera, token):
    """Reclama lo ganado de UN resultado ya liquidado (documentación oficial: tokenIds es una lista repetible; con un solo
    token por llamada no hay duda de cómo se escribe). Devuelve lote, tx, estado y error del pedido.
    Sin probar todavía con una posición real."""
    d = _firmado("POST", PRED + "/batch-redeem", walletAddress=direccion, walletId=id_billetera, tokenIds=token)
    r = (d.get("results") or [{}])[0]
    return {"lote": d.get("batchId"), "tx": r.get("txHash"), "estado": r.get("status"), "error": r.get("error")}
