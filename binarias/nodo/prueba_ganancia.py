# -*- coding: utf-8 -*-
"""Pruebas del plan v9 · por ganancia de dinero (20/11/2026), criterios A1 a A5 de ganancia/3-PROMPT-PLAN-v9-GANANCIA.md.
Sin red. Si está a mano el medidor de la vigilante (ganancia/vigilante/medidor_ganancia.py), se compara con él.
Uso: python3 -I prueba_ganancia.py   (en el teléfono tarda unos 20 s más que en el PC por la simulación A5)"""
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402

VIG = None
for d in (os.path.join(AQUI, "..", "ganancia", "vigilante"), os.path.join(AQUI, "vigilante")):
    if os.path.exists(os.path.join(d, "medidor_ganancia.py")):
        sys.path.insert(0, d)
        import medidor_ganancia as VIG  # noqa: E402
        break

FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def entradas(resultados, q=0.5, t0=1794000000, W=15, d=-1):
    """Entradas de la libreta: (acierto 1, fallo 0 o empate 0,5) compradas a q, una por ventana."""
    out = []
    for i, x in enumerate(resultados):
        qi = q[i] if isinstance(q, (list, tuple)) else q
        g = d if x == 1 else (0 if x == 0.5 else -d)
        out.append({"t": t0 + i * 60 * W, "dir": d, "v": t0 + i * 60 * W, "q": qi, "g": g, "W": W})
    return out


def repartidos(aciertos, total):
    return [1 if (i * aciertos) % total < aciertos else 0 for i in range(total)]


# ---------------------------------------------------------------- A1: la matemática
ok(abs(N.r_de({"q": 0.46, "g": 1, "dir": 1}) - (0.98 / 0.46 - 1)) < 1e-12, "A1 r: acierto a 0,46 deja 0,98 / 0,46 − 1 (+1,13)")
ok(abs(N.r_de({"q": 0.5, "g": 0, "dir": 1}) - (0.49 / 0.5 - 1)) < 1e-12, "A1 r: empate a 0,50 deja 0,49 / 0,50 − 1 (−0,02)")
ok(N.r_de({"q": 0.3, "g": -1, "dir": 1}) == -1.0, "A1 r: fallo deja −1")
F = N.FRACCIONES
ok(N.cuenta_de_prueba([]) == 1.0, "A1 cuenta de prueba: sin apuestas vale 1")
a_mano = sum(1 + f * 0.96 for f in F) / len(F)
ok(abs(N.cuenta_de_prueba([0.96]) - a_mano) < 1e-12, f"A1 cuenta de prueba: un acierto a 0,50 vale {a_mano:.6f}, igual que a mano")
a_mano = sum((1 + f * 0.96) * (1 - f) * (1 + f * 0.96) for f in F) / len(F)
ok(abs(N.cuenta_de_prueba([0.96, -1.0, 0.96]) - a_mano) < 1e-12, "A1 cuenta de prueba: acierto, fallo y acierto, igual que a mano")
x = [0.96] * 40 + [-1.0] * 10
ok(abs(N.cuenta_de_prueba(x) - N.cuenta_de_prueba(list(reversed(x)))) < 1e-9 * N.cuenta_de_prueba(x),
   "A1 cuenta de prueba: no depende del orden (cada cuenta es un producto)")
ok(N.cuenta_de_prueba([97.0] * 2000) > 1e100 and math.isfinite(N.cuenta_de_prueba([97.0] * 2000)),
   "A1 cuenta de prueba: en logaritmos no se desborda")
e = entradas([1, 1], q=0.5, t0=1794000000) + [{"t": 1794000000 + 300, "dir": 1, "v": 1794000000, "q": 0.5, "g": -1, "W": 15}]
ap = N.retornos(e)
ok(len(ap) == 2 and abs(ap[0][1] - (0.96 - 1) / 2) < 1e-12, "A1 una apuesta por ventana: dos entradas en la misma ventana cuentan como una (la media)")
ok(N.retornos([{"t": 1, "dir": 1, "g": 1}]) == [] and N.retornos([{"t": 1, "dir": 1, "q": 0.5}]) == [],
   "A1 sin precio real o sin ganador oficial no cuenta")

if VIG:
    rnd = random.Random(7)
    pares = [(round(rnd.uniform(0.3, 0.7), 2), 1 if rnd.random() < 0.58 else 0) for _ in range(160)]
    v = VIG.evaluar(pares, k=8, alfa=0.05, minimo=100)
    mio = N.ganancia_de(entradas([w for _q, w in pares], q=[q for q, _w in pares]))
    ok(abs(mio["inf_normal"] - v["inf_normal"]) < 1e-4 and abs(mio["neto"] - v["neto_usdt"]) < 1e-3,
       "A1 paridad con el medidor de la vigilante: mismo límite normal y mismo neto")
    if "inf_boot" in mio:
        ok(abs(mio["inf_boot"] - v["inf_boot"]) < 1e-4, "A1 paridad: mismo límite bootstrap (misma semilla y cortes)")
    ok(mio["regla_vigilante"] == v["decision"], f"A1 paridad: misma decisión que la vigilante ({v['decision']})")
    for nombre, prs in (("pierde", [(0.8, 1 if i % 4 else 0) for i in range(400)]),
                        ("gana barato", [(0.2, 1 if i % 4 == 0 else 0) for i in range(1000)]),
                        ("pocas", [(0.3, 1) for _ in range(60)])):
        v = VIG.evaluar(prs, k=8, alfa=0.05, minimo=100)
        mio = N.ganancia_de(entradas([w for _q, w in prs], q=[q for q, _w in prs]))
        ok(mio["regla_vigilante"] == v["decision"], f"A1 paridad «{nombre}»: la regla de la vigilante da lo mismo ({v['decision']})")
else:
    print("(sin el medidor de la vigilante a mano: se salta la paridad A1)")

# ---------------------------------------------------------------- A3: el acierto solo ya no basta
d = N.ganancia_de(entradas([1] * 25))
ok(not d["alto"] and d["estado"] == N.POCA and d["n"] == 25, "A3 25 de 25: MUESTRA INSUFICIENTE, no es alto")
d = N.ganancia_de(entradas(repartidos(80, 100), q=0.86))
ok(not d["alto"] and d["neto"] < 0, "A3 80 de 100 pagando 0,86: pierde dinero aunque acierte 80 %, no es alto")
d = N.ganancia_de(entradas(repartidos(3, 100), q=0.02))
ok(not d["alto"] and d["neto"] > 0 and d["estado"] != N.GANA,
   f"A3 tres aciertos de lotería a 0,02 en 100: neto {d['neto']:+.1f}, pero no demuestra nada ({d['estado']})")

# ---------------------------------------------------------------- A4: una ventaja real sí pasa; la pausa la frena
d = N.ganancia_de(entradas(repartidos(210, 300), q=0.5))
ok(d["alto"] and d["estado"] == N.GANA and d["regla_vigilante"] == N.GANA and d["prueba"] >= 160,
   f"A4 210 de 300 a 0,50: GANA DINERO (demostrado), cuenta de prueba {d['prueba']:.0f}")
d = N.ganancia_de(entradas(repartidos(210, 275) + [0] * 25, q=0.5))
ok(d["demostrada"] and d["pausa"] and not d["alto"], "A4 la misma ventaja con sus últimas 25 perdidas: en pausa, no es alto")
d = N.ganancia_de(entradas(repartidos(62, 100), q=0.5))
ok(not d["alto"], f"A4 62 de 100 a 0,50 (+19 % por apuesta): todavía no se demuestra con 100 ({d['estado']})")
d = N.ganancia_de(entradas(repartidos(160, 400), q=0.25))
ok(d["alto"], f"A4 una ventaja real comprando barato (160 de 400 a 0,25, +57 %) también se demuestra ({d['estado']})")
d = N.ganancia_de(entradas(repartidos(70, 300), q=0.5))
ok(d["estado"] == N.PIERDE and not d["alto"], "A4 70 de 300 a 0,50: PIERDE DINERO (demostrado)")

# ---------------------------------------------------------------- avisos de dinero y ganancia.json
ENV = []
est = {}
g0 = {"fuentes": {"centro|E1": dict(N.ganancia_de(entradas([1, 0] * 10)), nombre="E1"),
                  "centro|E3": dict(N.ganancia_de(entradas(repartidos(210, 300))), nombre="E3")}}
t = N.avisos_dinero({}, est, g0, enviar=ENV.append)
ok(len(ENV) == 1 and "Plan v9" in ENV[0] and "E3" in ENV[0] and "Demuestran ganancia: E3" in ENV[0] and "de 25" not in ENV[0],
   "avisos: al arrancar, un resumen de dinero de cada fuente (sin aciertos de 25)")
ok(N.avisos_dinero({}, est, g0, enviar=ENV.append) is None and len(ENV) == 1, "avisos: sin cambios, no se repite")
g1 = {"fuentes": dict(g0["fuentes"], **{"centro|E3": dict(N.ganancia_de(entradas(repartidos(210, 275) + [0] * 25)), nombre="E3")})}
N.avisos_dinero({}, est, g1, enviar=ENV.append)
ok(len(ENV) == 2 and "EN PAUSA" in ENV[1], "avisos: cuando una fuente demostrada entra en pausa, se avisa una vez")
g2 = {"fuentes": dict(g1["fuentes"], **{"centro|E1": dict(N.ganancia_de(entradas([1, 0] * 50)), nombre="E1")})}
ok(g2["fuentes"]["centro|E1"]["estado"] == N.NO_DEMOSTRADO and N.avisos_dinero({}, est, g2, enviar=ENV.append) is None
   and est["dinero_estados"]["centro|E1"] == N.NO_DEMOSTRADO,
   "avisos: un cambio que no toca la ganancia demostrada (de muestra insuficiente a no demostrado) se guarda sin avisar")

BASE = tempfile.mkdtemp(prefix="ganancia_prueba_")
N.AQUI = BASE
c = {"carpeta": BASE, "centinela": os.path.join(BASE, "c"), "operador": os.path.join(BASE, "o")}
fu = N.Fuentes(c)
d1 = N.ganancia_de(entradas(repartidos(210, 300)))
fu.escribir_ganancia([("centro", "E3", 15, {"dinero": d1}), ("centro", "E1", 15, {"dinero": N.ganancia_de(entradas([0] * 30))})], 1000.0)
g = json.load(open(os.path.join(BASE, "ganancia.json"), encoding="utf-8"))
ok(g["demostradas"] == ["centro|E3"] and g["fuentes"]["centro|E3"]["estado"] == N.GANA and g["umbral_prueba"] == 160
   and g["hora"] == 1000 and g["version"] == N.VERSION, "ganancia.json: estados, demostradas, umbral y hora")
os.utime(os.path.join(BASE, "ganancia.json"), (1, 1))
fu.escribir_ganancia([("centro", "E3", 15, {"dinero": d1}), ("centro", "E1", 15, {"dinero": N.ganancia_de(entradas([0] * 30))})], 1100.0)
ok(os.path.getmtime(os.path.join(BASE, "ganancia.json")) == 1, "ganancia.json: sin cambios y antes de 5 min no se reescribe")
fu.escribir_ganancia([("centro", "E3", 15, {"dinero": d1}), ("centro", "E1", 15, {"dinero": N.ganancia_de(entradas([0] * 30))})], 1400.0)
ok(json.load(open(os.path.join(BASE, "ganancia.json"), encoding="utf-8"))["hora"] == 1400,
   "ganancia.json: a los 5 min se reescribe aunque nada cambie (así se sabe que el nodo sigue vivo)")
shutil.rmtree(BASE, ignore_errors=True)


# ---------------------------------------------------------------- A5: sin ventaja, ¿cuánto arma por azar?
def simular(reps, apuestas=1000, fuentes=8, semilla=20261120):
    """Fuentes sin ventaja (cada apuesta acierta exactamente su equilibrio, q / 0,98, con q entre 0,30 y 0,70), mirando después
    de cada apuesta. Se lleva en paralelo la regla completa del plan v9 y la regla fija sola (con su límite normal, que con
    estos precios casi coincide con el bootstrap; el bootstrap se hace solo cuando la cuenta de prueba ya pasó el umbral)."""
    rng = random.Random(semilla)
    z = N.NormalDist().inv_cdf(1 - N.ALFA / N.K_FUENTES)
    arma_v9 = arma_fija = 0
    for _ in range(reps):
        v9 = fija = False
        for _f in range(fuentes):
            logs = [0.0] * len(N.FRACCIONES)
            s = s2 = 0.0
            rs = []
            for i in range(apuestas):
                q = rng.uniform(0.30, 0.70)
                r = N.PAGO / q - 1 if rng.random() < q / N.PAGO else -1.0
                rs.append(r)
                s += r
                s2 += r * r
                for j, f in enumerate(N.FRACCIONES):
                    logs[j] += math.log1p(f * r)
                n = i + 1
                if n < N.MINIMO:
                    continue
                m = s / n
                sd = math.sqrt(max(0.0, (s2 - n * m * m) / (n - 1)))
                if m - z * sd / math.sqrt(n) <= 0:
                    continue
                fija = True
                mx = max(logs)
                if math.exp(mx) * sum(math.exp(x - mx) for x in logs) / len(logs) < N.UMBRAL_PRUEBA:
                    continue
                if N.remuestreo(rs, N.ALFA / N.K_FUENTES)[0] > 0:
                    v9 = True
                    break
        arma_v9 += v9
        arma_fija += fija
    return arma_v9 / reps, arma_fija / reps


reps = 200   # 20/11/2026: con 40 la muestra es chica (los primeros 40 meses de esta semilla traen 5 armados: 12,5 %); con 200, 3,0 %
t0 = time.time()
p9, pf = simular(reps)
ok(p9 <= 0.05, f"A5 sin ventaja, mirando después de cada apuesta: la regla v9 arma por azar en {100 * p9:.1f} % de {reps} meses de "
               f"8 fuentes x 1.000 apuestas (debe ser 5 % o menos); la regla fija sola, en {100 * pf:.1f} % ({time.time() - t0:.0f} s)")

print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
