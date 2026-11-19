"""Ganancia esperada de las binarias de 15 min (12/11/2026, pedido suyo: «mirar los vectores de ganancia primero y operar así»).

Solo calcula: no lee llaves, no manda órdenes y no usa numpy, para correr igual en el PC y en la caja. Las reglas están en
REGLAS-ANTES-DE-MEDIR.md (escritas el 12/11/2026 a las 19:00, antes de medir) y aquí solo se aplican.

- Probabilidad: la red de la pérdida extendida a los minutos 1 a 14 (datos\\modelo.json, hecha por evaluar.py con 2021-2023).
  Da la probabilidad de que gane el lado que va perdiendo; la del lado que va ganando es 1 − p − p_empate.
- Probabilidad prudente (R2): la de la red corregida con el peor trimestre a ciegas de su tramo.
- Ganancia esperada por USDT comprando a q: G = p × (1 − c) / q − 1. El empate no se cuenta a favor.
- Vector de ganancia: para cada lado, p, p prudente, precio real, G, G prudente, precio límite y fracción de Kelly.
- Política: lo que el agente de la nube puede mover, recortado siempre a los límites de R7."""
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(AQUI), "laboratorio"))  # al final: no tapa módulos de quien importe esto
import perdida_red as PRED  # noqa: E402  los doce rasgos: una sola función para la historia y el vivo

MODELO = os.path.join(AQUI, "datos", "modelo.json")
POLITICA = os.path.join(AQUI, "datos", "politica.json")
COMISION = 0.02
PASO = 0.01                                             # el precio se mueve de 0,01 en 0,01
MINUTOS = tuple(range(1, 15))
TRAMOS_P = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50)  # tramos de probabilidad predicha del perdedor; el último llega a 1
MARGEN = 0.10                                           # R3.3: ganancia esperada prudente mínima; el agente puede subirla, no bajarla
PRECIO_MIN, PRECIO_MAX = 0.01, 0.90                     # 0,90 es el tope de precio de la Mesa
KELLY, TOPE_SALDO, MIN_USDT, SALDO_PAPEL = 0.25, 0.16, 2.0, 46.0
MIN_RESTA_S = 10
CORTES_MINUTO = ((1, 5), (6, 10), (11, 14))
CORTES_PRECIO = (0.02, 0.05, 0.10, 0.30, 0.70, 0.90)


def cargar(ruta=MODELO):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def predecir(modelo, x):
    """Probabilidad de que gane el lado que va perdiendo. Logística, o perceptrón con tanh si el modelo trae capas."""
    if modelo.get("tipo") == "perceptron":
        h = [(v - modelo["mu"][i]) / modelo["de"][i] for i, v in enumerate(x)]
        for W, b in zip(modelo["W"][:-1], modelo["b"][:-1]):
            h = [math.tanh(max(-40.0, min(40.0, sum(h[i] * W[i][k] for i in range(len(h))) + b[k]))) for k in range(len(b))]
        z = sum(h[i] * modelo["W"][-1][i][0] for i in range(len(h))) + modelo["b"][-1][0]
    else:
        z = modelo["w"][0]
        for i, v in enumerate(x):
            z += modelo["w"][i + 1] * (v - modelo["mu"][i]) / modelo["de"][i]
    z = max(-40.0, min(40.0, z))
    p = 1 / (1 + math.exp(-z))
    cal = modelo.get("recalibracion")  # dos números del logit, solo si R2 la dejó entrar
    if cal:
        lg = math.log(max(p, 1e-12) / max(1 - p, 1e-12))
        p = 1 / (1 + math.exp(-max(-40.0, min(40.0, cal[0] + cal[1] * lg))))
    return p


def tramo(p):
    """Índice del tramo de probabilidad predicha (R2)."""
    k = 0
    for i, lo in enumerate(TRAMOS_P):
        if p >= lo:
            k = i
    return k


def prudente(modelo, p):
    """(p prudente del perdedor, p prudente del ganador): el peor trimestre a ciegas de su tramo, por abajo y por arriba."""
    k = tramo(p)
    h = min(1.0, float(modelo["h"][k]))
    H = max(1.0, float(modelo["H"][k]))
    emp = float(modelo.get("p_empate", 0.0))
    return p * h, max(0.0, 1 - min(1.0, p * H) - emp)


def ganancia(p, q, comision=COMISION):
    """Ganancia esperada por USDT comprando a q un lado que gana con probabilidad p. El empate no se cuenta a favor."""
    return p * (1 - comision) / q - 1


def kelly(p, q, comision=COMISION):
    """Fracción del saldo que maximiza el crecimiento: p − (1 − p) / b, con b la ganancia neta por USDT si acierta."""
    b = (1 - comision) / q - 1
    return max(0.0, p - (1 - p) / b) if b > 0 else 0.0


def precio_limite(p_prud, margen=MARGEN, comision=COMISION):
    """El precio más alto que deja la ganancia esperada prudente en `margen` o más, bajado al paso de 0,01."""
    return math.floor((1 - comision) * p_prud / (1 + margen) / PASO + 1e-9) * PASO


def contratos(q, usdt=1.0, comision=COMISION):
    return usdt * (1 - comision) / q


def celda(papel, m, q):
    """Celda de R4: papel del lado, tramo de minuto y tramo de precio."""
    mm = next((f"{a}-{b}" for a, b in CORTES_MINUTO if a <= m <= b), "?")
    pp = next((f"≤{c:.2f}" for c in CORTES_PRECIO if q <= c + 1e-9), ">0.90")
    return f"{papel}|{mm}|{pp}"


def sigma60(cierres, j):
    """Raíz de la media de los rendimientos de 1 min al cuadrado en los 60 min que terminan en la vela j."""
    r2 = [math.log(cierres[i] / cierres[i - 1]) ** 2 for i in range(j - 59, j + 1)]
    return math.sqrt(max(sum(r2) / 60, 1e-12))


def z_de(cierres, s, m, strike):
    """El movimiento normalizado de la ventana en su minuto m (el mismo de laboratorio\perdida.py), o None."""
    j = s + m - 1
    if j < 61 or not strike or strike <= 0:
        return None
    return math.log(cierres[j] / strike) / (sigma60(cierres, j) * math.sqrt(15 - m))


def al_instante(x, perdedor, cierres, s, m, strike, vivo, resta_s):
    """Enmienda 1: los rasgos de la vela cerrada con lo atrasado y el tiempo recalculados con el precio del instante.
    Devuelve (x, perdedor, z) o None si el precio está justo en la apertura."""
    mov = math.log(vivo / strike)
    if mov == 0 or resta_s <= 0:
        return None
    tau = resta_s / 60
    z = mov / (sigma60(cierres, s + m - 1) * math.sqrt(tau))
    lado = -1 if z > 0 else 1
    a = min(abs(z), 8.0)
    x = list(x)
    x[0], x[1], x[2], x[11] = a, a * a, tau / 5, math.log(a + 0.05)
    if lado != perdedor:  # las dos devoluciones llevan el signo del perdedor: si cambió de lado, se invierten
        x[4], x[5] = -x[4], -x[5]
    return x, lado, z


def vector(modelo, cierres, altos, bajos, vol, s, m, strike, t_j, ask, comision=COMISION, margen=MARGEN, vivo=None, resta_s=None):
    """Vector de ganancia del minuto m (1 a 14) de la ventana que empieza en el índice s.
    ask: {1: precio de compra de «sube», -1: el de «baja»} (None si ese lado no tiene ventas). Devuelve None si no hay rasgos.
    Con `vivo` (precio de contado del instante) y `resta_s` (segundos para el cierre) decide la probabilidad del instante
    (enmienda 1) y deja anotada también la de la vela cerrada (p_cierre, z_cierre).
    Por lado: papel, p, p_prud, q, G, G_prud, limite (precio máximo con el margen) y kelly (con la p prudente)."""
    r = PRED.rasgos(cierres, altos, bajos, vol, s, m, strike, t_j)
    if r is None or modelo is None:
        return None
    x, perdedor = r
    out = {"m": m, "z_cierre": z_de(cierres, s, m, strike), "p_cierre": predecir(modelo, x), "perdedor_cierre": perdedor}
    out["z"] = out["z_cierre"]
    if vivo is not None and resta_s is not None:
        r = al_instante(x, perdedor, cierres, s, m, strike, vivo, resta_s)
        if r is None:
            return None
        x, perdedor, out["z"] = r
        out["vivo"], out["resta_s"] = vivo, resta_s
    p = predecir(modelo, x)
    p_perd, p_gan = prudente(modelo, p)
    emp = float(modelo.get("p_empate", 0.0))
    out.update({"perdedor": perdedor, "p": p, "x": x, "lados": {}})
    for lado in (1, -1):
        es_perd = lado == perdedor
        pl, pp = (p, p_perd) if es_perd else (max(0.0, 1 - p - emp), p_gan)
        q = (ask or {}).get(lado)
        d = {"papel": "perdedor" if es_perd else "ganador", "p": pl, "p_prud": pp, "q": q,
             "limite": precio_limite(pp, margen, comision)}
        if q and 0 < q < 1:
            d["G"], d["G_prud"], d["kelly"] = ganancia(pl, q, comision), ganancia(pp, q, comision), kelly(pp, q, comision)
        out["lados"][lado] = d
    return out


# ---------------------------------------------------------------- política (lo que mueve el agente de la nube, R7)
def politica_base():
    return {"version": 1, "hecha": "12/11/2026, reglas escritas antes de medir", "margen": MARGEN, "kelly": KELLY,
            "tope_saldo": TOPE_SALDO, "celdas_apagadas": [], "nota": "todas las celdas encendidas en papel"}


def recortar(pol):
    """Devuelve (política válida, lista de recortes). El agente puede subir el margen, bajar el Kelly y el tope y apagar
    celdas; nada más. Cualquier otra cosa se devuelve a los límites de R7 y queda anotada. Aquí no existe el dinero real."""
    base, recortes = politica_base(), []
    if not isinstance(pol, dict):
        return base, ["política ilegible: se usa la base"]
    out = dict(base)
    out["version"] = pol.get("version", base["version"])
    out["hecha"] = str(pol.get("hecha", ""))[:120]
    out["nota"] = str(pol.get("nota", ""))[:400]
    for clave, lim, sentido in (("margen", MARGEN, "min"), ("kelly", KELLY, "max"), ("tope_saldo", TOPE_SALDO, "max")):
        try:
            v = float(pol.get(clave, lim))
        except (TypeError, ValueError):
            v = lim
        if not math.isfinite(v) or (sentido == "min" and v < lim) or (sentido == "max" and (v > lim or v < 0)):
            recortes.append(f"{clave} {pol.get(clave)!r} fuera del límite: queda {lim}")
            v = lim
        out[clave] = min(v, 5.0) if sentido == "min" else v
    cel = pol.get("celdas_apagadas", [])
    out["celdas_apagadas"] = sorted({str(c) for c in cel})[:60] if isinstance(cel, list) else []
    for clave in pol:
        if clave not in base:
            recortes.append(f"clave «{clave}» ignorada")
    return out, recortes


def cargar_politica(ruta=POLITICA):
    try:
        with open(ruta, encoding="utf-8") as f:
            return recortar(json.load(f))
    except (OSError, ValueError):
        return politica_base(), []


def decidir(vec, pol, resta_s):
    """Qué lado compraría el comprador v1 en esta mirada (R3). Devuelve (lado o None, motivo, celda, sombra).
    sombra = True cuando la celda está apagada: la compra se anota aparte, sin contar, para saber si la celda merece volver (R5)."""
    if vec is None:
        return None, "sin rasgos", None, False
    if resta_s < MIN_RESTA_S:
        return None, "quedan menos de 10 s", None, False
    mejor = None
    for lado, d in vec["lados"].items():
        q = d.get("q")
        if not q or not PRECIO_MIN - 1e-9 <= q <= PRECIO_MAX + 1e-9:
            continue
        if d.get("G_prud") is None or d["G_prud"] < pol["margen"] - 1e-12:
            continue
        if mejor is None or d["G_prud"] > vec["lados"][mejor]["G_prud"]:
            mejor = lado
    if mejor is None:
        return None, "ningún lado llega al margen", None, False
    c = celda(vec["lados"][mejor]["papel"], vec["m"], vec["lados"][mejor]["q"])
    if c in pol["celdas_apagadas"]:
        return mejor, "celda apagada: se anota en sombra", c, True
    return mejor, "cumple", c, False


def importe_b(saldo, d, pol, disponibles):
    """USDT del libro B: fracción del Kelly prudente, con tope del saldo y sin pasar de lo que el libro ofrece. 0 si no llega al mínimo."""
    f = min(pol["kelly"] * d.get("kelly", 0.0), pol["tope_saldo"])
    usdt = saldo * f
    if disponibles is not None and d.get("q"):
        usdt = min(usdt, disponibles * d["q"])
    usdt = math.floor(usdt * 100 + 1e-9) / 100
    return usdt if usdt >= MIN_USDT else 0.0
