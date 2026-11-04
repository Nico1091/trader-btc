"""El borrador de la Mesa (04/11/2026): opera en papel, en vivo, los mercados de 15 min con los precios reales del libro.

En cada cierre de múltiplo de 15 min aplica el núcleo (ruptura de 20 velas de 5 min, al revés), anota el SÍ o NO y el precio de
compra real a los 5, 30 y 60 s, y liquida con el ganador oficial del mercado (si tarda, con las velas). Para contar usa el
precio de los 30 s, que es cuando él alcanza a tocar; si pasa del tope, esa operación no entra.
Lo que el PC no vio (apagado o dormido) se rehace con las velas a 0,51 y queda marcado «semilla»: nunca cuenta como precio real.
"""
import json
import os
import threading
import time

import conexion as C
import reglas as R

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
ARCHIVO = os.path.join(DATOS, "borrador.json")
PRECIO_SEMILLA = 0.51


def senal(v1, t_dec):
    """Idéntica a semaforo.senal: ruptura al revés. Velas (t, alto, bajo, cierre); la prueba compara las dos."""
    por5 = {}
    for t, hi, lo, c in v1:
        if t + 60 > t_dec:
            continue
        k = t // 300
        a = por5.setdefault(k, [0, -1e18, 1e18, 0.0, 0])
        a[1], a[2], a[3], a[4] = max(a[1], hi), min(a[2], lo), c, a[4] + 1
    llaves = sorted(k for k, a in por5.items() if a[4] == 5)
    if len(llaves) < 21 or (llaves[-1] + 1) * 300 != t_dec:
        return 0
    ult = por5[llaves[-1]]
    prev = [por5[k] for k in llaves[-21:-1]]
    if ult[3] > max(p[1] for p in prev):
        return -1
    if ult[3] < min(p[2] for p in prev):
        return 1
    return 0


class Borrador:
    def __init__(self, cfg=R.CFG):
        self.cfg, self.cand = cfg, threading.Lock()
        self.ops, self.revisada = [], None
        os.makedirs(DATOS, exist_ok=True)
        try:
            with open(ARCHIVO, encoding="utf-8") as f:
                self.ops = json.load(f)["ops"]
        except (OSError, ValueError, KeyError):
            self.ops = []

    def copia(self):
        with self.cand:
            return [dict(o) for o in self.ops]

    def _guardar(self):
        tmp = ARCHIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ops": self.ops[-3000:]}, f, ensure_ascii=False)
        os.replace(tmp, ARCHIVO)

    def sembrar(self, dias=9):
        """Rehace con velas lo que no vio en vivo. Devuelve cuántas añadió."""
        v5 = C.historial(dias)
        v = [(x[0], x[2], x[3], x[4]) for x in v5]
        cierre = {x[0] + 60: x[3] for x in v}
        ahora, nuevas = time.time(), []
        with self.cand:
            hechas = {o["t"] for o in self.ops}
            for i, x in enumerate(v):
                t = x[0] + 60
                if t % 900 or t in hechas or t + 960 > ahora:
                    continue
                s = senal(v[max(0, i - 130):i + 1], t)
                a, b = cierre.get(t), cierre.get(t + 900)
                if s and a is not None and b is not None:
                    m = (b - a) * s
                    res = 1 if m > 0 else (0.5 if m == 0 else 0)
                    nuevas.append({"t": t, "dir": s, "semilla": True, "ask30": PRECIO_SEMILLA, "entra": True, "res": res,
                                   "neto": round(R.neto_op(res, PRECIO_SEMILLA, self.cfg), 4), "si": False, "doi": None})
            self.ops = sorted(self.ops + nuevas, key=lambda o: o["t"])
            self._guardar()
        return len(nuevas)

    def _decidir(self, t_dec):
        """Cierre de vela de múltiplo de 15 min: si hay señal, abre la operación."""
        cerr, _ = C.velas(160)
        if not cerr or cerr[-1][0] + 60 != t_dec:
            return False
        s = senal([(x[0], x[2], x[3], x[4]) for x in cerr], t_dec)
        if not s:
            return True
        try:
            doi = C.cambio_interes(t_dec)
        except Exception:
            doi = None
        with self.cand:
            r = R.resumen(self.ops, t_dec, self.cfg)
            op = {"t": t_dec, "dir": s, "aviso": cerr[-1][4], "ask5": None, "ask30": None, "ask60": None, "entra": None, "res": None,
                  "neto": None, "si": R.marcar_si(r["neto"], r["perdio"], doi, self.cfg), "doi": None if doi is None else round(doi, 6),
                  "neto_previo": r["neto"], "reciente": f"{r['k25']}/{r['n25']}"}
            self.ops.append(op)
            self._guardar()
        return True

    def _muestrear(self, ahora, m):
        """Anota el precio real de compra a los 5, 30 y 60 s de la señal."""
        if not m:
            return
        with self.cand:
            cambio = False
            for o in self.ops[-3:]:
                if o.get("res") is not None or o["t"] != m.get("t"):
                    continue
                o["topic"], ask, seg = m["topic"], (m.get("ask") or {}).get(o["dir"]), ahora - o["t"]
                for campo, desde in (("ask5", 3), ("ask30", 30), ("ask60", 60)):
                    if ask is not None and o.get(campo) is None and seg >= desde:
                        o[campo] = ask
                        cambio = True
                if o.get("entra") is None and o.get("ask30") is not None:
                    o["entra"] = o["ask30"] <= self.cfg["ask_max"]
                    cambio = True
            if cambio:
                self._guardar()

    def _cerrar(self, ahora):
        with self.cand:
            abiertas = [dict(o) for o in self.ops if o.get("res") is None and o["t"] + 908 <= ahora]
        for a in abiertas:
            ganador = None
            if a.get("topic"):
                try:
                    ganador = C.resultado(a["topic"])
                except Exception:
                    ganador = None
            if ganador is None and ahora < a["t"] + 1080:
                continue  # se le da tres minutos a la resolución oficial
            res, fuente = (1 if ganador == a["dir"] else 0), "oficial"
            if ganador is None:
                x, _ = C.velas(16, (a["t"] - 60) * 1000)
                if len(x) < 16:
                    continue
                m = (x[15][4] - x[0][4]) * a["dir"]
                res, fuente = (1 if m > 0 else (0.5 if m == 0 else 0)), "velas"
            with self.cand:
                for o in self.ops:
                    if o["t"] == a["t"]:
                        o["res"], o["fuente"] = res, fuente
                        if o.get("entra") and o.get("ask30"):
                            o["neto"] = round(R.neto_op(res, o["ask30"], self.cfg), 4)
                self._guardar()

    def paso(self, ahora, m):
        t_dec = int(ahora // 900 * 900)
        if ahora - t_dec >= 3 and self.revisada != t_dec and not any(o["t"] == t_dec for o in self.ops[-3:]):
            if self._decidir(t_dec):
                self.revisada = t_dec
        self._muestrear(ahora, m)
        self._cerrar(ahora)
