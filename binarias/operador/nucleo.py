"""Núcleo del operador (16/11/2026): rasgos, modelo, vector de ganancia y decisión, con ventana de 5 o de 15 minutos.

Es comprador/ganancia.py y laboratorio/perdida_red.rasgos del 12/11 con la ventana como parámetro (W). Con W = 15 da
exactamente lo mismo que ellos (paridad en prueba_operador.py). Solo biblioteca estándar: corre igual en el PC y en la caja.
Reglas: REGLAS-ANTES-DE-MEDIR.md con su enmienda 2 del 16/11. Aquí no hay llaves ni órdenes.

- Probabilidad: logística de doce rasgos por ventana (datos/modelo_15.json y datos/modelo_5.json, hechos por entrenar.py con
  2021-2023). Da la probabilidad de que gane el lado que va perdiendo; la del que va ganando es 1 − p − p_empate.
- Probabilidad prudente (R2): la del modelo corregida con el peor trimestre a ciegas de su tramo.
- Ganancia esperada por USDT comprando a q: G = p × (1 − c) / q − 1. El empate no se cuenta a favor.
- Vector de ganancia: para cada lado, p, p prudente, precio real, G, G prudente, precio límite y fracción de Kelly."""
import json
import math
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
VENTANAS = (15, 5)                                      # minutos de cada mercado con API
COMISION = 0.02
PASO = 0.01                                             # el precio se mueve de 0,01 en 0,01
TRAMOS_P = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50)  # tramos de probabilidad predicha del perdedor; el último llega a 1
MARGEN = 0.10                                           # R3.3: ganancia esperada prudente mínima; se puede subir, no bajar
PRECIO_MIN, PRECIO_MAX = 0.01, 0.90
KELLY, TOPE_SALDO, MIN_USDT, SALDO_PAPEL = 0.25, 0.16, 2.0, 46.0
MIN_RESTA_S = 10
CORTES_MINUTO = {15: ((1, 5), (6, 10), (11, 14)), 5: ((1, 2), (3, 4))}
CORTES_PRECIO = (0.02, 0.05, 0.10, 0.30, 0.70, 0.90)
NOMBRES = ["atraso |z|", "atraso al cuadrado", "minutos que faltan", "volatilidad 5/60", "devolución del último minuto",
           "devolución de 3 min", "rango de la ventana", "cruces de la apertura", "volumen 3/60", "hora (seno)", "hora (coseno)",
           "log del atraso"]


def ruta_modelo(W):
    return os.path.join(DATOS, f"modelo_{W}.json")


def cargar(W=15, ruta=None):
    try:
        with open(ruta or ruta_modelo(W), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- rasgos (los doce de perdida_red.rasgos, con W)
def rasgos(C, H, L, V, s, m, ref, t_j, W=15):
    """Rasgos del minuto m (1 a W − 1) de la ventana que empieza en el índice s, con apertura ref. Devuelve (x, lado) o None.
    C, H, L, V: listas de velas de 1 min (al menos 60 antes de s + m − 1); t_j: apertura (s) de la vela j."""
    j = s + m - 1
    if j < 61 or ref <= 0:
        return None
    r = [math.log(C[i] / C[i - 1]) for i in range(j - 59, j + 1)]
    sig = math.sqrt(max(sum(v * v for v in r) / 60, 1e-12))
    sig5 = math.sqrt(max(sum(v * v for v in r[-5:]) / 5, 1e-12))
    mov = math.log(C[j] / ref)
    if mov == 0:
        return None
    z = mov / (sig * math.sqrt(W - m))
    lado = -1 if z > 0 else 1
    a = min(abs(z), 8.0)
    hi, lo = max(H[s:j + 1]), min(L[s:j + 1])
    cruces = 0
    for i in range(s, j):
        if (C[i] - ref) * (C[i + 1] - ref) < 0:
            cruces += 1
    v3 = (V[j] + V[j - 1] + V[j - 2]) / 3
    v60 = sum(V[j - 59:j + 1]) / 60
    hora = ((t_j + 60) % 86400) / 3600
    x = [a, a * a, (W - m) / 5, sig5 / sig, (r[-1] * lado) / sig, math.log(C[j] / C[j - 3]) * lado / (sig * math.sqrt(3)),
         (hi - lo) / (ref * sig * math.sqrt(m)), cruces / 3, math.log((v3 + 1e-9) / (v60 + 1e-9)),
         math.sin(2 * math.pi * hora / 24), math.cos(2 * math.pi * hora / 24), math.log(a + 0.05)]
    return x, lado


# ---------------------------------------------------------------- modelo
def predecir(modelo, x):
    """Probabilidad de que gane el lado que va perdiendo (logística)."""
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


def celda(papel, m, q, W=15):
    """Celda de R4: papel del lado, tramo de minuto y tramo de precio."""
    mm = next((f"{a}-{b}" for a, b in CORTES_MINUTO[W] if a <= m <= b), "?")
    pp = next((f"≤{c:.2f}" for c in CORTES_PRECIO if q <= c + 1e-9), ">0.90")
    return f"{papel}|{mm}|{pp}"


def plazo(W, m):
    """Etiqueta del plazo de una mirada (enmienda 2): cuántos minutos faltaban al decidir. Solo para informar."""
    faltan = W - m
    if W == 5:
        return "5 min"
    if faltan >= 13:
        return "15 min"
    if 9 <= faltan <= 11:
        return "10 min"
    if 4 <= faltan <= 6:
        return "5 min"
    return f"otro ({faltan} min)"


def sigma60(cierres, j):
    """Raíz de la media de los rendimientos de 1 min al cuadrado en los 60 min que terminan en la vela j."""
    r2 = [math.log(cierres[i] / cierres[i - 1]) ** 2 for i in range(j - 59, j + 1)]
    return math.sqrt(max(sum(r2) / 60, 1e-12))


def z_de(cierres, s, m, strike, W=15):
    """El movimiento normalizado de la ventana en su minuto m, o None."""
    j = s + m - 1
    if j < 61 or not strike or strike <= 0:
        return None
    return math.log(cierres[j] / strike) / (sigma60(cierres, j) * math.sqrt(W - m))


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


def vector(modelo, cierres, altos, bajos, vol, s, m, strike, t_j, ask, comision=COMISION, margen=MARGEN, vivo=None, resta_s=None,
           W=15):
    """Vector de ganancia del minuto m (1 a W − 1) de la ventana que empieza en el índice s.
    ask: {1: precio de compra de «sube», -1: el de «baja»} (None si ese lado no tiene ventas o no hay libro).
    Con `vivo` (precio de contado del instante) y `resta_s` (segundos para el cierre) decide la probabilidad del instante
    (enmienda 1) y deja anotada también la de la vela cerrada (p_cierre, z_cierre). Devuelve None si no hay rasgos.
    Por lado: papel, p, p_prud, q, G, G_prud, limite (precio máximo con el margen) y kelly (con la p prudente)."""
    r = rasgos(cierres, altos, bajos, vol, s, m, strike, t_j, W)
    if r is None or modelo is None:
        return None
    x, perdedor = r
    out = {"m": m, "z_cierre": z_de(cierres, s, m, strike, W), "p_cierre": predecir(modelo, x), "perdedor_cierre": perdedor}
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


# ---------------------------------------------------------------- política (lo único que se puede mover, R7)
def politica_base():
    return {"version": 1, "hecha": "12/11/2026, reglas escritas antes de medir", "margen": MARGEN, "kelly": KELLY,
            "tope_saldo": TOPE_SALDO, "celdas_apagadas": [], "nota": "todas las celdas encendidas en papel"}


def recortar(pol):
    """Devuelve (política válida, lista de recortes). Se puede subir el margen, bajar el Kelly y el tope y apagar celdas;
    nada más. Cualquier otra cosa vuelve a los límites de R7 y queda anotada."""
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


def cargar_politica(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return recortar(json.load(f))
    except (OSError, ValueError):
        return politica_base(), []


def decidir(vec, pol, resta_s, W=15):
    """Qué lado compraría el comprador v1 en esta mirada (R3). Devuelve (lado o None, motivo, celda, sombra).
    sombra = True cuando la celda está apagada: la compra se anota aparte, sin contar (R5)."""
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
    c = celda(vec["lados"][mejor]["papel"], vec["m"], vec["lados"][mejor]["q"], W)
    if c in pol["celdas_apagadas"]:
        return mejor, "celda apagada: se anota en sombra", c, True
    return mejor, "cumple", c, False


def importe_b(saldo, d, pol, disponibles):
    """USDT del libro B: fracción del Kelly prudente, con tope del saldo y sin pasar de lo que el libro ofrece.
    0 si no llega al mínimo."""
    f = min(pol["kelly"] * d.get("kelly", 0.0), pol["tope_saldo"])
    usdt = saldo * f
    if disponibles is not None and d.get("q"):
        usdt = min(usdt, disponibles * d["q"])
    usdt = math.floor(usdt * 100 + 1e-9) / 100
    return usdt if usdt >= MIN_USDT else 0.0
