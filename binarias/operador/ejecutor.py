"""Ejecutor del operador (16/11/2026): lo único que toca dinero. Tres escrituras y nada más (cotizar, comprar en predicción y
cobrar lo ganado), todas por la API oficial de Binance Wallet. Sin IA: aplica la regla y sus frenos tal como quedaron en la
enmienda 2 de REGLAS-ANTES-DE-MEDIR.md.

El candado, completo, antes de cada compra:
  1. El archivo ARMADO en la carpeta del operador, que solo se crea por orden del dueño. Sin él no hay orden real.
  2. La llave propia de este equipo (operar.txt), restringida por IP y sin retiros, transferencias, margen ni futuros.
  3. Una orden por mercado. Un mercado con una orden que Binance no haya rechazado con claridad queda cerrado.
  4. Importe del libro B sobre el saldo real de la billetera de predicción: una cuarta parte del Kelly prudente, tope del
     16 % del saldo, sin pasar de lo que ofrece el libro, mínimo 2 USDT. Sin apalancamiento: solo se paga con lo que hay ahí.
  5. Freno del día: lo perdido en el día de Colombia, contando como perdido lo que sigue abierto, no pasa del 16 % del saldo
     con que empezó el día. Tope de 20 órdenes por día.
  6. Cotización real antes de enviar: si el precio medio cotizado no deja la ganancia esperada prudente en el margen, no envía.
  7. (17/11/2026, aprobador) Una decisión de Claude «COMPRAR» vigente del nodo de este equipo para ese mercado y ese sentido
     (aprobacion.py). Sin ella, con «NO COMPRAR» o sin respuesta, no hay orden real. El papel no cambia.
Después: una orden es «comprada» solo si Binance lo confirma; cualquier estado que no sea final se relee hasta que lo sea,
también tras un reinicio (el 12/11 dos órdenes quedaron en SUBMITTED sin releer). Lo ganado se cobra y se anota.
Nada aquí duerme ni repite una escritura: cada paso() avanza lo que toque y devuelve el control."""
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import nucleo as N  # noqa: E402
from comunes import con_signo, dia, escribir_json, hora, leer_json, num, pct, sentido  # noqa: E402
import aprobacion as APROBACION  # noqa: E402  (17/11/2026: candado del aprobador)

DESLIZAMIENTO_BPS = 200      # el de la Mesa en las compras reales del 12/11
FUENTE = "MPC"               # la billetera de predicción; pagando desde spot Binance no compra (07/11)
TOPE_ORDENES_DIA = 20
FRENO_DIA = 0.16
INTENTOS_MERCADO = 2         # como mucho dos envíos en un mismo mercado, y el segundo solo tras un rechazo claro
INTENTOS_COBRO = 3
ACLARAR_S = 120              # una orden sin respuesta se busca en Binance este tiempo antes de darla por no llegada
SIN_CIERRE_S = 86400
SIN_RESULTADO_S = 172800
LLAVE_MALA = (-2015, -2014, -2008, -1022)
# estados que cierran una orden, tal como los nombra Binance (12/11: FILLED en las dos compras; 06 y 07/11: FAILED y EXPIRED)
N_COMPRADA = ("FILLED", "CLOSED", "COMPLETED", "MATCHED")
N_FALLIDOS = ("FAILED", "CANCELLED", "CANCELED", "EXPIRED", "REJECTED")
PROHIBIDOS = {"enableWithdrawals": "retiros", "enableInternalTransfer": "transferencias internas",
              "permitsUniversalTransfer": "transferencia universal", "enableMargin": "margen", "enableFutures": "futuros",
              "enableVanillaOptions": "opciones", "enablePortfolioMarginTrading": "margen de cartera"}


def texto_error(ex):
    return f"{type(ex).__name__}: {str(ex)[:140]}"


class Ejecutor:
    def __init__(self, C, fila, log, avisar, carpeta=AQUI, datos=None):
        self.C, self.fila, self.log, self.avisar = C, fila, log, avisar
        self.carpeta = carpeta
        self.datos = datos or os.path.join(carpeta, "datos")
        self.ruta = os.path.join(self.datos, "ordenes.json")
        d = leer_json(self.ruta, {}) or {}
        self.ordenes, self.dias = d.get("ordenes", []), d.get("dias", {})
        self.billetera, self.saldo, self.saldos, self.t_cuenta = None, None, {}, -1e9
        self.permisos = {"llave": None, "ok": False, "motivo": "sin revisar", "t": -1e9, "notas": []}
        self.t_error = -1e9
        cambio = False
        for o in self.ordenes:  # se apagó entre anotar la orden y saber si Binance la recibió: hay que aclararla
            if o["estado"] == "POR ENVIAR":
                o["estado"], cambio = "DUDOSA", True
        if cambio:
            self._guardar()

    # ------------------------------------------------------------ archivos e interruptor
    def _guardar(self):
        os.makedirs(self.datos, exist_ok=True)
        escribir_json(self.ruta, {"ordenes": self.ordenes, "dias": self.dias})

    def ruta_armado(self):
        return os.path.join(self.carpeta, "ARMADO")

    def armado(self, W=None):
        """El interruptor del dinero real. None si el archivo no existe; si existe, sus datos (un archivo vacío arma los dos
        mercados). Con W, solo si cubre ese mercado."""
        ruta = self.ruta_armado()
        if not os.path.exists(ruta):
            return None
        d = leer_json(ruta, None)
        if not isinstance(d, dict):
            d = {}
        mercados = d.get("mercados")
        if not isinstance(mercados, list):
            mercados = list(N.VENTANAS)
        d["mercados"] = [w for w in N.VENTANAS if w in mercados]
        if W is not None and W not in d["mercados"]:
            return None
        return d

    def armar(self, ahora, mercados, por, apto, nota=""):
        """Crea el interruptor. Solo se llama por orden del dueño; quién, cuándo y con qué cifras queda dentro del archivo."""
        d = {"hora": round(ahora), "cuando": hora(ahora, "%d/%m/%Y %H:%M"), "mercados": [w for w in N.VENTANAS if w in mercados],
             "por": por, "apto": apto, "nota": nota}
        escribir_json(self.ruta_armado(), d)
        self.fila({"tipo": "armado", "hora": round(ahora, 2), **d})
        self.log(f"ARMADO por {por}: mercados {d['mercados']}; apto {apto}")
        return d

    def desarmar(self, ahora, por):
        ruta = self.ruta_armado()
        if not os.path.exists(ruta):
            return False
        os.remove(ruta)
        self.fila({"tipo": "desarmado", "hora": round(ahora, 2), "por": por})
        self.log(f"desarmado por {por}")
        return True

    # ------------------------------------------------------------ cuenta y llave
    def cuenta(self, ahora, forzar=False):
        """Lee la billetera y el saldo de predicción (cada minuto, o ya mismo si se va a comprar). Mientras no haya salido la
        primera orden del día, el saldo con que empieza el día es el que haya: así cuenta lo que usted pase a media mañana."""
        if not forzar and ahora - self.t_cuenta < 60:
            return self.saldo is not None and self.billetera is not None
        self.t_cuenta = ahora
        self.billetera = self.C.billetera()
        self.saldos = self.C.saldos()
        self.saldo = float(self.saldos.get("CeDeFi", 0.0))
        d = self.dias.setdefault(dia(ahora), {"saldo_inicial": self.saldo, "fijo": False})
        if not d["fijo"] and d["saldo_inicial"] != self.saldo:
            d["saldo_inicial"] = self.saldo
        for viejo in sorted(self.dias)[:-40]:
            del self.dias[viejo]
        return self.billetera is not None

    def revisar_llave(self, ahora):
        """(pasa, motivo). La llave de operar debe estar restringida por IP y no traer nada de lo prohibido. Se revisa al
        verla, cuando cambia el archivo y cada hora."""
        marca = self.C.marca_llave()
        p = self.permisos
        if p["llave"] == marca and ahora - p["t"] < 3600:
            return p["ok"], p["motivo"]
        r = self.C.restricciones()
        malos = [nombre for campo, nombre in PROHIBIDOS.items() if r.get(campo)]
        if malos:
            ok, motivo = False, "la llave trae permisos de más (" + ", ".join(malos) + "): quítelos en Gestión de API"
        elif not r.get("ipRestrict"):
            ok, motivo = False, "la llave no está restringida a una IP: restrínjala en Gestión de API"
        else:
            ok, motivo = True, "restringida por IP y sin retiros, transferencias, margen ni futuros"
        notas = ["trae además compraventa de contado"] if r.get("enableSpotAndMarginTrading") else []
        self.permisos = {"llave": marca, "ok": ok, "motivo": motivo, "t": ahora, "notas": notas}
        self.log(f"llave de operar revisada: {motivo}" + (f" ({notas[0]})" if notas else ""))
        return ok, motivo

    # ------------------------------------------------------------ cuentas del día
    @staticmethod
    def limpia(o):
        """Binance dijo que no con claridad y no se compró nada: no cuenta como la orden de ese mercado."""
        return bool(o["final"] and not o["comprado"] and (o["estado"] == "RECHAZADA" or o["estado"] in N_FALLIDOS))

    def de_hoy(self, ahora):
        d = dia(ahora)
        return [o for o in self.ordenes if o["dia"] == d]

    def perdido_hoy(self, ahora):
        """Lo perdido hoy en el peor caso: lo ya liquidado por su neto (lo ganado resta) y lo que sigue abierto, entero."""
        x = 0.0
        for o in self.de_hoy(ahora):
            if o.get("res") in (0, 1, 2):
                x -= o["neto"]
            elif o["final"]:
                x += o["comprado"]
            else:
                x += o["usdt"]
        return x

    def cupo_hoy(self, ahora):
        """USDT que aún se pueden arriesgar hoy sin pasar el freno."""
        d = self.dias.get(dia(ahora))
        if not d:
            return 0.0
        return FRENO_DIA * d["saldo_inicial"] - self.perdido_hoy(ahora)

    # ------------------------------------------------------------ compra
    def _no(self, base, motivo):
        self.fila({**base, "enviada": False, "motivo": motivo})
        self.log(f"real de {base['W']} min: no envía ({motivo})")
        return None

    def _frenos(self, ahora, m, W):
        """El primer freno que no deja comprar, o None si puede seguir."""
        if os.path.exists(os.path.join(self.carpeta, "PARAR")):
            return "hay un archivo PARAR"
        if self.C.llave() != "operar":
            return "la llave de este equipo no es la de operar"
        try:
            ok, motivo = self.revisar_llave(ahora)
        except Exception as ex:
            return f"no pude leer los permisos de la llave ({texto_error(ex)})"
        if not ok:
            return motivo
        if m.get("sintetico") or not (m.get("tokens") or {}).get(1) or not m.get("topic"):
            return "sin mercado de Binance"
        if not m.get("abierto"):
            return "el mercado no figura abierto"
        if any(not o["final"] and o["estado"] in ("POR ENVIAR", "DUDOSA") for o in self.ordenes[-40:]):
            return "hay una orden sin aclarar"
        del_mercado = [o for o in self.ordenes[-60:] if o["W"] == W and o["t"] == m["t"]]
        if any(not self.limpia(o) for o in del_mercado):
            return "ya hay una orden en este mercado"
        if len(del_mercado) >= INTENTOS_MERCADO:
            return "Binance ya rechazó dos órdenes en este mercado"
        if len(self.de_hoy(ahora)) >= TOPE_ORDENES_DIA:
            return "tope de 20 órdenes del día"
        return None

    def intentar(self, ahora, m, cand):
        """Una mirada del papel dio candidato. Con todo el candado puesto, cotiza y compra. Devuelve la orden o None."""
        W, lado = cand["W"], cand["lado"]
        if cand.get("sombra") or not self.armado(W):
            return None
        d, pol = cand["vec"]["lados"][lado], cand["pol"]
        com = (m.get("comision_bps") or 200) / 10000
        base = {"tipo": "orden", "W": W, "t": m["t"], "topic": m.get("topic"), "m": cand["m"], "plazo": N.plazo(W, cand["m"]),
                "lado": lado, "papel": d["papel"], "celda": cand["celda"], "p": round(d["p"], 6), "p_prud": round(d["p_prud"], 6),
                "q_libro": d["q"], "G_prud": round(d["G_prud"], 6), "hora": round(ahora, 2), "comision": com}
        motivo = self._frenos(ahora, m, W) or APROBACION.falta(W, m["t"], lado, ahora)  # 17/11: Claude aprueba o no
        if motivo:
            return self._no(base, motivo)
        try:
            if not self.cuenta(ahora, forzar=True):
                return self._no(base, "la cuenta no tiene billetera de predicción")
        except Exception as ex:
            return self._no(base, f"no pude leer la billetera o el saldo ({texto_error(ex)})")
        w, saldo = self.billetera, self.saldo
        disp = 0.0
        for p, s in ((m.get("asks") or {}).get(lado) or []):
            if p <= d["q"] + 1e-9:
                disp += s
        pedido = N.importe_b(saldo, d, pol, disp)
        cupo = math.floor(self.cupo_hoy(ahora) * 100 + 1e-9) / 100
        usdt = min(pedido, cupo)
        base.update(saldo=round(saldo, 4), disp=round(disp, 2), kelly=round(d.get("kelly", 0.0), 6), cupo_dia=cupo)
        if pedido < N.MIN_USDT:
            return self._no(base, "importe menor que el mínimo de 2 USDT")
        if usdt < N.MIN_USDT:
            if not self.dias[dia(ahora)].get("avisado"):
                self.dias[dia(ahora)]["avisado"] = True
                self._guardar()
                self.avisar(f"Operador · freno del día: lo perdido hoy ({num(self.perdido_hoy(ahora))} USDT, contando lo abierto) ya no deja "
                            f"sitio dentro del 16 % del saldo con que empezó ({num(self.dias[dia(ahora)]['saldo_inicial'])} USDT). "
                            "No compra más hasta mañana.")
            return self._no(base, "freno del día: ya no cabe otra compra dentro del 16 %")
        resta = m["t"] + 60 * W - self.C.ahora()
        if resta < N.MIN_RESTA_S:
            return self._no(base, "quedan menos de 10 s")
        token = m["tokens"][lado]
        try:
            q = self.C.cotizar(w["walletAddress"], token, usdt, DESLIZAMIENTO_BPS, FUENTE)
        except Exception as ex:
            return self._no({**base, "usdt": usdt}, f"sin cotización ({texto_error(ex)})")
        precio = float(q.get("averagePrice") or 0)
        com_cot = float(q.get("feeRateBps") or 0) / 10000 or com
        contratos_cot = int(q["amountOut"]) / 1e18 if str(q.get("amountOut") or "").isdigit() else None
        base.update(usdt=usdt, cotizado=precio, comision=com_cot, contratos_cot=round(contratos_cot, 4) if contratos_cot else None)
        if not q.get("quoteId") or not N.PRECIO_MIN - 1e-9 <= precio <= N.PRECIO_MAX + 1e-9:
            return self._no(base, f"cotización a {num(precio, 3)}: fuera de 0,01 a 0,90")
        G_cot = N.ganancia(d["p_prud"], precio, com_cot)
        if contratos_cot:  # lo que de verdad entregarían por lo pagado, con la comisión que sea
            G_cot = min(G_cot, d["p_prud"] * contratos_cot / usdt - 1)
        base["G_cot"] = round(G_cot, 6)
        if G_cot < pol["margen"] - 1e-12:
            return self._no(base, f"la cotización a {num(precio, 3)} ya no deja el margen (ganancia esperada prudente {pct(G_cot, 0)})")
        # desde aquí hay orden: primero queda anotada y después se envía; si se va la luz en medio, al volver se aclara
        hoy = self.dias[dia(ahora)]
        hoy["fijo"] = True
        o = {k: v for k, v in base.items() if k != "tipo"}
        o.update(id=f"{W}-{m['t']}-{sum(1 for x in self.ordenes if x['W'] == W and x['t'] == m['t']) + 1}", dia=dia(ahora), token=token,
                 quote=q.get("quoteId"), estado="POR ENVIAR", final=False, orden=None, comprado=0.0, contratos=0.0, precio=None,
                 hora_envio=round(self.C.ahora(), 2), leida=0.0, lecturas=0, res=None, pago=None, neto=None, cobro=None,
                 saldo_inicial_dia=hoy["saldo_inicial"])
        self.ordenes.append(o)
        self._guardar()
        try:
            r = self.C.ordenar(w["walletAddress"], w["walletId"], q["quoteId"], DESLIZAMIENTO_BPS, FUENTE)
        except Exception as ex:
            codigo = getattr(ex, "codigo", None)
            if isinstance(codigo, int) and codigo < 0:   # Binance contestó que no: esa orden no existe
                o.update(estado="RECHAZADA", final=True, motivo=str(ex)[:200])
            else:                                         # sin respuesta, o respuesta rota: no se sabe si llegó
                o.update(estado="DUDOSA", motivo=texto_error(ex))
        else:
            if r.get("orderId"):
                o.update(estado="ENVIADA", orden=str(r["orderId"]))
            else:
                o.update(estado="DUDOSA", motivo="Binance respondió sin número de orden")
        self._guardar()
        self.fila({"tipo": "orden", "enviada": True, **{k: o.get(k) for k in (
            "id", "W", "t", "topic", "m", "plazo", "lado", "papel", "celda", "p", "p_prud", "q_libro", "G_prud", "G_cot", "usdt", "saldo",
            "cotizado", "contratos_cot", "comision", "estado", "orden", "motivo", "hora", "hora_envio", "cupo_dia")}})
        self.log(f"ORDEN REAL {o['id']}: {sentido(lado)} {usdt} USDT a {precio} en el mercado de {W} min · estado {o['estado']}"
                 + (f" · {o.get('motivo')}" if o.get("motivo") else ""))
        texto = (f"Operador · ORDEN REAL en el mercado de {W} min, con {W - cand['m']} min por delante: {sentido(lado)}, {num(usdt)} USDT "
                 f"cotizados a {num(precio, 3)}. El modelo le da {pct(d['p'])} (prudente {pct(d['p_prud'])}); ganancia esperada "
                 f"prudente {pct(G_cot, 0)}. ")
        if o["estado"] == "ENVIADA":
            texto += f"Binance la recibió (orden {o['orden']}); le aviso cuando la confirme."
        elif o["estado"] == "RECHAZADA":
            texto += f"Binance la rechazó: {o['motivo']}. No se compró nada."
        else:
            texto += "Binance no respondió al envío: la busco en su cuenta antes de hacer nada más."
        self.avisar(texto)
        return o

    # ------------------------------------------------------------ después de enviar
    def paso(self, ahora):
        """Avanza lo pendiente: aclara envíos sin respuesta, relee órdenes abiertas, liquida las compradas y cobra lo ganado."""
        vivas = [o for o in self.ordenes[-120:] if not o["final"] or (o["comprado"] and o.get("res") is None) or self._cobro_abierto(o)]
        if not vivas or self.C.llave() is None:
            return
        cambio = False
        for o in vivas:
            try:
                if self.billetera is None and not self.cuenta(ahora, forzar=True):
                    return
                if not o["final"]:
                    cambio |= self._aclarar(ahora, o) if o["estado"] == "DUDOSA" else self._releer(ahora, o)
                elif o["comprado"] and o.get("res") is None:
                    cambio |= self._liquidar(ahora, o)
                else:
                    cambio |= self._cobrar(ahora, o)
            except Exception as ex:
                if getattr(ex, "codigo", None) in LLAVE_MALA:
                    if cambio:
                        self._guardar()
                    raise
                if ahora - self.t_error >= 60:
                    self.t_error = ahora
                    self.log(f"orden {o['id']}: no pude seguirla ({texto_error(ex)})")
        if cambio:
            self._guardar()

    @staticmethod
    def _toca(ahora, o, clave, espera):
        if ahora - o.get(clave, 0.0) < espera:
            return False
        o[clave] = round(ahora, 2)
        return True

    def _aplicar(self, ahora, o, x):
        """Pone en la orden lo que dice Binance. Devuelve True si cambió algo."""
        estado = str(x.get("status") or "SIN ESTADO")
        comprado = float(x.get("filledUsdtAmount") or 0)
        final = estado in N_FALLIDOS or estado in N_COMPRADA or bool(x.get("_cerrada"))
        if estado == o["estado"] and final == o["final"] and comprado == o["comprado"]:
            return False
        precio = float(x.get("price") or 0) or o.get("cotizado")
        o.update(estado=estado, final=final, comprado=comprado, precio=precio)
        if comprado > 0:
            calculados = comprado * (1 - o["comision"]) / precio if precio else 0.0
            leidos = float(x.get("filledShareQty") or 0)
            # Binance da los contratos; si su cifra se aparta más de 5 % de la cuenta, vale la cuenta (y queda anotada la suya)
            o["contratos"] = round(leidos if calculados and abs(leidos - calculados) <= 0.05 * calculados else calculados, 4)
            o["contratos_binance"] = leidos
        self.fila({"tipo": "orden leída", "id": o["id"], "W": o["W"], "t": o["t"], "orden": o["orden"], "estado": estado, "final": final,
                   "comprado": comprado, "precio": precio, "contratos": o["contratos"], "hora": round(ahora, 2)})
        self.log(f"orden {o['id']} ({o['orden']}): {estado}, comprado {comprado} USDT" + (" · final" if final else ""))
        if final:
            if comprado > 0:
                self.avisar(f"Operador · orden {o['orden']} COMPRADA: {sentido(o['lado'])} en el mercado de {o['W']} min, "
                            f"{num(comprado)} USDT a {num(precio, 3)} ({num(o['contratos'])} contratos). Si acierta paga "
                            f"{num(o['contratos'])} USDT.")
            else:
                self.avisar(f"Operador · orden {o['orden']}: Binance la cerró sin comprar ({estado}). El saldo queda igual.")
        return True

    def _releer(self, ahora, o):
        edad = ahora - o["hora_envio"]
        if not self._toca(ahora, o, "leida", 2 if edad < 30 else (10 if edad < 300 else 60)):
            return False
        o["lecturas"] += 1
        x = self.C.orden(self.billetera["walletAddress"], o["orden"])
        if x is None:
            if edad > SIN_CIERRE_S:
                o.update(estado="SIN CIERRE", final=True)
                self.avisar(f"Operador · la orden {o['orden']} lleva un día sin aparecer en Binance. Revísela en la app.")
                return True
            return False
        return self._aplicar(ahora, o, x)

    def _aclarar(self, ahora, o):
        """El envío quedó sin respuesta: se busca en Binance una orden de compra de ese mercado hecha desde el envío."""
        if not self._toca(ahora, o, "leida", 5):
            return False
        o["lecturas"] += 1
        abiertas, cerradas = self.C.ordenes(self.billetera["walletAddress"])
        mias = {str(x["orden"]) for x in self.ordenes if x.get("orden")}
        for cerrada, lote in ((True, cerradas), (False, abiertas)):
            for x in lote:
                if (str(x.get("marketTopicId")) == str(o["topic"]) and str(x.get("side", "BUY")).upper() == "BUY"
                        and str(x.get("orderId")) not in mias and float(x.get("createTime") or 0) / 1000 >= o["hora_envio"] - 15):
                    o["orden"] = str(x["orderId"])
                    self.log(f"orden {o['id']}: sí llegó a Binance ({o['orden']})")
                    self._aplicar(ahora, o, {**x, "_cerrada": cerrada})
                    if not o["final"] and o["estado"] == "DUDOSA":
                        o["estado"] = "ENVIADA"
                    return True
        if ahora - o["hora_envio"] > ACLARAR_S:
            # no aparece: se da por no llegada, pero su mercado queda cerrado igual (no es un rechazo claro)
            o.update(estado="NO LLEGÓ", final=True)
            self.fila({"tipo": "orden leída", "id": o["id"], "W": o["W"], "t": o["t"], "orden": None, "estado": "NO LLEGÓ", "final": True,
                       "comprado": 0.0, "hora": round(ahora, 2)})
            self.log(f"orden {o['id']}: no aparece en Binance tras {ACLARAR_S} s; se da por no llegada")
            self.avisar(f"Operador · el envío al mercado de {o['W']} min no llegó a Binance: no hay orden y el saldo queda igual.")
            return True
        return False

    def _liquidar(self, ahora, o):
        fin = o["t"] + 60 * o["W"]
        if ahora < fin + 30 or not self._toca(ahora, o, "t_res", 30 if ahora < fin + 3600 else 600):
            return False
        g = self.C.resultado(o["topic"])
        if g is None:
            if ahora > fin + SIN_RESULTADO_S:
                o.update(res=-1, pago=0.0, neto=0.0)
                self.avisar(f"Operador · el mercado de la orden {o['orden']} lleva dos días sin ganador oficial. Revíselo en la app.")
                return True
            return False
        if g == 0:
            res, pago = 2, o["contratos"] / 2
        elif g == o["lado"]:
            res, pago = 1, o["contratos"]
        else:
            res, pago = 0, 0.0
        o.update(res=res, pago=round(pago, 4), neto=round(pago - o["comprado"], 4), ganador=g, hora_res=round(ahora, 2))
        if pago > 0:
            o["cobro"] = {"estado": "PENDIENTE", "intentos": 0, "visto": 0.0, "pedido": 0.0, "tx": None, "desde": round(ahora, 2)}
        self.fila({"tipo": "liquidación", "id": o["id"], "W": o["W"], "t": o["t"], "orden": o["orden"], "ganador": g, "res": res,
                   "comprado": o["comprado"], "pago": o["pago"], "neto": o["neto"], "hora": round(ahora, 2)})
        self.log(f"orden {o['id']}: ganó {'el empate' if g == 0 else sentido(g)}; neto {o['neto']:+.2f} USDT")
        como = {1: "ACERTÓ", 0: "falló", 2: "empate (paga la mitad)"}[res]
        self.avisar(f"Operador · mercado de {o['W']} min de las {hora(o['t'], '%H:%M')}: ganó "
                    f"{'ninguno (empate)' if g == 0 else sentido(g)}. Su orden {sentido(o['lado'])} {como}: neto {con_signo(o['neto'])} USDT. "
                    f"Hoy va {con_signo(-self.perdido_hoy(ahora))} USDT contando lo abierto.")
        return True

    @staticmethod
    def _cobro_abierto(o):
        return bool(o.get("cobro")) and o["cobro"]["estado"] in ("PENDIENTE", "PEDIDO")

    def _cobrar(self, ahora, o):
        """Cobra lo ganado de una orden ya liquidada. Primero mira en Binance cómo figura esa posición; si ya está cobrada no
        pide nada. Como mucho tres pedidos, separados diez minutos; después le toca a usted en la app."""
        c = o["cobro"]
        if not self._cobro_abierto(o):
            return False
        direccion = self.billetera["walletAddress"]
        if c["estado"] == "PEDIDO":
            if not self._toca(ahora, c, "visto", 15):
                return False
            estado = self.C.estado_cobro(direccion, c["tx"])
            if estado == "CONFIRMED":
                return self._cobrado(ahora, o, "confirmado en la cadena")
            if estado == "FAILED" or (estado in ("NOT_FOUND", None) and ahora - c["pedido"] > 300) or ahora - c["pedido"] > 1800:
                c["estado"] = "PENDIENTE"
                self.fila({"tipo": "cobro", "id": o["id"], "orden": o["orden"], "estado": f"falló ({estado})", "tx": c["tx"], "hora": round(ahora, 2)})
                self.log(f"cobro de la orden {o['id']}: el pedido quedó {estado}")
                return True
            return False
        if not self._toca(ahora, c, "visto", 60):
            return False
        pos = next((p for p in self.C.liquidadas(direccion) if str(p.get("tokenId")) == str(o["token"])), None)
        if pos is None:
            if ahora - c["desde"] > 7200:
                return self._sin_cobrar(ahora, o, "Binance no muestra la posición liquidada")
            return False
        if str(pos.get("positionStatus")).upper() == "CLAIMED" or str(pos.get("redeemStatus")).upper() == "CONFIRMED":
            if pos.get("claimAmount") not in (None, ""):
                c["monto"] = float(pos["claimAmount"])
            return self._cobrado(ahora, o, "ya figuraba cobrada en Binance")
        if pos.get("isWinner") is False and o["res"] == 1:
            return self._sin_cobrar(ahora, o, "Binance no la da por ganadora")
        if self.C.llave() != "operar" or not self.revisar_llave(ahora)[0]:
            return False   # sin la llave de operar en regla no se pide nada: queda pendiente
        if c["intentos"] >= INTENTOS_COBRO:
            return self._sin_cobrar(ahora, o, f"{INTENTOS_COBRO} pedidos sin lograrlo")
        if c["intentos"] and ahora - c["pedido"] < 600:
            return False
        c["intentos"] += 1
        c["pedido"] = round(ahora, 2)
        self._guardar()   # el intento queda anotado antes de pedirlo
        r = self.C.cobrar(direccion, self.billetera["walletId"], o["token"])
        self.fila({"tipo": "cobro", "id": o["id"], "orden": o["orden"], "estado": "pedido", "intento": c["intentos"], "hora": round(ahora, 2), **r})
        if r.get("tx") and not r.get("error"):
            c.update(estado="PEDIDO", tx=r["tx"], visto=round(ahora, 2))
            self.log(f"cobro de la orden {o['id']}: pedido {c['intentos']} enviado")
        else:
            self.log(f"cobro de la orden {o['id']}: Binance no lo aceptó ({r.get('error') or r.get('estado')})")
        return True

    def _cobrado(self, ahora, o, como):
        c = o["cobro"]
        c.update(estado="COBRADO", hora=round(ahora, 2), como=como)
        monto = c.get("monto", o["pago"])
        self.fila({"tipo": "cobro", "id": o["id"], "orden": o["orden"], "estado": "cobrado", "como": como, "monto": monto, "tx": c.get("tx"),
                   "hora": round(ahora, 2)})
        self.log(f"cobro de la orden {o['id']}: cobrado ({como}), {monto} USDT")
        self.t_cuenta = -1e9  # el saldo cambió: se vuelve a leer
        self.avisar(f"Operador · cobrado: {num(monto)} USDT de la orden {o['orden']} ({como}).")
        return True

    def _sin_cobrar(self, ahora, o, motivo):
        o["cobro"].update(estado="SIN COBRAR", hora=round(ahora, 2), motivo=motivo)
        self.fila({"tipo": "cobro", "id": o["id"], "orden": o["orden"], "estado": "sin cobrar", "motivo": motivo, "hora": round(ahora, 2)})
        self.log(f"cobro de la orden {o['id']}: sin cobrar ({motivo})")
        self.avisar(f"Operador · no pude cobrar la orden {o['orden']} ({motivo}). Son {num(o['pago'])} USDT: cóbrelos en la app de "
                    "Binance, en Predicción.")
        return True

    # ------------------------------------------------------------ resumen
    def resumen(self, ahora):
        hoy = self.de_hoy(ahora)
        compradas = [o for o in self.ordenes if o["comprado"]]
        liquidadas = [o for o in compradas if o.get("res") in (0, 1, 2)]
        neto = 0.0
        for o in liquidadas:
            neto += o["neto"]
        d = self.dias.get(dia(ahora)) or {}
        return {"armado": self.armado(), "saldo": self.saldo, "saldo_inicial_dia": d.get("saldo_inicial"),
                "perdido_hoy": round(self.perdido_hoy(ahora), 4), "cupo_hoy": round(self.cupo_hoy(ahora), 4), "ordenes_hoy": len(hoy),
                "abiertas": sum(1 for o in self.ordenes if not o["final"]),
                "sin_liquidar": sum(1 for o in compradas if o.get("res") is None),
                "cobros_pendientes": sum(1 for o in self.ordenes if self._cobro_abierto(o)),
                "sin_cobrar": sum(1 for o in self.ordenes if o.get("cobro") and o["cobro"]["estado"] == "SIN COBRAR"),
                "compradas": len(compradas), "liquidadas": len(liquidadas), "aciertos": sum(1 for o in liquidadas if o["res"] == 1),
                "neto": round(neto, 4), "permisos": {k: self.permisos[k] for k in ("ok", "motivo", "notas")},
                "ultimas": [{k: o.get(k) for k in ("id", "W", "t", "plazo", "lado", "usdt", "cotizado", "estado", "comprado", "contratos",
                                                   "res", "neto", "orden")} | {"cobro": (o.get("cobro") or {}).get("estado")}
                            for o in self.ordenes[-8:]]}

