"""Comprar sobre la pérdida con el precio real del libro de Predict.fun (11/11/2026, pedido suyo). Solo papel: no manda órdenes.

Lo llama la Mesa en cada vuelta con el mercado de 15 min en curso (apertura oficial y libro de los dos lados). Reglas, escritas
antes de ver resultados:
- «A lo último»: en los últimos 3 minutos de la ventana, si el lado que va perdiendo cuesta 0,02 o menos, 0,05 o menos o
  0,10 o menos, se anota una compra de papel de 1 USDT a ese precio (una por umbral y ventana).
- «Temprana»: al cierre de los minutos 3, 5, 7, 9, 11, 13 y 14, la primera mirada con |z| ≥ 1 (z = ln(precio/apertura) /
  (σ60·√(15 − m)), la misma de laboratorio\\perdida.py) compra el lado perdedor al precio real de ese momento.
- «Red al final»: al cierre de los minutos 10 a 14, si el perdedor cuesta menos de 0,98 × la probabilidad que le da la red
  (laboratorio\\perdida_red.py), se anota la compra (una por ventana).
- Se liquida con el ganador oficial del mercado: si gana, cobra 1 USDT por contrato; si pierde, −1 USDT. Contratos que compra
  1 USDT = (1 − comisión) / precio: a 0,02 son 49; a 0,10, casi 10. Por eso cuanto más cae el perdedor, más contratos.

Correcciones del 12/11/2026, tras su pedido de revisar si compra cuando el mercado está por cerrarse. Lo anotado desde aquí es
la serie 2; lo anterior queda como serie 1 y se informa aparte, sin mezclar:
1. Contado, no futuros. El mercado abre y liquida con el precio medio de contado de Binance (flujo de Chainlink BTC/USDT; 12 de
   12 aperturas oficiales iguales al contado, ±0,01). Antes se comparaba el precio de FUTUROS con esa apertura, y futuros iba
   30,8 USD por debajo (de −40 a −17 en 236 min): la z de la temprana y la entrada de la red salían corridas y a ratos se
   miraba el lado que en realidad iba ganando.
2. El perdedor de «a lo último» es el lado más barato del libro (por debajo de 0,50): es el que el propio mercado da por
   perdedor, sin depender de otra fuente de precio.
3. Hora de Binance (conexion.ahora). El reloj del PC iba 4 s atrás: los segundos antes del cierre salían inflados y dos compras
   quedaron anotadas con el mercado ya cerrado.
4. Margen de 10 s: con menos tiempo no alcanza el doble toque. No se anota.
5. Las miradas al cierre de un minuto esperan un libro leído después de ese cierre (hasta 20 s; si no llega, se pierde la mirada).
6. Cada compra guarda los contratos que compra 1 USDT y, en «a lo último», cuántos contratos había a ese precio o menos.

Cada minuto manda el resumen a la placa ESP32 (POST /real), que lo guarda y se lo pasa a la caja para su Telegram.
La llave no sale del PC: la placa y la caja solo reciben precios y resultados."""
import json
import math
import os
import sys
import threading
import urllib.request

import conexion as C

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(AQUI), "laboratorio"))  # al final: no tapa módulos de la Mesa
import perdida_red as PRED  # noqa: E402  la red de la pérdida al final (sin llaves: solo calcula)
ARCHIVO = os.path.join(AQUI, "datos", "perdida_real.json")
PLACA = os.environ.get("PRECIO_PLACA", "http://192.168.20.159:8080")  # vacío: no se le manda a la placa
FUENTE = os.environ.get("PRECIO_FUENTE", "PC")  # quién lee el libro: el PC (la Mesa) o el equipo que corre precio_vivo.py
UMBRALES = (0.02, 0.05, 0.10)
ULTIMOS_S = 180
MARGEN_S = 10          # con menos no alcanza el doble toque
LIBRO_VIEJO_S = 8      # no se compra con un libro leído hace más de esto
ESPERA_LIBRO_S = 20    # lo que se espera un libro posterior al cierre del minuto antes de dar la mirada por perdida
MINUTOS = (3, 5, 7, 9, 11, 13, 14)
APUESTA = 1.0
SERIE = 2
NOTA_SERIE_1 = "serie 1, hasta el 12/11/2026: referencia de futuros y reloj del PC 4 s atrás"
TEMPRANA, RED = "temprana |z| ≥ 1", "red al final"


def contratos(precio, comision=0.02, usdt=APUESTA):
    """Contratos que compra `usdt` a ese precio; la comisión sale de los contratos."""
    return usdt * (1 - comision) / precio


class PerdidaReal:
    def __init__(self, log=print):
        self.log = log
        self.ops, self.t_envio, self.t_resultado = [], 0.0, {}
        self.minuto_visto, self.ultima_red, self.modelo = 0, None, None
        self._vivo, self._hilo, self._placa_caida = (0.0, None), None, False
        self.extra = None  # 12/11/2026: resumen corto del comprador por ganancia esperada; viaja a la placa con este resumen
        try:
            self.ops = json.load(open(ARCHIVO, encoding="utf-8")).get("ops", [])
        except (OSError, ValueError):
            pass

    def _guardar(self):
        os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
        with open(ARCHIVO + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"ops": self.ops[-3000:]}, f, ensure_ascii=False)
        os.replace(ARCHIVO + ".tmp", ARCHIVO)

    def _ya(self, t, regla):
        return any(o["t"] == t and o["regla"] == regla for o in self.ops[-200:])

    def _anotar(self, m, regla, lado, precio, ahora, extra):
        comision = (m.get("comision_bps") or 200) / 10000
        op = {"t": m["t"], "topic": m.get("topic"), "regla": regla, "lado": lado, "precio": precio, "hora": int(ahora),
              "resta_s": int(m["t"] + 900 - ahora), "comision": comision, "contratos": round(contratos(precio, comision), 2),
              "serie": SERIE, "res": None, **extra}
        self.ops.append(op)
        self.log(f"pérdida real: {regla} compra {'SUBE' if lado > 0 else 'BAJA'} a {precio}: {op['contratos']:g} contratos por "
                 f"1 USDT ({op['resta_s']} s antes del cierre)")
        self._guardar()

    def paso(self, ahora, m, viva=None, velas=None):
        """ahora: hora de Binance (conexion.ahora). viva y velas, de futuros, se aceptan por compatibilidad y ya no se usan."""
        if m and m.get("abierto") and 0 < m["t"] + 900 - ahora <= 900:
            self._ultimo(ahora, m)
            if m.get("strike"):
                self._miradas(ahora, m)
        self._liquidar(ahora)
        if ahora - self.t_envio >= 60:
            self.t_envio = ahora
            self._enviar_placa()

    # ------------------------------------------------------------ a lo último
    def _contado_vivo(self, ahora):
        """Último precio de contado, solo para dejarlo anotado junto a la compra; None si Binance no contesta."""
        if ahora - self._vivo[0] > 3:
            try:
                cerr, viva = C.velas_contado(2, 4)
                self._vivo = (ahora, (viva or cerr[-1])[4])
            except Exception:
                self._vivo = (ahora, None)
        return self._vivo[1]

    def _ultimo(self, ahora, m):
        resta = m["t"] + 900 - ahora
        if not MARGEN_S <= resta <= ULTIMOS_S or ahora - m.get("libro_t", ahora) > LIBRO_VIEJO_S:
            return
        ask = m.get("ask") or {}
        baratos = [(ask[lado], lado) for lado in (1, -1) if ask.get(lado) and 0 < ask[lado] < 0.5]
        if not baratos:
            return
        precio, perdedor = min(baratos)
        for u in UMBRALES:
            regla = f"último ≤ {u:.2f}"
            if precio <= u and not self._ya(m["t"], regla):
                niveles = [(p, s) for p, s in ((m.get("asks") or {}).get(perdedor) or []) if p <= u]
                self._anotar(m, regla, perdedor, precio, ahora,
                             {"btc": self._contado_vivo(ahora), "strike": m.get("strike"), "otro": ask.get(-perdedor),
                              "disp": round(sum(s for _p, s in niveles), 2), "disp_usdt": round(sum(p * s for p, s in niveles), 2)})

    # ------------------------------------------------------------ miradas al cierre de un minuto: temprana y red
    def _miradas(self, ahora, m):
        cierre = int(ahora // 60) * 60      # el minuto que acaba de cerrar va de cierre − 60 a cierre
        mm = (cierre - m["t"]) // 60        # su número dentro de la ventana: 1 a 14
        if cierre == self.minuto_visto or not 1 <= mm <= 14:
            return
        temprana = mm in MINUTOS and not self._ya(m["t"], TEMPRANA)
        red = mm in PRED.MINUTOS and not self._ya(m["t"], RED)
        if not (temprana or red) or ahora - cierre > ESPERA_LIBRO_S:
            self.minuto_visto = cierre  # nada que mirar, o la mirada se pasó (red caída, libro sin leer): no se inventa
            return
        if m.get("libro_t", ahora) < cierre:
            return                      # el libro que hay es anterior al cierre del minuto: se espera al siguiente
        cerr, _viva = C.velas_contado(90)
        T = [v[0] for v in cerr]
        if not T or T[-1] != cierre - 60 or m["t"] not in T:
            return                      # Binance aún no entrega la vela cerrada: se reintenta en la próxima vuelta
        self.minuto_visto = cierre
        s, j = T.index(m["t"]), len(T) - 1
        if j - s + 1 != mm or j < 61 or any(T[i] != T[i - 1] + 60 for i in range(j - 60, j + 1)):
            return                      # falta historia o hay un hueco en las velas
        strike, ask = float(m["strike"]), m.get("ask") or {}
        cierres = [v[4] for v in cerr]
        if temprana:
            r2 = [math.log(cierres[i] / cierres[i - 1]) ** 2 for i in range(j - 59, j + 1)]
            sig = math.sqrt(max(sum(r2) / 60, 1e-12))
            z = math.log(cierres[j] / strike) / (sig * math.sqrt(15 - mm))
            perdedor = -1 if z > 0 else 1
            precio = ask.get(perdedor)
            if abs(z) >= 1.0 and precio and 0 < precio < 1:
                self._anotar(m, TEMPRANA, perdedor, precio, ahora, {"btc": cierres[j], "strike": strike, "z": round(z, 3), "m": mm})
        if red:
            self.modelo = self.modelo or PRED.cargar()
            r = PRED.rasgos(cierres, [v[2] for v in cerr], [v[3] for v in cerr], [v[5] for v in cerr], s, mm, strike, T[j]) \
                if self.modelo else None
            if r is not None:
                x, lado = r
                p = PRED.predecir(self.modelo, x)
                precio = ask.get(lado)
                self.ultima_red = {"t": m["t"], "m": mm, "lado": lado, "p": round(p, 5), "precio_max": round(0.98 * p, 4), "ask": precio}
                if precio and 0 < precio < 0.98 * p:
                    self._anotar(m, RED, lado, precio, ahora, {"btc": cierres[j], "strike": strike, "p_red": round(p, 5),
                                                               "precio_max": round(0.98 * p, 4), "m": mm})

    # ------------------------------------------------------------ liquidación y resumen
    def _liquidar(self, ahora):
        """Una consulta por mercado cada 30 s, y su ganador se aplica a todas las compras de ese mercado (antes liquidaba una
        compra cada 30 s: con cinco compras en una ventana tardaba dos minutos y medio)."""
        pendientes = {}
        for o in self.ops:
            if o["res"] is None and ahora >= o["t"] + 960:
                pendientes.setdefault(o["topic"], []).append(o)
        cambio = False
        for topic, ops in pendientes.items():
            if ahora - self.t_resultado.get(topic, 0) < 30:
                continue
            self.t_resultado[topic] = ahora
            try:
                ganador = C.resultado(topic)
            except Exception as ex:
                self.log(f"pérdida real: sin resultado de {topic} ({type(ex).__name__})")
                continue
            for o in ops:
                if ganador is None:
                    if ahora > o["t"] + 7200:
                        o["res"] = -1  # sin resolver en dos horas (o empate, que el mercado reparte 50-50): no cuenta
                        cambio = True
                    continue
                o["res"] = 1 if ganador == o["lado"] else 0
                o["neto"] = round(APUESTA * (1 - o["comision"]) / o["precio"] - APUESTA, 4) if o["res"] else -APUESTA
                cambio = True
        if cambio:
            self._guardar()

    @staticmethod
    def _cuenta(ops):
        por = {}
        for o in ops:
            if o.get("res") not in (0, 1):
                continue
            x = por.setdefault(o["regla"], {"n": 0, "k": 0, "apostado": 0.0, "neto": 0.0, "contratos": 0.0})
            x["n"] += 1
            x["k"] += o["res"]
            x["apostado"] += APUESTA
            x["neto"] = round(x["neto"] + o["neto"], 4)
            x["contratos"] = round(x["contratos"] + (o.get("contratos") or contratos(o["precio"], o.get("comision", 0.02))), 2)
        tot = {"n": sum(x["n"] for x in por.values()), "k": sum(x["k"] for x in por.values()),
               "apostado": sum(x["apostado"] for x in por.values()), "neto": round(sum(x["neto"] for x in por.values()), 4),
               "contratos": round(sum(x["contratos"] for x in por.values()), 2)}
        return tot, por

    def resumen(self):
        """Las cifras de arriba (n, k, apostado, neto, contratos, por_regla) son de la serie vigente; «antes» lleva la anterior."""
        tot, por = self._cuenta([o for o in self.ops if o.get("serie", 1) == SERIE])
        antes, por_antes = self._cuenta([o for o in self.ops if o.get("serie", 1) != SERIE])
        ultimas = [{k: o.get(k) for k in ("t", "regla", "lado", "precio", "contratos", "resta_s", "res", "neto", "serie")}
                   for o in self.ops[-8:]]
        return {**tot, "por_regla": por, "abiertas": sum(1 for o in self.ops if o["res"] is None), "ultimas": ultimas,
                "red": self.ultima_red, "hora": int(C.ahora()), "serie": SERIE,
                "antes": {**antes, "por_regla": por_antes, "nota": NOTA_SERIE_1} if antes["n"] else None,
                "fuente": f"{FUENTE}, libro real de Predict.fun (solo lectura); apertura y precio de contado de Binance",
                **({"comprador": self.extra} if self.extra else {})}

    def _enviar_placa(self):
        """En un hilo aparte: si la placa está apagada, la espera de 6 s no frena la lectura del libro (12/11/2026: con la placa
        desconectada el bucle se detenía 6 s cada minuto, también en los últimos 3 min). Avisa una vez al caer y otra al volver."""
        if not PLACA or (self._hilo and self._hilo.is_alive()):
            return
        datos = json.dumps(self.resumen()).encode()

        def enviar():
            try:
                req = urllib.request.Request(PLACA + "/real", data=datos, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=6).read()
                if self._placa_caida:
                    self._placa_caida = False
                    self.log("pérdida real: la placa volvió a recibir")
            except Exception as ex:
                if not self._placa_caida:
                    self._placa_caida = True
                    self.log(f"pérdida real: la placa no recibe ({type(ex).__name__}); avisaré cuando vuelva")

        self._hilo = threading.Thread(target=enviar, daemon=True)
        self._hilo.start()
