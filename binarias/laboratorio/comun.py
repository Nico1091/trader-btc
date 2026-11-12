"""Laboratorio de binarias BTC/USDT (11/11/2026): constantes y utilidades que comparten todos los módulos.

Solo papel: nada de esto apuesta, ni conoce llaves, ni escribe en la carpeta del centinela. Los criterios de esta hoja se
escribieron antes de ver resultados (PROMPT-FINAL.md, parte 6) y no se cambian mirando lo que dan.
Trampas que se cuidan aquí: en el PC numpy 1.26 usa enteros de 32 bits por defecto (los tiempos van en int64 explícito) y la
suma de Python cambió en la 3.12 (las sumas que importan van con numpy o con bucles)."""
import datetime as dt
import math
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
BASE = os.path.join(AQUI, "lab.db")
PARAR = os.path.join(AQUI, "PARAR")
REGISTRO = os.path.join(AQUI, "laboratorio.log")
RESPALDOS = os.path.join(AQUI, "respaldos")
COL = dt.timezone(dt.timedelta(hours=-5))
UTC = dt.timezone.utc
EN_CAJA = not sys.platform.startswith("win") and os.path.isdir("/data/local/tmp")
PUERTO = 8798  # candado de instancia única y página de estado en 127.0.0.1


def utc(a, m, d):
    return int(dt.datetime(a, m, d, tzinfo=UTC).timestamp())


# Tramos escritos antes de ver resultados. «vivo» es todo lo que el laboratorio mide en tiempo real desde que una forma entra.
TRAMOS = (("aprende", utc(2021, 1, 1), utc(2024, 1, 1)),
          ("elige", utc(2024, 1, 1), utc(2025, 7, 1)),
          ("juzga", utc(2025, 7, 1), utc(2026, 11, 1)))
TRAMO = {n: (a, b) for n, a, b in TRAMOS}
DESDE_PRUEBAS = utc(2023, 12, 1)  # la caja carga velas desde aquí para probar formas (un mes de arranque antes de «elige»)
DESDE_RED = utc(2020, 12, 1)      # los rasgos de la red se calculan desde aquí (un mes de arranque antes de «aprende»)

PLAZOS = (10, 15)
PAGO10 = 0.85                     # Contratos de Evento a 10 min
PRECIO15, COMISION = 0.51, 0.02   # binarias de 15 min de Predict.fun
EQUILIBRIO = {10: 1 / (1 + PAGO10), 15: PRECIO15 / (1 - COMISION)}
PAGOS = {10: (0.80, 0.85, 0.90), 15: (0.50, 0.51, 0.53)}
PASO = {p: math.ceil((60 + 60 * p) / 300) for p in PLAZOS}  # barras de 5 min hasta la siguiente apuesta de la misma forma
UMBRAL_OI = 0.00022               # el mismo de semaforo.py y centro.py (P14b)
MIN_ELIGE, Q_BH = 300, 0.05
MIN_OBS, MIN_APTA, DIAS_SIN_LLEGAR = 100, 300, 30
TOPE_VIVO = 1000
TOPE_FAMILIA = 12  # revisión del 11/11, 20:15: como mucho 12 vivas por familia (mismos disparos, filtros, sentido y plazo)


def neto(res, plazo, x=None):
    """Ganancia por unidad apostada: a 10 min con pago x (0,85); a 15 min comprando a precio x (0,51) con 2 % de comisión."""
    if plazo == 10:
        x = PAGO10 if x is None else x
        return x if res else -1.0
    x = PRECIO15 if x is None else x
    return (1 - COMISION) / x - 1 if res else -1.0


def inicio_dia(t):
    """Medianoche de Colombia (UTC−5) del día que contiene t."""
    t = int(t)
    return t - (t - 18000) % 86400


def hora(t, fmt="%d/%m %H:%M"):
    return dt.datetime.fromtimestamp(t, COL).strftime(fmt)


def num(x, d=1):
    """Número a la colombiana: coma decimal y punto de miles."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, d=1):
    return num(100 * x, d) + " %"


def log(msg):
    linea = f"{hora(time.time(), '%Y-%m-%d %H:%M:%S')} {msg}"
    try:
        with open(REGISTRO, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:
        pass
    if os.environ.get("LAB_ECO"):
        try:
            print(linea, flush=True)
        except Exception:
            pass


def temperatura():
    """Temperatura del procesador de la caja en °C; None en el PC."""
    for zona in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"):
        try:
            with open(zona) as f:
                v = float(f.read().strip())
            return v / 1000 if v > 1000 else v
        except (OSError, ValueError):
            continue
    return None


def parar():
    return os.path.exists(PARAR)
