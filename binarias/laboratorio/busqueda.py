"""Búsqueda de formas nuevas (11/11/2026).

Cada tanda genera 2.000 fichas al azar dentro de la gramática, la red de búsqueda las ordena y se prueban en «elige» las 40
mejores (origen «red») y 10 al azar entre las demás (origen «azar», que mide si la red aporta). Mientras no haya 100 pruebas
para aprender, las 50 van al azar. Entra a vivo la que pasa la valla del juez; su cifra de «juzga» se calcula una sola vez,
al entrar, y nunca vuelve a la red ni a la selección."""
import json
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base  # noqa: E402
import formas as F  # noqa: E402
import juez as J  # noqa: E402
import red as R  # noqa: E402
from comun import EQUILIBRIO, TOPE_FAMILIA, TOPE_VIVO, TRAMOS  # noqa: E402

ORIGENES_NUEVOS = ("red", "azar", "dueño", "IA")


def probar(ctx, ficha, tramos=("elige",)):
    s = F.senal(ctx, ficha)
    B, _D, Rr, RI = J.apuestas(ctx, s, ficha["p"])
    return J.cifras(ctx, B, Rr, RI, ficha["p"], [x for x in TRAMOS if x[0] in tramos])


def guardar_prueba(con, fid, tramo, c):
    con.execute("INSERT OR REPLACE INTO pruebas (forma, tramo, n, k, wilson_inf, wilson_sup, p, n_i, k_i, t) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fid, tramo, c["n"], c["k"], c["wi"], c["ws"], c["p"], c.get("n_i"), c.get("k_i"), int(time.time())))


def nueva_forma(con, ficha, origen, lote=None, estado="probada", nombre=None):
    h = F.huella(ficha)
    if con.execute("SELECT 1 FROM formas WHERE huella=?", (h,)).fetchone():
        return None
    cur = con.execute("INSERT INTO formas (huella, ficha, origen, nombre, nacida, lote, estado, familia) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (h, json.dumps(ficha, ensure_ascii=False, sort_keys=True), origen, nombre or F.describir(ficha),
                       int(time.time()), lote, estado, F.familia(ficha)))
    return cur.lastrowid


def vivas(con):
    return con.execute("SELECT COUNT(*) FROM formas WHERE estado='viva'").fetchone()[0]


def familia_llena(con, fam, tope_familia=TOPE_FAMILIA):
    return con.execute("SELECT COUNT(*) FROM formas WHERE estado='viva' AND origen<>'pasada' AND familia=?",
                       (fam,)).fetchone()[0] >= tope_familia


def entrar(con, fid, ctx, ficha, tope=TOPE_VIVO, calcular_juzga=True):
    """Pasa a vivo (o a la espera si ya hay `tope` vivas o 12 de su familia). La cifra de «juzga» se calcula aquí, una vez."""
    if calcular_juzga and "pasada" not in ficha:
        guardar_prueba(con, fid, "juzga", probar(ctx, ficha, ("juzga",))["juzga"])
    ahora = int(time.time())
    if vivas(con) < tope and ("pasada" in ficha or not familia_llena(con, F.familia(ficha))):
        con.execute("UPDATE formas SET estado='viva', en_vivo=?, situacion='en observación', cambio=? WHERE id=?", (ahora, ahora, fid))
        return "viva"
    con.execute("UPDATE formas SET estado='admitida', cambio=? WHERE id=?", (ahora, fid))
    return "admitida"


def red_de_busqueda(con, minimo=100):
    filas = con.execute("SELECT f.ficha, p.n, p.k, p.wilson_inf, p.wilson_sup, p.p FROM formas f JOIN pruebas p "
                        "ON p.forma=f.id AND p.tramo='elige' WHERE f.origen IN ('red', 'azar', 'dueño', 'IA')").fetchall()
    if len(filas) < minimo:
        return None, len(filas)
    X, y = [], []
    for ficha, n, k, wi, ws, p in filas:
        f = json.loads(ficha)
        X.append(F.codificar(f))
        y.append(J.objetivo({"n": n, "k": k, "wi": wi}, f["p"]))
    return R.busqueda(X, y, semilla=len(filas)), len(filas)


def tanda(con, ctx, semilla, n_gen=2000, n_red=40, n_azar=10, tope=TOPE_VIVO):
    rng = random.Random(semilla)
    existentes = {h for (h,) in con.execute("SELECT huella FROM formas")}
    cand, vistos, intentos = [], set(), 0
    while len(cand) < n_gen and intentos < n_gen * 6:
        intentos += 1
        f = F.aleatoria(rng)
        h = F.huella(f)
        if h in existentes or h in vistos:
            continue
        vistos.add(h)
        cand.append(f)
    rb, aprendio = red_de_busqueda(con)
    if rb is not None:
        pred = rb.predecir(np.array([F.codificar(f) for f in cand]))
        orden = np.argsort(-pred, kind="stable")
        elegidas = [(cand[i], "red") for i in orden[:n_red].tolist()]
        resto = [cand[i] for i in orden[n_red:].tolist()]
        elegidas += [(f, "azar") for f in rng.sample(resto, min(n_azar, len(resto)))]
    else:
        elegidas = [(f, "azar") for f in rng.sample(cand, min(n_red + n_azar, len(cand)))]
    lote_id = base.leer(con, "lote", 0) + 1
    base.poner(con, "lote", lote_id)
    lote, mejores = [], []
    for f, origen in elegidas:
        fid = nueva_forma(con, f, origen, lote_id)
        if fid is None:
            continue
        c = probar(ctx, f)["elige"]
        guardar_prueba(con, fid, "elige", c)
        lote.append((fid, c, f["p"]))
        mejores.append(100 * (c["wi"] - EQUILIBRIO[f["p"]]) if c["n"] else -100.0)
    con.commit()
    admitidas = J.admitir(lote)
    entraron = []
    for fid, c, p in lote:
        if fid in admitidas:
            ficha = json.loads(con.execute("SELECT ficha FROM formas WHERE id=?", (fid,)).fetchone()[0])
            entraron.append((fid, entrar(con, fid, ctx, ficha, tope)))
    con.commit()
    por = {o: [m for (f, oo), m in zip(elegidas, mejores) if oo == o] for o in ("red", "azar")}
    return {"lote": lote_id, "probadas": len(lote), "admitidas": len(entraron), "entraron": [x for x in entraron if x[1] == "viva"],
            "a_vivo": sum(1 for _f, e in entraron if e == "viva"), "red": rb is not None,
            "aprendio_de": aprendio, "mejor_wi_sobre_eq": max(mejores) if mejores else None,
            "media_red": float(np.mean(por["red"])) if por["red"] else None,
            "media_azar": float(np.mean(por["azar"])) if por["azar"] else None}


def probar_dueno(con, ctx, ficha, tope=TOPE_VIVO):
    """Forma pedida por el dueño: se prueba en «elige» y entra a vivo para medirse, pase o no la valla (se informa cuál)."""
    fid = nueva_forma(con, ficha, "dueño")
    if fid is None:
        h = F.huella(ficha)
        fid = con.execute("SELECT id FROM formas WHERE huella=?", (h,)).fetchone()[0]
        return fid, None, "ya existía"
    c = probar(ctx, ficha)["elige"]
    guardar_prueba(con, fid, "elige", c)
    paso = bool(J.admitir([(fid, c, ficha["p"])]))
    estado = entrar(con, fid, ctx, ficha, tope)
    con.commit()
    return fid, c, ("pasó la valla" if paso else "no pasó la valla") + f"; {estado}"
