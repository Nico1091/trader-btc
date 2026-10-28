"""Controles de riesgo y registro de ejecución del papel (27/10/2026, investigación cuantitativa, cambios 1 y 2).

Antes, los topes (−4 % al día, −8 % a la semana, −20 % desde el máximo) solo estaban escritos en la guía y en el prompt,
y el papel suponía que toda señal se ejecutaba aunque la rutina no estuviera para poner la orden. Este módulo:

- `papel/ordenes.jsonl`: una línea por orden de papel que Claude decide, con su hora real (`sistema.py orden ...`).
- `papel/libro.jsonl`: una línea por operación cerrada (`sistema.py cerrar AAAA-MM-DD`), marcada «ejecutada» solo si
  hubo una orden de esa estrategia registrada antes del llenado. Cerrar dos veces el mismo día no duplica nada.
- `estado()`: la cuenta de 40.000 pesos rehecha con las operaciones EJECUTADAS que van a pesos, con las restricciones
  reales del contado (paso 0,00001 BTC, mínimo 5 USDT, comisión 0,075 % con BNB), 2 % de riesgo por operación sobre la
  distancia al stop conocida al entrar, una posición a la vez, y los topes. Dice si se puede operar y, si no, por qué.

Solo biblioteca estándar. Las rutas se pueden cambiar con la variable TRADER_PAPEL (lo usan las pruebas)."""
import datetime as dt
import json
import math
import os

UTC = dt.timezone.utc
COP_POR_USDT = 3177.85            # config.json: P2P del 20/10/2026
CAPITAL_USDT = 40000 / COP_POR_USDT
RIESGO = 0.02                     # por operación (guía v3)
TOPE_DIA, TOPE_SEMANA, TOPE_TOTAL = 0.04, 0.08, 0.20
PASO_BTC, NOCIONAL_MIN, COMISION = 0.00001, 5.0, 0.075   # contado BTCUSDT (exchangeInfo del 27/10) y BNB
LIMITE = {"P05b", "P05b+pat", "P05c", "N9"}               # entran con orden límite: la orden tiene que estar antes del llenado


def carpeta():
    return os.environ.get("TRADER_PAPEL") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "papel")


def _leer(nombre):
    ruta = os.path.join(carpeta(), nombre)
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def _escribir(nombre, filas):
    os.makedirs(carpeta(), exist_ok=True)
    ruta = os.path.join(carpeta(), nombre)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in filas:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, ruta)  # nunca queda un archivo a medio escribir


# ---------------------------------------------------------------- órdenes
def registrar_orden(estrategia, dia, nota="", t=None, activo="BTC"):
    """Claude anota una orden de papel en el momento en que la decide (o una condicionada para más tarde).
    activo: BTC por defecto; las de la cartera LC (P05c en ETH, SOL, BNB, XRP, DOGE, ADA) llevan el suyo."""
    t = int(t if t is not None else dt.datetime.now(UTC).timestamp())
    filas = _leer("ordenes.jsonl")
    fila = {"t": t, "hora_utc": dt.datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d %H:%M:%S"), "dia": str(dia),
            "estrategia": estrategia, "nota": nota, "activo": activo}
    filas.append(fila)
    _escribir("ordenes.jsonl", filas)
    return fila


def ejecutada(op, dia, ordenes=None):
    """Una operación del sistema cuenta como ejecutada si hubo una orden de su estrategia registrada antes de la entrada
    (llenado del límite o apertura a mercado) y destinada a ese día: con su «dia» igual al de la operación, o registrada
    desde las 00:00 UTC del día anterior (la condicionada del domingo por la noche para el lunes). AZAR es el testigo:
    se mide siempre (None)."""
    if op["estrategia"] == "AZAR":
        return None
    ordenes = _leer("ordenes.jsonl") if ordenes is None else ordenes
    nombres = {op["estrategia"], op["estrategia"].split("+")[0]}  # una orden de P05b cubre su pieza en pesos (P05b+pat)
    activo = op.get("activo", "BTC")
    d0 = int(dt.datetime.combine(dt.date.fromisoformat(str(dia)), dt.time(), UTC).timestamp())
    return any(o["estrategia"] in nombres and o.get("activo", "BTC") == activo and o["t"] <= op["entrada"]
               and (o["dia"] == str(dia) or o["t"] >= d0 - 86400) for o in ordenes)


# ---------------------------------------------------------------- libro de operaciones cerradas
def guardar_dia(dia, ops, distancias, activo="BTC"):
    """Reemplaza las operaciones del día y del activo en libro.jsonl (idempotente). distancias: estrategia -> distancia."""
    ordenes = _leer("ordenes.jsonl")
    resto = [r for r in _leer("libro.jsonl") if not (r["dia"] == str(dia) and r.get("activo", "BTC") == activo)]
    nuevas = []
    for o in ops:
        if o["motivo"] == "abierta":
            raise ValueError("el día no está completo: hay operaciones abiertas")
        nuevas.append({"dia": str(dia), "libro": o["libro"], "estrategia": o["estrategia"], "lado": o["lado"],
                       "senal": o["senal"], "entrada": o["entrada"], "salida": o["salida"], "pe": o["pe"], "px": o["px"],
                       "bruto": round(o["bruto"], 6), "neto": round(o["neto"], 6), "motivo": o["motivo"], "pesos": o["pesos"],
                       "dist": distancias.get(o["estrategia"], 0.03), "ejecutada": ejecutada(o, dia, ordenes),
                       "activo": activo})
    _escribir("libro.jsonl", sorted(resto + nuevas, key=lambda r: (r["entrada"], r.get("activo", "BTC"), r["estrategia"])))
    return nuevas


# ---------------------------------------------------------------- estado de la cuenta y topes
def _semana(t):
    return dt.datetime.fromtimestamp(t, UTC).isocalendar()[:2]


def cuenta(filas, ahora=None):
    """Rehace la cuenta en pesos con las operaciones dadas (ya filtradas). Devuelve el estado con los topes."""
    efectivo = CAPITAL_USDT
    maximo, libre, parada = CAPITAL_USDT, None, None
    pnl_dia, pnl_sem = {}, {}
    hechas, omitidas = [], []
    for r in sorted(filas, key=lambda r: r["entrada"]):
        saldo = efectivo
        if parada:
            omitidas.append((r, "parada total"))
            continue
        if libre is not None and r["entrada"] < libre:
            omitidas.append((r, "posición abierta"))
            continue
        d = dt.datetime.fromtimestamp(r["entrada"], UTC).date()
        w = _semana(r["entrada"])
        if pnl_dia.get(d, 0.0) <= -TOPE_DIA * saldo:
            omitidas.append((r, "tope del día"))
            continue
        if pnl_sem.get(w, 0.0) <= -TOPE_SEMANA * saldo:
            omitidas.append((r, "tope de la semana"))
            continue
        nocional = min(efectivo, RIESGO * saldo / max(r["dist"], 1e-6))
        q = math.floor(nocional / r["pe"] / PASO_BTC + 1e-9) * PASO_BTC
        if q * r["pe"] < NOCIONAL_MIN:
            omitidas.append((r, f"no cabe: {q * r['pe']:.2f} USDT < {NOCIONAL_MIN:.0f}"))
            continue
        coste = q * r["pe"]
        efectivo -= coste * (1 + COMISION / 100)                       # comisión de compra pagada en BNB
        efectivo += q * r["px"] * (1 - COMISION / 100)                 # venta
        g = efectivo - saldo
        pnl_dia[d] = pnl_dia.get(d, 0.0) + g
        pnl_sem[w] = pnl_sem.get(w, 0.0) + g
        maximo = max(maximo, efectivo)
        if (maximo - efectivo) / maximo >= TOPE_TOTAL:
            parada = dt.datetime.fromtimestamp(r["salida"], UTC).strftime("%Y-%m-%d %H:%M")
        hechas.append((r, coste, g))
        libre = r["salida"]
    ahora = ahora or dt.datetime.now(UTC)
    hoy, sem = ahora.date(), ahora.isocalendar()[:2]
    saldo = efectivo
    if parada:
        bloqueo = f"PARADA TOTAL desde {parada} (−{TOPE_TOTAL * 100:.0f} % desde el máximo): vuelta a papel puro; si hay algo abierto, se cierra a mercado; solo Nicolás decide reabrir"
    elif pnl_sem.get(sem, 0.0) <= -TOPE_SEMANA * saldo:
        bloqueo = f"BLOQUEADA ESTA SEMANA (pérdida de la semana ≥ {TOPE_SEMANA * 100:.0f} %): no se abre nada hasta el lunes 00:00 UTC"
    elif pnl_dia.get(hoy, 0.0) <= -TOPE_DIA * saldo:
        bloqueo = f"BLOQUEADA HOY (pérdida del día ≥ {TOPE_DIA * 100:.0f} %): no se abre nada hasta las 00:00 UTC"
    else:
        bloqueo = None
    return {"saldo_usdt": saldo, "saldo_cop": saldo * COP_POR_USDT, "maximo_cop": maximo * COP_POR_USDT,
            "caida_pct": (maximo - saldo) / maximo * 100, "pnl_hoy_cop": pnl_dia.get(hoy, 0.0) * COP_POR_USDT,
            "pnl_semana_cop": pnl_sem.get(sem, 0.0) * COP_POR_USDT, "operaciones": len(hechas), "omitidas": omitidas,
            "bloqueo": bloqueo, "hechas": hechas}


def estado(ahora=None):
    filas = [r for r in _leer("libro.jsonl") if r["pesos"] and r.get("activo", "BTC") == "BTC"]
    ej = cuenta([r for r in filas if r["ejecutada"]], ahora)
    te = cuenta(filas, ahora)
    return ej, te


def texto_estado(ahora=None):
    ej, te = estado(ahora)
    L = [f"RIESGO · cuenta de 40.000 pesos (contado, 2 % por operación, topes −4 % día / −8 % semana / −20 % total): "
         f"{'OPERABLE' if ej['bloqueo'] is None else ej['bloqueo']}",
         f"  ejecutado: saldo {ej['saldo_cop']:,.0f} COP ({(ej['saldo_cop'] / 40000 - 1) * 100:+.2f} %), caída desde el máximo "
         f"{ej['caida_pct']:.1f} %, hoy {ej['pnl_hoy_cop']:+,.0f}, semana {ej['pnl_semana_cop']:+,.0f}, {ej['operaciones']} operaciones",
         f"  teórico (todas las señales, como si siempre se hubiera estado a tiempo): saldo {te['saldo_cop']:,.0f} COP "
         f"({(te['saldo_cop'] / 40000 - 1) * 100:+.2f} %), {te['operaciones']} operaciones"]
    return "\n".join(L)
