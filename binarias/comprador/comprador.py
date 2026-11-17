"""Comprador por ganancia esperada, en papel (12/11/2026, pedido suyo). No manda órdenes: solo lee, calcula y anota.

Aplica REGLAS-ANTES-DE-MEDIR.md (R3 con la enmienda 1) sobre el mercado «BTC Up or Down» de 15 min:
- Mirada: en los 5 s siguientes al cierre de cada minuto 1 a 14 lee el libro de los dos lados y el precio de contado del
  instante, calcula el vector de ganancia (ganancia.py) y lo graba entero en datos\\vector-AAAAMMDD.jsonl, compre o no.
- Candidato: el lado cuya ganancia esperada prudente llega al margen de la política.
- Llenado honesto: 5 s después (libro principal) y 15 s después (libro de su doble toque) vuelve a leer libro y precio y
  recalcula. Solo anota la compra si en ese instante sigue cumpliendo, y al precio de ese instante.
- Una compra por ventana y por libro. Libro A: 1 USDT fijo. Libro B: fracción de Kelly con tope, sobre un saldo de papel.
- Liquida con el ganador oficial. Cada ventana mirada deja también su fila de resultado, para medir la red contra el mercado.
- Celda apagada por la política: la compra se anota «en sombra» y no cuenta.

Quién lo corre: la Mesa cuando está abierta o correr.py cuando no; un candado (puerto 8799) deja uno solo. Recibe el módulo de
conexión de quien lo llama y de él solo usa lecturas (leer_libros, velas_contado, resultado, ahora). Aquí no existe la compra real."""
import datetime as dt
import json
import os
import socket
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.append(AQUI)
import ganancia as G  # noqa: E402

DATOS = os.path.join(AQUI, "datos")
MIRADA_S = 5                 # enmienda 1: la mirada vale si se logra en los 5 s siguientes al cierre del minuto
LLENADOS = (5, 15)           # segundos entre decidir y comprar: el automático y su doble toque
NIVELES = 5                  # niveles del libro que se graban por lado
PUERTO_CANDADO = 8799
COL = dt.timezone(dt.timedelta(hours=-5))


def tomar_candado(puerto=PUERTO_CANDADO):
    """Un solo comprador por equipo: quien reserva el puerto lo corre. Devuelve el enchufe (hay que conservarlo) o None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", puerto))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def dia(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%Y%m%d")


class Comprador:
    def __init__(self, C, log=print, datos=DATOS, candado=True):
        self.C, self.log, self.datos = C, log, datos
        self.candado = tomar_candado() if candado else True
        self.activo = bool(self.candado)
        self.modelo = G.cargar()
        self.pol, self.pol_mtime = G.politica_base(), None
        self.compras, self.saldo = [], {str(L): G.SALDO_PAPEL for L in LLENADOS}
        self.ventanas, self.hechas, self.pend = {}, {}, None
        self.t_resultado, self.t_estado, self.t_candado, self.ultimo = {}, 0.0, 0.0, None
        self.cont = {"miradas": 0, "perdidas": 0, "candidatos": 0, "escapes": 0}
        os.makedirs(datos, exist_ok=True)
        self._cargar()

    def _cargar(self):
        try:
            with open(os.path.join(self.datos, "compras.json"), encoding="utf-8") as f:
                d = json.load(f)
            self.compras, self.ventanas = d.get("compras", []), {int(k): v for k, v in d.get("ventanas", {}).items()}
            self.saldo.update(d.get("saldo", {}))
            self.cont.update(d.get("cont", {}))
        except (OSError, ValueError):
            pass

    # ------------------------------------------------------------ archivos
    def _guardar(self):
        ruta = os.path.join(self.datos, "compras.json")
        with open(ruta + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"compras": self.compras, "saldo": self.saldo, "ventanas": self.ventanas, "cont": self.cont}, f, ensure_ascii=False)
        os.replace(ruta + ".tmp", ruta)

    def _fila(self, fila):
        with open(os.path.join(self.datos, f"vector-{dia(fila['t'])}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def _politica(self):
        ruta = os.path.join(self.datos, "politica.json")
        try:
            mt = os.path.getmtime(ruta)
        except OSError:
            mt = None
        if mt == self.pol_mtime:
            return
        self.pol_mtime = mt
        self.pol, recortes = G.cargar_politica(ruta)
        self.log(f"comprador: política v{self.pol['version']} (margen {self.pol['margen']:g}, Kelly {self.pol['kelly']:g}, "
                 f"{len(self.pol['celdas_apagadas'])} celdas apagadas)")
        for r in recortes:
            self.log(f"comprador: política recortada: {r}")

    # ------------------------------------------------------------ bucle
    def paso(self, ahora, m):
        """ahora: hora de Binance. m: el mercado de 15 min en curso, como lo arma la Mesa (t, topic, strike, abierto...)."""
        if not self.activo and self.candado is None and ahora - self.t_candado >= 30:
            # otro proceso (la Mesa o correr.py) lleva el papel: se vuelve a pedir el candado cada 30 s por si ya salió
            self.t_candado = ahora
            self.candado = tomar_candado()
            self.activo = bool(self.candado)
            if self.activo:
                self._cargar()
                self.log("comprador: el otro proceso salió; este toma el papel")
        if not self.activo or self.modelo is None:
            return
        self._politica()
        if m and m.get("abierto") and m.get("strike") and 0 < m["t"] + 900 - ahora <= 900:
            cierre = int(ahora // 60) * 60
            mm = (cierre - m["t"]) // 60
            hechas = self.hechas.setdefault(m["t"], set())
            if 1 <= mm <= 14 and mm not in hechas:
                if ahora - cierre <= MIRADA_S:
                    self._mirada(m, mm, cierre, hechas)
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
        if ahora - self.t_estado >= 30:
            self.t_estado = ahora
            self._guardar_estado()

    def _perdida(self, m, mm, motivo):
        self.cont["perdidas"] += 1
        self._fila({"tipo": "mirada perdida", "t": m["t"], "m": mm, "motivo": motivo})

    def _leer(self, m, mm):
        """Libro de los dos lados y velas de contado en este instante. None si Binance aún no entrega la vela cerrada del
        minuto mm; "hueco" si faltan velas; si no, lo necesario para el vector."""
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
                "v": [v[5] for v in cerr], "vivo": float((viva or cerr[-1])[4]), "resta": m["t"] + 900 - ahora}

    def _vector(self, m, mm, d):
        com = (m.get("comision_bps") or 200) / 10000
        return G.vector(self.modelo, d["c"], d["h"], d["l"], d["v"], d["s"], mm, float(m["strike"]), d["T"][-1], m.get("ask") or {},
                        com, self.pol["margen"], vivo=d["vivo"], resta_s=d["resta"])

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
            return  # la vela cerrada aún no llega: se reintenta en la próxima vuelta mientras duren los 5 s
        hechas.add(mm)
        if d == "hueco":
            return self._perdida(m, mm, "faltan velas")
        if d["ahora"] - cierre > MIRADA_S:
            return self._perdida(m, mm, "la lectura tardó más de 5 s")
        vec = self._vector(m, mm, d)
        if vec is None:
            return self._perdida(m, mm, "sin rasgos")
        lado, motivo, celda, sombra = G.decidir(vec, self.pol, d["resta"])
        fila = {"tipo": "mirada", "t": m["t"], "topic": m.get("topic"), "m": mm, "hora": round(d["ahora"], 2),
                "demora_s": round(d["ahora"] - cierre, 2), "strike": float(m["strike"]), "cierre": d["c"][-1], "vivo": d["vivo"],
                "resta_s": round(d["resta"], 1), "z": round(vec["z"], 4), "z_cierre": round(vec["z_cierre"], 4), "p": round(vec["p"], 6),
                "p_cierre": round(vec["p_cierre"], 6), "perdedor": vec["perdedor"], "x": [round(v, 6) for v in vec["x"]],
                "lados": {str(k): self._lado(m, k, v) for k, v in vec["lados"].items()}, "decide": lado or 0, "motivo": motivo,
                "celda": celda, "sombra": sombra, "modelo": self.modelo.get("huella"), "politica": self.pol["version"],
                "margen": self.pol["margen"], "comision": (m.get("comision_bps") or 200) / 10000}
        self._fila(fila)
        self.ultimo = fila
        self.cont["miradas"] += 1
        self.ventanas.setdefault(m["t"], {"topic": m.get("topic")})
        if lado:
            self.cont["candidatos"] += 1
            self.pend = {"t": m["t"], "topic": m.get("topic"), "m": mm, "lado": lado, "celda": celda, "sombra": sombra,
                         "hora": d["ahora"], "q0": vec["lados"][lado]["q"], "hechos": set()}

    # ------------------------------------------------------------ llenado honesto
    def _ya_compro(self, t, L, sombra):
        return any(o["t"] == t and o["llenado"] == L and bool(o.get("sombra")) == bool(sombra) for o in self.compras[-60:])

    def _llenar(self, m, L):
        pe = self.pend
        pe["hechos"].add(L)
        if self._ya_compro(pe["t"], L, pe["sombra"]):
            return
        base = {"tipo": "llenado", "t": pe["t"], "m": pe["m"], "lado": pe["lado"], "llenado": L, "celda": pe["celda"], "sombra": pe["sombra"]}
        d = self._leer(m, pe["m"])
        vec = self._vector(m, pe["m"], d) if isinstance(d, dict) else None
        dd = vec["lados"][pe["lado"]] if vec else None
        q = dd.get("q") if dd else None
        if not dd or not q:
            motivo = "sin lectura o sin precio"
        elif not G.PRECIO_MIN - 1e-9 <= q <= G.PRECIO_MAX + 1e-9:
            motivo = "precio fuera de 0,01 a 0,90"
        elif d["resta"] < G.MIN_RESTA_S:
            motivo = "quedan menos de 10 s"
        elif dd["G_prud"] < self.pol["margen"] - 1e-12:
            motivo = "se escapó: " + ("subió el precio" if q > pe["q0"] + 1e-9 else "bajó la probabilidad")
        else:
            motivo = None
        if motivo:
            self.cont["escapes"] += 1
            self._fila({**base, "compra": False, "motivo": motivo, "q": q, "vivo": d["vivo"] if isinstance(d, dict) else None,
                        "G_prud": round(dd["G_prud"], 6) if dd and dd.get("G_prud") is not None else None})
            self._guardar()
            return
        com = (m.get("comision_bps") or 200) / 10000
        disp = sum(s for p, s in ((m.get("asks") or {}).get(pe["lado"]) or []) if p <= q + 1e-9)
        usdt_b = 0.0 if pe["sombra"] else G.importe_b(float(self.saldo[str(L)]), dd, self.pol, disp)
        op = {"t": pe["t"], "topic": pe["topic"], "m": pe["m"], "lado": pe["lado"], "papel": dd["papel"], "celda": pe["celda"],
              "sombra": pe["sombra"], "llenado": L, "precio": q, "precio_decision": pe["q0"], "p": round(dd["p"], 6),
              "p_prud": round(dd["p_prud"], 6), "G": round(dd["G"], 6), "G_prud": round(dd["G_prud"], 6), "z": round(vec["z"], 4),
              "hora": round(d["ahora"], 2), "resta_s": round(d["resta"], 1), "vivo": d["vivo"], "disp": round(disp, 2), "comision": com,
              "contratos": round(G.contratos(q, 1.0, com), 2), "usdt_b": usdt_b, "res": None, "neto": None, "neto_b": None,
              "modelo": self.modelo.get("huella"), "politica": self.pol["version"]}
        if usdt_b:
            self.saldo[str(L)] = round(float(self.saldo[str(L)]) - usdt_b, 4)
        self.compras.append(op)
        self._fila({**base, "compra": True, "q": q, "vivo": d["vivo"], "p": op["p"], "p_prud": op["p_prud"], "G_prud": op["G_prud"],
                    "disp": op["disp"], "usdt_b": usdt_b, "resta_s": op["resta_s"], "x": [round(v, 6) for v in vec["x"]],
                    "p_red": round(vec["p"], 6), "comision": com})
        self._guardar()
        self.log(f"comprador ({L} s{', en sombra' if pe['sombra'] else ''}): compra {'SUBE' if pe['lado'] > 0 else 'BAJA'} a {q:g} en el minuto "
                 f"{pe['m']}: vale {100 * dd['p']:.1f} % (prudente {100 * dd['p_prud']:.1f} %), ganancia esperada prudente "
                 f"{100 * dd['G_prud']:+.0f} %, {op['contratos']:g} contratos por 1 USDT")

    # ------------------------------------------------------------ liquidación
    def _liquidar(self, ahora):
        cambio = False
        for t in sorted(self.ventanas):
            v = self.ventanas[t]
            if ahora < t + 960 or ahora - self.t_resultado.get(t, 0) < 30:
                continue
            self.t_resultado[t] = ahora
            try:
                g = self.C.resultado(v["topic"])
            except Exception as ex:
                self.log(f"comprador: sin resultado de la ventana {t} ({type(ex).__name__})")
                continue
            if g is None and ahora <= t + 7200:
                continue
            self._fila({"tipo": "resultado", "t": t, "ganador": g or 0})
            for o in self.compras:
                if o["t"] != t or o["res"] is not None:
                    continue
                L, pago = str(o["llenado"]), (1 - o["comision"]) / o["precio"]
                if g is None:   # sin ganador en dos horas (o empate): no cuenta y el libro B recupera lo puesto
                    o["res"], o["neto"], o["neto_b"] = -1, 0.0, 0.0
                    self.saldo[L] = round(float(self.saldo[L]) + o["usdt_b"], 4)
                elif g == o["lado"]:
                    o["res"], o["neto"], o["neto_b"] = 1, round(pago - 1, 4), round(o["usdt_b"] * (pago - 1), 4)
                    self.saldo[L] = round(float(self.saldo[L]) + o["usdt_b"] * pago, 4)
                else:
                    o["res"], o["neto"], o["neto_b"] = 0, -1.0, -o["usdt_b"]
            del self.ventanas[t]
            self.t_resultado.pop(t, None)
            cambio = True
        if cambio:
            self._guardar()

    # ------------------------------------------------------------ resumen
    @staticmethod
    def cuenta(ops):
        x = {"n": 0, "k": 0, "esperados": 0.0, "esperados_prud": 0.0, "neto": 0.0, "usdt_b": 0.0, "neto_b": 0.0, "abiertas": 0}
        for o in ops:
            if o["res"] is None:
                x["abiertas"] += 1
            if o["res"] not in (0, 1):
                continue
            x["n"] += 1
            x["k"] += o["res"]
            x["esperados"] += o["p"]
            x["esperados_prud"] += o["p_prud"]
            x["neto"] += o["neto"]
            x["usdt_b"] += o["usdt_b"]
            x["neto_b"] += o["neto_b"]
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()}

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
            ultimo = {"t": u["t"], "m": u["m"], "z": u["z"], "decide": u["decide"], "motivo": u["motivo"],
                      "lados": {k: {c: v.get(c) for c in ("papel", "p", "p_prud", "q", "G_prud", "limite")} for k, v in u["lados"].items()}}
        return {"hora": int(self.C.ahora()), "activo": self.activo, "modelo": self.modelo.get("huella") if self.modelo else None,
                "politica": {k: self.pol[k] for k in ("version", "margen", "kelly", "tope_saldo", "celdas_apagadas")},
                "libros": libros, "celdas": {c: self.cuenta(ops) for c, ops in celdas.items()}, "cont": self.cont, "ultimo": ultimo,
                "ultimas": [{k: o.get(k) for k in ("t", "m", "lado", "papel", "llenado", "precio", "p", "G_prud", "res", "neto", "usdt_b", "sombra")}
                            for o in self.compras[-8:]]}

    def corto(self):
        """Lo mínimo para la placa y para el Telegram de la caja."""
        r = self.resumen()
        return {"modelo": r["modelo"], "politica": r["politica"]["version"], "margen": r["politica"]["margen"],
                "libros": {L: {k: x[k] for k in ("n", "k", "esperados", "neto", "neto_b", "saldo_b", "abiertas")} for L, x in r["libros"].items()},
                "cont": r["cont"], "ultimo": r["ultimo"]}

    def _guardar_estado(self):
        ruta = os.path.join(self.datos, "comprador.json")
        try:
            with open(ruta + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.resumen(), f, ensure_ascii=False)
            os.replace(ruta + ".tmp", ruta)
        except OSError:
            pass
