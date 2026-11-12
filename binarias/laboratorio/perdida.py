"""«Comprar sobre la pérdida» (11/11/2026, pedido suyo): en las binarias de 15 min, cuando BTC ya se movió fuerte dentro de
la ventana, el lado que va perdiendo queda barato y paga más. Regla escrita antes de ver resultados:

- Ventanas de 15 min alineadas a :00, :15, :30 y :45 (Predict.fun «BTC Up or Down 15m»). Gana «sube» si el cierre del
  minuto 15 queda por encima de la apertura de la ventana; empate = fallo.
- Miradas al cierre de los minutos 3, 5, 7, 9 y 11. Movimiento normalizado z = ln(precio / apertura) / (σ60 · √(15 − m)),
  con σ60 la raíz de la media de los rendimientos de 1 min al cuadrado en los últimos 60 min (la misma de los rasgos).
- El lado perdedor es el contrario al movimiento. Tabla: cuántas veces gana el perdedor por minuto y por tamaño de |z|
  (0,5-1; 1-1,5; 1,5-2; 2-3; 3 o más). Precio máximo que vale la pena pagar = 0,98 × acierto (comisión del 2 %).
- En vivo, la primera mirada de cada ventana con |z| ≥ 1 cuenta como una compra de papel del lado perdedor.
Ni la caja ni la placa ven el precio real de la app (sale con su llave, que no sale del PC): el informe dice el precio
máximo y él compara. Es devolución, como manda la regla 6.2. Nada de esto compra."""
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validacion as V  # noqa: E402
from comun import DATOS, TRAMOS, hora, num, pct  # noqa: E402
from rasgos import en  # noqa: E402

MINUTOS = (3, 5, 7, 9, 11, 13, 14)  # v2 (11/11, 21:05, antes de ver sus cifras): 13 y 14 por su «compro a lo último»
CUBOS = ((0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 1e9))
UMBRAL_VIVO = 1.0
COMISION = 0.02
TABLA = os.path.join(DATOS, "perdida.json")


def cubo(z):
    a = abs(z)
    for lo, hi in CUBOS:
        if lo <= a < hi:
            return f"{lo:g}-{hi:g}" if hi < 1e8 else f"{lo:g}+"
    return None


def miradas(vel, desde=None, hasta=None):
    """Todas las miradas de las ventanas completas entre desde y hasta (s, apertura de la ventana).
    Devuelve arreglos: ventana, minuto, z, lado perdedor (+1 sube, −1 baja), ganó el perdedor (1, 0) y final presente."""
    C, O, n, t0 = vel.A[3, :vel.n], vel.A[0, :vel.n], vel.n, vel.t0
    a = 0 if desde is None else max(0, -(-(int(desde) - t0) // 900) * 15)
    b = n if hasta is None else min(n, (int(hasta) - t0) // 60)
    s = np.arange(a, max(a, b - 14), 15, dtype=np.int64)
    if not len(s):
        return {k: np.zeros(0) for k in ("ventana", "m", "z", "lado", "gana", "final")}
    lc = np.log(C)
    r = np.r_[0.0, np.diff(lc)]
    r2 = r * r
    filas = []
    ap, fin = O[s], C[s + 14]
    for m in MINUTOS:
        j = s + m - 1
        sig = np.sqrt(np.maximum(en(r2, 60, j, "mean"), 1e-12))
        with np.errstate(invalid="ignore", divide="ignore"):
            z = (lc[j] - np.log(ap)) / (sig * math.sqrt(15 - m))
        filas.append((np.full(len(s), m), z))
    ventana = np.tile(t0 + 60 * s, len(MINUTOS))
    m = np.concatenate([f[0] for f in filas])
    z = np.concatenate([f[1] for f in filas])
    apt, fint = np.tile(ap, len(MINUTOS)), np.tile(fin, len(MINUTOS))
    lado = -np.sign(z)
    with np.errstate(invalid="ignore"):
        gana = ((fint - apt) * lado > 0).astype(np.int8)
    valido = np.isfinite(z) & (z != 0) & np.isfinite(apt) & np.isfinite(fint)
    return {"ventana": ventana[valido], "m": m[valido], "z": z[valido], "lado": lado[valido].astype(np.int8),
            "gana": gana[valido], "final": fint[valido]}


def armar_tabla(vel):
    """Tabla por tramo, minuto y cubo: n, k, acierto, Wilson y precio máximo (0,98 × acierto). Se guarda en datos/perdida.json."""
    x = miradas(vel)
    out = {"regla": "lado perdedor; |z| = |ln(precio/apertura)| / (σ60·√(15−m)); empate = fallo; precio máximo = 0,98 × acierto",
           "tramos": {}}
    for nombre, a, b in TRAMOS[1:]:
        t = {}
        sel = (x["ventana"] >= a) & (x["ventana"] < b)
        for m in MINUTOS:
            t[str(m)] = {}
            for lo, hi in CUBOS:
                q = sel & (x["m"] == m) & (np.abs(x["z"]) >= lo) & (np.abs(x["z"]) < hi)
                n, k = int(q.sum()), int(x["gana"][q].astype(np.int64).sum())
                wi, ws = V.wilson(k, n)
                t[str(m)][cubo(lo)] = {"n": n, "k": k, "p": (k / n) if n else None, "wi": wi, "ws": ws,
                                       "precio_max": round((1 - COMISION) * k / n, 4) if n else None}
        out["tramos"][nombre] = t
    # lo que se usa en vivo: la primera mirada de cada ventana con |z| ≥ 1, en «juzga» (a ciegas)
    a, b = dict((n, (a, b)) for n, a, b in TRAMOS)["juzga"]
    prim = primeras(x, a, b)
    n, k = len(prim), int(sum(int(g) for g in prim.values()))
    out["vivo_juzga"] = {"n": n, "k": k, "p": (k / n) if n else None, "precio_max": round((1 - COMISION) * k / n, 4) if n else None}
    out["precio"] = {m: {c: v["precio_max"] for c, v in d.items()} for m, d in out["tramos"]["juzga"].items()}
    with open(TABLA, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def primeras(x, a, b):
    """{ventana: ganó} con la primera mirada de cada ventana que llega a |z| ≥ 1 (la compra de papel en vivo)."""
    out = {}
    orden = np.lexsort((x["m"], x["ventana"]))
    for i in orden.tolist():
        w = int(x["ventana"][i])
        if w < a or w >= b or w in out or abs(x["z"][i]) < UMBRAL_VIVO:
            continue
        out[w] = int(x["gana"][i])
    return out


def precio_tabla(m, z):
    try:
        return json.load(open(TABLA, encoding="utf-8"))["precio"][str(m)].get(cubo(z))
    except (OSError, ValueError, KeyError):
        return None


class Perdida:
    """En vivo: en cada ventana, la primera mirada con |z| ≥ 1 se anota como compra de papel del lado perdedor."""

    def __init__(self, con, vel):
        self.con, self.vel = con, vel
        con.execute("CREATE TABLE IF NOT EXISTS perdidas (ventana INTEGER PRIMARY KEY, m INTEGER, z REAL, lado INTEGER, cubo TEXT, "
                    "precio_max REAL, res INTEGER, t INTEGER)")
        con.commit()
        try:
            self.tabla = json.load(open(TABLA, encoding="utf-8"))
        except (OSError, ValueError):
            self.tabla = None

    def paso(self):
        vel = self.vel
        ultimo = vel.t0 + 60 * (vel.n - 1)  # apertura de la última vela presente (ya cerrada)
        desde = ultimo - 3 * 3600
        x = miradas_parciales(vel, desde)
        nuevas = 0
        for w, m, z in x:
            if abs(z) < UMBRAL_VIVO or self.con.execute("SELECT 1 FROM perdidas WHERE ventana=?", (w,)).fetchone():
                continue
            self.con.execute("INSERT OR IGNORE INTO perdidas (ventana, m, z, lado, cubo, precio_max, t) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (w, m, float(z), int(-math.copysign(1, z)), cubo(z), precio_tabla(m, z), int(time.time())))
            nuevas += 1
        C, O = vel.A[3], vel.A[0]
        for w, lado in self.con.execute("SELECT ventana, lado FROM perdidas WHERE res IS NULL").fetchall():
            s = (w - vel.t0) // 60
            if s + 14 < vel.n and C[s + 14] == C[s + 14] and O[s] == O[s]:
                self.con.execute("UPDATE perdidas SET res=? WHERE ventana=?", (1 if (C[s + 14] - O[s]) * lado > 0 else 0, w))
        self.con.commit()
        return nuevas

    def cifras(self, desde=0):
        n, k = self.con.execute("SELECT COUNT(*), COALESCE(SUM(res), 0) FROM perdidas WHERE res IN (0, 1) AND ventana>=?",
                                (desde,)).fetchone()
        return n, k

    def linea(self):
        n, k = self.cifras()
        t = "Pérdida a 15 min (comprar el lado que va perdiendo cuando |z| ≥ 1): "
        t += f"en vivo {k} de {n} ({pct(k / n)})" if n else "en vivo aún sin ventanas cerradas"
        if self.tabla and self.tabla.get("vivo_juzga", {}).get("n"):
            j = self.tabla["vivo_juzga"]
            t += f"; a ciegas en la historia {pct(j['p'])} en {num(j['n'], 0)}; vale la pena si cuesta menos de {num(j['precio_max'], 2)}"
        ab = self.con.execute("SELECT ventana, m, lado, precio_max FROM perdidas WHERE res IS NULL ORDER BY ventana DESC LIMIT 1").fetchone()
        if ab:
            w, m, lado, q = ab
            t += (f". Abierta: ventana de las {hora(w, '%H:%M')}, minuto {m}, {'SUBE' if lado > 0 else 'BAJA'}"
                  + (f", precio máximo {num(q, 2)}" if q else ""))
        return t + "."


def miradas_parciales(vel, desde):
    """Miradas ya cerradas de las ventanas recientes, aunque la ventana no haya terminado: (ventana, minuto, z) en orden."""
    C, O, t0, n = vel.A[3, :vel.n], vel.A[0, :vel.n], vel.t0, vel.n
    a = max(0, -(-(int(desde) - t0) // 900) * 15)
    out = []
    lc_cache = {}
    for s in range(a, n, 15):
        for m in MINUTOS:
            j = s + m - 1
            if j >= n or j < 60:
                continue
            if O[s] != O[s] or C[j] != C[j]:
                continue
            seg = C[j - 60:j + 1]
            if np.isnan(seg).any():
                continue
            r = np.diff(np.log(seg))
            sig = math.sqrt(max(float(np.mean(r * r)), 1e-12))
            z = (math.log(C[j]) - math.log(O[s])) / (sig * math.sqrt(15 - m))
            out.append((int(t0 + 60 * s), m, z))
    del lc_cache
    return out


def texto_tabla(tabla=None):
    tabla = tabla or json.load(open(TABLA, encoding="utf-8"))
    lineas = ["Laboratorio · comprar sobre la pérdida (15 min), a ciegas jul-2025 a oct-2026",
              "Por minuto y tamaño del movimiento: acierto del lado perdedor (n) y precio máximo que vale la pena:"]
    for m in map(str, MINUTOS):
        partes = []
        for c, v in tabla["tramos"]["juzga"][m].items():
            if v["n"]:
                partes.append(f"|z| {c.replace('.', ',')}: {pct(v['p'], 0)} ({num(v['n'], 0)}) → {num(v['precio_max'], 2)}")
        lineas.append(f"Minuto {m}: " + "; ".join(partes))
    j = tabla.get("vivo_juzga")
    if j and j.get("n"):
        lineas.append(f"Regla en vivo (primera mirada con |z| ≥ 1): {pct(j['p'])} en {num(j['n'], 0)} ventanas; "
                      f"compre solo si el lado perdedor cuesta menos de {num(j['precio_max'], 2)}. Es papel.")
    return "\n".join(lineas)
