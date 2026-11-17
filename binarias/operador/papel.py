"""Comprador de papel del operador (16/11/2026): el del 12/11 (comprador/comprador.py) con la ventana como parámetro.
No manda órdenes: solo lee, calcula y anota. Reglas: REGLAS-ANTES-DE-MEDIR.md (R3 con las enmiendas 1 y 2).

Dos series que no se mezclan, una por ventana entera:
- «papel» (con una llave que lee): en los 5 s siguientes al cierre de cada minuto 1 a W − 1 lee el libro de los dos lados y
  el precio de contado del instante, calcula el vector de ganancia y lo graba entero, compre o no. Si un lado llega al
  margen, vuelve a leer 5 s y 15 s después y solo anota la compra si entonces sigue cumpliendo, al precio de ese instante
  (llenado honesto). Una compra por ventana y por libro. Libro A: 1 USDT fijo. Libro B: fracción de Kelly con tope, sobre un
  saldo de papel. Liquida con el ganador oficial.
- «sin_llave» (enmienda 2): sin libro no hay compras de papel. Anota la probabilidad del modelo y el precio límite de cada
  lado, con la apertura de contado como referencia, y liquida con las velas de contado. Mide solo si el modelo acierta lo que dice.

Recibe el módulo de conexión de quien lo llama y de él usa solo lecturas (leer_libros, velas_contado, velas_desde,
resultado, ahora). Aquí no existe la compra real: de eso se encarga ejecutor.py, con el candidato que devuelve paso()."""
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import nucleo as N  # noqa: E402

MIRADA_S = 5                 # enmienda 1: la mirada vale si se logra en los 5 s siguientes al cierre del minuto
LLENADOS = (5, 15)           # segundos entre decidir y comprar: el automático y un doble toque
NIVELES = 5                  # niveles del libro que se graban por lado
SIN_GANADOR_S = 7200         # R3.7: sin ganador oficial en dos horas, la compra no cuenta
SERIES = ("papel", "sin_llave")


def _cal_vacia():
    return {"ventanas": 0, "miradas": 0, "esperados": 0.0, "ocurridos": 0, "pl_modelo": 0.0, "pl_normal": 0.0,
            "dif": 0.0, "dif2": 0.0, "tramos": [[0, 0.0, 0.0, 0] for _ in N.TRAMOS_P]}


def _menos_log(p, y):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return -math.log(p if y else 1 - p)


class Papel:
    def __init__(self, C, W, fila, log=print, datos=None, modelo=None):
        self.C, self.W, self.fila, self.log = C, W, fila, log
        self.datos = datos or N.DATOS
        self.dur = 60 * W
        self.modelo = modelo if modelo is not None else N.cargar(W)
        self.pol, self.pol_mtime = N.politica_base(), -1
        self.compras, self.saldo = [], {str(L): N.SALDO_PAPEL for L in LLENADOS}
        self.ventanas, self.hechas, self.pend = {}, {}, None
        self.t_resultado, self.ultimo = {}, None
        self.cont = {"miradas": 0, "perdidas": 0, "candidatos": 0, "escapes": 0, "sin_libro": 0}
        self.cal = {s: _cal_vacia() for s in SERIES}
        os.makedirs(self.datos, exist_ok=True)
        self._cargar()

    # ------------------------------------------------------------ archivos
    def _ruta(self, nombre):
        return os.path.join(self.datos, f"{nombre}_{self.W}.json")

    def _cargar(self):
        try:
            with open(self._ruta("papel"), encoding="utf-8") as f:
                d = json.load(f)
            self.ventanas = {int(k): v for k, v in d.get("ventanas", {}).items()}
            self.saldo.update(d.get("saldo", {}))
            self.cont.update(d.get("cont", {}))
            for s in SERIES:
                self.cal[s].update(d.get("cal", {}).get(s, {}))
        except (OSError, ValueError):
            pass
        try:
            with open(self._ruta("compras"), encoding="utf-8") as f:
                self.compras = json.load(f).get("compras", [])
        except (OSError, ValueError):
            pass

    @staticmethod
    def _escribir(ruta, dato):
        with open(ruta + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dato, f, ensure_ascii=False)
        os.replace(ruta + ".tmp", ruta)

    def _guardar(self, compras=False):
        """El estado pequeño se guarda en cada mirada; las compras, solo cuando cambian (para no gastar la memoria de la caja)."""
        self._escribir(self._ruta("papel"), {"ventanas": self.ventanas, "saldo": self.saldo, "cont": self.cont, "cal": self.cal})
        if compras:
            self._escribir(self._ruta("compras"), {"compras": self.compras})

    def _anotar(self, fila):
        self.fila({"W": self.W, **fila})

    def _politica(self):
        ruta = self._ruta("politica")
        try:
            mt = os.path.getmtime(ruta)
        except OSError:
            mt = None
        if mt == self.pol_mtime:
            return
        self.pol_mtime = mt
        self.pol, recortes = N.cargar_politica(ruta)
        self.log(f"papel de {self.W} min: política v{self.pol['version']} (margen {self.pol['margen']:g}, Kelly {self.pol['kelly']:g}, "
                 f"{len(self.pol['celdas_apagadas'])} celdas apagadas)")
        for r in recortes:
            self.log(f"papel de {self.W} min: política recortada: {r}")

    # ------------------------------------------------------------ bucle
    def paso(self, ahora, m):
        """ahora: hora de Binance. m: el mercado de W minutos en curso; el de Binance (con topic, tokens y apertura oficial) o
        uno armado con velas («sintetico») si no hay llave. Devuelve el candidato de esta vuelta, para el ejecutor, o None."""
        cand = None
        if self.modelo is None:
            return None
        self._politica()
        if m and (m.get("sintetico") or (m.get("abierto") and m.get("strike"))) and 0 < m["t"] + self.dur - ahora <= self.dur:
            cierre = int(ahora // 60) * 60
            mm = (cierre - m["t"]) // 60
            if m["t"] not in self.hechas:  # tras un reinicio a mitad de ventana no se repiten las miradas ya grabadas
                self.hechas[m["t"]] = {x[0] for x in self.ventanas.get(m["t"], {}).get("miradas", [])}
            hechas = self.hechas[m["t"]]
            if 1 <= mm <= self.W - 1 and mm not in hechas:
                if ahora - cierre <= MIRADA_S:
                    cand = self._mirada(m, mm, cierre, hechas)
                else:
                    hechas.add(mm)
                    self._perdida(m, mm, "pasaron los 5 s")
            if self.pend and self.pend["t"] == m["t"]:
                for L in LLENADOS:
                    if L not in self.pend["hechos"] and ahora - self.pend["hora"] >= L:
                        self._llenar(m, L)
        for t in [t for t in self.hechas if t < ahora - 3600]:
            del self.hechas[t]
        self._liquidar(ahora)
        return cand

    def serie_abierta(self, t):
        """La serie con la que ya se empezó a mirar la ventana t («papel» o «sin_llave»), o None si aún no tiene miradas.
        Una ventana se mide entera en una sola serie: el operador lo consulta para no mezclarlas tras un reinicio."""
        v = self.ventanas.get(t)
        return v.get("serie", "papel") if v else None

    def pendiente(self, ahora, m):
        """Verdadero si en los próximos segundos toca una mirada o un llenado: el bucle del operador gira entonces más rápido."""
        if self.pend and m and self.pend["t"] == m["t"] and len(self.pend["hechos"]) < len(LLENADOS):
            return True
        if not m or self.modelo is None:
            return False
        mm = (int(ahora // 60) * 60 - m["t"]) // 60
        return 1 <= mm <= self.W - 1 and mm not in self.hechas.get(m["t"], ()) and ahora % 60 <= MIRADA_S

    def _perdida(self, m, mm, motivo):
        self.cont["perdidas"] += 1
        self._anotar({"tipo": "mirada perdida", "serie": "sin_llave" if m.get("sintetico") else "papel", "t": m["t"], "m": mm,
                      "motivo": motivo, "hora": round(self.C.ahora(), 2)})

    def _leer(self, m, mm):
        """Libro de los dos lados (si hay llave) y velas de contado en este instante. None si Binance aún no entrega la vela
        cerrada del minuto mm; "hueco" si faltan velas; si no, lo necesario para el vector."""
        if not m.get("sintetico"):
            self.C.leer_libros(m)
        cerr, viva = self.C.velas_contado(90)
        ahora = self.C.ahora()
        T = [v[0] for v in cerr]
        if not T or T[-1] != m["t"] + 60 * (mm - 1) or m["t"] not in T:
            return None
        s, j = T.index(m["t"]), len(T) - 1
        if j - s + 1 != mm or j < 61 or any(T[i] != T[i - 1] + 60 for i in range(j - 60, j + 1)):
            return "hueco"
        return {"ahora": ahora, "T": T, "s": s, "c": [v[4] for v in cerr], "h": [v[2] for v in cerr], "l": [v[3] for v in cerr],
                "v": [v[5] for v in cerr], "vivo": float((viva or cerr[-1])[4]), "resta": m["t"] + self.dur - ahora,
                "apertura": float(cerr[s][1])}

    def _vector(self, m, mm, d):
        com = (m.get("comision_bps") or 200) / 10000
        ask = {} if m.get("sintetico") else (m.get("ask") or {})
        return N.vector(self.modelo, d["c"], d["h"], d["l"], d["v"], d["s"], mm, float(m["strike"]), d["T"][-1], ask,
                        com, self.pol["margen"], vivo=d["vivo"], resta_s=d["resta"], W=self.W)

    @staticmethod
    def _lado(m, lado, d):
        asks = ((m.get("asks") or {}).get(lado) or [])[:NIVELES]
        x = {k: (round(d[k], 6) if isinstance(d.get(k), float) else d.get(k)) for k in ("papel", "p", "p_prud", "q", "G", "G_prud", "limite", "kelly")}
        x["bid"] = (m.get("bid") or {}).get(lado)
        x["libro"] = [[p, s] for p, s in asks]
        return x

    # ------------------------------------------------------------ mirada
    def _mirada(self, m, mm, cierre, hechas):
        d = self._leer(m, mm)
        if d is None:
            return None  # la vela cerrada aún no llega: se reintenta en la próxima vuelta mientras duren los 5 s
        hechas.add(mm)
        if d == "hueco":
            return self._perdida(m, mm, "faltan velas")
        if d["ahora"] - cierre > MIRADA_S:
            return self._perdida(m, mm, "la lectura tardó más de 5 s")
        sin_libro = bool(m.get("sintetico"))
        if self.serie_abierta(m["t"]) not in (None, "sin_llave" if sin_libro else "papel"):
            return self._perdida(m, mm, "la ventana empezó en la otra serie")
        if sin_libro:
            m["strike"] = d["apertura"]
        vec = self._vector(m, mm, d)
        if vec is None:
            return self._perdida(m, mm, "sin rasgos")
        if sin_libro:
            lado, motivo, celda, sombra = None, "sin libro: solo se mide el modelo", None, False
        else:
            lado, motivo, celda, sombra = N.decidir(vec, self.pol, d["resta"], self.W)
        serie = "sin_llave" if sin_libro else "papel"
        fila = {"tipo": "mirada", "serie": serie, "t": m["t"], "topic": m.get("topic"), "m": mm, "plazo": N.plazo(self.W, mm),
                "hora": round(d["ahora"], 2), "demora_s": round(d["ahora"] - cierre, 2), "strike": float(m["strike"]),
                "cierre": d["c"][-1], "vivo": d["vivo"], "resta_s": round(d["resta"], 1), "z": round(vec["z"], 4),
                "z_cierre": round(vec["z_cierre"], 4), "p": round(vec["p"], 6), "p_cierre": round(vec["p_cierre"], 6),
                "perdedor": vec["perdedor"], "x": [round(v, 6) for v in vec["x"]],
                "lados": {str(k): self._lado(m, k, v) for k, v in vec["lados"].items()}, "decide": lado or 0, "motivo": motivo,
                "celda": celda, "sombra": sombra, "modelo": self.modelo.get("huella"), "politica": self.pol["version"],
                "margen": self.pol["margen"], "comision": (m.get("comision_bps") or 200) / 10000}
        self._anotar(fila)
        self.ultimo = fila
        self.cont["miradas"] += 1
        if sin_libro:
            self.cont["sin_libro"] += 1
        v = self.ventanas.setdefault(m["t"], {"topic": m.get("topic"), "serie": serie, "miradas": []})
        v["miradas"].append([mm, round(vec["p"], 6), vec["perdedor"], round(vec["z"], 4), round(vec["lados"][vec["perdedor"]]["p_prud"], 6)])
        self._guardar()
        if not lado:
            return None
        self.cont["candidatos"] += 1
        self.pend = {"t": m["t"], "topic": m.get("topic"), "m": mm, "lado": lado, "celda": celda, "sombra": sombra,
                     "hora": d["ahora"], "q0": vec["lados"][lado]["q"], "hechos": set()}
        return {"W": self.W, "t": m["t"], "m": mm, "lado": lado, "celda": celda, "sombra": sombra, "vec": vec, "hora": d["ahora"],
                "resta": d["resta"], "pol": dict(self.pol)}

    # ------------------------------------------------------------ llenado honesto
    def _ya_compro(self, t, L, sombra):
        return any(o["t"] == t and o["llenado"] == L and bool(o.get("sombra")) == bool(sombra) for o in self.compras[-60:])

    def _llenar(self, m, L):
        pe = self.pend
        pe["hechos"].add(L)
        if self._ya_compro(pe["t"], L, pe["sombra"]):
            return
        base = {"tipo": "llenado", "serie": "papel", "t": pe["t"], "m": pe["m"], "lado": pe["lado"], "llenado": L, "celda": pe["celda"],
                "sombra": pe["sombra"], "hora": round(self.C.ahora(), 2)}
        d = self._leer(m, pe["m"])
        vec = self._vector(m, pe["m"], d) if isinstance(d, dict) else None
        dd = vec["lados"][pe["lado"]] if vec else None
        q = dd.get("q") if dd else None
        if not dd or not q:
            motivo = "sin lectura o sin precio"
        elif not N.PRECIO_MIN - 1e-9 <= q <= N.PRECIO_MAX + 1e-9:
            motivo = "precio fuera de 0,01 a 0,90"
        elif d["resta"] < N.MIN_RESTA_S:
            motivo = "quedan menos de 10 s"
        elif dd["G_prud"] < self.pol["margen"] - 1e-12:
            motivo = "se escapó: " + ("subió el precio" if q > pe["q0"] + 1e-9 else "bajó la probabilidad")
        else:
            motivo = None
        if motivo:
            self.cont["escapes"] += 1
            self._anotar({**base, "compra": False, "motivo": motivo, "q": q, "vivo": d["vivo"] if isinstance(d, dict) else None,
                          "G_prud": round(dd["G_prud"], 6) if dd and dd.get("G_prud") is not None else None})
            self._guardar()
            return
        com = (m.get("comision_bps") or 200) / 10000
        disp = 0.0
        for p, s in ((m.get("asks") or {}).get(pe["lado"]) or []):
            if p <= q + 1e-9:
                disp += s
        usdt_b = 0.0 if pe["sombra"] else N.importe_b(float(self.saldo[str(L)]), dd, self.pol, disp)
        op = {"t": pe["t"], "W": self.W, "topic": pe["topic"], "m": pe["m"], "plazo": N.plazo(self.W, pe["m"]), "lado": pe["lado"],
              "papel": dd["papel"], "celda": pe["celda"], "sombra": pe["sombra"], "llenado": L, "precio": q,
              "precio_decision": pe["q0"], "p": round(dd["p"], 6), "p_prud": round(dd["p_prud"], 6), "G": round(dd["G"], 6),
              "G_prud": round(dd["G_prud"], 6), "z": round(vec["z"], 4), "hora": round(d["ahora"], 2),
              "resta_s": round(d["resta"], 1), "vivo": d["vivo"], "disp": round(disp, 2), "comision": com,
              "contratos": round(N.contratos(q, 1.0, com), 2), "usdt_b": usdt_b, "res": None, "neto": None, "neto_b": None,
              "modelo": self.modelo.get("huella"), "politica": self.pol["version"]}
        if usdt_b:
            self.saldo[str(L)] = round(float(self.saldo[str(L)]) - usdt_b, 4)
        self.compras.append(op)
        self._anotar({**base, "compra": True, "q": q, "vivo": d["vivo"], "p": op["p"], "p_prud": op["p_prud"], "G_prud": op["G_prud"],
                      "disp": op["disp"], "usdt_b": usdt_b, "resta_s": op["resta_s"], "x": [round(v, 6) for v in vec["x"]],
                      "p_red": round(vec["p"], 6), "comision": com})
        self._guardar(compras=True)
        self.log(f"papel de {self.W} min ({L} s{', en sombra' if pe['sombra'] else ''}): compra {'SUBE' if pe['lado'] > 0 else 'BAJA'} a {q:g} "
                 f"en el minuto {pe['m']}: vale {100 * dd['p']:.1f} % (prudente {100 * dd['p_prud']:.1f} %), ganancia esperada prudente "
                 f"{100 * dd['G_prud']:+.0f} %, {op['contratos']:g} contratos por 1 USDT")

    # ------------------------------------------------------------ liquidación
    def _ganador_velas(self, t):
        """Ganador según las velas de contado: 1, -1, 0 (cerró justo en la apertura) o None si aún faltan velas."""
        v = self.C.velas_desde(t, self.W)
        if len(v) < self.W or v[0][0] != t or v[self.W - 1][0] != t + self.dur - 60:
            return None
        a, c = v[0][1], v[self.W - 1][4]
        return 1 if c > a else (-1 if c < a else 0)

    def _calibrar(self, v, g):
        """Suma a la calibración de su serie las miradas de una ventana ya resuelta. El empate cuenta como que el perdedor no
        ganó, igual que al entrenar. La desviación se lleva por ventanas, porque las miradas de una misma ventana van juntas."""
        c = self.cal[v.get("serie", "papel")]
        c["ventanas"] += 1
        d = 0.0
        for _mm, p, perdedor, z, p_prud in v.get("miradas", []):
            y = 1 if g == perdedor else 0
            c["miradas"] += 1
            c["esperados"] += p
            c["ocurridos"] += y
            c["pl_modelo"] += _menos_log(p, y)
            c["pl_normal"] += _menos_log(0.5 * math.erfc(abs(z) / math.sqrt(2)), y)
            tr = c["tramos"][N.tramo(p)]
            tr[0] += 1
            tr[1] += p
            tr[2] += p_prud
            tr[3] += y
            d += y - p
        c["dif"] += d
        c["dif2"] += d * d

    def _liquidar(self, ahora):
        cambio = compras = False
        for t in sorted(self.ventanas):
            v = self.ventanas[t]
            oficial = v.get("serie", "papel") == "papel"
            if ahora < t + self.dur + (60 if oficial else 3) or ahora - self.t_resultado.get(t, 0) < (30 if oficial else 10):
                continue
            self.t_resultado[t] = ahora
            try:
                g = self.C.resultado(v["topic"]) if oficial else self._ganador_velas(t)
            except Exception as ex:
                if ahora <= t + SIN_GANADOR_S:
                    continue
                self.log(f"papel de {self.W} min: sin resultado de la ventana {t} ({type(ex).__name__})")
                g = None
            if g is None and ahora <= t + SIN_GANADOR_S:
                continue
            self._anotar({"tipo": "resultado", "serie": v.get("serie", "papel"), "t": t, "ganador": g,
                          "fuente": "oficial" if oficial else "velas", "hora": round(ahora, 2)})
            if g is not None:
                self._calibrar(v, g)
            for o in self.compras:
                if o["t"] != t or o["res"] is not None:
                    continue
                L, pago = str(o["llenado"]), (1 - o["comision"]) / o["precio"]
                if g is None:   # sin ganador en dos horas: no cuenta y el libro B recupera lo puesto
                    o["res"], o["neto"], o["neto_b"] = -1, 0.0, 0.0
                    self.saldo[L] = round(float(self.saldo[L]) + o["usdt_b"], 4)
                elif g == 0:    # empate: Binance paga la mitad a cada lado
                    o["res"], o["neto"], o["neto_b"] = 2, round(pago / 2 - 1, 4), round(o["usdt_b"] * (pago / 2 - 1), 4)
                    self.saldo[L] = round(float(self.saldo[L]) + o["usdt_b"] * pago / 2, 4)
                elif g == o["lado"]:
                    o["res"], o["neto"], o["neto_b"] = 1, round(pago - 1, 4), round(o["usdt_b"] * (pago - 1), 4)
                    self.saldo[L] = round(float(self.saldo[L]) + o["usdt_b"] * pago, 4)
                else:
                    o["res"], o["neto"], o["neto_b"] = 0, -1.0, -o["usdt_b"]
                compras = True
            del self.ventanas[t]
            self.t_resultado.pop(t, None)
            cambio = True
        if cambio:
            self._guardar(compras=compras)

    # ------------------------------------------------------------ resumen
    @staticmethod
    def cuenta(ops):
        x = {"n": 0, "k": 0, "empates": 0, "esperados": 0.0, "esperados_prud": 0.0, "neto": 0.0, "usdt_b": 0.0, "neto_b": 0.0, "abiertas": 0}
        for o in ops:
            if o["res"] is None:
                x["abiertas"] += 1
            if o["res"] not in (0, 1, 2):
                continue
            x["neto"] += o["neto"]
            x["usdt_b"] += o["usdt_b"]
            x["neto_b"] += o["neto_b"]
            if o["res"] == 2:
                x["empates"] += 1
                continue
            x["n"] += 1
            x["k"] += o["res"]
            x["esperados"] += o["p"]
            x["esperados_prud"] += o["p_prud"]
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()}

    def calibracion(self, serie):
        """Lo que dijo el modelo frente a lo que pasó, en las miradas ya resueltas de una serie."""
        c = self.cal[serie]
        n = c["miradas"]
        out = {"ventanas": c["ventanas"], "miradas": n, "esperados": round(c["esperados"], 2), "ocurridos": c["ocurridos"]}
        if n:
            out["pl_modelo"], out["pl_normal"] = round(c["pl_modelo"] / n, 5), round(c["pl_normal"] / n, 5)
            out["sigmas"] = round(c["dif"] / math.sqrt(c["dif2"]), 2) if c["dif2"] > 0 else 0.0
        return out

    def resumen(self):
        libros, celdas = {}, {}
        for L in LLENADOS:
            ops = [o for o in self.compras if o["llenado"] == L and not o.get("sombra")]
            libros[str(L)] = {**self.cuenta(ops), "saldo_b": self.saldo[str(L)]}
        for o in self.compras:
            if o["llenado"] == LLENADOS[0]:
                celdas.setdefault(("sombra · " if o.get("sombra") else "") + str(o["celda"]), []).append(o)
        u = self.ultimo
        ultimo = None
        if u:
            ultimo = {"t": u["t"], "m": u["m"], "serie": u["serie"], "plazo": u["plazo"], "z": u["z"], "p": u["p"], "decide": u["decide"],
                      "motivo": u["motivo"],
                      "lados": {k: {c: v.get(c) for c in ("papel", "p", "p_prud", "q", "G_prud", "limite")} for k, v in u["lados"].items()}}
        return {"W": self.W, "modelo": self.modelo.get("huella") if self.modelo else None,
                "politica": {k: self.pol[k] for k in ("version", "margen", "kelly", "tope_saldo", "celdas_apagadas")},
                "libros": libros, "celdas": {c: self.cuenta(ops) for c, ops in celdas.items()}, "cont": dict(self.cont),
                "calibracion": {s: self.calibracion(s) for s in SERIES}, "abiertas": len(self.ventanas), "ultimo": ultimo,
                "ultimas": [{k: o.get(k) for k in ("t", "m", "plazo", "lado", "papel", "llenado", "precio", "p", "G_prud", "res", "neto", "usdt_b", "sombra")}
                            for o in self.compras[-8:]]}
