"""Prueba del comprador por ganancia esperada (12/11/2026). Sin red, sin llave y sin tocar los datos reales: el reloj, las
velas de contado, el libro y el ganador oficial son simulados, y todo se escribe en una carpeta temporal.
Uso: python -X utf8 -I prueba_comprador.py"""
import copy
import json
import math
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import comprador as CP  # noqa: E402
import ganancia as G  # noqa: E402
import juez_comprador as J  # noqa: E402  (no «juez»: laboratorio\juez.py existe y perdida_red lo pone primero en la ruta)

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
velas_sim, ganador, registro = {}, {}, []
libro_fn, vivo_fn = [lambda t: {}], [None]


def ruido(t):
    return 0.00028 * math.sin(t / 37.0) + 0.00012 * math.sin(t / 11.0)


def armar_velas(ventana, pasos):
    """Velas seguidas desde 140 min antes de la ventana; pasos = {minuto de la ventana (1 a 15): rendimiento}."""
    velas_sim.clear()
    precio = 73500.0
    for t in range(ventana - 140 * 60, ventana + 20 * 60, 60):
        k = (t - ventana) // 60 + 1
        nuevo = precio * math.exp(pasos.get(k, ruido(t)) if 1 <= k <= 15 else ruido(t))
        velas_sim[t] = (t, precio, max(precio, nuevo) + 1.5, min(precio, nuevo) - 1.5, nuevo, 12.0 + 3 * math.sin(t / 500.0) ** 2)
        precio = nuevo


class Con:
    """La conexión simulada: solo lo que el comprador tiene permitido usar."""

    @staticmethod
    def ahora():
        return reloj[0]

    @staticmethod
    def velas_contado(limite=90, plazo=8):
        cerr = [v for t, v in sorted(velas_sim.items()) if t + 60 <= reloj[0]]
        viva = [v for t, v in sorted(velas_sim.items()) if t <= reloj[0] < t + 60]
        v = viva[0] if viva else None
        if v:  # el precio vivo es la apertura de la vela en curso, salvo que la prueba lo mueva
            v = v[:4] + (vivo_fn[0](reloj[0]) if vivo_fn[0] else v[1],) + v[5:]
        return cerr[-limite:], v

    @staticmethod
    def leer_libros(m):
        lb = libro_fn[0](reloj[0])
        m["ask"] = {k: (lb[k][0][0] if lb.get(k) else None) for k in (1, -1)}
        m["bid"] = {1: None, -1: None}
        m["asks"] = {k: lb.get(k, []) for k in (1, -1)}
        m["libro_t"] = reloj[0]
        return m

    @staticmethod
    def resultado(topic):
        return ganador.get(topic)


def mercado(t, topic):
    return {"t": t, "topic": topic, "strike": velas_sim[t][1], "abierto": True, "comision_bps": 200, "ask": {}, "bid": {}, "asks": {}}


def esperado(t, mm, vivo=None, resta=None):
    """El vector calculado aparte, con las mismas velas, para saber qué debe salir."""
    ts = sorted(x for x in velas_sim if x < t + 60 * mm)[-90:]
    c, h, l, v = ([velas_sim[x][i] for x in ts] for i in (4, 2, 3, 5))
    return G.vector(MODELO, c, h, l, v, ts.index(t), mm, velas_sim[t][1], ts[-1], {}, vivo=vivo if vivo else velas_sim[t + 60 * mm][1],
                    resta_s=resta if resta else 900 - 60 * mm - 1.0)


def armar_p(ventana, mm=12, lo=0.07, hi=0.14):
    """Arma velas con un empujón en el minuto 3 tal que, al cierre del minuto mm, el perdedor valga entre lo y hi."""
    for k in range(4, 60):
        armar_velas(ventana, {3: k * 0.00002})
        e = esperado(ventana, mm)
        if e and lo <= e["p"] <= hi:
            return e
    raise SystemExit("no hay empujón que deje la probabilidad pedida")


def filas(datos, tipo=None):
    out = []
    for nombre in sorted(os.listdir(datos)):
        if nombre.startswith("vector-"):
            with open(os.path.join(datos, nombre), encoding="utf-8") as f:
                out += [json.loads(x) for x in f]
    return [r for r in out if tipo is None or r["tipo"] == tipo]


def nuevo(politica=None):
    datos = tempfile.mkdtemp()
    if politica is not None:
        with open(os.path.join(datos, "politica.json"), "w", encoding="utf-8") as f:
            json.dump(politica, f)
    return CP.Comprador(Con, registro.append, datos=datos, candado=False), datos


def correr(cp, m, desde, hasta, paso=1.0):
    t = desde
    while t <= hasta:
        reloj[0] = t
        cp.paso(t, m)
        t += paso


MODELO = G.cargar()
ver("hay modelo con sus doce pesos, h y H", bool(MODELO) and len(MODELO["w"]) == 13 and len(MODELO["h"]) == len(G.TRAMOS_P) == len(MODELO["H"]))

# ---------------------------------------------------------------- cuentas de la ganancia
print("Cuentas")
ver("a 0,01 un USDT compra 98 contratos y el acierto deja 97", abs(G.contratos(0.01) - 98) < 1e-9 and abs(G.ganancia(1.0, 0.01) - 97) < 1e-9)
ver("a 0,01 hace falta más de 1,02 % para no perder", G.ganancia(0.0102, 0.01) < 0 < G.ganancia(0.0103, 0.01))
ver("la ganancia esperada es p × 0,98 / q − 1", abs(G.ganancia(0.10, 0.05) - 0.96) < 1e-12)
ver("el precio límite deja el margen del 10 % y baja al paso de 0,01", abs(G.precio_limite(0.03) - 0.02) < 1e-9 and abs(G.precio_limite(0.0825) - 0.07) < 1e-9
    and G.ganancia(0.0825, G.precio_limite(0.0825)) >= 0.10)
ver("Kelly es cero sin ventaja y positivo con ella", G.kelly(0.02, 0.02) == 0 and 0 < G.kelly(0.03, 0.02) < 0.02)
ver("la probabilidad prudente baja la del perdedor y la del ganador", all(G.prudente(MODELO, p)[0] <= p and G.prudente(MODELO, p)[1] <= 1 - p
                                                                         for p in (0.003, 0.008, 0.015, 0.03, 0.07, 0.15, 0.3, 0.6)))
ver("celdas", G.celda("perdedor", 13, 0.02) == "perdedor|11-14|≤0.02" and G.celda("ganador", 3, 0.55) == "ganador|1-5|≤0.70"
    and G.celda("perdedor", 7, 0.03) == "perdedor|6-10|≤0.05")
pol, rec = G.recortar({"margen": 0.01, "kelly": 2, "tope_saldo": 0.5, "real": True, "celdas_apagadas": ["perdedor|11-14|≤0.02"]})
ver("la política no puede bajar el margen, subir el Kelly ni el tope, ni traer claves nuevas",
    pol["margen"] == 0.10 and pol["kelly"] == 0.25 and pol["tope_saldo"] == 0.16 and "real" not in pol and len(rec) == 4, str(rec))
pol, rec = G.recortar({"margen": 0.25, "kelly": 0.1, "tope_saldo": 0.05, "celdas_apagadas": []})
ver("la política sí puede subir el margen y bajar el Kelly y el tope", pol["margen"] == 0.25 and pol["kelly"] == 0.1 and pol["tope_saldo"] == 0.05 and not rec)

# ---------------------------------------------------------------- el instante frente a la vela cerrada
print("Probabilidad del instante")
armar_velas(T0, {3: 0.0007})
ts = sorted(x for x in velas_sim if x < T0 + 60 * 12)[-90:]
c, h, l, v = ([velas_sim[x][i] for x in ts] for i in (4, 2, 3, 5))
cerrada = G.vector(MODELO, c, h, l, v, ts.index(T0), 12, velas_sim[T0][1], ts[-1], {})
igual = G.vector(MODELO, c, h, l, v, ts.index(T0), 12, velas_sim[T0][1], ts[-1], {}, vivo=c[-1], resta_s=180.0)
ver("con el precio del cierre y el tiempo exacto, la probabilidad del instante es la de la vela cerrada", abs(cerrada["p"] - igual["p"]) < 1e-12)
lejos = G.vector(MODELO, c, h, l, v, ts.index(T0), 12, velas_sim[T0][1], ts[-1], {}, vivo=c[-1] * 1.0006, resta_s=175.0)
ver("si el precio vivo se aleja de la apertura, el perdedor vale menos", lejos["p"] < cerrada["p"] and lejos["perdedor"] == cerrada["perdedor"])
cruzo = G.vector(MODELO, c, h, l, v, ts.index(T0), 12, velas_sim[T0][1], ts[-1], {}, vivo=velas_sim[T0][1] * 0.9995, resta_s=175.0)
ver("si el precio vivo cruzó la apertura, el perdedor cambia de lado", cruzo["perdedor"] == -cerrada["perdedor"])

# ---------------------------------------------------------------- 1. compra con llenado a 5 s y a 15 s
print("1. Compra normal")
armar_p(T0)
m = mercado(T0, 77)
e = esperado(T0, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
ver("el caso de prueba deja comprar a 0,02 o más, un paso bajo el límite", lim >= 0.02, f"precio {lim}, p {e['p']}")
libro_fn[0] = lambda t: {perd: [(lim, 500.0), (lim + 0.05, 900.0)], -perd: [(0.97, 800.0)]}
cp, datos = nuevo()
reloj[0] = T0 + 721.0
cp.paso(reloj[0], m)
mir = filas(datos, "mirada")
ver("al segundo del cierre del minuto 12 queda una mirada grabada con los dos lados", len(mir) == 1 and mir[0]["m"] == 12 and set(mir[0]["lados"]) == {"1", "-1"})
ver("decide el lado perdedor, que cumple el margen", mir[0]["decide"] == perd and mir[0]["lados"][str(perd)]["G_prud"] >= 0.10)
ver("la mirada no compra por sí sola", not cp.compras)
reloj[0] += 5.5
cp.paso(reloj[0], m)
ver("5 s después compra en el libro principal al precio de ese instante", len(cp.compras) == 1 and cp.compras[0]["llenado"] == 5 and cp.compras[0]["precio"] == lim)
reloj[0] += 10
cp.paso(reloj[0], m)
ver("15 s después compra en el libro de su toque", len(cp.compras) == 2 and cp.compras[1]["llenado"] == 15)
ver("1 USDT a ese precio da (1 − 0,02) / precio contratos", abs(cp.compras[0]["contratos"] - round(0.98 / lim, 2)) < 1e-9)
b = cp.compras[0]["usdt_b"]
ver("el libro B pone una fracción del saldo: entre el mínimo de 2 USDT y el tope del 16 %", b == 0 or 2.0 <= b <= 0.16 * 46 + 1e-9, str(b))
correr(cp, m, T0 + 781.0, T0 + 800.0)
ver("en el minuto siguiente ya no compra otra vez en esa ventana", len(cp.compras) == 2 and len(filas(datos, "mirada")) == 2)
saldo_antes = float(cp.saldo["5"])
ganador[77] = perd
correr(cp, m, T0 + 961.0, T0 + 962.0)
o = cp.compras[0]
ver("se liquida con el ganador oficial: acierto y neto (0,98 / precio − 1)", o["res"] == 1 and abs(o["neto"] - round(0.98 / lim - 1, 4)) < 1e-9)
ver("el libro B cobra lo suyo", abs(float(cp.saldo["5"]) - (saldo_antes + b * 0.98 / lim)) < 1e-3)
ver("queda la fila de resultado de la ventana", [r["ganador"] for r in filas(datos, "resultado")] == [perd])
d = J.leer(datos)
ver("la auditoría rehace miradas y compras sin diferencias", J.auditar(d, MODELO) == [], str(J.auditar(d, MODELO)[:3]))
malo = copy.deepcopy(d)
malo["compras"][0]["precio"] = lim + 0.03
ver("la auditoría nota una compra con el precio cambiado", len(J.auditar(malo, MODELO)) >= 1)
malo = copy.deepcopy(d)
malo["miradas"][(T0, 12)]["x"][0] += 0.4
ver("la auditoría nota una mirada con los rasgos cambiados", len(J.auditar(malo, MODELO)) >= 1)
malo = copy.deepcopy(d)
malo["compras"][0]["res"] = 0
ver("la auditoría nota un resultado que no es el oficial", len(J.auditar(malo, MODELO)) >= 1)
cp2 = CP.Comprador(Con, registro.append, datos=datos, candado=False)
ver("al reabrir conserva compras y saldos", len(cp2.compras) == 2 and cp2.saldo == cp.saldo)
r = cp.resumen()
ver("el resumen separa los dos libros", r["libros"]["5"]["n"] == 1 and r["libros"]["5"]["k"] == 1 and r["libros"]["15"]["n"] == 1)

# ---------------------------------------------------------------- 2. el precio sube antes del llenado
print("2. Se escapó por precio")
ganador.clear()
T1 = T0 + 900
armar_p(T1)
m = mercado(T1, 78)
e = esperado(T1, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
dec = T1 + 721.0
libro_fn[0] = lambda t: {perd: [(lim + 0.10 if dec + 3 <= t <= dec + 9 else lim, 500.0)], -perd: [(0.97, 800.0)]}
cp, datos = nuevo()
reloj[0] = dec
cp.paso(dec, m)
reloj[0] = dec + 5.5
cp.paso(reloj[0], m)
ll = filas(datos, "llenado")
ver("a los 5 s el precio subió: no compra y lo anota", not cp.compras and len(ll) == 1 and ll[0]["compra"] is False and "subió el precio" in ll[0]["motivo"])
reloj[0] = dec + 15.5
cp.paso(reloj[0], m)
ver("a los 15 s el precio volvió: el libro de su toque sí compra", len(cp.compras) == 1 and cp.compras[0]["llenado"] == 15)

# ---------------------------------------------------------------- 3. el precio vivo se aleja antes del llenado
print("3. Se escapó por probabilidad")
T2 = T1 + 900
armar_p(T2)
m = mercado(T2, 79)
e = esperado(T2, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
dec = T2 + 721.0
libro_fn[0] = lambda t: {perd: [(lim, 500.0)], -perd: [(0.97, 800.0)]}
base = velas_sim[T2 + 720][1]
vivo_fn[0] = lambda t: base * (1 - perd * 0.0012) if t >= dec + 3 else base  # se aleja de la apertura: el perdedor vale menos
cp, datos = nuevo()
reloj[0] = dec
cp.paso(dec, m)
ver("decide con el precio del instante", filas(datos, "mirada")[0]["decide"] == perd)
correr(cp, m, dec + 5.5, dec + 16.0, 10.0)
ll = filas(datos, "llenado")
ver("el precio vivo se alejó: ninguno de los dos libros compra", not cp.compras and len(ll) == 2 and all("bajó la probabilidad" in x["motivo"] for x in ll))
vivo_fn[0] = None

# ---------------------------------------------------------------- 4. el «97 por 1» que no vale
print("4. A 0,01 con el precio lejos")
T3 = T2 + 900
armar_velas(T3, {2: 0.0011, 5: 0.0009, 9: 0.0008})
m = mercado(T3, 80)
e = esperado(T3, 13)
perd = e["perdedor"]
ver("el caso de prueba tiene al perdedor por debajo de 1 %", e["p"] < 0.01, f"p {e['p']}")
libro_fn[0] = lambda t: {perd: [(0.01, 6000.0)], -perd: [(0.99, 800.0)]}
cp, datos = nuevo()
correr(cp, m, T3 + 781.0, T3 + 800.0)
mir = filas(datos, "mirada")
ver("no compra a 0,01 un lado que vale menos de 1,02 %", not cp.compras and mir[0]["decide"] == 0 and mir[0]["lados"][str(perd)]["G_prud"] < 0)

# ---------------------------------------------------------------- 5. el lado que va ganando, regalado
print("5. El ganador barato")
T4 = T3 + 900
armar_p(T4)
m = mercado(T4, 81)
e = esperado(T4, 12)
perd = e["perdedor"]
libro_fn[0] = lambda t: {perd: [(0.60, 300.0)], -perd: [(0.45, 300.0)]}
cp, datos = nuevo()
correr(cp, m, T4 + 721.0, T4 + 727.0, 5.5)
ver("compra el lado que va ganando si es el que deja margen: no importa si es sube o baja",
    len(cp.compras) == 1 and cp.compras[0]["lado"] == -perd and cp.compras[0]["papel"] == "ganador" and cp.compras[0]["precio"] == 0.45)

# ---------------------------------------------------------------- 6. mirada tardía
print("6. Mirada tardía")
T5 = T4 + 900
armar_p(T5)
m = mercado(T5, 82)
e = esperado(T5, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
libro_fn[0] = lambda t: {perd: [(lim, 500.0)], -perd: [(0.97, 800.0)]}
cp, datos = nuevo()
correr(cp, m, T5 + 727.0, T5 + 745.0)
ver("7 s después del cierre la mirada se pierde y no hay compra", not cp.compras and not filas(datos, "mirada")
    and [r["motivo"] for r in filas(datos, "mirada perdida")] == ["pasaron los 5 s"])

# ---------------------------------------------------------------- 7. celda apagada: en sombra
print("7. Celda apagada")
T6 = T5 + 900
armar_p(T6)
m = mercado(T6, 83)
e = esperado(T6, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
libro_fn[0] = lambda t: {perd: [(lim, 500.0)], -perd: [(0.97, 800.0)]}
cp, datos = nuevo({"version": 3, "margen": 0.10, "kelly": 0.25, "tope_saldo": 0.16, "celdas_apagadas": [G.celda("perdedor", 12, lim)]})
correr(cp, m, T6 + 721.0, T6 + 727.0, 5.5)
ver("la celda apagada compra solo en sombra, sin poner saldo del libro B", len(cp.compras) == 1 and cp.compras[0]["sombra"] is True and cp.compras[0]["usdt_b"] == 0)
ver("la compra en sombra no entra en la cuenta del libro", cp.resumen()["libros"]["5"]["n"] == 0 and cp.resumen()["libros"]["5"]["abiertas"] == 0)

# ---------------------------------------------------------------- 8. política fuera de los límites
print("8. Política recortada")
registro.clear()
cp, datos = nuevo({"version": 9, "margen": 0.01, "kelly": 3, "tope_saldo": 0.9, "real": True})
correr(cp, m, T6 + 800.0, T6 + 801.0)
ver("una política que baja el margen o sube los topes vuelve a los límites y queda anotado",
    cp.pol["margen"] == 0.10 and cp.pol["kelly"] == 0.25 and cp.pol["tope_saldo"] == 0.16 and sum("recortada" in x for x in registro) == 4, str(registro[-5:]))

# ---------------------------------------------------------------- 9. sin ganador en dos horas
print("9. Sin ganador oficial")
ganador.clear()
T7 = T6 + 900
armar_p(T7)
m = mercado(T7, 84)
e = esperado(T7, 12)
perd, lim = e["perdedor"], e["lados"][e["perdedor"]]["limite"]
lim = round(lim - 0.01, 2)  # un paso por debajo del límite: segundos después sigue cumpliendo
libro_fn[0] = lambda t: {perd: [(lim, 500.0)], -perd: [(0.97, 800.0)]}
cp, datos = nuevo()
correr(cp, m, T7 + 721.0, T7 + 727.0, 5.5)
puesto = cp.compras[0]["usdt_b"]
correr(cp, m, T7 + 1000.0, T7 + 1001.0)
ver("sin ganador, la compra sigue abierta", cp.compras[0]["res"] is None)
correr(cp, m, T7 + 7201.0, T7 + 7202.0)
ver("a las dos horas no cuenta y el libro B recupera lo puesto", cp.compras[0]["res"] == -1 and abs(float(cp.saldo["5"]) - G.SALDO_PAPEL) < 1e-6, f"puesto {puesto}")

# ---------------------------------------------------------------- 10. una ventana entera, segundo a segundo
print("10. Ventana completa")
T8 = T7 + 900
armar_velas(T8, {})
m = mercado(T8, 85)
libro_fn[0] = lambda t: {1: [(0.90, 300.0)], -1: [(0.90, 300.0)]}  # a 0,90 ningún lado puede dejar el margen del 10 %
ganador[85] = 1
cp, datos = nuevo()
correr(cp, m, T8 + 0.5, T8 + 1000.5)
mir = filas(datos, "mirada")
ver("catorce miradas, una por minuto cerrado, todas en los 5 s", [r["m"] for r in mir] == list(range(1, 15)) and all(0 <= r["demora_s"] <= 5 for r in mir))
ver("con el libro caro no hay candidatos ni compras", not cp.compras and all(r["decide"] == 0 for r in mir))
ver("la ventana deja su resultado aunque no haya compras", [r["ganador"] for r in filas(datos, "resultado")] == [1] and not cp.ventanas)
ver("existe el resumen para la Mesa, la placa y el agente", os.path.exists(os.path.join(datos, "comprador.json")))
d = J.leer(datos)
ver("el juez lee las catorce miradas con su resultado", len(d["miradas"]) == 14 and d["resultados"] == {T8: 1} and J.auditar(d, MODELO) == [])
cal = J.calibracion(d)
ver("la calibración cuenta las catorce miradas", sum(x["n"] for x in cal) == 14)
ver("el mapa de ganancia cuenta los dos lados de cada mirada", sum(x["n"] for x in J.mapa(d).values()) == 28)

# ---------------------------------------------------------------- juez: R5 y R6
print("Juez")
ver("binomial de Poisson: sin aciertos en 60 compras de 10 % pasa 0,18 % de las veces", abs(J.cola_baja([0.10] * 60, 0) - 0.9 ** 60) < 1e-12)
ver("binomial de Poisson: suma bien la cola", abs(J.cola_baja([0.5] * 4, 1) - 5 / 16) < 1e-12)


def compra(i, res, celda="perdedor|11-14|≤0.05", p=0.10, precio=0.05, L=5, sombra=False):
    return {"t": T0 + 900 * 6 * i, "m": 12, "lado": 1, "papel": "perdedor", "celda": celda, "sombra": sombra, "llenado": L, "precio": precio,
            "p": p, "p_prud": p * 0.9, "G_prud": G.ganancia(p * 0.9, precio), "resta_s": 170, "comision": 0.02, "usdt_b": 2.0, "res": res,
            "neto": round(0.98 / precio - 1, 4) if res else -1.0, "neto_b": round(2 * (0.98 / precio - 1), 4) if res else -2.0}


mala = [compra(i, 0) for i in range(60)]
cs = J.celdas(mala)
ver("R5: una celda con 60 compras y ningún acierto se apaga", cs["perdedor|11-14|≤0.05"]["manda"] == "apagar")
polx, cambios = J.politica_que_manda(mala, G.politica_base())
ver("R5: la política que sale la trae apagada y sube de versión", polx["celdas_apagadas"] == ["perdedor|11-14|≤0.05"] and polx["version"] == 2 and len(cambios) == 1)
pocas = [compra(i, 0) for i in range(40)]
ver("R5: con menos de 50 compras no se apaga nada", J.celdas(pocas)["perdedor|11-14|≤0.05"]["manda"] == "seguir")
sombra = mala + [compra(100 + i, 1 if i % 8 == 0 else 0, sombra=True) for i in range(100)]
ver("R5: una celda apagada vuelve con 100 compras en sombra de neto positivo",
    J.celdas(sombra, ["perdedor|11-14|≤0.05"])["perdedor|11-14|≤0.05"]["manda"] == "encender")
buenas = [compra(i, 1 if i % 8 == 0 else 0, L=L) for i in range(320) for L in (5, 15)]
crit, apto = J.criterios(buenas, 0)
ver("R6: 320 compras en 20 días con 40 aciertos repartidos quedan aptas", apto, str([(n, d) for n, ok, d in crit if not ok]))
crit, apto = J.criterios(buenas[:400], 0)
ver("R6: con 200 compras no es apto", not apto and not crit[0][1])
crit, apto = J.criterios(buenas, 3)
ver("R6: con diferencias de auditoría no es apto", not apto and not crit[5][1])
suerte = [compra(i, 1 if i < 2 else 0, p=0.01, precio=0.01, L=L) for i in range(320) for L in (5, 15)]
crit, apto = J.criterios(suerte, 0)
ver("R6: dos golpes de suerte no bastan (pocos aciertos y neto concentrado)", not apto and not crit[0][1] and not crit[4][1])
ver("R6: el remuestreo es repetible", J.remuestreo(J.libro(buenas)) == J.remuestreo(J.libro(buenas)))

# ---------------------------------------------------------------- candado: aquí no existe la compra real
print("Candado")
prohibido = ("cotizar", "ordenar(", "cobrar", "place-order", "get-quote", "batch-redeem", "REAL_AUTORIZADO", "lectura.txt", "_firmado", "X-MBX")
for nombre in ("comprador.py", "ganancia.py", "juez_comprador.py", "correr.py"):
    ruta = os.path.join(AQUI, nombre)
    if not os.path.exists(ruta):
        continue
    texto = open(ruta, encoding="utf-8").read()
    ver(f"{nombre} no nombra órdenes, llaves ni el archivo del dinero real", not [p for p in prohibido if p in texto], str([p for p in prohibido if p in texto]))
s1 = CP.tomar_candado(48799)
s2 = CP.tomar_candado(48799)
ver("el candado deja un solo comprador por equipo", s1 is not None and s2 is None)
if s1:
    s1.close()

print(f"\n{hechas[0] - len(fallas)} de {hechas[0]} pruebas bien" + (f"; FALLAN: {fallas}" if fallas else ""))
sys.exit(1 if fallas else 0)
