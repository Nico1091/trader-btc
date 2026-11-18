#!/usr/bin/env python3
"""Simulador de la regla de armado automático del operador de binarias («la regla del 70 %»).

Responde una pregunta concreta: si ninguna estrategia del Centro tiene ventaja, ¿con qué frecuencia la regla
«18 de 25» arma el dinero real por azar? Y si la ventaja es real, ¿cuánto tarda en armar? Compara la regla actual
con alternativas que exigen más apuestas y una cota inferior de Wilson por encima del equilibrio.

Solo usa la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance ni a la caja, no envía órdenes,
no lee ni escribe archivos del operador y no toca binarias/operador/ ni binarias/aprobador/.

Uso:
    python simulador_regla70.py                       # tabla por defecto (1.000 repeticiones, unos segundos)
    python simulador_regla70.py --reps 5000 --dias 60
    python simulador_regla70.py --reglas 18/25,wilson:200:1.96 --p 0.5405,0.56
"""

import argparse
import math
import random
import sys
from collections import deque

PAGO_POR_DEFECTO = 0.85

# Apuestas por día de cada una de las cinco estrategias del Centro. Fuente: bloc de binarias, sección 5,
# «paridad con c12 en 40 días»: 1.155, 585, 109, 51 y 45 señales, es decir, 40 días de cada una.
TASAS_CENTRO_POR_DIA = (1155 / 40, 585 / 40, 109 / 40, 51 / 40, 45 / 40)

REGLA_ACTUAL = "18/25"
REGLAS_POR_DEFECTO = "18/25,30/40,wilson:200:1.96,wilson:400:1.96"
PROBABILIDADES_POR_DEFECTO = "0.50,equilibrio,0.55,0.58"


def equilibrio(pago):
    """Acierto mínimo para no perder en promedio: con pago 0,85 por cada 1 apostado, 1 / (1 + 0,85) = 54,05 %."""
    if not 0 < pago < 10:
        raise ValueError("el pago debe estar entre 0 y 10")
    return 1.0 / (1.0 + pago)


def cota_inferior_wilson(aciertos, apuestas, z=1.96):
    """Límite inferior del intervalo de Wilson para una proporción de aciertos."""
    if apuestas <= 0:
        return 0.0
    p = aciertos / apuestas
    z2 = z * z
    centro = p + z2 / (2 * apuestas)
    margen = z * math.sqrt(p * (1 - p) / apuestas + z2 / (4 * apuestas * apuestas))
    return (centro - margen) / (1 + z2 / apuestas)


def prob_ventana(n, k, p):
    """Probabilidad exacta de al menos k aciertos en n apuestas independientes con probabilidad p de acertar cada una."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


class Regla:
    """Una regla de armado: mira las últimas `ventana` apuestas cerradas de cada estrategia y dice si arma."""

    def __init__(self, nombre, ventana, cumple):
        self.nombre = nombre
        self.ventana = ventana
        self.cumple = cumple  # recibe los aciertos de la ventana llena y devuelve True o False


def parsear_regla(texto, eq):
    """«18/25» (k de n) o «wilson:N:z» (cota inferior de Wilson por encima del equilibrio con N apuestas)."""
    t = texto.strip().lower()
    if "/" in t:
        partes = t.split("/")
        if len(partes) != 2:
            raise ValueError(f"regla «{texto}»: se espera k/n, por ejemplo 18/25")
        k, n = int(partes[0]), int(partes[1])
        if not 1 <= k <= n:
            raise ValueError(f"regla «{texto}»: hace falta 1 <= k <= n")
        return Regla(f"{k} de {n}", n, lambda s, k=k: s >= k)
    if t.startswith("wilson:"):
        partes = t.split(":")
        if len(partes) != 3:
            raise ValueError(f"regla «{texto}»: se espera wilson:N:z, por ejemplo wilson:200:1.96")
        n, z = int(partes[1]), float(partes[2])
        if n < 1 or z <= 0:
            raise ValueError(f"regla «{texto}»: N y z deben ser positivos")
        return Regla(f"Wilson {n} apuestas, z {z:g}", n,
                     lambda s, n=n, z=z: cota_inferior_wilson(s, n, z) >= eq)
    raise ValueError(f"regla «{texto}» no reconocida (use k/n o wilson:N:z)")


def primer_armado(rng, tasas, probabilidades, dias, regla):
    """Día (entero, desde 1) en que la regla arma por primera vez, o None si no arma dentro del plazo.

    Cada estrategia es un proceso de Poisson de cierres (tiempo entre cierres exponencial) con aciertos independientes.
    Un cierre llega a la ventana y la regla se evalúa en ese momento; como la ventana solo cambia al cerrar una apuesta,
    evaluar en cada cierre equivale a mirar cada minuto, salvo por el minuto de retraso. Como cada estrategia se
    evalúa por separado, el primer armado es el mínimo de los primeros armados de las cinco.
    """
    mejor = None
    for tasa, p in zip(tasas, probabilidades):
        t = 0.0
        ventana = deque()
        suma = 0
        while True:
            t += rng.expovariate(tasa)
            if t > dias or (mejor is not None and t >= mejor):
                break
            acierto = 1 if rng.random() < p else 0
            ventana.append(acierto)
            suma += acierto
            if len(ventana) > regla.ventana:
                suma -= ventana.popleft()
            if len(ventana) == regla.ventana and regla.cumple(suma):
                mejor = t
                break
    return None if mejor is None else max(1, math.ceil(mejor))


def estimar(regla, probabilidades, tasas, dias, reps, rng):
    """Devuelve (probabilidad de armar dentro del plazo, mediana de días entre las que arman o None)."""
    dias_armado = []
    for _ in range(reps):
        d = primer_armado(rng, tasas, probabilidades, dias, regla)
        if d is not None:
            dias_armado.append(d)
    prob = len(dias_armado) / reps
    if not dias_armado:
        return prob, None
    dias_armado.sort()
    return prob, dias_armado[len(dias_armado) // 2]


def formato_pct(x):
    return f"{100 * x:.1f} %".replace(".", ",")


def formato_p(p):
    return f"p = {100 * p:.2f} %".replace(".", ",")


def construir_parser():
    ap = argparse.ArgumentParser(
        description="Probabilidad de que la regla de armado automático arme dinero real, con o sin ventaja.")
    ap.add_argument("--dias", type=float, default=30.0, help="días de la simulación (30 por defecto)")
    ap.add_argument("--reps", type=int, default=1000, help="repeticiones por celda (1.000 por defecto)")
    ap.add_argument("--semilla", type=int, default=20261118, help="semilla del generador (siempre la misma salida)")
    ap.add_argument("--pago", type=float, default=PAGO_POR_DEFECTO,
                    help="pago del contrato por cada 1 apostado (0,85 por defecto)")
    ap.add_argument("--reglas", default=REGLAS_POR_DEFECTO,
                    help="reglas separadas por coma: k/n o wilson:N:z (la primera debe ser la actual, 18/25)")
    ap.add_argument("--p", default=PROBABILIDADES_POR_DEFECTO,
                    help="aciertos verdaderos a simular, separados por coma; «equilibrio» es el acierto de no perder")
    ap.add_argument("--tasas", default=None,
                    help="apuestas por día de cada estrategia, cinco números separados por coma (por defecto, las del Centro)")
    return ap


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = construir_parser()
    args = ap.parse_args(argv)
    try:
        if args.dias <= 0 or args.reps < 1:
            raise ValueError("--dias y --reps deben ser positivos")
        eq = equilibrio(args.pago)
        if args.tasas is None:
            tasas = list(TASAS_CENTRO_POR_DIA)
        else:
            tasas = [float(x.replace(",", ".")) for x in args.tasas.split(",")]
            if len(tasas) != 5 or any(t <= 0 for t in tasas):
                raise ValueError("--tasas: se esperan cinco números positivos")
        escenarios = []
        for trozo in args.p.split(","):
            trozo = trozo.strip().lower()
            escenarios.append(eq if trozo == "equilibrio" else float(trozo.replace(",", ".")))
        if any(not 0 <= p <= 1 for p in escenarios):
            raise ValueError("--p: cada probabilidad debe estar entre 0 y 1")
        reglas = [parsear_regla(t, eq) for t in args.reglas.split(",") if t.strip()]
        if not reglas:
            raise ValueError("--reglas: indique al menos una regla")
    except ValueError as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2

    rng = random.Random(args.semilla)
    cabecera = f"{'Regla':<28}" + "".join(f"{formato_p(p):>22}" for p in escenarios)
    print(f"Simulación: {len(tasas)} estrategias, {args.dias:g} días, {args.reps} repeticiones por celda, "
          f"semilla {args.semilla}.")
    print(f"Pago {str(args.pago).replace('.', ',')} por 1; equilibrio {formato_pct(eq)}.")
    print("Celda: probabilidad de que la regla arme dinero real al menos una vez en el plazo, y en paréntesis "
          "la mediana del día del primer armado entre las que arman.")
    print()
    print(cabecera)
    print("-" * len(cabecera))
    for regla in reglas:
        nombre = regla.nombre + (" (actual)" if regla.nombre == "18 de 25" else "")
        celdas = []
        for p in escenarios:
            prob, mediana = estimar(regla, [p] * len(tasas), tasas, args.dias, args.reps, rng)
            celda = f"{formato_pct(prob)}" + (f" ({mediana} d)" if mediana is not None else " (-)")
            celdas.append(f"{celda:>22}")
        print(f"{nombre:<28}" + "".join(celdas))
    print()
    print("Una sola ventana de 25 apuestas (sin tiempo ni varias estrategias), para comparar:")
    for p in escenarios:
        print(f"  {formato_p(p)}: la regla 18 de 25 se cumple con probabilidad "
              f"{formato_pct(prob_ventana(25, 18, p))} en cada ventana.")
    print()
    print("No modela: el control de aptitud del papel (la regla automática no lo exige), la dependencia entre")
    print("estrategias y entre apuestas de una misma hora, los cambios de régimen del mercado y la selección de las")
    print("estrategias entre cientos de variantes (que eleva el acierto aparente de las elegidas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
