#!/usr/bin/env python3
"""Auditor del libro de dinero real del operador de binarias (propuesta del 19/11/2026).

Lee el archivo ordenes.json que escribe el ejecutor del operador (carpeta datos/) y comprueba,
orden por orden, las reglas de dinero que el bloc y el código dicen que se cumplen.

Solo lee. No consulta Binance, no compra, no vende y no escribe nada junto al archivo.
Biblioteca estándar; Python 3.8 o superior.

Uso:
    python3 auditor_reglas_dinero.py RUTA/ordenes.json [--ahora UNIX]

Código de salida: 0 si no hay infracciones, 1 si las hay, 2 si el archivo no se puede leer.
Que no haya infracciones prueba que el operador obedeció sus reglas; no prueba que gane dinero.
"""
import datetime as dt
import json
import sys
import time

COL = dt.timezone(dt.timedelta(hours=-5))   # día de Colombia, como comunes.py del operador
MIN_USDT = 2.0                              # nucleo.py: MIN_USDT
TOPE_SALDO = 0.16                           # nucleo.py: TOPE_SALDO (16 % del saldo)
FRENO_DIA = 0.16                            # ejecutor.py: FRENO_DIA
TOPE_ORDENES_DIA = 20                       # ejecutor.py: TOPE_ORDENES_DIA
INTENTOS_MERCADO = 2                        # ejecutor.py: INTENTOS_MERCADO
PRECIO_MIN, PRECIO_MAX = 0.01, 0.90         # nucleo.py: PRECIO_MIN, PRECIO_MAX
IMPORTE_IA = 2.0                            # ejecutor.py: IMPORTE_IA (orden del dueño, 18/11/2026)
TOLERANCIA_IA = 0.02                        # ejecutor.py: TOLERANCIA_IA
N_FALLIDOS = ("FAILED", "CANCELLED", "CANCELED", "EXPIRED", "REJECTED")
SIN_ACLARAR = ("POR ENVIAR", "DUDOSA")
SIN_CIERRE_S = 86400                        # ejecutor.py: SIN_CIERRE_S
SIN_RESULTADO_S = 172800                    # ejecutor.py: SIN_RESULTADO_S
TOL_USDT = 0.01                             # tolerancia de un céntimo, como el redondeo del freno
VENTANAS = (15, 5)

REGLAS = {
    "R1": "importe de al menos 2 USDT",
    "R2": "orden de hasta el 16 % del saldo al decidir",
    "R3": "orden de la IA de 2 USDT (desde el 18/11/2026)",
    "R4": "como mucho 20 órdenes por día",
    "R5": "una orden por mercado y, como mucho, dos intentos",
    "R6": "freno del día: lo perdido en el peor caso más la orden, sin pasar del 16 % del saldo inicial",
    "R7": "precio cotizado entre 0,01 y 0,90",
    "R8": "precio de la IA como mucho 0,02 por encima del que vio",
    "R9": "cuentas: pago según el resultado, neto = pago - comprado, contratos según el precio",
    "R10": "cobro: todo pago queda registrado como cobrado",
    "R11": "órdenes sin aclarar, sin cierre o sin resultado (solo avisos)",
    "R12": "integridad: id único, mercado de 5 o 15 min y día coherente con la hora",
}
SOLO_AVISO = {"R11"}


def dia_de(t):
    """Día de Colombia de la hora t (segundos Unix), como AAAAMMDD."""
    return dt.datetime.fromtimestamp(t, COL).strftime("%Y%m%d")


def hora_de(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%d/%m/%Y %H:%M")


def fnum(x):
    """El número del campo, o None si falta o no es un número (un campo vacío no cuenta como cero)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def limpia(o):
    """Igual que el ejecutor: Binance dijo que no con claridad y no se compró nada."""
    return bool(o.get("final") and not o.get("comprado")
                and (o.get("estado") == "RECHAZADA" or o.get("estado") in N_FALLIDOS))


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if not isinstance(datos, dict) or not isinstance(datos.get("ordenes"), list):
        raise ValueError("el archivo no tiene la forma de ordenes.json (falta la lista «ordenes»)")
    return datos


class Auditoria:
    def __init__(self, datos, ahora):
        self.ordenes = datos["ordenes"]
        self.dias = datos.get("dias") or {}
        self.ahora = ahora
        self.inf, self.avi, self.sin_dato = {}, {}, {}
        self.pico = None            # (día, fracción del saldo inicial en el peor caso)

    # ------------------------------------------------------------ anotaciones
    def _inf(self, regla, oid, texto):
        self.inf.setdefault(regla, []).append((oid, texto))

    def _avi(self, regla, oid, texto):
        self.avi.setdefault(regla, []).append((oid, texto))

    def _sd(self, regla):
        self.sin_dato[regla] = self.sin_dato.get(regla, 0) + 1

    # ------------------------------------------------------------ revisión
    def revisar(self):
        conteo = {}
        for o in self.ordenes:
            oid = str(o.get("id", "?"))
            conteo[oid] = conteo.get(oid, 0) + 1
        for oid, n in conteo.items():
            if n > 1:
                self._inf("R12", oid, f"id repetido {n} veces")
        for o in self.ordenes:
            self._por_orden(o)
        self._por_dia()
        self._por_mercado()
        self._freno()

    def _por_orden(self, o):
        oid = str(o.get("id", "?"))
        usdt = fnum(o.get("usdt"))
        saldo = fnum(o.get("saldo"))
        cot = fnum(o.get("cotizado"))
        visto = fnum(o.get("visto"))
        comprado = fnum(o.get("comprado")) or 0.0
        res = o.get("res")

        # R1 y R2: importe mínimo y tope del 16 % del saldo al decidir
        if usdt is None:
            self._sd("R1")
        elif usdt + 1e-9 < MIN_USDT:
            self._inf("R1", oid, f"importe {usdt:.2f} USDT, menos de {MIN_USDT:.0f}")
        if usdt is None or saldo is None:
            self._sd("R2")
        elif saldo <= 0 or usdt > TOPE_SALDO * saldo + 1e-9:
            pct = 100 * usdt / saldo if saldo > 0 else float("inf")
            self._inf("R2", oid, f"importe {usdt:.2f} USDT es el {pct:.1f} % del saldo {saldo:.2f} (tope 16 %)")

        # R3: la orden de la IA es de 2 USDT
        if o.get("origen") == "ia":
            if usdt is None:
                self._sd("R3")
            elif abs(usdt - IMPORTE_IA) > 1e-9:
                self._inf("R3", oid, f"orden de la IA de {usdt:.2f} USDT; debe ser {IMPORTE_IA:.0f}")

        # R7 y R8: precio cotizado y tolerancia frente a lo que vio la IA
        if cot is None:
            self._sd("R7")
        elif not PRECIO_MIN - 1e-9 <= cot <= PRECIO_MAX + 1e-9:
            self._inf("R7", oid, f"precio cotizado {cot:.3f} fuera de 0,01 a 0,90")
        if o.get("origen") == "ia":
            if cot is None or visto is None:
                self._sd("R8")
            elif cot > visto + TOLERANCIA_IA + 1e-9:
                self._inf("R8", oid, f"cotizado {cot:.3f} con visto {visto:.3f}: pasa en "
                                     f"{cot - visto:.3f} (tope 0,02)")

        # R9: cuentas de una orden ya resuelta
        if res in (0, 1, 2):
            pago = fnum(o.get("pago"))
            neto = fnum(o.get("neto"))
            contratos = fnum(o.get("contratos")) or 0.0
            if pago is None or neto is None:
                self._inf("R9", oid, "resuelta sin pago o sin neto")
            else:
                esperado = {1: contratos, 2: contratos / 2, 0: 0.0}[res]
                if abs(pago - esperado) > 0.0001:
                    self._inf("R9", oid, f"pago {pago:.4f} no corresponde al resultado {res} (debía ser {esperado:.4f})")
                if abs(neto - (pago - comprado)) > 0.0001:
                    self._inf("R9", oid, f"neto {neto:.4f} distinto de pago - comprado ({pago - comprado:.4f})")
            precio = fnum(o.get("precio")) or cot
            comision = fnum(o.get("comision"))
            if comprado > 0 and precio and comision is not None:
                calculado = comprado * (1 - comision) / precio
                if abs(contratos - calculado) > 0.051 * calculado + 0.0001:
                    self._inf("R9", oid, f"contratos {contratos:.4f} lejos de {calculado:.4f} "
                                         f"(comprado {comprado:.2f} a precio {precio:.3f})")
            elif comprado > 0:
                self._sd("R9")

        # R10: cobro de todo pago
        pago_o = fnum(o.get("pago")) or 0.0
        cobro = o.get("cobro")
        if pago_o > 0:
            if not isinstance(cobro, dict):
                self._inf("R10", oid, f"pago de {pago_o:.2f} USDT sin registro de cobro")
            elif cobro.get("estado") == "SIN COBRAR":
                self._avi("R10", oid, f"sin cobrar: {pago_o:.2f} USDT; cobrar a mano en la app")
            elif cobro.get("estado") != "COBRADO":
                self._avi("R10", oid, f"cobro en estado «{cobro.get('estado')}» ({pago_o:.2f} USDT)")

        # R11: avisos de órdenes sin aclarar, sin cierre o sin resultado
        estado = o.get("estado")
        if estado in SIN_ACLARAR:
            self._avi("R11", oid, f"sin aclarar (estado {estado})")
        he = fnum(o.get("hora_envio"))
        if he is not None:
            edad = self.ahora - he
            if not o.get("final") and estado not in SIN_ACLARAR and edad > SIN_CIERRE_S:
                self._avi("R11", oid, f"sin cierre a las 24 h (estado {estado})")
            if o.get("final") and comprado > 0 and res not in (0, 1, 2) and edad > SIN_RESULTADO_S:
                self._avi("R11", oid, "comprada sin resultado a las 48 h")
            if res == -1:
                self._avi("R11", oid, "sin ganador oficial: revisar en la app")

        # R12: integridad
        W = o.get("W")
        if W not in VENTANAS:
            self._inf("R12", oid, f"mercado de {W} min; solo hay de 5 y de 15")
        if he is not None:
            dia = o.get("dia")
            validos = {dia_de(he), dia_de(fnum(o.get("hora")) or he)}
            if dia not in validos:
                self._inf("R12", oid, f"día {dia} no coincide con la hora de envío ({dia_de(he)} en Colombia)")

    def _grupos_dia(self):
        grupos = {}
        for o in self.ordenes:
            d = o.get("dia") or (dia_de(fnum(o.get("hora_envio"))) if fnum(o.get("hora_envio")) else "sin día")
            grupos.setdefault(d, []).append(o)
        return grupos

    def _por_dia(self):
        # R4: tope de órdenes por día
        for d, lista in self._grupos_dia().items():
            for k, o in enumerate(lista[TOPE_ORDENES_DIA:], start=TOPE_ORDENES_DIA + 1):
                self._inf("R4", str(o.get("id", "?")), f"orden nº {k} del día {d}; el tope es {TOPE_ORDENES_DIA}")

    def _por_mercado(self):
        # R5: una orden por mercado y como mucho dos intentos (las limpias no cuentan, como en el ejecutor)
        mercados = {}
        for o in self.ordenes:
            mercados.setdefault((o.get("W"), o.get("t")), []).append(o)
        for (W, t), lista in mercados.items():
            con_orden = False
            for k, o in enumerate(lista):
                oid = str(o.get("id", "?"))
                if k >= INTENTOS_MERCADO or con_orden:
                    motivo = "segunda orden en un mercado que ya tenía una" if con_orden else f"orden nº {k + 1} en el mismo mercado"
                    self._inf("R5", oid, f"{motivo} ({W} min, inicio {hora_de(t) if t else '?'})")
                if not limpia(o):
                    con_orden = True

    def _freno(self):
        # R6: lo perdido en el peor caso, más la orden nueva, sin pasar del 16 % del saldo inicial del día
        for d, lista in self._grupos_dia().items():
            base = fnum((self.dias.get(d) or {}).get("saldo_inicial"))
            if base is None and lista:
                base = fnum(lista[0].get("saldo_inicial_dia"))
            if base is None or base <= 0:
                self._sd("R6")
                continue
            tope = FRENO_DIA * base
            for i, o in enumerate(lista):
                usdt = fnum(o.get("usdt"))
                t_i = fnum(o.get("hora_envio")) or fnum(o.get("hora")) or 0.0
                if usdt is None:
                    self._sd("R6")
                    continue
                perdido = 0.0
                for j in lista[:i]:
                    hr = fnum(j.get("hora_res"))
                    if j.get("res") in (0, 1, 2) and hr is not None and hr <= t_i:
                        perdido -= fnum(j.get("neto")) or 0.0           # ya liquidada: cuenta su neto
                    elif j.get("final"):
                        perdido += fnum(j.get("comprado")) or 0.0       # cerrada y abierta: cuenta lo comprado
                    else:
                        perdido += fnum(j.get("usdt")) or 0.0           # sin cerrar: cuenta el importe entero
                fraccion = (perdido + usdt) / base
                if self.pico is None or fraccion > self.pico[1]:
                    self.pico = (d, fraccion)
                if perdido + usdt > tope + TOL_USDT:
                    self._inf("R6", str(o.get("id", "?")),
                              f"en el día {d}, lo perdido en el peor caso ({perdido:.2f}) más {usdt:.2f} USDT pasa "
                              f"el 16 % de {base:.2f} ({tope:.2f})")

    # ------------------------------------------------------------ resumen y salida
    def resumen(self):
        r = {"ordenes": len(self.ordenes), "dias": len(self._grupos_dia()), "compradas": 0, "comprado": 0.0,
             "aciertos": 0, "empates": 0, "fallos": 0, "sin_ganador": 0, "abiertas": 0, "neto": 0.0,
             "cobrado": 0.0, "sin_cobrar": 0.0}
        for o in self.ordenes:
            comprado = fnum(o.get("comprado")) or 0.0
            if comprado > 0:
                r["compradas"] += 1
                r["comprado"] += comprado
            res = o.get("res")
            if res in (0, 1, 2):
                r["neto"] += fnum(o.get("neto")) or 0.0
                r["aciertos"] += res == 1
                r["empates"] += res == 2
                r["fallos"] += res == 0
            elif res == -1:
                r["sin_ganador"] += 1
            elif comprado > 0:
                r["abiertas"] += 1
            pago = fnum(o.get("pago")) or 0.0
            est = (o.get("cobro") or {}).get("estado") if isinstance(o.get("cobro"), dict) else None
            if est == "COBRADO":
                r["cobrado"] += pago
            elif est == "SIN COBRAR":
                r["sin_cobrar"] += pago
        return r

    def estado_regla(self, regla):
        n_inf = len(self.inf.get(regla, []))
        n_avi = len(self.avi.get(regla, []))
        n_sd = self.sin_dato.get(regla, 0)
        if regla in SOLO_AVISO:
            base = f"AVISO ({n_avi})" if n_avi else "sin avisos"
        elif n_inf:
            base = f"INCUMPLE ({n_inf})"
        else:
            base = "CUMPLE" + (f", con {n_avi} aviso(s)" if n_avi else "")
        if n_sd:
            base += f" · sin dato en {n_sd} orden(es)"
        return base

    def imprimir(self, ruta):
        r = self.resumen()
        lineas = [
            "AUDITORÍA DEL LIBRO DE DINERO REAL (solo lectura)",
            f"Archivo: {ruta}",
            f"Revisado el {hora_de(self.ahora)} (hora de Colombia)",
            "",
            "Resumen de dinero",
            f"  Órdenes en el libro: {r['ordenes']} en {r['dias']} día(s); compradas: {r['compradas']}, "
            f"por {r['comprado']:.2f} USDT.",
            f"  Resueltas: {r['aciertos'] + r['empates'] + r['fallos']} (aciertos {r['aciertos']}, empates {r['empates']}, "
            f"fallos {r['fallos']}); sin ganador oficial: {r['sin_ganador']}; abiertas: {r['abiertas']}.",
            f"  Neto de las resueltas: {r['neto']:+.2f} USDT. Cobrado según el registro: {r['cobrado']:.2f} USDT; "
            f"sin cobrar: {r['sin_cobrar']:.2f} USDT.",
        ]
        if self.pico:
            lineas.append(f"  Mayor riesgo de un día, en el peor caso: {100 * self.pico[1]:.1f} % del saldo inicial "
                           f"(día {self.pico[0]}; tope 16 %).")
        lineas += ["", "Reglas"]
        for regla, texto in REGLAS.items():
            lineas.append(f"  {regla:<4} {texto}: {self.estado_regla(regla)}")
        if self.inf:
            lineas += ["", "Infracciones (orden por orden)"]
            for regla in REGLAS:
                for oid, texto in self.inf.get(regla, []):
                    lineas.append(f"  [{regla}] {oid}: {texto}")
        if any(self.avi.values()):
            lineas += ["", "Avisos (no son infracciones)"]
            for regla in REGLAS:
                for oid, texto in self.avi.get(regla, []):
                    lineas.append(f"  [{regla}] {oid}: {texto}")
        n_inf = sum(len(v) for v in self.inf.values())
        lineas.append("")
        if n_inf:
            lineas.append(f"VEREDICTO: NO CUMPLE. {n_inf} infracción(es) en el libro. Revíselas antes de seguir.")
        else:
            lineas.append("VEREDICTO: CUMPLE las reglas de dinero revisadas en este libro.")
        lineas.append("Lo que esto NO prueba: que el operador gane. Cumplir las reglas no es ventaja.")
        print("\n".join(lineas))
        return n_inf


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ruta = argv[1]
    ahora = time.time()
    if "--ahora" in argv:
        ahora = float(argv[argv.index("--ahora") + 1])
    try:
        datos = cargar(ruta)
    except (OSError, ValueError) as ex:
        print(f"No pude leer el libro: {ex}")
        return 2
    a = Auditoria(datos, ahora)
    a.revisar()
    return 1 if a.imprimir(ruta) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
