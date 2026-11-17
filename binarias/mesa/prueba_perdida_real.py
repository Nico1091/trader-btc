"""Prueba del papel de «comprar sobre la pérdida» con precio real (12/11/2026). Sin red, sin llave y sin tocar los datos reales:
el libro, las velas de contado, el reloj y el ganador oficial son simulados. Uso: python -I prueba_perdida_real.py"""
import json
import math
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ["PRECIO_PLACA"] = ""  # la prueba no le manda nada a la placa
import conexion as C  # noqa: E402
import perdida_real as PR  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
fallas, hechas = [], [0]


def ver(nombre, cond, detalle=""):
    hechas[0] += 1
    if not cond:
        fallas.append(nombre)
    print(("  bien  " if cond else "  FALLA ") + nombre + (f"  [{detalle}]" if detalle and not cond else ""))


T0 = 1794463200  # una ventana de 15 min cualquiera (múltiplo de 900)
reloj = [float(T0)]
ganador = {}
velas_sim = {}   # apertura (s) -> (t, apertura, máximo, mínimo, cierre, volumen), de contado
registro = []


def ruido(t):
    return 0.00028 * math.sin(t / 37.0) + 0.00012 * math.sin(t / 11.0)


def armar_velas(inicio, pasos):
    """Velas seguidas desde `inicio`; pasos = {apertura_s: rendimiento de ese minuto}; el resto lleva un ruido pequeño fijo."""
    velas_sim.clear()
    precio = 73500.0
    for t in range(inicio, inicio + 60 * 140, 60):
        nuevo = precio * math.exp(pasos.get(t, ruido(t)))
        velas_sim[t] = (t, precio, max(precio, nuevo) + 1.5, min(precio, nuevo) - 1.5, nuevo, 12.0 + 3 * math.sin(t / 500.0) ** 2)
        precio = nuevo


def velas_contado(limite=90, plazo=8):
    cerr = [v for t, v in sorted(velas_sim.items()) if t + 60 <= reloj[0]]
    viva = [v for t, v in sorted(velas_sim.items()) if t <= reloj[0] < t + 60]
    return cerr[-limite:], (viva[0] if viva else None)


C.ahora = lambda: reloj[0]
C.velas_contado = velas_contado
C.resultado = lambda topic: ganador.get(topic)
PR.ARCHIVO = os.path.join(tempfile.mkdtemp(), "perdida_real.json")
# dos compras de la serie anterior, como las del archivo real: sin «serie» ni «contratos»
json.dump({"ops": [{"t": T0 - 9000, "topic": 1, "regla": "último ≤ 0.02", "lado": -1, "precio": 0.01, "hora": T0 - 8200, "resta_s": 100,
                    "comision": 0.02, "res": 0, "neto": -1.0},
                   {"t": T0 - 9000, "topic": 1, "regla": "temprana |z| ≥ 1", "lado": 1, "precio": 0.2, "hora": T0 - 8500, "resta_s": 400,
                    "comision": 0.02, "res": 1, "neto": 3.9}]}, open(PR.ARCHIVO, "w", encoding="utf-8"))
p = PR.PerdidaReal(registro.append)


def mercado(t, sube, baja, niveles=None, strike=None, libro_hace=1.0, topic=None):
    """Sin apertura (strike) solo corre «a lo último», que mira el libro; con ella corren también la temprana y la red."""
    m = {"t": t, "topic": topic or t, "abierto": True, "strike": strike, "comision_bps": 200, "ask": {1: sube, -1: baja},
         "bid": {}, "asks": {1: [], -1: []}, "libro_t": reloj[0] - libro_hace}
    if niveles:
        m["asks"][1 if sube < baja else -1] = niveles
    return m


def nuevas(desde):
    return [o for o in p.ops[desde:]]


print("1) a lo último: el perdedor es el lado barato del libro, con sus contratos")
armar_velas(T0 - 60 * 100, {})
n = len(p.ops)
reloj[0] = T0 + 900 - 181
p.paso(reloj[0], mercado(T0, 0.93, 0.08))
ver("a 181 s del cierre todavía no compra", len(p.ops) == n)
reloj[0] = T0 + 900 - 170
p.paso(reloj[0], mercado(T0, 0.93, 0.08, [(0.08, 50.0), (0.09, 100.0), (0.12, 30.0)]), viva=(0, 0, 0, 0, 1.0), velas=[])
o = nuevas(n)
ver("a 170 s con BAJA a 0,08: una compra, la de ≤ 0,10", len(o) == 1 and o[0]["regla"] == "último ≤ 0.10" and o[0]["lado"] == -1, str(o))
ver("precio 0,08 → 12,25 contratos por 1 USDT", o and o[0]["precio"] == 0.08 and o[0]["contratos"] == 12.25, str(o))
ver("había 150 contratos a 0,10 o menos (13 USDT)", o and o[0]["disp"] == 150.0 and o[0]["disp_usdt"] == 13.0, str(o))
ver("queda como serie 2, con los segundos que faltan por la hora de Binance", o and o[0]["serie"] == 2 and o[0]["resta_s"] == 170)
p.paso(reloj[0] + 2, mercado(T0, 0.93, 0.08))
ver("no repite la misma regla en la misma ventana", len(p.ops) == n + 1)
reloj[0] = T0 + 900 - 60
p.paso(reloj[0], mercado(T0, 0.985, 0.02, [(0.02, 400.0), (0.03, 900.0)]))
o = nuevas(n + 1)
ver("a 60 s con BAJA a 0,02: entran ≤ 0,05 y ≤ 0,02", sorted(x["regla"] for x in o) == ["último ≤ 0.02", "último ≤ 0.05"], str(o))
ver("0,02 → 49 contratos por 1 USDT", all(x["contratos"] == 49.0 for x in o))
ver("≤ 0,02 ve 400 contratos; ≤ 0,05 ve 1.300", {x["regla"]: x["disp"] for x in o} == {"último ≤ 0.02": 400.0, "último ≤ 0.05": 1300.0}, str(o))

print("2) márgenes: sin tiempo, con el libro viejo o sin lado barato no compra")
n = len(p.ops)
T1 = T0 + 900
reloj[0] = T1 + 900 - 9
p.paso(reloj[0], mercado(T1, 0.99, 0.01))
ver("a 9 s del cierre no anota (no alcanza el doble toque)", len(p.ops) == n)
reloj[0] = T1 + 900 - 30
p.paso(reloj[0], mercado(T1, 0.99, 0.01, libro_hace=9.0))
ver("con el libro leído hace 9 s no anota", len(p.ops) == n)
p.paso(reloj[0], mercado(T1, 0.55, 0.47))
ver("con los dos lados cerca de 0,50 no anota", len(p.ops) == n)
p.paso(reloj[0], {**mercado(T1, 0.99, 0.01), "abierto": False})
ver("con el mercado cerrado no anota", len(p.ops) == n)
p.paso(reloj[0], mercado(T1, 0.99, 0.01))
ver("y con todo en regla sí: tres compras a 0,01 (98 contratos cada una)", len(p.ops) == n + 3 and all(x["contratos"] == 98.0 for x in nuevas(n)))

print("3) el perdedor sale del libro, no del precio de futuros")
n = len(p.ops)
T2 = T1 + 900
reloj[0] = T2 + 900 - 100
# futuros (la vela «viva» que antes mandaba) dice que BTC va por debajo de la apertura: antes habría mirado SUBE, que va ganando
p.paso(reloj[0], mercado(T2, 0.96, 0.05), viva=(0, 0, 0, 0, 73470.0), velas=[])
o = nuevas(n)
ver("compra BAJA (el barato) aunque futuros esté por debajo de la apertura", len(o) == 2 and all(x["lado"] == -1 for x in o), str(o))

print("4) temprana: velas de contado frente a la apertura oficial, y libro posterior al cierre del minuto")
T3 = T2 + 900
armar_velas(T3 - 60 * 100, {T3: -0.00048, T3 + 60: -0.00048, T3 + 120: -0.00048})
strike = velas_sim[T3][1]
n = len(p.ops)
reloj[0] = T3 + 181
p.paso(reloj[0], mercado(T3, 0.19, 0.83, strike=strike, libro_hace=2.0))  # libro leído 1 s antes del cierre del minuto 3
ver("con el libro anterior al cierre del minuto espera", len(p.ops) == n)
reloj[0] = T3 + 183
p.paso(reloj[0], mercado(T3, 0.19, 0.83, strike=strike, libro_hace=1.0))
o = nuevas(n)
cerr, _ = velas_contado(90)
cs = [v[4] for v in cerr]
sig = math.sqrt(sum(math.log(cs[i] / cs[i - 1]) ** 2 for i in range(len(cs) - 60, len(cs))) / 60)
z = math.log(cs[-1] / strike) / (sig * math.sqrt(12))
ver("minuto 3 con z = %.3f: compra SUBE (el perdedor) a 0,19" % z, len(o) == 1 and o[0]["regla"] == PR.TEMPRANA and o[0]["lado"] == 1
    and o[0]["precio"] == 0.19 and o[0]["m"] == 3, str(o))
ver("la z anotada es la de la fórmula del laboratorio", o and abs(o[0]["z"] - z) < 1e-3 and z <= -1, f"{o and o[0]['z']} frente a {z}")
reloj[0] = T3 + 303
p.paso(reloj[0], mercado(T3, 0.10, 0.92, strike=strike))
ver("no vuelve a comprar la temprana en la misma ventana", len(p.ops) == n + 1)
T4 = T3 + 900
n = len(p.ops)
reloj[0] = T4 + 183
p.paso(reloj[0], mercado(T4, 0.45, 0.57, strike=velas_sim[T4][1]))
ver("con |z| menor que 1 no compra", len(p.ops) == n)
reloj[0] = T4 + 300 + 25
p.paso(reloj[0], mercado(T4, 0.05, 0.97, strike=velas_sim[T4][1] * 1.01))
ver("una mirada que llega 25 s tarde se pierde (no se inventa)", len(p.ops) == n)

print("5) la red al final: misma probabilidad que laboratorio\\perdida_red.py y compra solo por debajo de 0,98 × p")
T5 = T4 + 900
armar_velas(T5 - 60 * 100, {T5 + 60 * i: -0.00009 for i in range(9)})
strike = velas_sim[T5][1]
n = len(p.ops)
reloj[0] = T5 + 600 + 3
m5 = mercado(T5, 0.5, 0.52, strike=strike)
cerr, _ = velas_contado(90)
Ts = [v[0] for v in cerr]
r = PR.PRED.rasgos([v[4] for v in cerr], [v[2] for v in cerr], [v[3] for v in cerr], [v[5] for v in cerr], Ts.index(T5), 10, strike, Ts[-1])
esperado = PR.PRED.predecir(PR.PRED.cargar(), r[0])
m5["ask"][r[1]] = round(0.98 * esperado - 0.011, 2)
p.paso(reloj[0], m5)
o = [x for x in nuevas(n) if x["regla"] == PR.RED]
ver("minuto 10: la red da p = %.4f al perdedor, igual que el laboratorio" % esperado, p.ultima_red and abs(p.ultima_red["p"] - esperado) < 1e-5
    and p.ultima_red["m"] == 10 and p.ultima_red["lado"] == r[1], str(p.ultima_red))
ver("precio por debajo de 0,98 × p: compra", len(o) == 1 and o[0]["precio"] < 0.98 * esperado and o[0]["lado"] == r[1], str(o))
T6 = T5 + 900
armar_velas(T6 - 60 * 100, {T6 + 60 * i: -0.00009 for i in range(9)})
strike = velas_sim[T6][1]
n = len(p.ops)
reloj[0] = T6 + 600 + 3
m6 = mercado(T6, 0.5, 0.52, strike=strike)
cerr, _ = velas_contado(90)
Ts = [v[0] for v in cerr]
r = PR.PRED.rasgos([v[4] for v in cerr], [v[2] for v in cerr], [v[3] for v in cerr], [v[5] for v in cerr], Ts.index(T6), 10, strike, Ts[-1])
m6["ask"][r[1]] = round(0.98 * PR.PRED.predecir(PR.PRED.cargar(), r[0]) + 0.02, 2)
p.paso(reloj[0], m6)
ver("precio por encima de 0,98 × p: no compra", not [x for x in nuevas(n) if x["regla"] == PR.RED])

print("6) liquidación con el ganador oficial y resumen por series")
ganador.update({T0: -1, T1: 1, T2: 1, T3: 1, T5: -r[1]})
reloj[0] = T6 + 900 + 2000
p.paso(reloj[0], None)
reloj[0] += 31
p.paso(reloj[0], None)
por_t = {}
for x in p.ops:
    por_t.setdefault(x["t"], []).append(x)
gan = [x for x in por_t[T0] if x["regla"] == "último ≤ 0.10"][0]
ver("ganó BAJA comprada a 0,08: cobra 12,25 y gana 11,25", gan["res"] == 1 and gan["neto"] == 11.25, str(gan))
ver("las de la ventana que ganó SUBE pierden 1 USDT", all(x["res"] == 0 and x["neto"] == -1.0 for x in por_t[T1]))
ver("la temprana que compró SUBE a 0,19 gana 4,1579", [x for x in por_t[T3] if x["regla"] == PR.TEMPRANA][0]["neto"] == 4.1579)
ver("la ventana sin resultado sigue abierta", all(x["res"] is None for x in por_t.get(T6, [])))
s = p.resumen()
ver("el resumen de arriba es solo la serie 2", s["serie"] == 2 and s["n"] == sum(1 for x in p.ops if x.get("serie") == 2 and x["res"] in (0, 1)), str(s["n"]))
ver("la serie anterior va aparte, sin mezclar", s["antes"] and s["antes"]["n"] == 2 and s["antes"]["k"] == 1 and s["antes"]["neto"] == 2.9, str(s["antes"]))
ver("cuenta los contratos comprados por regla", s["por_regla"]["último ≤ 0.02"]["contratos"] == 49.0 + 98.0, str(s["por_regla"].get("último ≤ 0.02")))
ver("el resumen cabe en la placa (menos de 6 KB)", len(json.dumps(s)) < 6000, str(len(json.dumps(s))))
ver("no se escribió nada en los datos reales", os.path.dirname(PR.ARCHIVO) != os.path.join(AQUI, "datos"))

print(f"\n{hechas[0] - len(fallas)} de {hechas[0]} pruebas bien" + ("" if not fallas else "; FALLAN: " + "; ".join(fallas)))
sys.exit(1 if fallas else 0)
