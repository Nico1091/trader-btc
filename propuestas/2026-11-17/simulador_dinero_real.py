#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador del dinero real de las binarias con las reglas que ya están instaladas.

Pregunta que responde: si las señales del Centro fueran azar (o tuvieran una
ventaja pequeña), ¿cuántas órdenes de dinero real haría el operador con sus
reglas de armado, compuerta y frenos, cuánto dinero pondría en riesgo y cuánto
podría perder o ganar en un periodo?

Solo usa la biblioteca estándar de Python (3.11 o superior). No se conecta a
Binance, no envía órdenes, no lee la caja ni el teléfono y no escribe archivos,
salvo que se pida con --json.

Las constantes vienen del código de binarias/operador, binarias/nodo y
binarias/operador/nucleo.py en la rama binarias/plan-v7-2026-11-04, y se citan
junto a cada una. Si cambian allí, cambian aquí.
"""

import argparse
import heapq
import json
import math
import random
import sys
from collections import deque
from dataclasses import dataclass, asdict

# --- Reglas del operador (citas: archivo y línea en la rama binarias/plan-v7-2026-11-04)
COMISION = 0.02            # nucleo.py:19 · el cobro es 0,98 ÷ precio
COBRO = 1.0 - COMISION
VENTANA = 25               # las últimas 25 señales cerradas de cada estrategia del Centro
UMBRAL_ARMAR = 18          # operador.py:52 · UMBRAL_ARMAR = 18 (regla ARMAR_AL_70)
UMBRAL_ORDEN = 19          # nodo: 19 de 25 o más, con ganancia neta (AVANCE.md del aprobador)
FRENO_DIA = 0.16           # ejecutor.py:43 · lo perdido hoy no pasa del 16 % del saldo del inicio del día
TOPE_SALDO = 0.16          # nucleo.py:24 · cada orden no pasa del 16 % del saldo
IMPORTE = 2.0              # ejecutor.py:56 · IMPORTE_IA = 2.0 USDT por orden de la IA
TOPE_ORDENES_DIA = 20      # ejecutor.py:42 · TOPE_ORDENES_DIA = 20
DIA_S = 86400

# Escenarios por defecto (los precios vienen del bloc de binarias; ver LEEME.md)
# La ventaja es cuántos puntos de acierto hay por encima del precio pagado. Con 0 el mercado es justo:
# el acierto real iguala al precio y cada USDT apostado pierde la comisión (2 %). Esa es la hipótesis nula honesta.
VENTAJAS_DEF = (0.0, 0.02, 0.04)
PRECIOS_DEF = (0.46, 0.544, 0.58)            # precios vistos en la caja (SUBE 0,46 · precio medio 0,544 · BAJA 0,58)


# ----------------------------------------------------------------- economía
def pago_bruto(precio):
    """USDT que vuelven por cada USDT apostado si acierta (0,98 ÷ precio; con 0,46 son 2,13)."""
    return COBRO / precio


def ganancia_si_acierta(precio):
    """Ganancia neta por USDT apostado si acierta."""
    return pago_bruto(precio) - 1.0


def equilibrio(precio):
    """Acierto mínimo para no perder: precio ÷ 0,98."""
    return precio / COBRO


def valor_esperado_por_usdt(acierto, precio):
    """Valor esperado por USDT apostado: acierto · ganancia − fallo · 1."""
    return acierto * ganancia_si_acierta(precio) - (1.0 - acierto)


def prob_cola(n, k, p=0.5):
    """P(X >= k) para X binomial(n, p). Con n=25, k=18 y p=0,5 da 2,16 %: el azar que arma."""
    return sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(k, n + 1))


def compuerta_orden(k, precio):
    """El nodo solo manda a la IA un punto con 19 de 25 o más y con ganancia neta no negativa al precio pagado."""
    neto = k * ganancia_si_acierta(precio) - (VENTANA - k)
    return k >= UMBRAL_ORDEN and neto >= -1e-12


# ----------------------------------------------------------------- estado del operador
class Estado:
    """Lo que el operador lleva en memoria: armado, saldo, día, órdenes abiertas y ventanas del Centro."""

    def __init__(self, saldo_inicial):
        self.saldo = float(saldo_inicial)
        self.armado = False
        self.dia = None
        self.saldo_dia = float(saldo_inicial)
        self.pnl_dia = 0.0          # ganancia menos pérdida ya liquidada hoy (lo ganado resta, como en perdido_hoy)
        self.ordenes_dia = 0
        self.ordenes_total = 0
        self.aciertos = 0
        self.abiertas = []          # órdenes que siguen sin cerrar
        self.ventanas = {}          # estrategia -> últimas 25 señales cerradas (1 = acierto, 0 = fallo)
        self.peor_perdido = 0.0     # máximo de lo perdido en un día, en USDT, en el peor caso
        self.max_frac = 0.0         # el mismo máximo como fracción del saldo del inicio del día

    # día y freno
    def fijar_dia(self, dia):
        if dia != self.dia:
            self.dia = dia
            self.saldo_dia = self.saldo
            self.pnl_dia = 0.0
            self.ordenes_dia = 0

    def perdido(self):
        """Lo perdido hoy en el peor caso: pérdida neta liquidada más lo abierto de hoy, entero (ejecutor.perdido_hoy)."""
        abiertas_hoy = sum(o["stake"] for o in self.abiertas if o["dia"] == self.dia)
        return -self.pnl_dia + abiertas_hoy

    def cupo(self):
        """USDT que aún caben hoy dentro del freno, con dos decimales hacia abajo (ejecutor.cupo_hoy)."""
        return math.floor((FRENO_DIA * self.saldo_dia - self.perdido()) * 100 + 1e-9) / 100

    # Centro y armado
    def registrar(self, estrategia, gano):
        q = self.ventanas.get(estrategia)
        if q is None:
            q = self.ventanas[estrategia] = deque(maxlen=VENTANA)
        q.append(1 if gano else 0)

    def k_de(self, estrategia):
        q = self.ventanas.get(estrategia)
        if q is None or len(q) < VENTANA:
            return None
        return sum(q)

    def regla_cumplida(self):
        """Armado automático: alguna estrategia con 18 de 25 o más (operador._armar_solo)."""
        for e in self.ventanas:
            k = self.k_de(e)
            if k is not None and k >= UMBRAL_ARMAR:
                return True
        return False

    # compra
    def motivo_no_comprar(self, k, precio):
        """El primer freno que no deja comprar, o None si puede comprar (ejecutor._frenos y cupo_hoy)."""
        if not self.armado:
            return "no armado"
        if not compuerta_orden(k, precio):
            return "compuerta de 19 de 25 con ganancia"
        if self.ordenes_dia >= TOPE_ORDENES_DIA:
            return "tope diario de órdenes"
        if IMPORTE > TOPE_SALDO * self.saldo + 1e-9:
            return "tope por orden (16 % del saldo)"
        if self.cupo() < IMPORTE - 1e-9:
            return "freno del día"
        return None

    def abrir(self, precio):
        o = {"dia": self.dia, "stake": IMPORTE, "precio": precio}
        self.abiertas.append(o)
        self.ordenes_dia += 1
        self.ordenes_total += 1
        p = self.perdido()
        self.peor_perdido = max(self.peor_perdido, p)
        if self.saldo_dia > 0:
            self.max_frac = max(self.max_frac, p / self.saldo_dia)
        return o

    def liquidar(self, o, gano):
        pnl = o["stake"] * ganancia_si_acierta(o["precio"]) if gano else -o["stake"]
        self.saldo += pnl
        if o["dia"] == self.dia:
            self.pnl_dia += pnl
        self.abiertas.remove(o)
        if gano:
            self.aciertos += 1
        return pnl


# ----------------------------------------------------------------- simulación
@dataclass
class Escenario:
    precio: float               # precio pagado por el lado comprado
    ventaja: float = 0.0        # puntos de acierto por encima del precio (0 = mercado justo)
    saldo0: float = 20.50       # el saldo que el bloc registra en la llave (20,50 USDT)
    dias: int = 30
    estrategias: int = 5        # las cinco del Centro
    senales_dia: float = 16.0   # señales por día en total; el bloc habla de unas 16 al día en el núcleo
    aprobacion: float = 1.0     # fracción de los puntos que la IA aprueba (1 = siempre: el caso más expuesto)
    llenado: float = 1.0        # fracción de las órdenes que se llenan al precio visto (1 = siempre: el caso más expuesto)
    tope_total: float = 0.0     # 0 = sin tope (es lo que hay hoy). Si > 0, no compra más cuando el saldo baja esta fracción del inicial

    @property
    def acierto(self):
        """Acierto real de las señales: el precio pagado más la ventaja."""
        return self.precio + self.ventaja


def replica(cfg, rng):
    """Una réplica: genera las señales del periodo y pasa cada evento (apertura o cierre) por las reglas."""
    horizonte = cfg.dias * DIA_S
    tasa = cfg.senales_dia / cfg.estrategias / DIA_S
    eventos = []
    n = 0
    for s in range(cfg.estrategias):
        t = 0.0
        while True:
            t += rng.expovariate(tasa)
            if t >= horizonte:
                break
            W = 5 if rng.random() < 0.5 else 15      # minutos del mercado de la señal
            gano = rng.random() < cfg.acierto
            heapq.heappush(eventos, (t, 1, n, "abre", s, gano))       # 1: la apertura va después del cierre del mismo instante
            heapq.heappush(eventos, (t + W * 60, 0, n, "cierra", s, gano))
            n += 1
    est = Estado(cfg.saldo0)
    en_orden = {}
    t_armado = None
    suelo = cfg.saldo0 * (1.0 - cfg.tope_total) if cfg.tope_total > 0 else None
    while eventos:
        t, _, idx, tipo, s, gano = heapq.heappop(eventos)
        est.fijar_dia(int(t // DIA_S))
        if tipo == "abre":
            if est.armado and (suelo is None or est.saldo > suelo + 1e-9):
                k = est.k_de(s)
                if k is not None and est.motivo_no_comprar(k, cfg.precio) is None:
                    if rng.random() < cfg.aprobacion and rng.random() < cfg.llenado:
                        en_orden[idx] = est.abrir(cfg.precio)
        else:
            est.registrar(s, gano)
            o = en_orden.pop(idx, None)
            if o is not None:
                est.liquidar(o, gano)
            if not est.armado and est.regla_cumplida():
                est.armado = True
                t_armado = t / DIA_S
    return {
        "pnl": est.saldo - cfg.saldo0,
        "ordenes": est.ordenes_total,
        "aciertos": est.aciertos,
        "armado": est.armado,
        "dia_armado": t_armado,
        "peor_perdido": est.peor_perdido,
        "max_frac": est.max_frac,
    }


def cuantil(xs, q):
    ys = sorted(xs)
    if not ys:
        return float("nan")
    i = min(len(ys) - 1, max(0, int(round(q * (len(ys) - 1)))))
    return ys[i]


def correr(cfg, reps, semilla):
    """Corre las réplicas de un escenario. La réplica r usa la misma semilla en todos los escenarios."""
    filas = []
    for r in range(reps):
        rng = random.Random(semilla * 1000003 + r)
        filas.append(replica(cfg, rng))
    armados = [f for f in filas if f["armado"]]
    total_ord = sum(f["ordenes"] for f in filas)
    total_ac = sum(f["aciertos"] for f in filas)
    pnl = [f["pnl"] for f in filas]
    ev_orden = IMPORTE * valor_esperado_por_usdt(cfg.acierto, cfg.precio)   # por orden colocada; no depende de cuántas se colocan
    return {
        **asdict(cfg),
        "acierto": cfg.acierto,
        "reps": reps,
        "equilibrio": equilibrio(cfg.precio),
        "valor_esperado_por_orden_usdt": ev_orden,
        "p_armado": len(armados) / reps,
        "dia_armado_mediana": cuantil([f["dia_armado"] for f in armados], 0.5) if armados else None,
        "ordenes_media": total_ord / reps,
        "p_alguna_orden": sum(1 for f in filas if f["ordenes"] > 0) / reps,
        "acierto_real_de_ordenes": (total_ac / total_ord) if total_ord else None,
        "pnl_media": sum(pnl) / reps,
        "pnl_p5": cuantil(pnl, 0.05),
        "pnl_p50": cuantil(pnl, 0.50),
        "pnl_p95": cuantil(pnl, 0.95),
        "p_perdida": sum(1 for x in pnl if x < -1e-9) / reps,
        "peor_dia_usdt_p95": cuantil([f["peor_perdido"] for f in filas], 0.95),
        "peor_dia_frac_max": max(f["max_frac"] for f in filas),
    }


# ----------------------------------------------------------------- salida
def fmt(x, d=2, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if pct:
        return f"{100 * x:.{d}f} %".replace(".", ",")
    return f"{x:.{d}f}".replace(".", ",")


def tabla(filas):
    cab = ("ventaja", "precio", "acierto", "equil.", "EV/orden", "P(armado)", "órdenes", "P(≥1 orden)",
           "pnl medio", "pnl P5", "pnl P95", "P(pérdida)", "peor día P95")
    cuerpo = []
    for r in filas:
        cuerpo.append((
            fmt(100 * r["ventaja"], 1, False) + " pts", fmt(r["precio"], 3), fmt(r["acierto"], 2, True),
            fmt(r["equilibrio"], 3, False),
            fmt(r["valor_esperado_por_orden_usdt"]), fmt(r["p_armado"], 0, True), fmt(r["ordenes_media"], 2),
            fmt(r["p_alguna_orden"], 0, True), fmt(r["pnl_media"]), fmt(r["pnl_p5"]), fmt(r["pnl_p95"]),
            fmt(r["p_perdida"], 0, True), fmt(r["peor_dia_usdt_p95"]),
        ))
    anchos = [max(len(c[i]) for c in cuerpo + [cab]) for i in range(len(cab))]
    lin = lambda c: "  ".join(str(v).rjust(anchos[i]) for i, v in enumerate(c))
    out = [lin(cab), lin(tuple("-" * a for a in anchos))]
    out += [lin(c) for c in cuerpo]
    return "\n".join(out)


def lista_numeros(texto):
    """Convierte «0,46; 0.544» en [0.46, 0.544]. La lista va separada por punto y coma, porque la coma es decimal."""
    return [float(x.strip().replace(",", ".")) for x in texto.split(";") if x.strip()]


def principal(argv=None):
    ap = argparse.ArgumentParser(description="Simulador del dinero real de binarias con sus reglas (solo lectura).")
    ap.add_argument("--ventaja", default=";".join(str(x) for x in VENTAJAS_DEF),
                    help="puntos de acierto por encima del precio, separados por punto y coma (por defecto: 0;0.02;0.04). "
                         "0 = mercado justo")
    ap.add_argument("--precio", default=";".join(str(x) for x in PRECIOS_DEF),
                    help="precio pagado por el lado comprado, separados por punto y coma (por defecto: 0.46;0.544;0.58)")
    ap.add_argument("--senales-dia", type=float, default=16.0, help="señales por día en total del Centro (por defecto 16)")
    ap.add_argument("--saldo", type=float, default=20.50, help="saldo inicial en USDT (por defecto 20,50)")
    ap.add_argument("--dias", type=int, default=30, help="días simulados (por defecto 30)")
    ap.add_argument("--reps", type=int, default=1000, help="réplicas por escenario (por defecto 1000)")
    ap.add_argument("--aprobacion", type=float, default=1.0, help="fracción de puntos que la IA aprueba (por defecto 1)")
    ap.add_argument("--llenado", type=float, default=1.0, help="fracción de órdenes llenadas al precio visto (por defecto 1)")
    ap.add_argument("--tope-total", type=float, default=0.0,
                    help="no compra más si el saldo baja esta fracción del inicial, p. ej. 0.25 (por defecto 0 = sin tope, "
                         "como hoy: el bloc solo tiene el freno del día)")
    ap.add_argument("--semilla", type=int, default=2026, help="semilla de las réplicas (por defecto 2026)")
    ap.add_argument("--json", metavar="RUTA", help="escribe todos los resultados en este archivo JSON")
    a = ap.parse_args(argv)

    try:
        ventajas = lista_numeros(a.ventaja)
        precios = lista_numeros(a.precio)
    except ValueError:
        ap.error("--ventaja y --precio deben ser números separados por punto y coma")
    for p in precios:
        if not 0.01 <= p <= 0.99:
            ap.error("--precio debe estar entre 0,01 y 0,99")
    for v in ventajas:
        for p in precios:
            if not 0.0 <= p + v <= 1.0:
                ap.error(f"precio {p} con ventaja {v} da un acierto fuera de 0 a 1")

    print("Simulador del dinero real de binarias (solo lectura, biblioteca estándar)")
    print(f"Reglas: armado 18 de 25 · compuerta 19 de 25 con ganancia · orden {IMPORTE:g} USDT · "
          f"tope por orden {TOPE_SALDO:.0%} del saldo · freno del día {FRENO_DIA:.0%} · máx. {TOPE_ORDENES_DIA} órdenes al día")
    print(f"Escenario: saldo {fmt(a.saldo)} USDT · {a.dias} días · {a.senales_dia:g} señales al día en total · "
          f"{a.reps} réplicas · IA aprueba {fmt(a.aprobacion, 0, True)} · llenado {fmt(a.llenado, 0, True)} · "
          f"tope total {'sin tope' if a.tope_total <= 0 else fmt(a.tope_total, 0, True)}")
    print(f"Referencia: con moneda justa, P(18 o más aciertos de 25) = {fmt(100 * prob_cola(25, 18), 2, False)} %"
          " (la regla de armado mira las cinco estrategias y repite la prueba cada vez que cierra una señal).")
    print("Montos en USDT. «acierto» = precio + ventaja. «equil.» = acierto que hace falta (precio ÷ 0,98). "
          "«EV/orden» = valor esperado de una orden de 2 USDT.")
    print("Con ventaja 0 el mercado es justo: el acierto iguala al precio y cada orden pierde la comisión (EV/orden −0,04).")
    print()

    filas = []
    for v in ventajas:
        for p in precios:
            cfg = Escenario(precio=p, ventaja=v, saldo0=a.saldo, dias=a.dias, senales_dia=a.senales_dia,
                            aprobacion=a.aprobacion, llenado=a.llenado, tope_total=a.tope_total)
            filas.append(correr(cfg, a.reps, a.semilla))
    print(tabla(filas))
    print()
    print("Cómo leer la tabla: «P(armado)» es la probabilidad de que el operador se arme solo en el periodo. "
          "«pnl» es la ganancia o pérdida del periodo, en USDT. «peor día P95» es la pérdida del peor día, "
          "en el 95 % de las réplicas, con el freno del 16 % contado como lo cuenta el ejecutor.")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False, indent=2)
        print(f"Resultados completos en {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
