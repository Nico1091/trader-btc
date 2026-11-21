"""Prueba del ejecutor del operador de binarias contra un Binance simulado (21/11/2026).

Qué hace: ejecuta el código real de `ejecutor.py` (la parte que toca dinero: `ejecutar_ia`, `_frenos`, `_enviar`, `paso`,
`_aclarar`, `_liquidar`) sobre un Binance falso que vive en memoria. No hay red, no hay llaves, no hay saldo real: nada de
esto puede enviar una orden ni gastar un centavo. Cada escenario comprueba una regla que el propio código dice cumplir.

Qué NO hace: no prueba que Binance responda igual que el simulado (eso solo lo dice una prueba real sin fondos), ni prueba
el modelo, ni el nodo, ni la llave real. No modifica nada de la carpeta del operador: solo la lee.

Uso:
  python -X utf8 prueba_ejecutor_simulado.py --operador RUTA_A_binarias/operador

Sale con código 0 si todo se cumple y 1 si algún escenario falla. Los fallos se muestran tal cual, sin corregirlos aquí.
"""
import argparse
import os
import sys
import tempfile
import traceback

T0 = 1_800_000_000          # inicio de una ventana de 5 min y 15 min (múltiplo de 300 s)
SALDO_BASE = 20.0


class ErrBinance(Exception):
    """Igual que conexion.ErrorBinance para el ejecutor: lleva `codigo` (Binance dijo que no)."""

    def __init__(self, codigo, msg=""):
        super().__init__(f"{codigo}: {msg}")
        self.codigo = codigo


class Binance:
    """Binance simulado. Mismos métodos que usa el ejecutor. Todo lo que se envía queda en `llamadas`."""

    def __init__(self, t):
        self.t = t
        self.saldo = SALDO_BASE
        self.restr = {"ipRestrict": True, "enableWithdrawals": False, "enableInternalTransfer": False,
                      "permitsUniversalTransfer": False, "enableMargin": False, "enableFutures": False,
                      "enableVanillaOptions": False, "enablePortfolioMarginTrading": False,
                      "enableSpotAndMarginTrading": False}
        self.precio = 0.50            # precio medio que devuelve la cotización
        self.cot_error = None         # excepción que lanza cotizar, si se pone
        self.ord_error = None         # excepción que lanza ordenar, si se pone (la orden no llega)
        self.ord_error_llega = False  # si True, la orden sí queda creada en Binance aunque la respuesta se pierda
        self.llamadas = []            # ("cotizar"|"ordenar", dato)
        self.cotiz = {}               # quoteId -> (usdt, precio, topic, lado)
        self.ords = {}                # orderId -> dict como lo da Binance
        self.ganador = {}             # topic -> ganador (1, -1, 0) cuando el mercado cierra
        self.n = 0

    # --- contrato que usa el ejecutor ---
    def ahora(self):
        return self.t

    def llave(self):
        return "operar"

    def marca_llave(self):
        return "marca-1"

    def restricciones(self):
        return dict(self.restr)

    def billetera(self):
        return {"walletAddress": "0xSIM", "walletId": "W-SIM"}

    def saldos(self):
        return {"CeDeFi": self.saldo}

    def cotizar(self, addr, token, usdt, bps, fuente):
        self.llamadas.append(("cotizar", usdt))
        if self.cot_error is not None:
            raise self.cot_error
        _, topic = token.split("|")
        lado = 1 if token.startswith("UP") else -1
        self.n += 1
        qid = f"Q{self.n}"
        self.cotiz[qid] = (usdt, self.precio, topic, lado)
        return {"quoteId": qid, "averagePrice": self.precio, "feeRateBps": 200,
                "amountOut": str(int(usdt / self.precio * 1e18))}

    def ordenar(self, addr, wid, quote, bps, fuente):
        self.llamadas.append(("ordenar", quote))
        usdt, precio, topic, lado = self.cotiz[quote]
        if self.ord_error is not None:
            oid = None
            if self.ord_error_llega:
                oid = self._crear(usdt, precio, topic, lado)
            raise self.ord_error
        oid = self._crear(usdt, precio, topic, lado)
        return {"orderId": oid}

    def _crear(self, usdt, precio, topic, lado, creada=None):
        self.n += 1
        oid = str(900000 + self.n)
        self.ords[oid] = {"orderId": oid, "marketTopicId": topic, "side": "BUY", "status": "NEW", "usdt": usdt,
                          "price": precio, "filledUsdtAmount": 0.0, "filledShareQty": 0.0,
                          "createTime": int((creada if creada is not None else self.t) * 1000), "lado": lado}
        return oid

    def orden(self, addr, oid):
        x = self.ords.get(str(oid))
        return dict(x) if x else None

    def ordenes(self, addr):
        abiertas = [dict(x) for x in self.ords.values() if x["status"] == "NEW"]
        cerradas = [dict(x) for x in self.ords.values() if x["status"] == "FILLED"]
        return abiertas, cerradas

    def resultado(self, topic):
        return self.ganador.get(topic)

    def llenar(self, oid):
        x = self.ords[str(oid)]
        x.update(status="FILLED", filledUsdtAmount=x["usdt"],
                 filledShareQty=round(x["usdt"] * (1 - 0.02) / x["price"], 6))

    def manual(self, topic, usdt, precio, creada):
        """Una compra a mano del dueño en la misma cuenta, en el mismo mercado."""
        oid = self._crear(usdt, precio, topic, 1, creada=creada)
        self.llenar(oid)
        return oid

    # Estas partes no las usa el ejecutor en los escenarios de compra; si se llaman, la prueba lo muestra.
    def cobrar(self, *a, **k):
        raise AssertionError("cobrar no debía llamarse en esta prueba")

    def estado_cobro(self, *a, **k):
        raise AssertionError("estado_cobro no debía llamarse en esta prueba")

    def liquidadas(self, *a, **k):
        raise AssertionError("liquidadas no debía llamarse en esta prueba")


def mercado(W, t, topic):
    return {"W": W, "t": t, "topic": topic, "abierto": True, "sintetico": False,
            "tokens": {1: f"UP|{topic}", -1: f"DN|{topic}"}, "comision_bps": 200, "asks": {}}


class Entorno:
    """Un ejecutor nuevo, con su carpeta temporal, sus filas y sus avisos."""

    def __init__(self, EJ, AP, C, carpeta):
        self.EJ, self.AP, self.C, self.carpeta = EJ, AP, C, carpeta
        self.filas, self.logs, self.avisos = [], [], []
        self.ej = EJ.Ejecutor(C, self.filas.append, self.logs.append, self.avisos.append,
                              carpeta=carpeta, datos=os.path.join(carpeta, "datos"))
        self.decisiones = {}
        AP.orden = lambda W, t, ahora, r=None: self.decisiones.get((W, t), (None, None))

    def armar(self, mercados=(15, 5)):
        import json
        with open(os.path.join(self.carpeta, "ARMADO"), "w", encoding="utf-8") as f:
            json.dump({"mercados": list(mercados), "por": "prueba", "apto": True}, f)

    def decidir(self, W, t, lado=1, pu=0.50, pd=0.50, sin_precio=False):
        precios = {} if sin_precio else {"1": pu, "-1": pd}
        self.decisiones[(W, t)] = (lado, {"t": t + 30, "id": f"D-{W}-{t}", "decision": "COMPRAR", "precios": precios})

    def ronda(self, W, t, ahora, **kw):
        self.decidir(W, t, **kw)
        self.C.t = ahora
        return self.ej.ejecutar_ia(ahora, mercado(W, t, f"T{W}-{t}"))


def esperar(cond, texto, fallos):
    fallos.append((bool(cond), texto))


def ordenes_enviadas(C):
    return [x for x in C.llamadas if x[0] == "ordenar"]


def escenarios(EJ, AP, base):
    """Cada escenario devuelve una lista de (cumple, descripción)."""
    out = {}

    def nuevo(saldo=SALDO_BASE, nombre=""):
        d = tempfile.mkdtemp(prefix=f"sim_{nombre}_", dir=base)
        C = Binance(T0 + 60)
        C.saldo = saldo
        return Entorno(EJ, AP, C, d), C

    def e1():
        f = []
        env, C = nuevo(nombre="sinarm")
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is None and not C.llamadas, "sin ARMADO no se cotiza ni se compra", f)
        return f
    out["E01 Sin archivo ARMADO no hay ninguna compra"] = e1

    def e2():
        f = []
        env, C = nuevo(nombre="armmerc")
        env.armar(mercados=(5,))
        r15 = env.ronda(15, T0, T0 + 60)
        esperar(r15 is None and not C.llamadas, "ARMADO solo de 5 min no compra en el mercado de 15", f)
        r5 = env.ronda(5, T0 + 300, T0 + 360)
        esperar(r5 is not None and len(ordenes_enviadas(C)) == 1, "ARMADO de 5 min sí compra en el de 5", f)
        return f
    out["E02 ARMADO por mercado: solo el que dice"] = e2

    def e3():
        f = []
        env, C = nuevo(nombre="parar")
        env.armar()
        open(os.path.join(env.carpeta, "PARAR"), "w").close()
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is None and not C.llamadas, "con el archivo PARAR no se compra aunque esté armado", f)
        return f
    out["E03 PARAR corta la compra"] = e3

    def e4():
        f = []
        env, C = nuevo(nombre="permisos")
        env.armar()
        C.restr["enableWithdrawals"] = True
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is None and not C.llamadas, "llave con retiros permitidos: no se compra", f)
        return f
    out["E04 Llave con retiros permitidos: no compra"] = e4

    def e5():
        f = []
        env, C = nuevo(nombre="ip")
        env.armar()
        C.restr["ipRestrict"] = False
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is None and not C.llamadas, "llave sin restricción de IP: no se compra", f)
        return f
    out["E05 Llave sin restricción de IP: no compra"] = e5

    def e6():
        f = []
        env, C = nuevo(nombre="sinIA")
        env.armar()
        r = env.ronda(5, T0, T0 + 60, lado=None)
        esperar(r is None and not C.llamadas, "sin decisión vigente de la IA no se hace nada", f)
        return f
    out["E06 Sin decisión de la IA: nada"] = e6

    def e7():
        f = []
        env, C = nuevo(nombre="ciegas")
        env.armar()
        r = env.ronda(5, T0, T0 + 60, sin_precio=True)
        esperar(r is None and not C.llamadas, "decisión sin el precio que vio la IA: no se compra a ciegas", f)
        return f
    out["E07 Decisión sin precio visto: no compra a ciegas"] = e7

    def e8():
        f = []
        env, C = nuevo(nombre="sube")
        env.armar()
        C.precio = 0.56   # visto 0,50: 0,06 más, por encima de la tolerancia de 0,02
        r = env.ronda(5, T0, T0 + 60, pu=0.50)
        esperar(r is None and not ordenes_enviadas(C), "precio 0,06 sobre lo visto: cotiza pero no ordena", f)
        return f
    out["E08 Precio 0,06 sobre lo visto: no ordena"] = e8

    def e9():
        f = []
        env, C = nuevo(nombre="frontera")
        env.armar()
        C.precio = 0.52   # justo visto + 0,02: debe pasar
        r = env.ronda(5, T0, T0 + 60, pu=0.50)
        esperar(r is not None and r["estado"] in ("ENVIADA", "FILLED", "POR ENVIAR") and len(ordenes_enviadas(C)) == 1,
                "precio justo visto + 0,02: sí ordena", f)
        return f
    out["E09 Precio en la frontera (visto + 0,02): ordena"] = e9

    def e10():
        f = []
        env, C = nuevo(nombre="ciclo")
        env.armar()
        C.precio = 0.52
        r = env.ronda(5, T0, T0 + 60, pu=0.50)
        esperar(r is not None, "ciclo: se envía la orden", f)
        if r is None:
            return f
        oid = r["orden"]
        C.llenar(oid)
        env.ej.paso(T0 + 60 + 300 + 40)            # tras el cierre del mercado (300 s) + 30 s
        o = env.ej.ordenes[-1]
        esperar(o["estado"] == "FILLED" and abs(o["comprado"] - 2.0) < 1e-9, "ciclo: orden leída como comprada por 2 USDT", f)
        C.ganador[f"T5-{T0}"] = 1  # gana SUBE
        env.ej.paso(T0 + 60 + 300 + 40 + 60)
        o = env.ej.ordenes[-1]
        esperar(o.get("res") == 1 and abs(o["neto"] - (2 * 0.98 / 0.52 - 2)) < 0.01,
                f"ciclo: gana SUBE, neto ≈ +1,77 (obtenido {o.get('neto')})", f)
        return f
    out["E10 Ciclo completo: compra, lectura y liquidación"] = e10

    def e11():
        f = []
        env, C = nuevo(nombre="freno")
        env.armar()
        r1 = env.ronda(5, T0, T0 + 60)
        r2 = env.ronda(5, T0 + 300, T0 + 360)
        total = sum(o["usdt"] for o in env.ej.ordenes if o.get("origen") == "ia")
        esperar(r1 is not None and r2 is None, "freno: con 20 USDT y 2 USDT abiertos no entra una segunda compra de 2", f)
        esperar(total <= 0.16 * SALDO_BASE + 1e-9, f"freno: lo ordenado en el día ({total}) no pasa el 16 % del saldo", f)
        return f
    out["E11 Freno del día: no pasa del 16 % del saldo"] = e11

    def e12():
        f = []
        env, C = nuevo(saldo=10.0, nombre="saldo")
        env.armar()
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is None and not C.llamadas, "saldo de 10 USDT: 2 USDT pasan el 16 % (1,6) y no compra", f)
        return f
    out["E12 Saldo chico: 2 USDT pasan el 16 %, no compra"] = e12

    def e13():
        f = []
        env, C = nuevo(saldo=10000.0, nombre="tope20")
        env.armar()
        n = 0
        for k in range(21):
            t = T0 + 300 * k
            r = env.ronda(5, t, t + 60)
            n += 1 if r is not None else 0
        esperar(n == 20 and len(ordenes_enviadas(C)) == 20,
                f"tope de 20 órdenes al día: se enviaron {n} de 21 intentos", f)
        return f
    out["E13 Tope de 20 órdenes por día"] = e13

    def e14():
        f = []
        env, C = nuevo(nombre="rechazo")
        env.armar()
        C.ord_error = ErrBinance(-2010, "rechazada")
        t = T0
        resultados = []
        for k in range(4):
            resultados.append(env.ronda(5, t, t + 60 + 20 * k))
        esperar(len(ordenes_enviadas(C)) == 2, f"rechazo claro: como mucho 2 envíos por mercado (hubo {len(ordenes_enviadas(C))})", f)
        esperar(all(r is None or r["estado"] == "RECHAZADA" for r in resultados), "rechazo claro queda RECHAZADA", f)
        return f
    out["E14 Rechazo claro: máximo dos envíos por mercado"] = e14

    def e15():
        f = []
        env, C = nuevo(nombre="dudosa")
        env.armar()
        C.ord_error = TimeoutError("sin respuesta")
        r = env.ronda(5, T0, T0 + 60)
        esperar(r is not None and r["estado"] == "DUDOSA", "sin respuesta: la orden queda DUDOSA", f)
        r2 = env.ronda(5, T0, T0 + 80)
        env.ej.paso(T0 + 60 + 150)                 # ya pasaron 120 s sin que aparezca
        r3 = env.ronda(5, T0, T0 + 220)
        esperar(len(ordenes_enviadas(C)) == 1 and r2 is None and r3 is None,
                "sin respuesta y sin aparecer: no se duplica la compra en el mercado", f)
        esperar(env.ej.ordenes[-1]["estado"] == "NO LLEGÓ", "sin respuesta: queda NO LLEGÓ tras 120 s", f)
        return f
    out["E15 Sin respuesta y no llegó: no se duplica"] = e15

    def e16():
        f = []
        env, C = nuevo(nombre="llego")
        env.armar()
        C.ord_error = TimeoutError("sin respuesta")
        C.ord_error_llega = True                   # Binance sí la creó
        r = env.ronda(5, T0, T0 + 60)
        env.ej.paso(T0 + 60 + 10)
        o = env.ej.ordenes[-1]
        esperar(o["orden"] == str(max(C.ords)) and o["estado"] != "DUDOSA",
                "sin respuesta pero llegó: se reconoce la orden y deja de estar DUDOSA", f)
        esperar(len(ordenes_enviadas(C)) == 1, "sin respuesta pero llegó: no se vuelve a enviar", f)
        return f
    out["E16 Sin respuesta pero la orden llegó: se reconoce"] = e16

    def e17():
        f = []
        env, C = nuevo(nombre="ajena")
        env.armar()
        C.ord_error = TimeoutError("sin respuesta")  # nuestra orden no llegó
        env.ronda(5, T0, T0 + 60)
        manual = C.manual(f"T5-{T0}", 10.0, 0.50, creada=T0 + 65)   # compra a mano del dueño, 10 USDT, mismo mercado
        env.ej.paso(T0 + 60 + 20)
        o = env.ej.ordenes[-1]
        esperar(o.get("orden") != str(manual),
                "orden ajena del dueño (10 USDT, mismo mercado y minutos después) NO se adopta como nuestra", f)
        return f
    out["E17 Compra ajena del mismo mercado no se adopta"] = e17

    def e18():
        f = []
        env, C = nuevo(nombre="2015cot")
        env.armar()
        C.cot_error = ErrBinance(-2015, "IP no autorizada")
        try:
            env.ronda(5, T0, T0 + 60)
            propagado = False
        except ErrBinance:
            propagado = True
        esperar(propagado, "−2015 al cotizar sube al operador (que pasa al estado 1 y avisa), no se traga", f)
        return f
    out["E18 −2015 al cotizar llega al operador"] = e18

    def e19():
        f = []
        env, C = nuevo(nombre="2015ord")
        env.armar()
        C.ord_error = ErrBinance(-2015, "IP no autorizada")
        try:
            env.ronda(5, T0, T0 + 60)
            propagado = False
        except ErrBinance:
            propagado = True
        esperar(propagado, "−2015 al ordenar sube al operador, no se registra como rechazo normal", f)
        return f
    out["E19 −2015 al ordenar llega al operador"] = e19

    def e20():
        f = []
        env, C = nuevo(nombre="precio")
        env.armar()
        C.precio = 0.95
        r = env.ronda(5, T0, T0 + 60, pu=0.94)
        esperar(r is None and not ordenes_enviadas(C), "cotización a 0,95 (fuera de 0,01 a 0,90): no ordena", f)
        return f
    out["E20 Cotización fuera de 0,01–0,90: no ordena"] = e20

    def e21():
        f = []
        env, C = nuevo(nombre="resta")
        env.armar()
        r = env.ronda(5, T0, T0 + 300 - 5)   # quedan 5 s
        esperar(r is None and not C.llamadas, "quedan menos de 10 s: no cotiza", f)
        return f
    out["E21 Menos de 10 s para el cierre: no cotiza"] = e21

    def e22():
        f = []
        env, C = nuevo(nombre="ejec_todo")
        env.armar()                           # por defecto escribe los dos mercados, 15 y 5
        r = env.ronda(15, T0, T0 + 60)
        esperar(r is not None, "ARMADO de 15 min (por defecto) sí compra en el de 15", f)
        return f
    out["E22 ARMADO por defecto cubre los dos mercados"] = e22

    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--operador", required=True, help="carpeta binarias/operador (solo se lee)")
    a = ap.parse_args()
    ruta = os.path.abspath(a.operador)
    sys.path.insert(0, ruta)
    import ejecutor as EJ          # noqa: E402
    import aprobacion as AP        # noqa: E402
    base = tempfile.mkdtemp(prefix="sim_ejecutor_")
    total, malos = 0, 0
    print(f"Operador probado: {ruta}")
    print(f"Carpeta temporal: {base}")
    print("Binance simulado; sin red, sin llaves, sin fondos.\n")
    for nombre, fn in escenarios(EJ, AP, base).items():
        try:
            resultados = fn()
        except Exception:
            resultados = [(False, "el escenario se cayó: " + traceback.format_exc(limit=2).strip().replace("\n", " | "))]
        ok = all(c for c, _ in resultados)
        total += 1
        malos += 0 if ok else 1
        print(f"[{'OK   ' if ok else 'FALLO'}] {nombre}")
        for c, d in resultados:
            if not c:
                print(f"         - no se cumple: {d}")
    print(f"\nEscenarios: {total}. Con fallo: {malos}. Cumplen: {total - malos}.")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
