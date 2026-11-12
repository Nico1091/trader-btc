"""Formas de hacer binarias (11/11/2026): la ficha, su huella, la gramática de las nuevas y las pasadas.

Una forma es uno o dos disparos, sus filtros, un sentido (−1 al revés, +1 a favor) y un plazo de 10 o 15 min. La ficha se
guarda con su huella antes de probarse y ningún parámetro cambia después: un cambio es otra forma.
Pasadas, con su regla original: E1 a E5 del Centro (mesa\\centro.py, copiado sin cambios), el núcleo del semáforo (ruptura
de 20 velas al revés en las marcas de 10 min), la neurona t33 del 31/10 con sus pesos y el banco de motor\\senales.py."""
import hashlib
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import DATOS, PLAZOS  # noqa: E402

DISPAROS = {  # parámetro: (mínimo, máximo, paso); los límites del plan
    "ruptura": {"n": (10, 120, 1)},
    "bollinger": {"w": (10, 60, 1), "k": (1.5, 3.0, 0.1)},
    "rsi": {"tf": (5, 15, 10), "u": (65, 85, 1)},
    "impulso": {"m": (5, 60, 1), "z": (1.0, 3.5, 0.1)},
    "rango": {"h": (1, 24, 1), "q": (0.85, 0.98, 0.01)},
    "red": {"c": (0.52, 0.62, 0.01)},
}
NOMBRE_DISPARO = {"ruptura": "ruptura de {n} velas de 5 min", "bollinger": "cierre fuera de Bollinger {w} × {k}",
                  "rsi": "RSI de {tf} min más allá de {u}", "impulso": "impulso de {m} min sobre {z} volatilidades",
                  "rango": "posición en el rango de {h} h más allá de {q}", "red": "la red sola con confianza {c}"}
EQUIVALENTE = {  # pasadas que la gramática reproduce exactamente
    "E1": {"d": [["ruptura", {"n": 20}]], "f": {}, "s": -1},
    "E2": {"d": [["ruptura", {"n": 50}]], "f": {}, "s": -1},
    "nucleo": {"d": [["ruptura", {"n": 20}]], "f": {"cada10": True}, "s": -1},
}
NOMBRE_PASADA = {"E1": "E1 · ruptura de 20 velas al revés", "E2": "E2 · ruptura de 50 velas al revés",
                 "E3": "E3 · compresión de Bollinger al revés", "E4": "E4 · EMA 50 y MACD al revés",
                 "E5": "E5 · rechazo en techo o piso azules", "nucleo": "núcleo del semáforo · ruptura de 20 al revés cada 10 min",
                 "t33": "neurona t33 del 31/10 con confianza 0,56"}


def _redondear(x, paso):
    return int(round(x)) if float(paso).is_integer() else round(float(x), 4)


def normalizar(ficha):
    """Ficha canónica: disparos ordenados, números redondeados a su paso y filtros solo si están activos."""
    if "pasada" in ficha:
        return {k: ficha[k] for k in sorted(ficha)}
    d = []
    for nombre, prm in ficha["d"]:
        rangos = DISPAROS[nombre]
        q = {k: _redondear(min(max(float(prm[k]), rangos[k][0]), rangos[k][1]), rangos[k][2]) for k in rangos}
        if nombre == "rsi":
            q["tf"] = 5 if float(prm["tf"]) < 10 else 15
        d.append([nombre, q])
    d.sort(key=lambda x: (x[0], json.dumps(x[1], sort_keys=True)))
    f = {}
    for k, v in sorted(ficha.get("f", {}).items()):
        if k in ("oi", "cada10") and v:
            f[k] = True
        elif k == "franja" and v:
            f[k] = [int(v[0]) % 24, int(min(max(int(v[1]), 1), 23))]
        elif k == "vol" and v:
            f[k] = [v[0], round(min(max(float(v[1]), 0.6), 1.6), 2)]
        elif k == "conf" and v:
            f[k] = round(min(max(float(v), 0.5), 0.7), 2)
    return {"d": d, "f": f, "s": int(ficha["s"]), "p": int(ficha["p"])}


def equivalente(ficha):
    if "pasada" in ficha and ficha["pasada"] in EQUIVALENTE:
        e = dict(EQUIVALENTE[ficha["pasada"]])
        e["p"] = int(ficha["p"])
        return normalizar(e)
    return ficha


def huella(ficha):
    texto = json.dumps(equivalente(normalizar(ficha)), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


def _valor(rango, rng):
    lo, hi, paso = rango
    return _redondear(lo + paso * rng.randint(0, int(round((hi - lo) / paso))), paso)


def aleatoria(rng):
    """Una forma nueva al azar dentro de la gramática."""
    if rng.random() < 0.7:
        nombres = [rng.choice(sorted(DISPAROS))]
    else:
        nombres = rng.sample([x for x in sorted(DISPAROS) if x != "red"], 2)
    d = [[nm, {k: _valor(r, rng) for k, r in DISPAROS[nm].items()}] for nm in nombres]
    f = {}
    if rng.random() < 0.5:
        f["oi"] = True
    if rng.random() < 0.25:
        f["franja"] = [rng.randint(0, 23), rng.randint(4, 12)]
    if rng.random() < 0.25:
        f["vol"] = [rng.choice(["baja", "alta"]), _valor((0.6, 1.6, 0.05), rng)]
    if rng.random() < 0.3 and nombres != ["red"]:
        f["conf"] = _valor((0.52, 0.62, 0.01), rng)
    s = 1 if nombres == ["red"] else (-1 if rng.random() < 0.6 else 1)
    return normalizar({"d": d, "f": f, "s": s, "p": rng.choice(PLAZOS)})


def describir(ficha):
    if "pasada" in ficha:
        if ficha["pasada"] == "banco":
            base = f"banco · {ficha['senal']}"
        else:
            base = NOMBRE_PASADA.get(ficha["pasada"], ficha["pasada"])
        return f"{base} · {ficha['p']} min"
    partes = [NOMBRE_DISPARO[n].format(**{k: (str(v).replace(".", ",")) for k, v in prm.items()}) for n, prm in ficha["d"]]
    texto = " + ".join(partes) + (" · al revés" if ficha["s"] < 0 else " · a favor") + f" · {ficha['p']} min"
    f = ficha.get("f", {})
    if f.get("oi"):
        texto += " · interés que no sube"
    if f.get("franja"):
        h0, largo = f["franja"]
        texto += f" · de {h0:02d} a {(h0 + largo) % 24:02d} h"
    if f.get("vol"):
        texto += f" · volatilidad {f['vol'][0]} ({str(f['vol'][1]).replace('.', ',')})"
    if f.get("conf"):
        texto += f" · red ≥ {str(f['conf']).replace('.', ',')}"
    if f.get("cada10"):
        texto += " · cada 10 min"
    return texto


def familia(ficha):
    """Mismos disparos, filtros, sentido y plazo: las variantes de una misma idea (para el tope de 12 vivas por familia)."""
    if "pasada" in ficha:
        return "pasada:" + ficha["pasada"] + ":" + str(ficha.get("senal", "")) + f":{ficha['p']}"
    return "+".join(sorted(n for n, _ in ficha["d"])) + "|" + ",".join(sorted(ficha.get("f", {}))) + f"|{ficha['s']}|{ficha['p']}"


def sentido(ficha):
    if "pasada" in ficha:
        return -1 if ficha["pasada"] in ("E1", "E2", "E3", "E4", "E5", "nucleo") else 0
    return ficha["s"]


# ---------------------------------------------------------------- codificación para la red de búsqueda (28 entradas)
def codificar(ficha):
    x = []
    d = dict((n, p) for n, p in ficha["d"])
    for nombre in sorted(DISPAROS):
        x.append(1.0 if nombre in d else 0.0)
        for k, (lo, hi, _paso) in DISPAROS[nombre].items():
            x.append((float(d[nombre][k]) - lo) / (hi - lo) if nombre in d else 0.0)
    f = ficha.get("f", {})
    x.append(1.0 if f.get("oi") else 0.0)
    if f.get("franja"):
        h0, largo = f["franja"]
        ang = 2 * math.pi * ((h0 + largo / 2) % 24) / 24
        x += [1.0, math.sin(ang), math.cos(ang), largo / 12]
    else:
        x += [0.0, 0.0, 0.0, 0.0]
    if f.get("vol"):
        x += [1.0, 1.0 if f["vol"][0] == "alta" else -1.0, (float(f["vol"][1]) - 0.6)]
    else:
        x += [0.0, 0.0, 0.0]
    x += [1.0, (float(f["conf"]) - 0.52) / 0.1] if f.get("conf") else [0.0, 0.0]
    x += [float(ficha["s"]), 1.0 if ficha["p"] == 15 else 0.0]
    return x


# ---------------------------------------------------------------- señal de una forma de la gramática
def senal(ctx, ficha):
    """Apuesta por barra (−1, 0, +1) de una forma de la gramática o de una pasada equivalente; None si es especial."""
    f = equivalente(ficha)
    if "pasada" in f:
        return None
    p = f["p"]
    raw = None
    for nombre, prm in f["d"]:
        r = ctx.disparo(nombre, prm, p)
        raw = r if raw is None else np.where(raw == r, raw, 0).astype(np.int8)
    apuesta = (raw * f["s"]).astype(np.int8)
    m = np.ones(ctx.nb, dtype=bool)
    for nombre, valor in sorted(f.get("f", {}).items()):
        m &= ctx.filtro(nombre, valor, p, apuesta)
    apuesta[~m] = 0
    return apuesta


# ---------------------------------------------------------------- pasadas especiales
def t33_pesos():
    return json.load(open(os.path.join(DATOS, "t33_indice.json"), encoding="utf-8"))


def senal_t33(ctx, pesos=None, b=None):
    """Neurona t33 del 31/10 con sus pesos: apuesta en su sentido cuando su confianza llega a 0,56."""
    pesos = pesos or t33_pesos()
    X, ok = ctx.rasgos_red(b)
    Z = (X[:, :10] - np.array(pesos["mu"])) / np.array(pesos["de"])
    w = np.array(pesos["w"])
    with np.errstate(over="ignore", invalid="ignore"):
        p = 1 / (1 + np.exp(-(w[0] + Z @ w[1:])))
    out = np.zeros(len(p), dtype=np.int8)
    m = ok & (np.abs(p - 0.5) >= 0.06)
    out[m] = np.where(p[m] > 0.5, 1, -1)
    if b is None:
        return out
    full = np.zeros(ctx.nb, dtype=np.int8)
    full[np.asarray(b)] = out
    return full


def velas15(ctx):
    """Velas completas de 15 min como las arma centro.agrupar: (cierre, apertura, máximo, mínimo, último)."""
    vel = ctx.vel
    nq = vel.n // 15
    A = vel.A[:, :nq * 15]
    O, H, L, C = A[0, 0::15], A[1].reshape(nq, 15).max(axis=1), A[2].reshape(nq, 15).min(axis=1), A[3, 14::15]
    ok = np.isfinite(O) & np.isfinite(H) & np.isfinite(L) & np.isfinite(C)
    T = vel.t0 + 900 * (np.arange(nq, dtype=np.int64) + 1)
    return [(int(t), float(o), float(h), float(lo), float(c)) for t, o, h, lo, c, k in zip(T, O, H, L, C, ok) if k]


def senal_e3_e4(ctx, desde_T=None):
    """E3 y E4 con las funciones del Centro, sobre las velas de 15 min del contexto. Devuelve dos arreglos por barra."""
    import centro
    v15 = velas15(ctx)
    s3, s4 = np.zeros(ctx.nb, dtype=np.int8), np.zeros(ctx.nb, dtype=np.int8)
    if len(v15) < 2:
        return s3, s4
    primero = 0
    if desde_T is not None:
        primero = next((i for i, x in enumerate(v15) if x[0] >= desde_T), len(v15))
    ind = centro.indicadores15(v15, desde=primero)
    for i in range(max(1, primero), len(v15)):
        a, b = centro.e3_e4(ind, i)
        if a or b:
            k = (v15[i][0] - ctx.t0) // 300 - 1
            if 0 <= k < ctx.nb:
                s3[k], s4[k] = a, b
    return s3, s4


def velas1(ctx, desde_i=0):
    vel = ctx.vel
    t = vel.t0 + 60 * np.arange(desde_i, vel.n, dtype=np.int64)
    A = vel.A[:, desde_i:vel.n]
    ok = np.isfinite(A[3])
    return [(int(a), float(o), float(h), float(lo), float(c)) for a, o, h, lo, c, k in zip(t, A[0], A[1], A[2], A[3], ok) if k]


def senal_e5_ultima(ctx):
    """E5 en la última barra del contexto (solo en vivo: cinco líneas sobre los últimos 150 minutos)."""
    import centro
    v1 = velas1(ctx, max(0, ctx.vel.n - 400))
    T = int(ctx.T[-1])
    pos = {x[0]: i for i, x in enumerate(v1)}
    i1 = pos.get(T - 60)
    if i1 is None:
        return 0
    return int(centro.e5(v1, i1)[0])


def senales_banco(ctx, desde_T=None):
    """Señales del banco de motor\\senales.py sobre las velas presentes: {nombre: arreglo por barra}."""
    from motor import senales as banco
    vel = ctx.vel
    ok = np.isfinite(vel.A[3, :vel.n])
    t = (vel.t0 + 60 * np.arange(vel.n, dtype=np.int64))[ok]
    o, h, l, c = (vel.A[k, :vel.n][ok] for k in range(4))
    S = banco.todas(t, o, h, l, c)[0]
    out = {}
    for nombre, (_grupo, tiempos, dirs) in S.items():
        a = np.zeros(ctx.nb, dtype=np.int8)
        tiempos = np.asarray(tiempos, dtype=np.int64)
        dirs = np.asarray(dirs)
        m = (tiempos % 300 == 0) & (dirs != 0)
        if desde_T is not None:
            m &= tiempos >= desde_T
        k = (tiempos[m] - ctx.t0) // 300 - 1
        dd = np.sign(dirs[m]).astype(np.int8)
        v = (k >= 0) & (k < ctx.nb)
        a[k[v]] = dd[v]
        out[str(nombre)] = a
    return out


def pasadas(nombres_banco=()):
    """Fichas de las formas pasadas que entran todas a vivo."""
    out = [({"pasada": x, "p": 15}, NOMBRE_PASADA[x]) for x in ("E1", "E2", "E3", "E4", "E5")]
    out += [({"pasada": "E1", "p": 10}, NOMBRE_PASADA["E1"] + " a 10 min"),
            ({"pasada": "E2", "p": 10}, NOMBRE_PASADA["E2"] + " a 10 min"),
            ({"pasada": "nucleo", "p": 10}, NOMBRE_PASADA["nucleo"]),
            ({"pasada": "t33", "p": 10}, NOMBRE_PASADA["t33"])]
    for nombre in sorted(nombres_banco):
        for p in PLAZOS:
            out.append(({"pasada": "banco", "senal": nombre, "p": p}, f"banco · {nombre} · {p} min"))
    return [(normalizar(f), n) for f, n in out]


# ---------------------------------------------------------------- peticiones «probar …» del dueño
def parsear(texto):
    """«probar ruptura 30 al revés 15», «probar rsi 15 75 a favor 10 con oi», «probar red 0,56 10». Devuelve ficha o error."""
    import re
    t = texto.lower().replace(",", ".").replace("é", "e").replace("á", "a").replace("í", "i")
    palabras = t.split()
    if palabras and palabras[0] in ("lab", "laboratorio"):
        palabras = palabras[1:]
    if not palabras or palabras[0] != "probar" or len(palabras) < 2:
        return None, "Escriba: probar <disparo> <parámetros> <al revés|a favor> <10|15> [con oi]."
    nombre = palabras[1]
    if nombre not in DISPAROS:
        return None, "Disparos posibles: " + ", ".join(sorted(DISPAROS)) + "."
    resto = " ".join(palabras[2:])
    s = 1 if ("favor" in resto or nombre == "red") else -1
    corte = len(resto)
    for marca in ("al reves", "reves", "a favor", "favor"):
        if marca in resto:
            corte = min(corte, resto.index(marca))
    antes = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", resto[:corte])]
    despues = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", resto[corte:])]
    claves = list(DISPAROS[nombre])
    if len(antes) < len(claves):
        return None, f"«{nombre}» necesita {len(claves)} número(s): " + ", ".join(claves) + "."
    prm = {k: antes[i] for i, k in enumerate(claves)}
    extra = antes[len(claves):] + despues
    plazo = next((int(x) for x in extra if int(x) in PLAZOS), 15)
    f = {"oi": True} if (" oi" in " " + resto or "interes" in resto) else {}
    ficha = normalizar({"d": [[nombre, prm]], "f": f, "s": s, "p": plazo})
    return ficha, None
