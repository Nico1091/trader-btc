"""Papel en vivo del laboratorio (11/11/2026).

Cada cierre de 5 min evalúa todas las formas vivas en la barra nueva con el mismo código de la historia (ventanas finitas),
sobre tres días de velas; E3 y E4 con 30 días, como el Centro, y el banco con 40. Abre sus apuestas de papel (una abierta por
forma, la siguiente desde T + 60 s + plazo) y cada minuto cierra las que ya tienen su vela de salida, con el cierre de futuros
y con el índice de precio. Si el laboratorio estuvo caído, rehace hasta dos días con velas cerradas y marca esas apuestas
como «semilla». Nada de esto compra."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base  # noqa: E402
import formas as F  # noqa: E402
import juez as J  # noqa: E402
import rasgos as RG  # noqa: E402
import red as R  # noqa: E402
from comun import DATOS, TOPE_FAMILIA, log  # noqa: E402

VENTANA, VENTANA_E34, VENTANA_BANCO = 3 * 86400, 30 * 86400, 40 * 86400
REDES = os.path.join(DATOS, "redes.json")


class MotorRed:
    """Las redes de mercado vigentes (una por plazo) y la decisión de usar la red o la neurona."""

    def __init__(self, ruta=REDES):
        d = json.load(open(ruta, encoding="utf-8"))
        self.ruta, self.t = ruta, d["t"]
        self.red, self.neu, self.usa, self.informe = {}, {}, {}, {}
        for p, x in d["plazos"].items():
            p = int(p)
            self.red[p] = R.MLP.desde_dict(x["red"])
            self.neu[p] = R.Neurona.desde_dict(x["neurona"])
            self.usa[p] = x["usa"]
            self.informe[p] = x["informe"]

    def modelo(self, p):
        return self.red[p] if self.usa[p] == "red" else self.neu[p]

    def prob(self, ctx, b=None):
        X, ok = ctx.rasgos_red(b)
        out = {}
        for p in self.red:
            a = np.full(len(X), np.nan)
            if ok.any():
                a[ok] = self.modelo(p).predecir(X[ok])
            out[p] = a
        return out

    def guardar(self):
        d = {"t": int(time.time()), "plazos": {}}
        for p in self.red:
            d["plazos"][str(p)] = {"red": self.red[p].a_dict(), "neurona": self.neu[p].a_dict(), "informe": self.informe[p],
                                   "usa": self.usa[p]}
        R.guardar(self.ruta, d)
        self.t = d["t"]


def prob_historia(ctx, motor):
    """Probabilidades de la historia: las de red_p.npz (a ciegas, mes a mes) y, después de su última barra, las del motor."""
    out = {p: np.full(ctx.nb, np.nan) for p in (10, 15)}
    ruta = os.path.join(DATOS, "red_p.npz")
    ultimo = None
    if os.path.exists(ruta):
        z = np.load(ruta)
        T = z["T"].astype(np.int64)
        idx = np.searchsorted(T, ctx.T)
        ok = (idx < len(T)) & (T[np.minimum(idx, len(T) - 1)] == ctx.T)
        for p in (10, 15):
            out[p][ok] = z[f"p{p}"][idx[ok]]
        ultimo = int(T[-1])
    resto = np.flatnonzero(ctx.T > (ultimo or 0))
    if len(resto) and motor is not None:
        pr = motor.prob(ctx, resto)
        for p in (10, 15):
            out[p][resto] = pr[p]
    return out


class Emulador:
    def __init__(self, con, vel, interes, motor):
        self.con, self.vel, self.interes, self.motor = con, vel, interes, motor
        self.hecho = base.leer(con, "hecho_T")
        self.recargar()

    def recargar(self):
        self.vivas = {fid: (json.loads(f), en) for fid, f, en in
                      self.con.execute("SELECT id, ficha, en_vivo FROM formas WHERE estado='viva'")}
        self.ultimo = {fid: t for fid, t in self.con.execute("SELECT forma, MAX(t) FROM senales GROUP BY forma")}

    def _libre(self, fid, T, plazo):
        u = self.ultimo.get(fid)
        return u is None or T >= u + 60 + 60 * plazo

    def paso(self):
        """Evalúa las barras de 5 min nuevas. Devuelve cuántas apuestas abrió."""
        nb = self.vel.n // 5
        T_ult = self.vel.t0 + 300 * nb
        if self.hecho is None:
            self.hecho = T_ult
            base.poner(self.con, "hecho_T", T_ult)
            return 0
        if T_ult <= self.hecho:
            return 0
        semilla = T_ult - self.hecho > 900
        desde_T = max(self.hecho, T_ult - 2 * 86400)
        ctx = RG.Contexto(self.vel.recorte(desde_T - VENTANA), self.interes)
        ctx.prob = self.motor.prob(ctx) if self.motor is not None else {}
        nuevas = np.flatnonzero((ctx.T > desde_T) & (ctx.T <= T_ult))
        tipos = {f.get("pasada") for f, _ in self.vivas.values()}
        especiales = {}
        if "E3" in tipos or "E4" in tipos:
            c30 = RG.Contexto(self.vel.recorte(desde_T - VENTANA_E34), None)
            s3, s4 = F.senal_e3_e4(c30, desde_T=desde_T + 1)
            for nombre, s in (("E3", s3), ("E4", s4)):
                especiales[nombre] = {int(c30.T[b]): int(s[b]) for b in np.flatnonzero(s)}
        if "banco" in tipos:
            c40 = RG.Contexto(self.vel.recorte(desde_T - VENTANA_BANCO), None)
            try:
                for nombre, s in F.senales_banco(c40, desde_T=desde_T + 1).items():
                    especiales[("banco", nombre)] = {int(c40.T[b]): int(s[b]) for b in np.flatnonzero(s)}
            except Exception as ex:
                log(f"banco sin calcular ({type(ex).__name__}: {str(ex)[:80]})")
        if "E5" in tipos and len(ctx.T):
            especiales["E5"] = {int(ctx.T[-1]): F.senal_e5_ultima(ctx)}
        if "t33" in tipos and len(nuevas):
            s = F.senal_t33(ctx, b=nuevas)
            especiales["t33"] = {int(ctx.T[b]): int(s[b]) for b in nuevas if s[b]}
        abiertas = 0
        for fid, (ficha, _en) in self.vivas.items():
            p, q = ficha["p"], ficha.get("pasada")
            if q is None or q in F.EQUIVALENTE:
                s = F.senal(ctx, ficha)
                lista = [(int(ctx.T[b]), int(s[b])) for b in nuevas if s[b]]
            else:
                m = especiales.get(("banco", ficha.get("senal")) if q == "banco" else q, {})
                lista = sorted((T, d) for T, d in m.items() if desde_T < T <= T_ult and d)
            for T, d in lista:
                if not self._libre(fid, T, p):
                    continue
                b = (T - ctx.t0) // 300 - 1
                pr = ctx.prob.get(p)
                pr = float(pr[b]) if pr is not None and 0 <= b < len(pr) and pr[b] == pr[b] else None
                self.con.execute("INSERT OR IGNORE INTO senales (forma, t, dir, plazo, p_red, semilla) VALUES (?, ?, ?, ?, ?, ?)",
                                 (fid, T, d, p, pr, int(semilla)))
                self.ultimo[fid] = T
                abiertas += 1
        self.con.commit()
        self.hecho = T_ult
        base.poner(self.con, "hecho_T", T_ult)
        return abiertas

    def cerrar(self):
        """Cierra las apuestas cuya vela de salida ya llegó. Espera el índice hasta 5 min; un hueco de datos no cuenta (res −1)."""
        C, I, n, t0 = self.vel.A[3], self.vel.I, self.vel.n, self.vel.t0
        cerradas = 0
        for sid, T, d, P in self.con.execute("SELECT id, t, dir, plazo FROM senales WHERE res IS NULL").fetchall():
            e = (T - t0) // 60
            s = e + P
            if s >= n:
                continue
            ce, cs = C[e], C[s]
            if ce != ce or cs != cs:
                if n > s + 60:
                    self.con.execute("UPDATE senales SET res=-1 WHERE id=?", (sid,))
                continue
            ie, i_s = I[e], I[s]
            falta_i = ie != ie or i_s != i_s
            if falta_i and n <= s + 5:
                continue
            ri = None if falta_i else (1 if (i_s - ie) * d > 0 else 0)
            self.con.execute("UPDATE senales SET entrada=?, salida=?, res=?, entrada_i=?, salida_i=?, res_i=? WHERE id=?",
                             (float(ce), float(cs), 1 if (cs - ce) * d > 0 else 0, None if falta_i else float(ie),
                              None if falta_i else float(i_s), ri, sid))
            cerradas += 1
        self.con.commit()
        return cerradas

    def situaciones(self, ahora=None):
        """Recalcula la situación de cada forma viva; devuelve los cambios (id, antes, ahora, n, k, origen, nombre)."""
        ahora = ahora or time.time()
        cambios = []
        filas = self.con.execute("SELECT id, origen, nombre, ficha, en_vivo, situacion FROM formas WHERE estado='viva'").fetchall()
        for fid, origen, nombre, ficha, en_vivo, sit in filas:
            p = json.loads(ficha)["p"]
            n, k = self.con.execute("SELECT COUNT(*), COALESCE(SUM(res), 0) FROM senales WHERE forma=? AND res IN (0, 1) AND t>=?",
                                    (fid, en_vivo or 0)).fetchone()
            jz = self.con.execute("SELECT n, k FROM pruebas WHERE forma=? AND tramo='juzga'", (fid,)).fetchone()
            nueva = J.estado_vivo(n, k, p, {"n": jz[0], "k": jz[1]} if jz else None, (ahora - (en_vivo or ahora)) / 86400)
            if nueva != sit:
                self.con.execute("UPDATE formas SET situacion=?, cambio=? WHERE id=?", (nueva, int(ahora), fid))
                cambios.append((fid, sit, nueva, n, k, origen, nombre))
        self.con.commit()
        return cambios

    def rotar(self, tope):
        """Rotación diaria: salen las descartadas que no son pasadas y entran las admitidas que esperaban cupo."""
        ahora = int(time.time())
        salen = [fid for (fid,) in self.con.execute(
            "SELECT id FROM formas WHERE estado='viva' AND situacion='descartada' AND origen<>'pasada'")]
        for fid in salen:
            self.con.execute("UPDATE formas SET estado='descartada', cambio=? WHERE id=?", (ahora, fid))
        libres = tope - self.con.execute("SELECT COUNT(*) FROM formas WHERE estado='viva'").fetchone()[0]
        cupo = {fam: TOPE_FAMILIA - n for fam, n in self.con.execute(
            "SELECT familia, COUNT(*) FROM formas WHERE estado='viva' AND origen<>'pasada' GROUP BY familia")}
        entran = []
        for fid, fam in self.con.execute("SELECT f.id, f.familia FROM formas f LEFT JOIN pruebas p ON p.forma=f.id AND "
                                         "p.tramo='elige' WHERE f.estado='admitida' ORDER BY p.wilson_inf DESC, f.cambio").fetchall():
            if len(entran) >= libres:
                break
            if cupo.get(fam, TOPE_FAMILIA) > 0:
                cupo[fam] = cupo.get(fam, TOPE_FAMILIA) - 1
                entran.append(fid)
        for fid in entran:
            self.con.execute("UPDATE formas SET estado='viva', en_vivo=?, situacion='en observación', cambio=? WHERE id=?",
                             (ahora, ahora, fid))
        self.con.commit()
        self.recargar()
        return salen, entran
