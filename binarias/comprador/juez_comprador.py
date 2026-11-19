"""Juez del comprador (12/11/2026): audita el papel contra el vector grabado, mide la red contra el mercado, aplica el
apagado de celdas (R5) y dice si el comprador quedó «apto» (R6). Solo lee archivos; sin numpy, para que corra igual en el
PC, en la caja y en la nube. Las reglas están en REGLAS-ANTES-DE-MEDIR.md y aquí no se cambian.

Uso:
  python -X utf8 juez_comprador.py                    informe corto (lo que el agente manda a Telegram)
  python -X utf8 juez_comprador.py --todo             informe con el detalle por celda, la calibración y el mapa de ganancia
  python -X utf8 juez_comprador.py --politica         la política que resulta de aplicar R5 (JSON; el agente la revisa y la guarda)
  python -X utf8 juez_comprador.py --velas AAAA-MM-DD rehace con el archivo oficial de Binance la probabilidad de cierre de ese día"""
import csv
import glob
import io
import json
import math
import os
import random
import sys
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.append(AQUI)
import ganancia as G  # noqa: E402

DATOS = os.path.join(AQUI, "datos")
LIBRO, LIBRO_TOQUE = 5, 15
MIN_CELDA, MIN_SOMBRA, COLA = 50, 100, 0.01          # R5
MIN_COMPRAS, MIN_ACIERTOS, MIN_DIAS = 300, 30, 14    # R6
REMUESTRAS, SEMILLA = 10000, 12112026
ARCHIVO_BINANCE = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{dia}.zip"


def leer(datos=DATOS):
    """Miradas {(t, m): fila} (la primera de cada una), llenados, resultados {t: ganador} y compras."""
    miradas, llenados, resultados, perdidas = {}, [], {}, 0
    for ruta in sorted(glob.glob(os.path.join(datos, "vector-*.jsonl"))):
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                try:
                    r = json.loads(linea)
                except ValueError:
                    continue
                if r.get("tipo") == "mirada":
                    miradas.setdefault((r["t"], r["m"]), r)
                elif r.get("tipo") == "llenado":
                    llenados.append(r)
                elif r.get("tipo") == "resultado":
                    resultados[r["t"]] = r["ganador"]
                elif r.get("tipo") == "mirada perdida":
                    perdidas += 1
    try:
        with open(os.path.join(datos, "compras.json"), encoding="utf-8") as f:
            compras = json.load(f).get("compras", [])
    except (OSError, ValueError):
        compras = []
    return {"miradas": miradas, "llenados": llenados, "resultados": resultados, "compras": compras, "perdidas": perdidas}


# ---------------------------------------------------------------- cuentas
def cola_baja(ps, k):
    """P(aciertos ≤ k) cuando cada compra acierta con su propia probabilidad (binomial de Poisson)."""
    d = [1.0] + [0.0] * (k + 1)
    for p in ps:
        for i in range(min(k + 1, len(d) - 1), 0, -1):
            d[i] = d[i] * (1 - p) + d[i - 1] * p
        d[0] *= 1 - p
    return min(1.0, sum(d[:k + 1]))


def cuenta(ops):
    cerr = [o for o in ops if o.get("res") in (0, 1)]
    neto = 0.0
    for o in cerr:  # bucle explícito: sum() suma distinto desde la 3.12
        neto += o["neto"]
    neto_b = 0.0
    for o in cerr:
        neto_b += o.get("neto_b") or 0.0
    esp = 0.0
    for o in cerr:
        esp += o["p"]
    var = 0.0
    for o in cerr:
        var += o["p"] * (1 - o["p"])
    return {"n": len(cerr), "k": sum(o["res"] for o in cerr), "esperados": round(esp, 3), "desv": round(math.sqrt(var), 3),
            "neto": round(neto, 4), "neto_b": round(neto_b, 4), "abiertas": sum(1 for o in ops if o.get("res") is None)}


def libro(compras, L=LIBRO, sombra=False):
    return [o for o in compras if o["llenado"] == L and bool(o.get("sombra")) == sombra]


def remuestreo(ops, veces=REMUESTRAS, semilla=SEMILLA):
    """Percentil 5 del neto del libro A al remuestrear por ventanas (hay una compra por ventana)."""
    netos = [o["neto"] for o in ops if o.get("res") in (0, 1)]
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
    """La política tras aplicar R5 a la vigente; (política, cambios). El agente puede además subir el margen o bajar el Kelly."""
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
    return G.recortar(nueva)[0], cambios


# ---------------------------------------------------------------- R6: apto
def criterios(compras, diferencias):
    a, b = libro(compras, LIBRO), libro(compras, LIBRO_TOQUE)
    ca, cb = cuenta(a), cuenta(b)
    cerr = [o for o in a if o.get("res") in (0, 1)]
    dias = (max(o["t"] for o in cerr) - min(o["t"] for o in cerr)) / 86400 if cerr else 0.0
    p5 = remuestreo(a)
    mayor = max([o["neto"] for o in cerr if o["res"] == 1], default=0.0)
    out = [
        ("300 compras o más y 30 aciertos o más", ca["n"] >= MIN_COMPRAS and ca["k"] >= MIN_ACIERTOS, f"{ca['n']} compras, {ca['k']} aciertos"),
        ("neto positivo en los libros A y B y percentil 5 mayor que cero", ca["neto"] > 0 and ca["neto_b"] > 0 and p5 is not None and p5 > 0,
         f"A {ca['neto']:+.2f}, B {ca['neto_b']:+.2f}, percentil 5 {p5 if p5 is not None else 'sin datos'}"),
        ("neto positivo también con 15 s de llenado", cb["n"] > 0 and cb["neto"] > 0, f"{cb['n']} compras, neto {cb['neto']:+.2f}"),
        ("aciertos dentro de lo que predice la red", ca["n"] > 0 and abs(ca["k"] - ca["esperados"]) <= 2 * ca["desv"],
         f"{ca['k']} frente a {ca['esperados']:.1f} ± {2 * ca['desv']:.1f}"),
        ("ningún acierto aporta más de la cuarta parte del neto", ca["neto"] > 0 and mayor <= 0.25 * ca["neto"],
         f"el mayor acierto deja {mayor:+.2f} de {ca['neto']:+.2f}"),
        ("14 días o más y auditoría sin diferencias", dias >= MIN_DIAS and diferencias == 0, f"{dias:.1f} días, {diferencias} diferencias"),
    ]
    return out, all(ok for _n, ok, _d in out)


# ---------------------------------------------------------------- auditoría contra el vector grabado
def auditar(d, modelo):
    """Rehace cada mirada y cada compra con lo grabado. Devuelve la lista de diferencias (vacía si todo cuadra)."""
    dif = []
    for (t, m), r in d["miradas"].items():
        if r.get("modelo") != modelo.get("huella"):
            continue  # otra versión de la red: se audita con su propio modelo
        p = G.predecir(modelo, r["x"])
        if abs(p - r["p"]) > 2e-6:
            dif.append(f"mirada {t} m{m}: probabilidad {r['p']} y rehecha {p:.6f}")
        p_perd, p_gan = G.prudente(modelo, p)
        mejor = None
        for lado, x in r["lados"].items():
            pp = p_perd if x["papel"] == "perdedor" else p_gan
            if abs(pp - x["p_prud"]) > 2e-6:
                dif.append(f"mirada {t} m{m} lado {lado}: prudente {x['p_prud']} y rehecha {pp:.6f}")
            q = x.get("q")
            if q and abs(G.ganancia(x["p_prud"], q, r.get("comision", G.COMISION)) - x["G_prud"]) > 2e-5:
                dif.append(f"mirada {t} m{m} lado {lado}: ganancia prudente {x['G_prud']} y no cuadra con su precio")
            if q and G.PRECIO_MIN - 1e-9 <= q <= G.PRECIO_MAX + 1e-9 and x["G_prud"] >= r["margen"] - 1e-12:
                if mejor is None or x["G_prud"] > r["lados"][mejor]["G_prud"]:
                    mejor = lado
        if r["resta_s"] >= G.MIN_RESTA_S and int(mejor or 0) != r["decide"]:
            dif.append(f"mirada {t} m{m}: decidió {r['decide']} y la regla da {mejor or 0}")
    vistos = set()
    for o in d["compras"]:
        clave = (o["t"], o["llenado"], bool(o.get("sombra")))
        if clave in vistos:
            dif.append(f"compra {o['t']}: dos compras del mismo libro en la ventana")
        vistos.add(clave)
        r = d["miradas"].get((o["t"], o["m"]))
        if not r or r["decide"] != o["lado"]:
            dif.append(f"compra {o['t']} m{o['m']}: no hay mirada que la decida")
        ll = [x for x in d["llenados"] if x["t"] == o["t"] and x["m"] == o["m"] and x["llenado"] == o["llenado"] and x.get("compra")]
        if not ll or abs(ll[0]["q"] - o["precio"]) > 1e-9:
            dif.append(f"compra {o['t']} m{o['m']}: sin fila de llenado con su precio")
        elif o.get("modelo") == modelo.get("huella") and abs(G.predecir(modelo, ll[0]["x"]) - ll[0]["p_red"]) > 2e-6:
            dif.append(f"compra {o['t']} m{o['m']}: la probabilidad del llenado no sale de sus rasgos")
        if not G.PRECIO_MIN - 1e-9 <= o["precio"] <= G.PRECIO_MAX + 1e-9 or o["resta_s"] < G.MIN_RESTA_S:
            dif.append(f"compra {o['t']} m{o['m']}: precio o tiempo fuera de la regla")
        if abs(G.ganancia(o["p_prud"], o["precio"], o.get("comision", G.COMISION)) - o["G_prud"]) > 2e-5 or o["G_prud"] < G.MARGEN - 1e-9:
            dif.append(f"compra {o['t']} m{o['m']}: la ganancia prudente no cuadra o no llega al margen")
        g = d["resultados"].get(o["t"])
        if o.get("res") in (0, 1) and g is not None and (1 if g == o["lado"] else 0) != o["res"]:
            dif.append(f"compra {o['t']} m{o['m']}: resultado {o['res']} y el ganador oficial fue {g}")
    return dif


# ---------------------------------------------------------------- la red contra el mercado (todas las miradas, se compre o no)
def calibracion(d):
    """Por tramo de probabilidad del lado perdedor: miradas con resultado, predicho, prudente y ocurrido."""
    out = [{"tramo": [G.TRAMOS_P[i], (list(G.TRAMOS_P) + [1.0])[i + 1]], "n": 0, "predicho": 0.0, "prudente": 0.0, "ocurrido": 0} for i in range(len(G.TRAMOS_P))]
    for (t, _m), r in d["miradas"].items():
        g = d["resultados"].get(t)
        if not g:
            continue
        x = out[G.tramo(r["p"])]
        perd = r["lados"][str(r["perdedor"])]
        x["n"] += 1
        x["predicho"] += r["p"]
        x["prudente"] += perd["p_prud"]
        x["ocurrido"] += 1 if g == r["perdedor"] else 0
    return [x for x in out if x["n"]]


def mapa(d):
    """Mapa de ganancia: por celda, cuántas veces el mercado ofreció cada lado y qué habría dejado comprar 1 USDT al precio de
    la mirada, sin margen ni llenado (lo que el mercado regala o cobra de más, antes de cualquier regla)."""
    out = {}
    for (t, m), r in d["miradas"].items():
        g = d["resultados"].get(t)
        if not g:
            continue
        for lado, x in r["lados"].items():
            q = x.get("q")
            if not q or not G.PRECIO_MIN - 1e-9 <= q <= G.PRECIO_MAX + 1e-9:
                continue
            c = out.setdefault(G.celda(x["papel"], m, q), {"n": 0, "k": 0, "esperados": 0.0, "neto": 0.0, "con_margen": 0})
            gano = int(lado) == g
            c["n"] += 1
            c["k"] += gano
            c["esperados"] += x["p"]
            c["neto"] += (1 - G.COMISION) / q - 1 if gano else -1.0
            c["con_margen"] += 1 if x.get("G_prud") is not None and x["G_prud"] >= r["margen"] else 0
    return {c: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for c, x in sorted(out.items())}


# ---------------------------------------------------------------- archivo oficial de Binance (para la nube)
def velas_oficiales(dia):
    """Velas de contado de 1 min del archivo oficial de ese día UTC (AAAA-MM-DD): {apertura_s: (o, h, l, c, v)}."""
    req = urllib.request.Request(ARCHIVO_BINANCE.format(dia=dia), headers={"User-Agent": "comprador-binarias"})
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
    out = {}
    for fila in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")):
        if not fila or not fila[0].isdigit():
            continue
        t = int(fila[0])
        t = t // 1000000 if t > 10 ** 14 else t // 1000  # desde 2025 el archivo de contado viene en microsegundos
        out[t] = tuple(float(v) for v in fila[1:6])
    return out


def auditar_velas(d, modelo, V):
    """Con velas oficiales: rehace los rasgos de la vela cerrada de cada mirada de ese día y compara la probabilidad de cierre."""
    n, dif = 0, []
    for (t, m), r in sorted(d["miradas"].items()):
        ts = [t - 60 * k for k in range(75, 0, -1)] + [t + 60 * k for k in range(m)]
        if any(x not in V for x in ts) or r.get("modelo") != modelo.get("huella"):
            continue
        c, h, l, v = ([V[x][i] for x in ts] for i in (3, 1, 2, 4))
        vec = G.vector(modelo, c, h, l, v, 75, m, r["strike"], ts[-1], {})
        n += 1
        if vec is None or abs(vec["p_cierre"] - r["p_cierre"]) > 2e-5:
            dif.append(f"mirada {t} m{m}: probabilidad de cierre {r['p_cierre']} y con el archivo oficial {None if vec is None else round(vec['p_cierre'], 6)}")
    return n, dif


# ---------------------------------------------------------------- informe
def pct(x, d=1):
    return f"{100 * x:.{d}f}".replace(".", ",") + " %"


def informe(datos=DATOS, todo=False):
    d = leer(datos)
    modelo = G.cargar()
    pol, _rec = G.cargar_politica(os.path.join(datos, "politica.json"))
    dif = auditar(d, modelo) if modelo else ["no hay modelo"]
    a, b = cuenta(libro(d["compras"], LIBRO)), cuenta(libro(d["compras"], LIBRO_TOQUE))
    crit, apto = criterios(d["compras"], len(dif))
    cumplidos = sum(1 for _n, ok, _d in crit if ok)
    con_res = sum(1 for (t, _m) in d["miradas"] if d["resultados"].get(t))
    lineas = [
        f"Comprador en papel · red {modelo.get('huella') if modelo else '?'} · política v{pol['version']} (margen {pct(pol['margen'], 0)})",
        f"Miradas grabadas: {len(d['miradas'])} ({con_res} con resultado), {d['perdidas']} perdidas. Auditoría: {len(dif)} diferencias.",
        f"Libro principal (5 s): {a['n']} compras, {a['k']} aciertos (la red esperaba {a['esperados']:.1f}), neto {a['neto']:+.2f} USDT de papel con 1 USDT fijo; "
        f"con Kelly {a['neto_b']:+.2f}. Abiertas: {a['abiertas']}.",
        f"Libro de su toque (15 s): {b['n']} compras, {b['k']} aciertos, neto {b['neto']:+.2f}.",
        f"Criterios de «apto»: {cumplidos} de {len(crit)}. " + ("APTO en papel: falta su orden." if apto else "NO APTO todavía."),
    ]
    _nueva, cambios = politica_que_manda(d["compras"], pol)
    lineas.append("Celdas: " + ("; ".join(cambios) if cambios else "sin cambios por R5."))
    if todo:
        lineas.append("")
        lineas += [f"  {'sí' if ok else 'no'} · {n}: {det}" for n, ok, det in crit]
        lineas += ["", "La red contra el mercado (todas las miradas con resultado), por tramo de probabilidad del lado perdedor:"]
        lineas += [f"  {pct(x['tramo'][0])} a {pct(x['tramo'][1])}: {x['n']} miradas, predicho {pct(x['predicho'] / x['n'], 2)}, "
                   f"prudente {pct(x['prudente'] / x['n'], 2)}, ocurrido {pct(x['ocurrido'] / x['n'], 2)}" for x in calibracion(d)]
        lineas += ["", "Mapa de ganancia (comprar 1 USDT al precio de la mirada, sin regla): celda, veces, aciertos frente a esperados, neto, veces con margen:"]
        lineas += [f"  {c}: {x['n']}, {x['k']} frente a {x['esperados']:.1f}, {x['neto']:+.1f}, {x['con_margen']}" for c, x in mapa(d).items()]
        lineas += ["", "Celdas del libro principal:"]
        lineas += [f"  {c}: {x.get('n', 0)} compras, {x.get('k', 0)} aciertos, neto {x.get('neto', 0):+.2f}, cola {x.get('cola', '-')}, manda {x['manda']}"
                   for c, x in sorted(celdas(d["compras"], pol["celdas_apagadas"]).items())]
        lineas += [""] + [f"  diferencia: {x}" for x in dif[:20]]
    return "\n".join(lineas)


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--politica" in argv:
        d = leer()
        nueva, cambios = politica_que_manda(d["compras"], G.cargar_politica()[0])
        print(json.dumps({"politica": nueva, "cambios": cambios}, ensure_ascii=False, indent=1))
    elif "--velas" in argv:
        dia = argv[argv.index("--velas") + 1]
        n, dif = auditar_velas(leer(), G.cargar(), velas_oficiales(dia))
        print(f"{n} miradas rehechas con el archivo oficial del {dia}; {len(dif)} diferencias")
        for x in dif[:20]:
            print("  " + x)
    else:
        print(informe(todo="--todo" in argv))


if __name__ == "__main__":
    main(sys.argv[1:])
