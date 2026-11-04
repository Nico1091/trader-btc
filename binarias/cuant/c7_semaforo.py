"""C7 (03/11/2026): el «semáforo» papel → real que pidió Nicolás, probado con las apuestas a ciegas de BTCUSDT.

Su idea (03/11): «cuando el bot que ejecuta operaciones normales [en papel] está funcionando con una gran cantidad de
acierto, entonces se ejecuta el verdadero ese día y hace las operaciones; si pierde, se detiene. Para la real no debe
haber apalancamiento».
Reglas escritas antes de ver resultados (no se ajusta nada):
- Secuencias: apuestas a ciegas de BTC del banco (t18 reglas y t19 modelo) y la regla simple de C1 «ruptura al revés».
  Se usa el resultado de entrar 60 s tarde, porque la apuesta real la toca él a mano.
- Semáforos (se decide al empezar el día de Colombia, solo con apuestas ya cerradas):
  S1: acierto de las últimas 50 apuestas de papel >= 60 %.   S2: últimas 100 >= 58 %.   S3: el día anterior >= 65 % con 5+.
- Parada en real: P0 sin parada; P1 se detiene en la primera pérdida del día; P2 en la segunda.
- Monto real fijo de 5 USDT (≈ 15.900 COP), pago 0,85, sin apalancamiento (en binarias no existe).
- Comparación: siempre en real (sin semáforo) y un semáforo al azar con los mismos días (2.000 sorteos): si el semáforo no
  mejora el acierto por encima del azar, no sirve.
Uso: python -I c7_semaforo.py
"""
import datetime as dt
import math
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as B  # noqa: E402
import validacion as V  # noqa: E402
from c1_cruces import datos, es, pct  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
PRUEBAS = os.path.join(B.RAIZ, "pruebas")
MONTO, PAGO = 15900.0, 0.85


def leer_banco(nombre):
    lin = open(os.path.join(PRUEBAS, nombre), encoding="utf-8-sig").read().splitlines()
    cab = lin[0].split(";")
    jf, jr = cab.index("fecha_hora_colombia"), cab.index("resultado_60s_tarde")
    dias, res = [], []
    for f in lin[1:]:
        p = f.split(";")
        dias.append(p[jf][:10])
        res.append(1 if p[jr] == "acierta" else 0)
    return np.array(dias), np.array(res)


def secuencia_ruptura():
    d = datos("BTCUSDT")
    r = d["F"]["ruptura"]
    s = np.where(r == 0, -1, np.where(r == 1, 1, 0))
    m = s != 0
    t = d["t"][m]
    y = d["y"][m]
    gana = (y == s[m]).astype(int)
    col = dt.timezone(dt.timedelta(hours=-5))
    dias = np.array([dt.datetime.fromtimestamp(int(x), col).strftime("%Y-%m-%d") for x in t])
    return dias, gana


def simular(dias, res, regla, parada):
    """Devuelve (apuestas reales, aciertos, ganancia COP, días en real, caída máxima COP)."""
    unicos, ini = np.unique(dias, return_index=True)
    orden = np.argsort(ini)
    unicos, ini = unicos[orden], ini[orden]
    fin = np.r_[ini[1:], len(res)]
    n = k = 0
    saldo, pico, caida, dias_real = 0.0, 0.0, 0.0, 0
    for a, b in zip(ini, fin):
        previas = res[:a]
        if regla == "siempre":
            enciende = True
        elif regla == "S1":
            enciende = len(previas) >= 50 and previas[-50:].mean() >= 0.60
        elif regla == "S2":
            enciende = len(previas) >= 100 and previas[-100:].mean() >= 0.58
        elif regla == "S3":
            ayer = res[ini[max(0, list(ini).index(a) - 1)]:a] if a > 0 else np.array([])
            enciende = len(ayer) >= 5 and ayer.mean() >= 0.65
        else:
            enciende = False
        if not enciende:
            continue
        dias_real += 1
        perdidas = 0
        for g in res[a:b]:
            n += 1
            k += g
            saldo += MONTO * PAGO if g else -MONTO
            pico = max(pico, saldo)
            caida = max(caida, pico - saldo)
            if not g:
                perdidas += 1
                if (parada == "P1" and perdidas >= 1) or (parada == "P2" and perdidas >= 2):
                    break
    return n, k, saldo, dias_real, caida


def azar(dias, res, dias_real_obj, parada, veces=2000, semilla=3112026):
    """Acierto de un semáforo al azar que enciende la misma cantidad de días."""
    rng = np.random.default_rng(semilla)
    unicos, ini = np.unique(dias, return_index=True)
    orden = np.argsort(ini)
    ini = ini[orden]
    fin = np.r_[ini[1:], len(res)]
    accs = []
    for _ in range(veces):
        elegidos = rng.choice(len(ini), size=min(dias_real_obj, len(ini)), replace=False)
        n = k = 0
        for j in elegidos:
            perd = 0
            for g in res[ini[j]:fin[j]]:
                n += 1
                k += g
                if not g:
                    perd += 1
                    if (parada == "P1" and perd >= 1) or (parada == "P2" and perd >= 2):
                        break
        accs.append(k / n if n else np.nan)
    return np.array(accs)


def main():
    L = ["C7 · semáforo papel → real en BTCUSDT (apuestas a ciegas; resultado de entrar 60 s tarde; 5 USDT fijos; pago 0,85)", ""]
    fuentes = [("banco t18 (reglas BTC)", *leer_banco("t18_BTCUSDT_apuestas.csv")),
               ("banco t19 (modelo BTC)", *leer_banco("t19_BTCUSDT_apuestas.csv")),
               ("ruptura al revés (C1)", *secuencia_ruptura())]
    for nombre, dias, res in fuentes:
        total_dias = len(np.unique(dias))
        L.append(f"{nombre}: {len(res):,} apuestas en {total_dias:,} días · acierto con 60 s de retraso {pct(res.mean())}".replace(",", "."))
        for regla in ("siempre", "S1", "S2", "S3"):
            for parada in ("P0", "P1", "P2"):
                n, k, g, dr, cd = simular(dias, res, regla, parada)
                if n == 0:
                    L.append(f"   {regla:<7} {parada}: el semáforo nunca encendió")
                    continue
                acc = k / n
                linea = (f"   {regla:<7} {parada}: {dr:,} días en real ({100 * dr / total_dias:4.1f} %) · {n:,} apuestas · acierto {pct(acc)} · "
                         f"resultado {es(g / 1e6, 2)} M COP · caída máxima {es(cd / 1e6, 2)} M COP")
                if regla != "siempre":
                    a = azar(dias, res, dr, parada, veces=400)
                    p_mejor = float(np.mean(a >= acc))
                    linea += f" · azar con los mismos días: {pct(np.nanmean(a))} (p = {es(p_mejor, 3)})"
                L.append(linea.replace(",", "§").replace(".", ",").replace("§", ".") if False else linea)
        R = V.rachas(res)
        L.append(f"   rachas: tras acertar {pct(R['tras_1_acierto'][0])} · tras fallar {pct(R['tras_1_fallo'][0])} · tras 3 aciertos {pct(R['tras_3_aciertos'][0])}")
        L.append("")
    L.append("Cómo leerlo: si el semáforo sirviera, su acierto sería claramente mayor que el de «siempre» y que el del azar con los")
    L.append("mismos días (p pequeño). Parar en la primera pérdida no cambia el acierto esperado de cada apuesta: solo reduce cuántas")
    L.append("se hacen (menos ganancia si hay ventaja, menos pérdida si no la hay).")
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, "c7_semaforo_BTCUSDT.txt"), "w", encoding="utf-8").write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
