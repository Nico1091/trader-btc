"""Juez del operador (16/11/2026): el del 12/11 (comprador/juez_comprador.py) por mercado. Audita el papel contra lo grabado
en el registro, aplica el apagado de celdas (R5) y dice si el comprador de un mercado quedó «apto» (R6). Solo lee archivos y
no usa numpy. Las reglas están en REGLAS-ANTES-DE-MEDIR.md y aquí no se cambian. «Apto» no autoriza dinero: lo arma el dueño.

Cada mercado (5 y 15 min) se juzga con su propia serie de papel con precios reales; la serie «sin_llave» no entra.
El registro se lee línea a línea y cada día ya cerrado se resume una sola vez (datos/juicio_cache_W.json), para que la caja
no tenga que cargar meses de miradas en memoria."""
import glob
import json
import math
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import nucleo as N  # noqa: E402
from comunes import escribir_json, leer_json  # noqa: E402

LIBRO, LIBRO_TOQUE = 5, 15
MIN_CELDA, MIN_SOMBRA, COLA = 50, 100, 0.01          # R5
MIN_COMPRAS, MIN_ACIERTOS, MIN_DIAS = 300, 30, 14    # R6
REMUESTRAS, SEMILLA = 10000, 12112026
MAX_DIF = 40


# ---------------------------------------------------------------- lectura del registro
def _auditar_mirada(r, modelo, dif):
    """Rehace una mirada con lo que dejó grabado: probabilidad, prudente, ganancia y decisión."""
    t, m = r["t"], r["m"]
    p = N.predecir(modelo, r["x"])
    if abs(p - r["p"]) > 2e-6:
        dif.append(f"mirada {t} m{m}: probabilidad {r['p']} y rehecha {p:.6f}")
    p_perd, p_gan = N.prudente(modelo, p)
    mejor = None
    for lado, x in r["lados"].items():
        pp = p_perd if x["papel"] == "perdedor" else p_gan
        if abs(pp - x["p_prud"]) > 2e-6:
            dif.append(f"mirada {t} m{m} lado {lado}: prudente {x['p_prud']} y rehecha {pp:.6f}")
        q = x.get("q")
        if q and abs(N.ganancia(x["p_prud"], q, r.get("comision", N.COMISION)) - x["G_prud"]) > 2e-5:
            dif.append(f"mirada {t} m{m} lado {lado}: ganancia prudente {x['G_prud']} y no cuadra con su precio")
        if q and N.PRECIO_MIN - 1e-9 <= q <= N.PRECIO_MAX + 1e-9 and x["G_prud"] >= r["margen"] - 1e-12:
            if mejor is None or x["G_prud"] > r["lados"][mejor]["G_prud"]:
                mejor = lado
    if r["resta_s"] >= N.MIN_RESTA_S and int(mejor or 0) != r["decide"]:
        dif.append(f"mirada {t} m{m}: decidió {r['decide']} y la regla da {mejor or 0}")


def _resumir_archivo(ruta, W, modelo):
    """Lo que un día de registro deja para el juicio de un mercado: cuántas miradas, sus diferencias, las miradas que
    decidieron comprar, los llenados con compra y los resultados."""
    out = {"miradas": 0, "perdidas": 0, "dif": [], "decide": {}, "llenados": [], "resultados": {}}
    huella = modelo.get("huella")
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            try:
                r = json.loads(linea)
            except ValueError:
                continue
            if r.get("W") != W or r.get("serie") != "papel":
                continue
            tipo = r.get("tipo")
            if tipo == "mirada":
                clave = f"{r['t']}:{r['m']}"
                if clave in out["decide"]:
                    continue  # vale la primera de cada una
                out["miradas"] += 1
                out["decide"][clave] = r["decide"]
                if r.get("modelo") == huella and len(out["dif"]) < MAX_DIF:
                    _auditar_mirada(r, modelo, out["dif"])
            elif tipo == "llenado" and r.get("compra"):
                out["llenados"].append({k: r.get(k) for k in ("t", "m", "llenado", "q", "x", "p_red", "sombra")})
            elif tipo == "resultado":
                out["resultados"][str(r["t"])] = r["ganador"]
            elif tipo == "mirada perdida":
                out["perdidas"] += 1
    out["decide"] = {k: v for k, v in out["decide"].items() if v}  # solo hacen falta las que decidieron comprar
    return out


def leer(registro, datos, W, modelo):
    """Todo el registro de un mercado, resumido. Un archivo que no cambió de tamaño no se vuelve a leer."""
    ruta_cache = os.path.join(datos, f"juicio_cache_{W}.json")
    cache = leer_json(ruta_cache, {}) or {}
    if cache.get("modelo") != modelo.get("huella"):
        cache = {"modelo": modelo.get("huella"), "archivos": {}}
    total = {"miradas": 0, "perdidas": 0, "dif": [], "decide": {}, "llenados": [], "resultados": {}}
    cambio, vistos = False, set()
    for ruta in sorted(glob.glob(os.path.join(registro, "*.jsonl"))):
        nombre, peso = os.path.basename(ruta), os.path.getsize(ruta)
        vistos.add(nombre)
        x = cache["archivos"].get(nombre)
        if not x or x.get("peso") != peso:
            x = {"peso": peso, **_resumir_archivo(ruta, W, modelo)}
            cache["archivos"][nombre] = x
            cambio = True
        total["miradas"] += x["miradas"]
        total["perdidas"] += x["perdidas"]
        total["dif"] += x["dif"]
        total["decide"].update(x["decide"])
        total["llenados"] += x["llenados"]
        total["resultados"].update(x["resultados"])
    for nombre in [n for n in cache["archivos"] if n not in vistos]:
        del cache["archivos"][nombre]
        cambio = True
    if cambio:
        try:
            escribir_json(ruta_cache, cache)
        except OSError:
            pass
    compras = (leer_json(os.path.join(datos, f"compras_{W}.json"), {}) or {}).get("compras", [])
    return {**total, "compras": compras}


# ---------------------------------------------------------------- cuentas
def cola_baja(ps, k):
    """P(aciertos ≤ k) cuando cada compra acierta con su propia probabilidad (binomial de Poisson)."""
    d = [1.0] + [0.0] * (k + 1)
    for p in ps:
        for i in range(min(k + 1, len(d) - 1), 0, -1):
            d[i] = d[i] * (1 - p) + d[i - 1] * p
        d[0] *= 1 - p
    s = 0.0
    for v in d[:k + 1]:
        s += v
    return min(1.0, s)


def cuenta(ops):
    """Compras cerradas: n y aciertos sin los empates; el neto sí cuenta lo que dejó cada empate."""
    x = {"n": 0, "k": 0, "empates": 0, "esperados": 0.0, "var": 0.0, "neto": 0.0, "neto_b": 0.0, "abiertas": 0}
    for o in ops:  # bucles explícitos: sum() suma distinto desde la 3.12
        if o.get("res") is None:
            x["abiertas"] += 1
        if o.get("res") not in (0, 1, 2):
            continue
        x["neto"] += o["neto"]
        x["neto_b"] += o.get("neto_b") or 0.0
        if o["res"] == 2:
            x["empates"] += 1
            continue
        x["n"] += 1
        x["k"] += o["res"]
        x["esperados"] += o["p"]
        x["var"] += o["p"] * (1 - o["p"])
    return {"n": x["n"], "k": x["k"], "empates": x["empates"], "esperados": round(x["esperados"], 3), "desv": round(math.sqrt(x["var"]), 3),
            "neto": round(x["neto"], 4), "neto_b": round(x["neto_b"], 4), "abiertas": x["abiertas"]}


def libro(compras, L=LIBRO, sombra=False):
    return [o for o in compras if o["llenado"] == L and bool(o.get("sombra")) == sombra]


def remuestreo(ops, veces=REMUESTRAS, semilla=SEMILLA):
    """Percentil 5 del neto del libro A al remuestrear por ventanas (hay una compra por ventana)."""
    netos = [o["neto"] for o in ops if o.get("res") in (0, 1, 2)]
    if len(netos) < 2:
        return None
    rng, n, sumas = random.Random(semilla), len(netos), []
    for _ in range(veces):
        s = 0.0
        for _ in range(n):
            s += netos[rng.randrange(n)]
        sumas.append(s)
    sumas.sort()
    return round(sumas[int(0.05 * veces)], 4)


# ---------------------------------------------------------------- R5: celdas
def celdas(compras, apagadas=()):
    """Por celda del libro principal: cuenta, probabilidad de tan pocos aciertos según la probabilidad prudente y qué manda R5."""
    out = {}
    for sombra in (False, True):
        por = {}
        for o in libro(compras, LIBRO, sombra):
            if o.get("res") in (0, 1):
                por.setdefault(o["celda"], []).append(o)
        for c, ops in por.items():
            x = out.setdefault(c, {"apagada": c in apagadas})
            ct = cuenta(ops)
            if sombra:
                x["sombra"] = ct
            else:
                x.update(ct)
                x["cola"] = round(cola_baja([o["p_prud"] for o in ops], ct["k"]), 5)
    for c, x in out.items():
        x["manda"] = "seguir"
        if not x["apagada"] and x.get("n", 0) >= MIN_CELDA and x["cola"] < COLA:
            x["manda"] = "apagar"
        elif x["apagada"] and x.get("sombra", {}).get("n", 0) >= MIN_SOMBRA and x["sombra"]["neto"] > 0:
            x["manda"] = "encender"
    return out


def politica_que_manda(compras, pol):
    """La política tras aplicar R5 a la vigente: (política, cambios)."""
    apagadas = set(pol["celdas_apagadas"])
    cambios = []
    for c, x in celdas(compras, apagadas).items():
        if x["manda"] == "apagar":
            apagadas.add(c)
            cambios.append(f"se apaga {c}: {x['k']} aciertos en {x['n']} compras; con la probabilidad prudente eso pasa {100 * x['cola']:.2f} % de las veces")
        elif x["manda"] == "encender":
            apagadas.discard(c)
            cambios.append(f"vuelve {c}: {x['sombra']['n']} compras en sombra con neto {x['sombra']['neto']:+.2f}")
    nueva = dict(pol)
    nueva["celdas_apagadas"] = sorted(apagadas)
    if cambios:
        nueva["version"] = int(pol.get("version", 1)) + 1
    return N.recortar(nueva)[0], cambios


# ---------------------------------------------------------------- R6: apto
def criterios(compras, diferencias):
    a, b = libro(compras, LIBRO), libro(compras, LIBRO_TOQUE)
    ca, cb = cuenta(a), cuenta(b)
    cerr = [o for o in a if o.get("res") in (0, 1, 2)]
    dias = (max(o["t"] for o in cerr) - min(o["t"] for o in cerr)) / 86400 if cerr else 0.0
    # el remuestreo (lo más pesado para la caja) solo se hace cuando ya hay compras suficientes: con menos, R6.1 no pasa igual
    p5 = remuestreo(a) if ca["n"] >= MIN_COMPRAS else None
    mayor = max([o["neto"] for o in cerr if o["res"] == 1], default=0.0)
    out = [
        ("300 compras o más y 30 aciertos o más", ca["n"] >= MIN_COMPRAS and ca["k"] >= MIN_ACIERTOS, f"{ca['n']} compras, {ca['k']} aciertos"),
        ("neto positivo en los libros A y B y percentil 5 mayor que cero", ca["neto"] > 0 and ca["neto_b"] > 0 and p5 is not None and p5 > 0,
         f"A {ca['neto']:+.2f}, B {ca['neto_b']:+.2f}, percentil 5 {p5 if p5 is not None else 'sin calcular (faltan compras)'}"),
        ("neto positivo también con 15 s de llenado", cb["n"] > 0 and cb["neto"] > 0, f"{cb['n']} compras, neto {cb['neto']:+.2f}"),
        ("aciertos dentro de lo que predice el modelo", ca["n"] > 0 and abs(ca["k"] - ca["esperados"]) <= 2 * ca["desv"],
         f"{ca['k']} frente a {ca['esperados']:.1f} ± {2 * ca['desv']:.1f}"),
        ("ningún acierto aporta más de la cuarta parte del neto", ca["neto"] > 0 and mayor <= 0.25 * ca["neto"],
         f"el mayor acierto deja {mayor:+.2f} de {ca['neto']:+.2f}"),
        ("14 días o más y auditoría sin diferencias", dias >= MIN_DIAS and diferencias == 0, f"{dias:.1f} días, {diferencias} diferencias"),
    ]
    return out, all(ok for _n, ok, _d in out)


# ---------------------------------------------------------------- auditoría de las compras
def auditar(d, modelo):
    """Las diferencias de las miradas (ya rehechas al leer) más las de cada compra contra su mirada, su llenado y su resultado."""
    dif = list(d["dif"])
    vistos = set()
    for o in d["compras"]:
        clave = (o["t"], o["llenado"], bool(o.get("sombra")))
        if clave in vistos:
            dif.append(f"compra {o['t']}: dos compras del mismo libro en la ventana")
        vistos.add(clave)
        if d["decide"].get(f"{o['t']}:{o['m']}") != o["lado"]:
            dif.append(f"compra {o['t']} m{o['m']}: no hay mirada que la decida")
        ll = [x for x in d["llenados"] if x["t"] == o["t"] and x["m"] == o["m"] and x["llenado"] == o["llenado"]]
        if not ll or abs(ll[0]["q"] - o["precio"]) > 1e-9:
            dif.append(f"compra {o['t']} m{o['m']}: sin fila de llenado con su precio")
        elif o.get("modelo") == modelo.get("huella") and abs(N.predecir(modelo, ll[0]["x"]) - ll[0]["p_red"]) > 2e-6:
            dif.append(f"compra {o['t']} m{o['m']}: la probabilidad del llenado no sale de sus rasgos")
        if not N.PRECIO_MIN - 1e-9 <= o["precio"] <= N.PRECIO_MAX + 1e-9 or o["resta_s"] < N.MIN_RESTA_S:
            dif.append(f"compra {o['t']} m{o['m']}: precio o tiempo fuera de la regla")
        if abs(N.ganancia(o["p_prud"], o["precio"], o.get("comision", N.COMISION)) - o["G_prud"]) > 2e-5 or o["G_prud"] < N.MARGEN - 1e-9:
            dif.append(f"compra {o['t']} m{o['m']}: la ganancia prudente no cuadra o no llega al margen")
        g = d["resultados"].get(str(o["t"]))
        if o.get("res") in (0, 1, 2) and g is not None and (2 if g == 0 else (1 if g == o["lado"] else 0)) != o["res"]:
            dif.append(f"compra {o['t']} m{o['m']}: resultado {o['res']} y el ganador oficial fue {g}")
    return dif


# ---------------------------------------------------------------- juicio completo de un mercado
def juzgar(registro, datos, W, modelo, pol):
    """Todo lo que hay que saber del papel de un mercado: auditoría, cuentas, R6 y lo que R5 manda hacer con las celdas."""
    d = leer(registro, datos, W, modelo)
    dif = auditar(d, modelo)
    crit, apto = criterios(d["compras"], len(dif))
    nueva, cambios = politica_que_manda(d["compras"], pol)
    return {"W": W, "miradas": d["miradas"], "perdidas": d["perdidas"], "diferencias": len(dif), "muestra_dif": dif[:5],
            "libro_a": cuenta(libro(d["compras"], LIBRO)), "libro_toque": cuenta(libro(d["compras"], LIBRO_TOQUE)),
            "criterios": [[n, bool(ok), det] for n, ok, det in crit], "cumplidos": sum(1 for _n, ok, _d in crit if ok),
            "apto": bool(apto), "politica": nueva, "cambios": cambios}
