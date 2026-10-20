"""Simulación de operaciones minuto a minuto con las reglas reales de una cuenta pequeña de contado.

Pensado para que NO aparezcan ganancias que no existen:
- Entrada en la apertura del minuto siguiente al cierre de la vela de señal (nunca al cierre visto).
- Comisión 0,1 % por lado; en la compra Binance la cobra en BTC, en la venta en USDT.
- Cantidades en pasos de 0,00001 BTC y mínimo de 5 USDT; el «polvo» que no se puede vender
  queda aparte y se informa.
- Stop a mercado con deslizamiento; si el minuto abre más allá del stop, se llena en la apertura.
- Si en un mismo minuto se tocan stop y objetivo, se asume el stop (lo peor).
- El paso a «sin pérdida» (breakeven) actúa desde el minuto siguiente al que lo habilita.
- Topes del Trading Plan de Nicolás: 3 % por operación, 15 % diario, 20 % semanal.
"""
import datetime as dt
import math
from dataclasses import dataclass, field

MIN = 60_000
BOGOTA = dt.timezone(dt.timedelta(hours=-5))          # Colombia no tiene horario de verano


@dataclass
class Reglas:
    capital: float = 9.7                 # USDT iniciales (40.000 COP al cambio del día)
    comision: float = 0.001              # por lado, contado sin descuento BNB
    deslizamiento: float = 0.0002        # órdenes a mercado y stops
    paso: float = 0.00001                # LOT_SIZE de BTCUSDT
    nocional_min: float = 5.0            # NOTIONAL de BTCUSDT
    riesgo_max: float = 0.03             # pérdida máxima por operación sobre el capital
    perdida_diaria: float = 0.15
    perdida_semanal: float = 0.20
    max_ops_dia: int = 12
    perdidas_seguidas: int = 3           # tras tantas pérdidas seguidas, pausa
    pausa_min: int = 240                 # minutos de pausa
    largo_solo: bool = True              # contado: solo compras


@dataclass
class Senal:
    t_cierre: int                        # ms UTC del cierre de la vela de señal
    stop_pct: float                      # distancia del stop desde la entrada (fracción)
    objetivo_pct: float                  # distancia del objetivo (fracción)
    max_min: int                         # minutos máximos en la operación
    be_r: float = 1.0                    # en múltiplos de R se mueve el stop a sin pérdida (0 = nunca)
    nombre: str = ""
    rasgos: dict = field(default_factory=dict)


def _dia_semana(t):
    d = dt.datetime.fromtimestamp(t / 1000, BOGOTA)
    return d.date(), d.isocalendar()[:2]


def _bajar_a_paso(q, paso):
    return math.floor(q / paso + 1e-9) * paso


def simular(v1, senales, r=None, indice_de_tiempo=None):
    """v1: velas de 1m. senales: lista ordenada por t_cierre. Devuelve dict con operaciones y métricas."""
    r = r or Reglas()
    if indice_de_tiempo is None:
        indice_de_tiempo = {}
    efectivo = r.capital
    polvo = 0.0
    ops = []
    omitidas = {"posicion_abierta": 0, "minimo": 0, "freno_diario": 0, "freno_semanal": 0,
                "max_dia": 0, "pausa": 0, "sin_datos": 0}
    libre_desde = 0
    pausa_hasta = 0
    seguidas = 0
    dia_actual = semana_actual = None
    inicio_dia = inicio_semana = efectivo
    ops_dia = 0
    t = v1.t
    n = len(t)
    for s in senales:
        if s.t_cierre < libre_desde:
            omitidas["posicion_abierta"] += 1
            continue
        if s.t_cierre < pausa_hasta:
            omitidas["pausa"] += 1
            continue
        j0 = _indice(t, s.t_cierre, indice_de_tiempo)
        if j0 is None or j0 >= n or t[j0] - s.t_cierre > 5 * MIN:
            omitidas["sin_datos"] += 1
            continue
        dia, semana = _dia_semana(t[j0])
        valor = efectivo + polvo * v1.o[j0]
        if dia != dia_actual:
            dia_actual, inicio_dia, ops_dia = dia, valor, 0
        if semana != semana_actual:
            semana_actual, inicio_semana = semana, valor
        if valor <= inicio_dia * (1 - r.perdida_diaria):
            omitidas["freno_diario"] += 1
            continue
        if valor <= inicio_semana * (1 - r.perdida_semanal):
            omitidas["freno_semanal"] += 1
            continue
        if ops_dia >= r.max_ops_dia:
            omitidas["max_dia"] += 1
            continue
        entrada = v1.o[j0] * (1 + r.deslizamiento)
        # tamaño: todo el efectivo salvo que el riesgo por operación exija menos
        perdida_por_unidad = s.stop_pct + 2 * r.comision + r.deslizamiento
        nocional = min(efectivo, r.riesgo_max * valor / perdida_por_unidad)
        q = _bajar_a_paso(nocional / entrada, r.paso)
        if q * entrada < r.nocional_min or q <= 0:
            omitidas["minimo"] += 1
            continue
        coste = q * entrada
        q_neto = q * (1 - r.comision)                  # comisión de compra en BTC
        stop = entrada * (1 - s.stop_pct)
        objetivo = entrada * (1 + s.objetivo_pct)
        umbral_be = entrada * (1 + s.be_r * s.stop_pct) if s.be_r > 0 else float("inf")
        stop_be = entrada * (1 + 2 * r.comision + r.deslizamiento)
        be_activo = False
        fin = min(n - 1, j0 + s.max_min)
        motivo, salida, j = "TIEMPO", None, j0
        for j in range(j0, fin + 1):
            if t[j] - t[j0] > (s.max_min + 30) * MIN:       # hueco grande en los datos
                motivo, salida = "HUECO", v1.o[j] * (1 - r.deslizamiento)
                break
            st = stop_be if be_activo else stop
            if v1.l[j] <= st:
                motivo = "SIN_PERDIDA" if be_activo else "STOP"
                salida = min(v1.o[j], st) * (1 - r.deslizamiento)
                break
            if v1.h[j] >= objetivo * 1.0001:              # la orden límite solo se llena si el precio la atraviesa
                motivo, salida = "OBJETIVO", objetivo
                break
            if not be_activo and v1.h[j] >= umbral_be:
                be_activo = True
        if salida is None:
            salida = v1.c[fin] * (1 - r.deslizamiento)
            j = fin
        # Binance vende del saldo libre total: el polvo de la compra anterior entra en esta venta.
        q_venta = _bajar_a_paso(q_neto + polvo, r.paso)
        polvo = max(q_neto + polvo - q_venta, 0.0)
        recibido = q_venta * salida * (1 - r.comision)
        antes = efectivo
        efectivo = efectivo - coste + recibido
        ganancia = efectivo - antes
        ops_dia += 1
        seguidas = seguidas + 1 if ganancia < 0 else 0
        libre_desde = t[j] + MIN
        if seguidas >= r.perdidas_seguidas:
            pausa_hasta = t[j] + r.pausa_min * MIN
            seguidas = 0
        ops.append({
            "nombre": s.nombre, "t_entrada": t[j0], "t_salida": t[j], "entrada": entrada, "salida": salida,
            "motivo": motivo, "nocional": coste, "ganancia_usdt": ganancia, "ret_pct": ganancia / coste * 100,
            "capital": efectivo + polvo * salida, "rasgos": s.rasgos,
        })
    ultimo = v1.c[-1] if n else 0
    return {"operaciones": ops, "omitidas": omitidas, "efectivo": efectivo, "polvo_btc": polvo,
            "capital_final": efectivo + polvo * ultimo, "capital_inicial": r.capital}


def _indice(t, ms, cache):
    """Primer índice de 1m con t >= ms (búsqueda binaria con memoria)."""
    if ms in cache:
        return cache[ms]
    lo, hi = 0, len(t)
    while lo < hi:
        mid = (lo + hi) // 2
        if t[mid] < ms:
            lo = mid + 1
        else:
            hi = mid
    cache[ms] = lo if lo < len(t) else None
    return cache[ms]


def metricas(res, desde=None, hasta=None):
    ops = [o for o in res["operaciones"]
           if (desde is None or o["t_entrada"] >= desde) and (hasta is None or o["t_entrada"] < hasta)]
    n = len(ops)
    if n == 0:
        return {"ops": 0}
    rets = [o["ret_pct"] for o in ops]
    ganadas = [x for x in rets if x > 0]
    perdidas = [x for x in rets if x <= 0]
    media = sum(rets) / n
    var = sum((x - media) ** 2 for x in rets) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    # curva compuesta por operación (todo el capital en juego, como en la cuenta pequeña)
    capital = 1.0
    pico = 1.0
    caida_max = 0.0
    for x in rets:
        capital *= 1 + x / 100
        pico = max(pico, capital)
        caida_max = max(caida_max, 1 - capital / pico)
    dias = max((ops[-1]["t_salida"] - ops[0]["t_entrada"]) / 86_400_000, 1)
    motivos = {}
    for o in ops:
        motivos[o["motivo"]] = motivos.get(o["motivo"], 0) + 1
    return {
        "ops": n, "acierto_pct": round(len(ganadas) / n * 100, 1),
        "media_pct": round(media, 4), "mediana_pct": round(sorted(rets)[n // 2], 4),
        "factor_beneficio": round(sum(ganadas) / -sum(perdidas), 3) if perdidas and sum(perdidas) < 0 else None,
        "t_estadistico": round(media / (sd / math.sqrt(n)), 2) if sd > 0 else None,
        "retorno_compuesto_pct": round((capital - 1) * 100, 2),
        "caida_max_pct": round(caida_max * 100, 2),
        "ops_por_dia": round(n / dias, 2),
        "motivos": motivos,
    }
