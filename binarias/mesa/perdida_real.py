"""Comprar sobre la pérdida con el precio real del libro de Predict.fun (11/11/2026, pedido suyo). Solo papel: no manda órdenes.

Lo llama la Mesa en cada vuelta con el mercado de 15 min en curso (precio de apertura oficial, mejor precio de compra de los
dos lados) y la vela viva de BTC. Regla escrita antes de ver resultados:
- «A lo último»: en los últimos 3 minutos de la ventana, si el lado que va perdiendo frente a la apertura oficial cuesta
  0,02 o menos, 0,05 o menos o 0,10 o menos, se anota una compra de papel de 1 USDT a ese precio (una por umbral y ventana).
- «Temprana»: al cierre de los minutos 3, 5, 7, 9, 11, 13 y 14, la primera mirada con |z| ≥ 1 (z = ln(precio/apertura) /
  (σ60·√(15 − m)), la misma de laboratorio\\perdida.py) compra el lado perdedor al precio real de ese momento.
- Se liquida con el ganador oficial del mercado: ganancia = 1 USDT × (1 − comisión) / precio − 1 si gana; −1 si pierde.
Cada minuto manda el resumen a la placa ESP32 (POST /real), que lo guarda y se lo pasa a la caja para su Telegram.
La llave no sale del PC: la placa y la caja solo reciben precios y resultados."""
import json
import math
import os
import time
import urllib.request

import conexion as C

AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(AQUI, "datos", "perdida_real.json")
PLACA = "http://192.168.20.159:8080"
UMBRALES = (0.02, 0.05, 0.10)
ULTIMOS_S = 180
MINUTOS = (3, 5, 7, 9, 11, 13, 14)
APUESTA = 1.0


class PerdidaReal:
    def __init__(self, log=print):
        self.log = log
        self.ops, self.t_envio, self.t_resultado = [], 0.0, {}
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
        op = {"t": m["t"], "topic": m.get("topic"), "regla": regla, "lado": lado, "precio": precio, "hora": int(ahora),
              "resta_s": int(m["t"] + 900 - ahora), "comision": (m.get("comision_bps") or 200) / 10000, "res": None, **extra}
        self.ops.append(op)
        self.log(f"pérdida real: {regla} compra {'SUBE' if lado > 0 else 'BAJA'} a {precio} ({op['resta_s']} s antes del cierre)")
        self._guardar()

    def paso(self, ahora, m, viva, velas):
        if m and m.get("abierto") and m.get("strike") and viva:
            precio_btc, strike = float(viva[4]), float(m["strike"])
            resta = m["t"] + 900 - ahora
            if precio_btc != strike and 0 < resta <= 900:
                perdedor = -1 if precio_btc > strike else 1
                ask = (m.get("ask") or {}).get(perdedor)
                if ask and 0 < ask < 1:
                    if resta <= ULTIMOS_S:
                        for u in UMBRALES:
                            regla = f"último ≤ {u:.2f}"
                            if ask <= u and not self._ya(m["t"], regla):
                                self._anotar(m, regla, perdedor, ask, ahora, {"btc": precio_btc, "strike": strike})
                    minuto = int((ahora - m["t"]) // 60)
                    if minuto in MINUTOS and not self._ya(m["t"], "temprana |z| ≥ 1") and len(velas) >= 62:
                        cierres = [float(v[4]) for v in velas[-61:]]
                        r2 = [math.log(cierres[i] / cierres[i - 1]) ** 2 for i in range(1, 61)]
                        sig = math.sqrt(max(sum(r2) / 60, 1e-12))
                        z = math.log(precio_btc / strike) / (sig * math.sqrt(15 - minuto))
                        if abs(z) >= 1.0:
                            self._anotar(m, "temprana |z| ≥ 1", perdedor, ask, ahora, {"btc": precio_btc, "strike": strike, "z": round(z, 3)})
        self._liquidar(ahora)
        if ahora - self.t_envio >= 60:
            self.t_envio = ahora
            self._enviar_placa()

    def _liquidar(self, ahora):
        cambio = False
        for o in self.ops:
            if o["res"] is not None or ahora < o["t"] + 960:
                continue
            if ahora - self.t_resultado.get(o["topic"], 0) < 30:
                continue
            self.t_resultado[o["topic"]] = ahora
            try:
                ganador = C.resultado(o["topic"])
            except Exception as ex:
                self.log(f"pérdida real: sin resultado de {o['topic']} ({type(ex).__name__})")
                continue
            if ganador is None:
                if ahora > o["t"] + 7200:
                    o["res"] = -1  # sin resolver en dos horas: no cuenta
                    cambio = True
                continue
            o["res"] = 1 if ganador == o["lado"] else 0
            o["neto"] = round(APUESTA * (1 - o["comision"]) / o["precio"] - APUESTA, 4) if o["res"] else -APUESTA
            cambio = True
        if cambio:
            self._guardar()

    def resumen(self):
        por = {}
        for o in self.ops:
            if o.get("res") not in (0, 1):
                continue
            x = por.setdefault(o["regla"], {"n": 0, "k": 0, "apostado": 0.0, "neto": 0.0})
            x["n"] += 1
            x["k"] += o["res"]
            x["apostado"] += APUESTA
            x["neto"] = round(x["neto"] + o["neto"], 4)
        tot = {"n": sum(x["n"] for x in por.values()), "k": sum(x["k"] for x in por.values()),
               "apostado": sum(x["apostado"] for x in por.values()), "neto": round(sum(x["neto"] for x in por.values()), 4)}
        ultimas = [{k: o.get(k) for k in ("t", "regla", "lado", "precio", "resta_s", "res", "neto")} for o in self.ops[-8:]]
        return {**tot, "por_regla": por, "abiertas": sum(1 for o in self.ops if o["res"] is None), "ultimas": ultimas,
                "hora": int(time.time()), "fuente": "PC, libro real de Predict.fun (solo lectura)"}

    def _enviar_placa(self):
        try:
            datos = json.dumps(self.resumen()).encode()
            req = urllib.request.Request(PLACA + "/real", data=datos, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=6).read()
        except Exception as ex:
            self.log(f"pérdida real: la placa no recibió ({type(ex).__name__})")
