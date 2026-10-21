"""Trading seguido: lectura del mercado segundo a segundo, rasgos, ciclos cortos y su simulación.

Pedido de Nicolás (19/10/2026, precisado el 20/10): operar «seguido», un ciclo tras otro de
segundos a minutos, leyendo el mercado en segundos, minutos, horas y días, con una
probabilidad por ciclo y pausas de seguridad por tandas de 100 a 800 ciclos.

Una sola definición de rasgos sirve al banco de pruebas y al motor en vivo: `Serie` (velas de
1 s) y `Contexto` (velas de 1 min, 15 min y 1 h, interés abierto y financiación) reciben los
mismos datos en los dos casos, y `paso_salida` decide las salidas igual en la simulación y en
el motor. Así lo que se prueba es lo mismo que opera.

Reglas para no inventar ganancias:
- Se decide al cierre del segundo i con datos hasta i; la entrada es en la apertura del
  segundo i+1 (orden de tomador) o con una orden límite que solo se llena si el precio la
  atraviesa (orden de creador).
- Si en un mismo segundo se tocan el stop y el objetivo, cuenta el stop.
- El objetivo es una orden límite: se llena solo si el precio lo supera en 1 punto básico.
- Comisiones de cada instrumento, pasos de cantidad, mínimos de orden y polvo de BTC.
"""
import array
import bisect
import datetime as dt
import itertools
import math
import random
from dataclasses import dataclass, field

import datos
import indicadores as ind

SEG = 1000
MIN = 60_000
HORA = 3_600_000
NAN = float("nan")
BOGOTA = dt.timezone(dt.timedelta(hours=-5))

RASGOS = (
    "r10", "r60", "r300", "vol300", "vol3600", "z60", "fl10", "fl60", "fl300", "rv60", "rn60", "pr300",
    "pr3600", "tend1h", "pend1h", "rsi15m", "pos15m", "rsi1m", "patron1m", "atr1m", "vwap", "r1d", "r3d",
    "oi1h", "fin", "hs", "hc", "retroceso", "techo", "barrido_baja", "barrido_alza",
)
I_VOL3600 = RASGOS.index("vol3600")


def barrera_de(vol3600, segundos, k, minima):
    """Barrera (objetivo = stop, en fracción) que se ajusta a la volatilidad de la última hora:
    k desvíos del recorrido esperado en `segundos`, nunca por debajo de `minima`."""
    sigma_seg = vol3600 / 100 / 60.0 if vol3600 == vol3600 else 0.0      # vol3600 = σ·√3600 en %
    return max(minima, k * sigma_seg * math.sqrt(segundos))
VENTANA_MIN = 3600                     # segundos de historia que exige el rasgo más largo


def _acumulada(valores):
    out = array.array("d", [0.0])
    out.extend(itertools.accumulate(valores))
    return out


# ---------------------------------------------------------------- serie de 1 segundo
class Serie:
    """Velas de 1 s con sumas acumuladas (rasgos en tiempo constante) y bloques de 1 min
    (para saltar minutos en los que no se toca ninguna barrera)."""

    def __init__(self, v, rasgos=True):
        self.t, self.o, self.h, self.l, self.c = v.t, v.o, v.h, v.l, v.c
        self.v, self.tb, self.n = v.v, v.tb, v.n
        self.largo = len(v.t)
        self.desfase = ((MIN - v.t[0] % MIN) % MIN) // SEG if self.largo else 0
        self._bloques()
        self.con_rasgos = rasgos
        if rasgos:
            c = self.c
            self.lc = array.array("d", map(math.log, c))
            lc = self.lc
            r2 = array.array("d", [0.0])
            r2.extend((lc[k] - lc[k - 1]) ** 2 for k in range(1, self.largo))
            self.pv = _acumulada(self.v)
            self.ptb = _acumulada(self.tb)
            self.pn = _acumulada(self.n)
            self.pr2 = _acumulada(r2)
            mx, mn = ind.maximo_minimo(self.h, self.l, 300)
            self.maxh300, self.minl300 = array.array("d", mx), array.array("d", mn)
            mx, mn = ind.maximo_minimo(self.h, self.l, 3600)
            self.maxh3600, self.minl3600 = array.array("d", mx), array.array("d", mn)

    def _bloques(self):
        self.bmax, self.bmin, self.bok = array.array("d"), array.array("d"), []
        k = self.desfase
        while k + 59 < self.largo:
            self.bmax.append(max(self.h[k:k + 60]))
            self.bmin.append(min(self.l[k:k + 60]))
            self.bok.append(self.t[k + 59] - self.t[k] == 59 * SEG and self.t[k] % MIN == 0)
            k += 60

    def indice(self, t_ms):
        """Primer índice con t >= t_ms."""
        return bisect.bisect_left(self.t, t_ms)


def rasgos_segundo(s, i, ctx):
    """Vector de RASGOS para una decisión al cierre del segundo i. None si falta historia."""
    if i < VENTANA_MIN:
        return None
    lc, pv, ptb, pn, pr2 = s.lc, s.pv, s.ptb, s.pn, s.pr2
    x = lc[i]
    r10 = (x - lc[i - 10]) * 100
    r60 = (x - lc[i - 60]) * 100
    r300 = (x - lc[i - 300]) * 100
    var300 = pr2[i + 1] - pr2[i - 299]
    vol300 = math.sqrt(var300) * 100 if var300 > 0 else 0.0
    var3600 = pr2[i + 1] - pr2[i - 3599]
    vol3600 = math.sqrt(var3600) * 100 if var3600 > 0 else 0.0
    z60 = r60 / (vol300 * 0.4472135954999579) if vol300 > 1e-9 else 0.0     # sqrt(60/300)
    fin_ = i + 1

    def flujo(w):
        vol = pv[fin_] - pv[fin_ - w]
        return (ptb[fin_] - ptb[fin_ - w]) / vol - 0.5 if vol > 1e-12 else 0.0

    fl10, fl60, fl300 = flujo(10), flujo(60), flujo(300)
    v60 = pv[fin_] - pv[fin_ - 60]
    v3600 = pv[fin_] - pv[fin_ - 3600]
    rv60 = math.log((v60 + 1e-6) / (v3600 / 60 + 1e-6))
    n60 = pn[fin_] - pn[fin_ - 60]
    n3600 = pn[fin_] - pn[fin_ - 3600]
    rn60 = math.log((n60 + 1) / (n3600 / 60 + 1))
    c = s.c[i]
    rango = s.maxh300[i] - s.minl300[i]
    pr300 = (c - s.minl300[i]) / rango if rango > 0 else 0.5
    rango = s.maxh3600[i] - s.minl3600[i]
    pr3600 = (c - s.minl3600[i]) / rango if rango > 0 else 0.5
    k = ctx
    tend1h, pend1h, pos15m = k["tend1h"], k["pend1h"], k["pos15m"]
    retroceso = 1.0 if (pend1h > 0 and tend1h > 0 and 0.35 <= pos15m <= 0.65) else 0.0
    techo = 1.0 if pos15m >= 0.9 else 0.0
    barrido_baja = 1.0 if (z60 <= -3 and fl60 < -0.1) else 0.0
    barrido_alza = 1.0 if (z60 >= 3 and fl60 > 0.1) else 0.0
    return [r10, r60, r300, vol300, vol3600, z60, fl10, fl60, fl300, rv60, rn60, pr300, pr3600,
            tend1h, pend1h, k["rsi15m"], pos15m, k["rsi1m"], k["patron1m"], k["atr1m"], k["vwap"],
            k["r1d"], k["r3d"], k["oi1h"], k["fin"], k["hs"], k["hc"],
            retroceso, techo, barrido_baja, barrido_alza]


# ---------------------------------------------------------------- marcos mayores
class Contexto:
    """Rasgos de 1 min, 15 min y 1 h, interés abierto y financiación, sin mirar al futuro.

    Para una decisión en el instante T se usa solo lo cerrado antes del minuto en curso
    (M = inicio del minuto de T): la última vela de 1 min es la que empezó en M-1min, la de
    15 min y la de 1 h, las últimas cerradas a esa hora; las métricas de futuros, las
    publicadas hasta M-1min (margen de un minuto de retraso de publicación).
    """

    def __init__(self, v1m, metricas=None, financiacion=None, v1h=None):
        self.v1m = v1m
        t, o, h, l, c, vol = v1m.t, v1m.o, v1m.h, v1m.l, v1m.c, v1m.v
        self.i1m = {x: k for k, x in enumerate(t)}
        self.rsi1m = ind.rsi(c, 14)
        self.atr1m = ind.atr(h, l, c, 14)
        self.vwap1m = ind.vwap_diario(t, h, l, c, vol)
        self.patron1m = [0.0] * len(c)
        for k in range(3, len(c)):
            bajando = c[k] < c[k - 3]
            self.patron1m[k] = float(ind.patrones(o, h, l, c, k, bajando, not bajando)[0])
        v15 = datos.agregar(v1m, 15)
        self.t15 = v15.t
        self.i15 = {x: k for k, x in enumerate(v15.t)}
        self.rsi15 = ind.rsi(v15.c, 14)
        mx, mn = ind.maximo_minimo(v15.h, v15.l, 96)
        self.pos15 = ind.posicion_rango(v15.c, mx, mn)
        v60 = v1h if v1h is not None else datos.agregar(v1m, 60)
        self.c60 = v60.c
        self.i60 = {x: k for k, x in enumerate(v60.t)}
        self.ema50_1h = ind.ema(v60.c, 50)
        self.pend48_1h = ind.pendiente_log(v60.c, 48)
        self.met = metricas
        self.fin = financiacion
        self._cache = {}

    def en(self, T):
        M = T // MIN * MIN
        d = self._cache.get(M)
        if d is None:
            d = self._calcular(M)
            if len(self._cache) > 4096:
                self._cache.clear()
            self._cache[M] = d
        return d

    def _calcular(self, M):
        v = self.v1m
        k1 = self.i1m.get(M - MIN, -1)
        if k1 >= 0:
            c = v.c[k1]
            rsi1m = self.rsi1m[k1]
            atr1m = self.atr1m[k1] / c * 100 if self.atr1m[k1] == self.atr1m[k1] else NAN
            vwap = (c / self.vwap1m[k1] - 1) * 100
            patron = self.patron1m[k1]
            k_1d = self.i1m.get(M - MIN - 1440 * MIN, -1)
            k_3d = self.i1m.get(M - MIN - 4320 * MIN, -1)
            r1d = (c / v.c[k_1d] - 1) * 100 if k_1d >= 0 else NAN
            r3d = (c / v.c[k_3d] - 1) * 100 if k_3d >= 0 else NAN
        else:
            rsi1m = atr1m = vwap = patron = r1d = r3d = NAN
        k15 = self.i15.get(M // (15 * MIN) * (15 * MIN) - 15 * MIN, -1)
        rsi15m = self.rsi15[k15] if k15 >= 0 else NAN
        pos15m = self.pos15[k15] if k15 >= 0 else NAN
        k60 = self.i60.get(M // HORA * HORA - HORA, -1)
        if k60 >= 0 and self.ema50_1h[k60] == self.ema50_1h[k60]:
            tend1h = (self.c60[k60] / self.ema50_1h[k60] - 1) * 100
            pend1h = self.pend48_1h[k60]
        else:
            tend1h = pend1h = NAN
        oi1h = NAN
        if self.met is not None and len(self.met):
            km = bisect.bisect_right(self.met.t, M - MIN) - 1
            if km >= 12 and abs(self.met.t[km] - self.met.t[km - 12] - HORA) <= 5 * MIN \
                    and M - MIN - self.met.t[km] <= 15 * MIN:
                oi1h = (self.met.oi[km] / self.met.oi[km - 12] - 1) * 100
        fin = NAN
        if self.fin is not None and len(self.fin[0]):
            kf = bisect.bisect_right(self.fin[0], M) - 1
            if kf >= 0 and M - self.fin[0][kf] <= 9 * HORA:
                fin = self.fin[1][kf] * 100
        hora = (M % (24 * HORA)) / HORA
        return {"tend1h": tend1h, "pend1h": pend1h, "rsi15m": rsi15m, "pos15m": pos15m, "rsi1m": rsi1m,
                "patron1m": patron, "atr1m": atr1m, "vwap": vwap, "r1d": r1d, "r3d": r3d, "oi1h": oi1h,
                "fin": fin, "hs": math.sin(2 * math.pi * hora / 24), "hc": math.cos(2 * math.pi * hora / 24)}


# ---------------------------------------------------------------- salida de un ciclo
@dataclass
class Posicion:
    largo: bool
    entrada: float                # precio de entrada (ya con deslizamiento)
    tp: float                     # precio de la orden límite de objetivo
    sl: float                     # precio de disparo del stop
    fin: int                      # índice del último segundo permitido (salida por tiempo a su cierre)
    desliz: float = 0.0001


def paso_salida(p, j, o, h, l, c):
    """¿Termina el ciclo en el segundo j? Devuelve (motivo, precio) o None.

    El mismo código decide en la simulación y en el motor en vivo.
    """
    if p.largo:
        if l <= p.sl:
            return "STOP", min(o, p.sl) * (1 - p.desliz)
        if h >= p.tp * 1.0001:
            return "OBJETIVO", p.tp
    else:
        if h >= p.sl:
            return "STOP", max(o, p.sl) * (1 + p.desliz)
        if l <= p.tp * 0.9999:
            return "OBJETIVO", p.tp
    if j >= p.fin:
        return "TIEMPO", c * (1 - p.desliz) if p.largo else c * (1 + p.desliz)
    return None


def recorrer(s, p, j0):
    """Primer segundo en que termina el ciclo, desde j0 (inclusive). Devuelve (motivo, j, precio).

    Salta minutos enteros cuando su máximo y mínimo no tocan ninguna barrera: el resultado es
    idéntico a revisar segundo a segundo (lo comprueba una prueba unitaria).
    """
    o, h, l, c = s.o, s.h, s.l, s.c
    bmax, bmin, bok, off = s.bmax, s.bmin, s.bok, s.desfase
    fin = min(p.fin, s.largo - 1)
    if p.largo:
        alto, bajo = p.tp * 1.0001, p.sl
    else:
        alto, bajo = p.sl, p.tp * 0.9999
    j = j0
    while j <= fin:
        r = j - off
        if r >= 0 and r % 60 == 0 and j + 59 < fin:
            b = r // 60
            if b < len(bok) and bok[b] and bmin[b] > bajo and bmax[b] < alto:
                j += 60
                continue
        res = paso_salida(p, j, o[j], h[j], l[j], c[j])
        if res:
            return res[0], j, res[1]
        j += 1
    j = fin
    return "TIEMPO", j, c[j] * (1 - p.desliz) if p.largo else c[j] * (1 + p.desliz)


def primer_toque(s, j0, barrera, segundos):
    """Hacia dónde se mueve primero el precio desde la apertura del segundo j0: +1 si sube
    `barrera` (atravesándola 1 pb), -1 si baja lo mismo, 0 si no toca ninguna en `segundos`
    (o si toca las dos en el mismo segundo). Simétrico y sin comisiones: es la pregunta de
    dirección pura, separada de la de costos."""
    e = s.o[j0]
    arriba, abajo = e * (1 + barrera) * 1.0001, e * (1 - barrera) * 0.9999
    h, l = s.h, s.l
    bmax, bmin, bok, off = s.bmax, s.bmin, s.bok, s.desfase
    fin = min(j0 + segundos - 1, s.largo - 1)
    j = j0
    while j <= fin:
        r = j - off
        if r >= 0 and r % 60 == 0 and j + 59 <= fin:
            b = r // 60
            if b < len(bok) and bok[b] and bmin[b] > abajo and bmax[b] < arriba:
                j += 60
                continue
        sube, baja = h[j] >= arriba, l[j] <= abajo
        if sube or baja:
            return 0 if (sube and baja) else (1 if sube else -1)
        j += 1
    return 0


# ---------------------------------------------------------------- instrumentos y libros
@dataclass
class Instrumento:
    nombre: str
    largo: bool = True
    corto: bool = False
    com_tomador: float = 0.001
    com_creador: float = 0.001
    entrada_creador: bool = False      # entrada con orden límite que solo se llena si la atraviesan
    espera_creador: int = 10           # segundos que espera la orden límite antes de cancelarse
    tic: float = 0.01
    paso: float = 0.00001
    nocional_min: float = 5.0
    contado: bool = True               # contado: la comisión de compra se cobra en BTC (polvo)
    apalancamiento: float = 1.0
    desliz: float = 0.0001

    def costos(self):
        """(costo si gana, costo si pierde) en fracción: entrada + salida por objetivo o por stop."""
        entrada = self.com_creador if self.entrada_creador else self.com_tomador
        return (entrada + self.com_creador, entrada + self.com_tomador + self.desliz)


INSTRUMENTOS = {
    "contado": Instrumento("Contado BTCUSDT (tomador 0,10 %)"),
    "fdusd": Instrumento("BTC/FDUSD (creador 0 %, tomador 0,10 %)", com_creador=0.0, entrada_creador=True),
    "futuros": Instrumento("Futuros BTCUSDT (creador 0,02 %, tomador 0,05 %)", corto=True, com_tomador=0.0005,
                           com_creador=0.0002, entrada_creador=True, tic=0.1, paso=0.001, nocional_min=50.0,
                           contado=False, apalancamiento=10.0),
}


@dataclass
class Gestion:
    capital: float = 9.7
    riesgo_max: float = 0.03           # Trading Plan: 3 % por operación
    perdida_diaria: float = 0.15       # 15 % diario
    perdida_semanal: float = 0.20      # 20 % semanal
    perdidas_seguidas: int = 5         # tras tantas pérdidas seguidas...
    pausa_perdidas: int = 900          # ...pausa de 15 minutos
    tanda: int = 100                   # ciclos por tanda (100 a 800 según el capital)
    pausa_tanda: int = 1800            # pausa de revisión entre tandas (segundos)
    freno_tanda: float = 0.10          # si una tanda pierde más del 10 %, el libro se detiene
    max_ciclos_dia: int = 600


def tanda_por_capital(capital_usdt):
    """Ciclos por tanda: 100 con poco capital, hasta 800 con capital mayor (configurable)."""
    if capital_usdt <= 50:
        return 100
    if capital_usdt <= 200:
        return 200
    if capital_usdt <= 1000:
        return 400
    return 800


def _abajo(q, paso):
    return math.floor(q / paso + 1e-9) * paso


@dataclass
class Libro:
    """Cuenta en papel de un instrumento. Lleva efectivo, polvo, frenos, tandas y el diario."""
    inst: Instrumento
    gestion: Gestion
    efectivo: float = 0.0
    polvo: float = 0.0
    ciclos: list = field(default_factory=list)
    intentos_sin_llenar: int = 0
    omitidas: dict = field(default_factory=dict)
    detenido: str = ""
    pausa_hasta: int = 0               # instante (ms) desde el que puede volver a entrar
    seguidas: int = 0
    dia: object = None
    semana: object = None
    valor_dia: float = 0.0
    valor_semana: float = 0.0
    ciclos_dia: int = 0
    inicio_tanda: float = 0.0
    tandas: list = field(default_factory=list)

    def __post_init__(self):
        self.efectivo = self.gestion.capital
        self.inicio_tanda = self.gestion.capital

    def valor(self, precio):
        return self.efectivo + self.polvo * precio

    def _omitir(self, motivo):
        self.omitidas[motivo] = self.omitidas.get(motivo, 0) + 1

    def frenos(self, t_ms, precio):
        """Frenos del Trading Plan (hora de Colombia). None si se puede entrar; si no, el
        instante (ms) desde el que vale la pena volver a mirar, y el motivo queda anotado."""
        g = self.gestion
        fecha = dt.datetime.fromtimestamp(t_ms / 1000, BOGOTA)
        dia, semana = fecha.date(), fecha.isocalendar()[:2]
        valor = self.valor(precio)
        if dia != self.dia:
            self.dia, self.valor_dia, self.ciclos_dia = dia, valor, 0
        if semana != self.semana:
            self.semana, self.valor_semana = semana, valor
        manana = dt.datetime.combine(dia + dt.timedelta(days=1), dt.time(), BOGOTA)
        if valor <= self.valor_semana * (1 - g.perdida_semanal):
            self._omitir("freno_semanal")
            lunes = manana + dt.timedelta(days=(7 - manana.weekday()) % 7)
            return int(lunes.timestamp() * 1000)
        if valor <= self.valor_dia * (1 - g.perdida_diaria):
            self._omitir("freno_diario")
            return int(manana.timestamp() * 1000)
        if self.ciclos_dia >= g.max_ciclos_dia:
            self._omitir("max_dia")
            return int(manana.timestamp() * 1000)
        return None

    def tamano(self, precio, stop):
        """Cantidad de BTC para el ciclo, o 0 si no cabe en el 3 % o en el mínimo de la casa."""
        inst, g = self.inst, self.gestion
        costo_gana, costo_pierde = inst.costos()
        riesgo_unidad = stop + costo_pierde
        valor = self.valor(precio)
        nocional = g.riesgo_max * valor / riesgo_unidad
        if inst.contado:
            nocional = min(nocional, self.efectivo)
        else:
            nocional = min(nocional, valor * inst.apalancamiento)
        q = _abajo(nocional / precio, inst.paso)
        if q <= 0 or q * precio < inst.nocional_min:
            return 0.0
        return q

    def cerrar(self, largo, q, entrada, salida, motivo, t_in, t_out, creador_entrada, extra=None):
        """Aplica comisiones y deja el ciclo anotado. Devuelve la ganancia en USDT."""
        inst, g = self.inst, self.gestion
        com_in = inst.com_creador if creador_entrada else inst.com_tomador
        com_out = inst.com_creador if motivo == "OBJETIVO" else inst.com_tomador
        antes = self.valor(salida)
        if inst.contado:
            coste = q * entrada
            q_neto = q * (1 - com_in)                     # la comisión de compra se cobra en BTC
            q_venta = _abajo(q_neto + self.polvo, inst.paso)
            self.polvo = max(q_neto + self.polvo - q_venta, 0.0)
            self.efectivo += q_venta * salida * (1 - com_out) - coste
        else:
            bruto = q * (salida - entrada) if largo else q * (entrada - salida)
            self.efectivo += bruto - q * entrada * com_in - q * salida * com_out
        ganancia = self.valor(salida) - antes
        self.seguidas = self.seguidas + 1 if ganancia < 0 else 0
        self.ciclos_dia += 1
        fila = {"lado": "largo" if largo else "corto", "t_entrada": t_in, "t_salida": t_out,
                "entrada": entrada, "salida": salida, "motivo": motivo, "cantidad": q,
                "ganancia_usdt": ganancia, "ret_pct": ganancia / (q * entrada) * 100 if q else 0.0,
                "capital": self.valor(salida)}
        if extra:
            fila.update(extra)
        self.ciclos.append(fila)
        return ganancia

    def tras_ciclo(self, t_salida, precio):
        """Pausa por pérdidas seguidas y control de tanda. Devuelve el instante (ms) desde el
        que se puede volver a entrar."""
        g = self.gestion
        libre = t_salida + SEG
        if self.seguidas >= g.perdidas_seguidas:
            libre = max(libre, t_salida + g.pausa_perdidas * SEG)
            self.seguidas = 0
            self._omitir("pausas_por_perdidas")
        if len(self.ciclos) % g.tanda == 0:
            valor = self.valor(precio)
            cambio = valor / self.inicio_tanda - 1 if self.inicio_tanda > 0 else 0.0
            ultimos = self.ciclos[-g.tanda:]
            self.tandas.append({"tanda": len(self.tandas) + 1, "ciclos": g.tanda,
                                "acierto_pct": round(sum(1 for x in ultimos if x["ganancia_usdt"] > 0) / g.tanda * 100, 1),
                                "cambio_pct": round(cambio * 100, 3), "capital": round(valor, 4)})
            self.inicio_tanda = valor
            if cambio <= -g.freno_tanda:
                self.detenido = f"tanda {len(self.tandas)} perdió {cambio * 100:.1f} %: espera revisión"
            libre = max(libre, t_salida + g.pausa_tanda * SEG)
        self.pausa_hasta = libre
        return libre


def simular_libro(s_dec, s_ej, desde, hasta, decidir, inst, gestion, segundos):
    """Recorre los segundos [desde, hasta) del libro: decide, entra, sale, anota.

    s_dec: serie con la que se decidió (BTCUSDT). s_ej: serie donde se ejecuta (la misma, o
    BTCFDUSD). decidir(i) -> (lado, barrera) o None; ya incluye probabilidad, costos y margen.
    """
    lib = Libro(inst, gestion)
    o, h, l, c, t = s_ej.o, s_ej.h, s_ej.l, s_ej.c, s_ej.t
    i = desde
    while i < hasta - 1:
        if lib.detenido:
            break
        d = decidir(i)
        if d is None:
            i += 1
            continue
        lado, barrera = d
        if (lado == "largo" and not inst.largo) or (lado == "corto" and not inst.corto):
            i += 1
            continue
        volver = lib.frenos(t[i] + SEG, c[i])
        if volver is not None:
            i = max(i + 1, s_ej.indice(volver))
            continue
        largo = lado == "largo"
        # entrada
        if inst.entrada_creador:
            limite = (c[i] - inst.tic) if largo else (c[i] + inst.tic)
            j = i + 1
            ultimo = min(i + inst.espera_creador, hasta - 1)
            while j <= ultimo and not ((l[j] < limite) if largo else (h[j] > limite)):
                j += 1
            if j > ultimo:
                lib.intentos_sin_llenar += 1
                i = ultimo + 1
                continue
            entrada, j0 = limite, j
        else:
            j0 = i + 1
            entrada = o[j0] * (1 + inst.desliz) if largo else o[j0] * (1 - inst.desliz)
        q = lib.tamano(entrada, barrera)
        if q <= 0:
            lib._omitir("minimo_o_riesgo")
            i = j0
            continue
        if largo:
            p = Posicion(True, entrada, entrada * (1 + barrera), entrada * (1 - barrera), j0 + segundos - 1, inst.desliz)
        else:
            p = Posicion(False, entrada, entrada * (1 - barrera), entrada * (1 + barrera), j0 + segundos - 1, inst.desliz)
        motivo, js, precio = recorrer(s_ej, p, j0)
        lib.cerrar(largo, q, entrada, precio, motivo, t[j0], t[js], inst.entrada_creador)
        i = max(js + 1, s_ej.indice(lib.tras_ciclo(t[js], precio)))
    precio_final = c[min(hasta, s_ej.largo) - 1]
    return lib, precio_final


def resumen_libro(lib, precio_final, dias):
    ops = lib.ciclos
    n = len(ops)
    capital = lib.valor(precio_final)
    base = {"ciclos": n, "capital_inicial": lib.gestion.capital, "capital_final": round(capital, 4),
            "retorno_pct": round((capital / lib.gestion.capital - 1) * 100, 2),
            "ciclos_por_dia": round(n / dias, 1) if dias > 0 else None,
            "sin_llenar": lib.intentos_sin_llenar, "omitidas": lib.omitidas, "detenido": lib.detenido,
            "tandas": lib.tandas[:12]}
    if not n:
        return base
    rets = [x["ret_pct"] for x in ops]
    ganadas = [x for x in rets if x > 0]
    media = sum(rets) / n
    sd = math.sqrt(sum((x - media) ** 2 for x in rets) / (n - 1)) if n > 1 else 0.0
    motivos = {}
    for x in ops:
        motivos[x["motivo"]] = motivos.get(x["motivo"], 0) + 1
    pico, caida = lib.gestion.capital, 0.0
    for x in ops:
        pico = max(pico, x["capital"])
        caida = max(caida, 1 - x["capital"] / pico)
    base.update({"acierto_pct": round(len(ganadas) / n * 100, 1), "media_por_ciclo_pct": round(media, 4),
                 "t_estadistico": round(media / (sd / math.sqrt(n)), 2) if sd > 0 else None,
                 "caida_max_pct": round(caida * 100, 2), "motivos": motivos,
                 "duracion_media_s": round(sum((x["t_salida"] - x["t_entrada"]) / 1000 + 1 for x in ops) / n, 1)})
    return base


def esperanza(b, h, d, costo_gana, costo_pierde):
    """Ganancia esperada por ciclo (fracción del nocional) en largo y en corto.

    b: barrera; h: probabilidad de tocar alguna barrera en el tiempo; d: probabilidad de que,
    si toca, sea la de arriba. Un ciclo que termina por tiempo se cuenta como retorno bruto
    nulo que paga entrada y salida de tomador (costo_pierde).
    """
    gana, pierde = b - costo_gana, b + costo_pierde
    largo = h * (d * gana - (1 - d) * pierde) - (1 - h) * costo_pierde
    corto = h * ((1 - d) * gana - d * pierde) - (1 - h) * costo_pierde
    return largo, corto


def decisor_ev(B, H, D, base, inst, margen, sin_filtro=False):
    """Decide sobre arreglos por segundo (índice relativo a `base`): entra si la ganancia
    esperada después de comisiones supera `margen`. sin_filtro=True es «operar siempre»: entra
    en cada segundo libre por el lado de mayor esperanza, aunque sea negativa."""
    costo_gana, costo_pierde = inst.costos()

    def decidir(i):
        k = i - base
        if k < 0 or k >= len(D):
            return None
        d = D[k]
        if d != d:
            return None
        b = B[k]
        el, ec = esperanza(b, H[k], d, costo_gana, costo_pierde)
        if not inst.corto:
            ec = -1.0
        if sin_filtro:
            return ("largo", b) if el >= ec else ("corto", b)
        if el > margen and el >= ec:
            return "largo", b
        if ec > margen:
            return "corto", b
        return None
    return decidir


def decisor_azar(semilla, tasa, B, base, permitir_corto):
    """Entradas al azar con la misma barrera que habría usado el sistema en ese segundo."""
    rnd = random.Random(semilla)

    def decidir(i):
        k = i - base
        if k < 0 or k >= len(B) or rnd.random() >= tasa:
            return None
        if permitir_corto and rnd.random() < 0.5:
            return "corto", B[k]
        return "largo", B[k]
    return decidir
