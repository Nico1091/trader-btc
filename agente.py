"""El agente de trading seguido: opera solo, ciclo tras ciclo, en papel y en tiempo real.

Uso:    python -u -I agente.py          (en una consola, para verlo trabajar)
        ARRANCAR AGENTE.cmd             (oculto, sin ventana)
Parar:  crear el archivo PARAR en esta carpeta (o PARAR AGENTE.cmd): cierra lo abierto a
        precio de mercado, guarda el estado y sale.
Pausa:  crear PAUSA: sigue leyendo el mercado y cerrando lo abierto, no abre ciclos nuevos.
Reanudar un libro detenido por una tanda mala: crear REANUDAR.

Cada segundo, al cerrar la vela de 1 s de BTCUSDT y la de BTC/FDUSD:
1. Rasgos con el mismo código del banco de pruebas (rapido.rasgos_segundo).
2. Barrera, probabilidad de movimiento (H) y de dirección (D) con los modelos del banco.
3. En cada libro en papel: salida con rapido.paso_salida; entrada si la ganancia esperada
   neta de comisiones supera el margen elegido en validación, con los frenos 3/15/20 %, las
   tandas de ciclos y los frenos de contexto (datos macro de EE. UU. y agenda de Trump).
Dinero real: este archivo no tiene ningún camino de órdenes. Todo es papel.
"""
import array
import collections
import csv
import datetime as dt
import json
import math
import os
import queue
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout is None or sys.stderr is None:      # pythonw (sin consola): salida y errores al registro
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diario"), exist_ok=True)
    _registro = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diario", "agente.log"), "a",
                     encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _registro
    sys.stderr = sys.stderr or _registro
else:
    sys.stdout.reconfigure(encoding="utf-8")

import contexto as cx  # noqa: E402
import datos  # noqa: E402
import panel  # noqa: E402
import probabilidad as pb  # noqa: E402
import rapido as rp  # noqa: E402
import vivo  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
DIARIO = os.path.join(CARPETA, "diario")
RUTA_MODELOS = os.path.join(CARPETA, "modelos", "trading-seguido.json")
RUTA_ESTADO = os.path.join(CARPETA, "estado.json")
RUTA_PANEL = os.path.join(CARPETA, "panel.html")
SEG, MIN, HORA = 1000, 60_000, 3_600_000
CAPITAL = 9.7


def sin_freno_de_windows():
    """Windows 11 frena los procesos sin ventana (EcoQoS) y el agente se atrasaba frente al
    mercado. Se le pide la velocidad normal (SetProcessInformation, ProcessPowerThrottling)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class Estado(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.SetProcessInformation.restype = wintypes.BOOL
        e = Estado(1, 0x1, 0x0)          # versión 1; controla la velocidad de ejecución; sin freno
        return bool(k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(e), ctypes.sizeof(e)))
    except Exception:
        return False


def ahora_bogota():
    return dt.datetime.now(rp.BOGOTA)


def bogota(t_ms):
    return dt.datetime.fromtimestamp(t_ms / 1000, rp.BOGOTA)


class Diario:
    """Todo queda en local (regla de privacidad): eventos, ciclos, velas y minutos."""

    def __init__(self):
        os.makedirs(DIARIO, exist_ok=True)
        self._abiertos = {}

    def _archivo(self, nombre, cabecera=None):
        ruta = os.path.join(DIARIO, nombre)
        f = self._abiertos.get(ruta)
        if f is None:
            nuevo = not os.path.exists(ruta)
            f = open(ruta, "a", encoding="utf-8", newline="")
            if nuevo and cabecera:
                f.write(cabecera + "\n")
            self._abiertos[ruta] = f
            if len(self._abiertos) > 12:                     # cierra los de días anteriores
                for r in list(self._abiertos)[:-8]:
                    self._abiertos.pop(r).close()
        return f

    def evento(self, t_ms, tipo, **datos_):
        fila = {"t": t_ms, "hora": bogota(t_ms).isoformat(timespec="seconds"), "tipo": tipo}
        fila.update(datos_)
        self._archivo(f"eventos-{bogota(t_ms):%Y-%m-%d}.jsonl").write(json.dumps(fila, ensure_ascii=False) + "\n")

    def vela(self, simbolo, fila):
        f = self._archivo(f"velas-1s-{simbolo}-{bogota(fila[0]):%Y-%m-%d}.csv", "t,o,h,l,c,v,tb,n")
        f.write(",".join(repr(x) if isinstance(x, float) else str(x) for x in fila) + "\n")

    def ciclo(self, clave, fila):
        campos = ("t_entrada", "t_salida", "lado", "entrada", "salida", "motivo", "cantidad", "ganancia_usdt",
                  "ret_pct", "capital", "barrera", "prob_mov", "prob_sube", "esperanza", "en_vivo")
        f = self._archivo(f"ciclos-{clave}.csv", ",".join(campos))
        f.write(",".join(str(fila.get(c, "")) for c in campos) + "\n")

    def minuto(self, t_ms, fila):
        campos = list(fila)
        f = self._archivo(f"minutos-{bogota(t_ms):%Y-%m-%d}.csv", ",".join(campos))
        f.write(",".join(str(fila[c]) for c in campos) + "\n")

    def vaciar(self):
        for f in self._abiertos.values():
            f.flush()


class ModeloVivo:
    """Los modelos que dejó el banco de pruebas, listos para cada segundo."""

    def __init__(self, ruta):
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        self.generado = d["generado"]
        self.instrumentos = d["instrumentos"]
        self.testigo = d.get("testigo")
        self.modelos = {}
        for m in d["modelos"].values():
            cfg = tuple(m["config"])
            self.modelos[cfg] = (pb.Logistica.desde_dict(m["movimiento"]), pb.Logistica.desde_dict(m["direccion"]))

    def evaluar(self, x, cfg):
        segundos, k, minima = cfg
        b = rp.barrera_de(x[rp.I_VOL3600], segundos, k, minima)
        xz = x + [math.log(b * 100)]
        H, D = self.modelos[cfg]
        return b, H.prob(xz), D.prob(xz)


class LibroVivo:
    """Un libro en papel con los mismos pasos que rapido.simular_libro, segundo a segundo."""

    def __init__(self, clave, inst, gestion, cfg, margen, valido=True, siempre=False, nombre=None):
        self.clave, self.inst, self.cfg, self.margen = clave, inst, tuple(cfg), margen
        self.valido = valido                    # False: en validación no mostró ventaja
        self.siempre = siempre                  # testigo: entra en cada segundo libre, sin filtro
        self.nombre = nombre or inst.nombre
        self.libro = rp.Libro(inst, gestion)
        self.estado = "libre"                   # libre | apertura | orden | posicion
        self.pend = None
        self.pos = None
        self.bloqueos = collections.Counter()
        self.ultima_decision = None

    # ---------- decisión ----------
    def decidir(self, ev):
        """ev = (barrera, H, D) del segundo. Devuelve (lado, barrera, esperanza) o None."""
        if ev is None:
            return None
        b, h, d = ev
        cg, cp = self.inst.costos()
        el, ec = rp.esperanza(b, h, d, cg, cp)
        if not self.inst.corto:
            ec = -1.0
        self.ultima_decision = {"barrera": b, "prob_mov": h, "prob_sube": d, "esperanza_largo": el,
                                "esperanza_corto": ec if self.inst.corto else None}
        if self.siempre:
            return ("largo", b, el) if el >= ec else ("corto", b, ec)
        if el > self.margen and el >= ec:
            return "largo", b, el
        if ec > self.margen:
            return "corto", b, ec
        return None

    # ---------- un segundo ----------
    def segundo(self, t, o, h, l, c, ev, permitir, motivo_bloqueo, diario, en_vivo, real=None):
        self._real = real                         # auditor: mejor precio real del momento
        inst, lib = self.inst, self.libro
        if self.estado == "apertura":
            p, self.pend, self.estado = self.pend, None, "libre"
            entrada = o * (1 + inst.desliz) if p["lado"] == "largo" else o * (1 - inst.desliz)
            self._abrir(t, entrada, p, False, diario)
        elif self.estado == "orden":
            p = self.pend
            lleno = (l < p["limite"]) if p["lado"] == "largo" else (h > p["limite"])
            if lleno:
                self.pend, self.estado = None, "libre"
                self._abrir(t, p["limite"], p, True, diario)
            elif t >= p["expira"]:
                self.pend, self.estado = None, "libre"
                lib.intentos_sin_llenar += 1
                diario.evento(t, "orden_sin_llenar", libro=self.clave, lado=p["lado"], limite=p["limite"])
                return                                    # como el banco: se vuelve a decidir al segundo siguiente
            else:
                return
        if self.estado == "posicion":
            res = rp.paso_salida(self.pos, t, o, h, l, c)
            if res:
                self._cerrar(t, res[0], res[1], diario, en_vivo)
            return
        # libre
        if lib.detenido or t < lib.pausa_hasta:
            return
        if not permitir:
            if motivo_bloqueo:
                self.bloqueos[motivo_bloqueo.split(":")[0]] += 1
            return
        dec = self.decidir(ev)
        if dec is None:
            return
        lado, b, esperanza = dec
        if (lado == "largo" and not inst.largo) or (lado == "corto" and not inst.corto):
            return
        volver = lib.frenos(t + SEG, c)
        if volver is not None:
            lib.pausa_hasta = volver
            diario.evento(t, "freno", libro=self.clave, hasta=bogota(volver).isoformat(timespec="minutes"),
                          omitidas=dict(lib.omitidas))
            return
        p = {"lado": lado, "b": b, "t_decision": t, "esperanza": esperanza, "dec": dict(self.ultima_decision)}
        if inst.entrada_creador:
            p["limite"] = (c - inst.tic) if lado == "largo" else (c + inst.tic)
            p["expira"] = t + inst.espera_creador * SEG
            self.estado, self.pend = "orden", p
        else:
            self.estado, self.pend = "apertura", p
        diario.evento(t, "decision", libro=self.clave, lado=lado, barrera=round(b, 6),
                      prob_mov=round(self.ultima_decision["prob_mov"], 4),
                      prob_sube=round(self.ultima_decision["prob_sube"], 4), esperanza_pb=round(esperanza * 1e4, 2),
                      limite=p.get("limite"))

    def _abrir(self, t, entrada, p, creador, diario):
        lib = self.libro
        q = lib.tamano(entrada, p["b"])
        if q <= 0:
            lib._omitir("minimo_o_riesgo")
            return
        b = p["b"]
        largo = p["lado"] == "largo"
        fin = t + (self.cfg[0] - 1) * SEG
        if largo:
            self.pos = rp.Posicion(True, entrada, entrada * (1 + b), entrada * (1 - b), fin, self.inst.desliz)
        else:
            self.pos = rp.Posicion(False, entrada, entrada * (1 - b), entrada * (1 + b), fin, self.inst.desliz)
        self.pos_meta = {"q": q, "t_in": t, "creador": creador, "p": p}
        self.estado = "posicion"
        auditor = {}
        r = getattr(self, "_real", None) or {}
        if "venta" in r:                          # contado: lo que costaba de verdad en el libro
            referencia = r["venta"] if largo else r["compra"]
            auditor = {"real_compra": r["compra"], "real_venta": r["venta"],
                       "papel_vs_real_pb": round((entrada / referencia - 1) * 1e4 * (1 if largo else -1), 2)}
        elif "marca" in r:                        # futuros: precio de marca del segundo
            auditor = {"real_marca": r["marca"], "papel_vs_marca_pb": round((entrada / r["marca"] - 1) * 1e4, 2)}
        diario.evento(t, "entrada", libro=self.clave, lado=p["lado"], precio=entrada, cantidad=q,
                      objetivo=self.pos.tp, stop=self.pos.sl, creador=creador, **auditor)

    def _cerrar(self, t, motivo, precio, diario, en_vivo):
        m, lib = self.pos_meta, self.libro
        largo = self.pos.largo
        ganancia = lib.cerrar(largo, m["q"], self.pos.entrada, precio, motivo, m["t_in"], t, m["creador"],
                              {"barrera": m["p"]["b"], "prob_mov": m["p"]["dec"]["prob_mov"],
                               "prob_sube": m["p"]["dec"]["prob_sube"], "esperanza": m["p"]["esperanza"],
                               "en_vivo": en_vivo})
        lib.pausa_hasta = lib.tras_ciclo(t, precio)
        diario.ciclo(self.clave, lib.ciclos[-1])
        diario.evento(t, "salida", libro=self.clave, motivo=motivo, precio=precio, ganancia_usdt=round(ganancia, 6),
                      capital=round(lib.valor(precio), 6), ciclos=len(lib.ciclos))
        if lib.tandas and lib.tandas[-1]["tanda"] * lib.gestion.tanda == len(lib.ciclos):
            diario.evento(t, "tanda", libro=self.clave, **lib.tandas[-1], detenido=lib.detenido)
        self.pos, self.pos_meta, self.estado = None, None, "libre"

    def cerrar_ya(self, t, precio, motivo, diario):
        """Cierre forzado (parada o reinicio) a precio de mercado, como tomador."""
        if self.estado == "posicion":
            p = self.pos
            salida = precio * (1 - p.desliz) if p.largo else precio * (1 + p.desliz)
            self._cerrar(t, motivo, salida, diario, True)
        self.pend, self.estado = None, "libre"

    # ---------- persistencia ----------
    def a_dict(self):
        lib = self.libro
        return {"nombre": self.nombre, "valido": self.valido, "siempre": self.siempre,
                "config": list(self.cfg), "margen": self.margen,
                "efectivo": lib.efectivo, "polvo": lib.polvo, "ciclos": len(lib.ciclos), "tandas": lib.tandas,
                "detenido": lib.detenido, "inicio_tanda": lib.inicio_tanda, "omitidas": lib.omitidas,
                "sin_llenar": lib.intentos_sin_llenar, "bloqueos": dict(self.bloqueos),
                "ultimos": lib.ciclos[-25:],
                "posicion": None if self.estado != "posicion" else {
                    "largo": self.pos.largo, "entrada": self.pos.entrada, "tp": self.pos.tp, "sl": self.pos.sl,
                    "fin": self.pos.fin, "t_in": self.pos_meta["t_in"], "q": self.pos_meta["q"]}}

    def restaurar(self, d):
        lib = self.libro
        lib.efectivo, lib.polvo = d["efectivo"], d["polvo"]
        lib.tandas, lib.detenido = d.get("tandas", []), d.get("detenido", "")
        lib.inicio_tanda = d.get("inicio_tanda", lib.efectivo)
        lib.omitidas = d.get("omitidas", {})
        lib.intentos_sin_llenar = d.get("sin_llenar", 0)
        self.bloqueos.update(d.get("bloqueos", {}))
        previos = d.get("ultimos", [])
        relleno = max(d.get("ciclos", 0) - len(previos), 0)
        lib.ciclos = [{"ganancia_usdt": 0.0, "relleno": True}] * relleno + previos   # el conteo de tandas sigue


class Agente:
    def __init__(self, reproducir=None):
        self.diario = Diario()
        self.modelo = ModeloVivo(RUTA_MODELOS)
        self.mercado = vivo.Mercado()
        self.externo = cx.Contexto()
        self.serie = vivo.SerieViva(rasgos=True)
        self.serie_fd = vivo.SerieViva(rasgos=False, guardar=7200)
        gestion = rp.Gestion(capital=CAPITAL, tanda=rp.tanda_por_capital(CAPITAL))
        self.libros = {}
        for clave, inst in rp.INSTRUMENTOS.items():
            e = self.modelo.instrumentos[clave]
            self.libros[clave] = LibroVivo(clave, inst, gestion, e["config"], e["margen"], e.get("valido", True))
        if self.modelo.testigo:
            t = self.modelo.testigo
            self.libros["testigo"] = LibroVivo("testigo", rp.INSTRUMENTOS[t["instrumento"]], gestion, t["config"],
                                               0.0, True, True, "Seguido sin filtro (testigo, contado)")
        self.ctx = None
        self.v1m = self.v1h = None
        self.met = datos.Metricas()
        self.fin = (array.array("q"), array.array("d"))
        self.pendientes = collections.defaultdict(dict)
        self.ultimo_minuto = None
        self.tareas = {}
        self.inicio = time.time()
        self.estadisticas = collections.Counter()
        self.ultimo_ev = {}
        self.ultimo_t = None
        self.ultimo_panel = 0.0
        self.reproducir = reproducir
        self.sincrono = bool(reproducir)          # en la repetición, las métricas se piden en el momento
        self._parar_fondo = threading.Event()
        self.sin_freno = None
        if not reproducir:
            self._restaurar()

    # ---------- estado guardado ----------
    def _restaurar(self):
        if not os.path.exists(RUTA_ESTADO):
            return
        try:
            with open(RUTA_ESTADO, encoding="utf-8") as f:
                d = json.load(f)
            for clave, dl in d.get("libros", {}).items():
                if clave in self.libros:
                    self.libros[clave].restaurar(dl)
                    self.libros[clave]._posicion_guardada = dl.get("posicion")
            self.estadisticas.update(d.get("estadisticas", {}))
        except (OSError, ValueError, KeyError) as e:
            print("No se pudo restaurar el estado:", e)

    def guardar_estado(self):
        t = self.ultimo_t or 0
        precio = self.serie.c[-1] if self.serie.largo else None
        d = {"actualizado": ahora_bogota().isoformat(timespec="seconds"),
             "hora_mercado": bogota(t).isoformat(timespec="seconds") if t else None,
             "modo": "PAPEL", "pausa": os.path.exists(os.path.join(CARPETA, "PAUSA")),
             "precio": precio, "modelos_generados": self.modelo.generado,
             "libros": {k: lv.a_dict() for k, lv in self.libros.items()},
             "decision": {k: lv.ultima_decision for k, lv in self.libros.items()},
             "salud": dict(self.mercado.salud, segundos_procesados=self.estadisticas["segundos"],
                           segundos_rellenados=self.estadisticas["rellenados"],
                           encendido_desde=dt.datetime.fromtimestamp(self.inicio, rp.BOGOTA).isoformat(timespec="seconds")),
             "estadisticas": dict(self.estadisticas),
             "contexto": self.externo.resumen(),
             "proximo_freno": self.externo.proximo(t) if t else None,
             "futuros": dict(self.mercado.marca),
             "liquidaciones_5min_btc": self.mercado.liquidado(t - 5 * MIN) if t else None,
             "libro_contado": dict(self.mercado.libro)}
        temporal = RUTA_ESTADO + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1, default=str)
        os.replace(temporal, RUTA_ESTADO)
        try:
            panel.escribir(RUTA_PANEL, d, rp.INSTRUMENTOS, CAPITAL)
        except Exception as e:
            self.diario.evento(t, "panel_error", detalle=str(e)[:200])
        self.diario.vaciar()

    # ---------- contexto de minutos, horas y futuros ----------
    def _velas_de(self, filas):
        v = datos.Velas()
        for f in filas:
            v.t.append(f[0])
            v.o.append(f[1])
            v.h.append(f[2])
            v.l.append(f[3])
            v.c.append(f[4])
            v.v.append(f[5])
            v.tb.append(f[6])
            v.n.append(f[7])
        return v

    def _cargar_contexto(self, ahora_ms):
        m = ahora_ms // MIN * MIN
        filas_1m = self.mercado.klines_rango("BTCUSDT", "1m", m - 6 * 1440 * MIN - 30 * MIN, m, MIN)
        self.v1m = self._velas_de(filas_1m)
        h = ahora_ms // HORA * HORA
        filas_1h = [f for f in self.mercado.klines("BTCUSDT", "1h", h - 1000 * HORA, 1000) if f[0] + HORA <= h]
        self.v1h = self._velas_de(filas_1h)
        self._metricas()
        self._financiacion()
        self._rehacer_ctx()

    def _metricas(self):
        try:
            for t, oi in self.mercado.metricas_oi(500 if not len(self.met) else 30):
                if not len(self.met) or t > self.met.t[-1]:
                    self.met.t.append(t)
                    self.met.oi.append(oi)
            if len(self.met) and self.ultimo_t:
                # retraso de publicación: el banco supone que el dato está a más tardar 1 min después
                self.estadisticas["metricas_retraso_max_s"] = max(
                    self.estadisticas["metricas_retraso_max_s"], (self.ultimo_t + SEG - self.met.t[-1]) // SEG - 300)
        except Exception as e:
            self.diario.evento(self.ultimo_t or 0, "error_metricas", detalle=str(e)[:160])

    def _financiacion(self):
        try:
            for t, r in self.mercado.financiacion(100):
                if not len(self.fin[0]) or t > self.fin[0][-1] + 60_000:
                    self.fin[0].append(t)
                    self.fin[1].append(r)
        except Exception as e:
            self.diario.evento(self.ultimo_t or 0, "error_financiacion", detalle=str(e)[:160])

    def _rehacer_ctx(self):
        self.ctx = rp.Contexto(self.v1m, self.met, self.fin, self.v1h)

    def _nuevo_minuto(self, m):
        """Al empezar el minuto m: la vela de 1 min que acaba de cerrar sale de las 60 velas de 1 s
        (igual a la de Binance), y se rehace el contexto."""
        s = self.serie
        i1 = s.indice(m)
        i0 = s.indice(m - MIN)
        if i1 - i0 == 60 and (not len(self.v1m.t) or self.v1m.t[-1] == m - 2 * MIN):
            # Como Binance: solo cuentan los segundos con operaciones (un segundo quieto repite
            # el cierre anterior y estiraría el máximo o el mínimo del minuto).
            con = [k for k in range(i0, i1) if s.n[k] > 0]
            ultimo_c = self.v1m.c[-1] if len(self.v1m.t) else s.c[i0]
            self.v1m.t.append(m - MIN)
            self.v1m.o.append(s.o[con[0]] if con else ultimo_c)
            self.v1m.h.append(max(s.h[k] for k in con) if con else ultimo_c)
            self.v1m.l.append(min(s.l[k] for k in con) if con else ultimo_c)
            self.v1m.c.append(s.c[con[-1]] if con else ultimo_c)
            self.v1m.v.append(sum(s.v[i0:i1]))
            self.v1m.tb.append(sum(s.tb[i0:i1]))
            self.v1m.n.append(sum(s.n[i0:i1]))
        else:                                     # hueco: se pide a Binance
            desde = (self.v1m.t[-1] + MIN) if len(self.v1m.t) else m - 6 * 1440 * MIN
            for f in self.mercado.klines_rango("BTCUSDT", "1m", desde, m, MIN):
                if not len(self.v1m.t) or f[0] > self.v1m.t[-1]:
                    for campo, valor in zip(("t", "o", "h", "l", "c", "v", "tb", "n"), f):
                        getattr(self.v1m, campo).append(valor)
            self.estadisticas["minutos_pedidos"] += 1
        if len(self.v1m.t) > 6 * 1440 + 120:
            self.v1m = datos.recortar(self.v1m, self.v1m.t[-(6 * 1440 + 60)], m + MIN)
        if self.sincrono:                         # repetición: igual que el banco, en el instante
            if m % HORA == 0:
                self._horas(m)
            self._metricas()
            if (m // MIN) % 30 == 0:
                self._financiacion()
        self._rehacer_ctx()                       # en vivo, el hilo de fondo ya trajo lo nuevo

    def _horas(self, m):
        """Las velas de 1 h cerradas que falten, tal cual las da Binance."""
        try:
            for f in self.mercado.klines("BTCUSDT", "1h", m - 3 * HORA, 5):
                if f[0] + HORA <= m and (not len(self.v1h.t) or f[0] > self.v1h.t[-1]):
                    for campo, valor in zip(("t", "o", "h", "l", "c", "v", "tb", "n"), f):
                        getattr(self.v1h, campo).append(valor)
        except Exception as e:
            self.diario.evento(m, "error_1h", detalle=str(e)[:160])

    def _fondo(self):
        """La API de Binance puede tardar segundos: nunca se la espera dentro del ciclo de cada
        segundo. Este hilo trae interés abierto (cada minuto, 5 s después del cambio), velas de
        1 h (cada 10 min) y financiación (cada 30 min)."""
        ultima_fin = ultima_1h = time.time()
        while not self._parar_fondo.is_set():
            self._parar_fondo.wait(60 - time.time() % 60 + 5)
            if self._parar_fondo.is_set():
                break
            try:
                self._metricas()
                if time.time() - ultima_1h >= 600:
                    self._horas((self.ultimo_t + SEG) // HORA * HORA)
                    ultima_1h = time.time()
                if time.time() - ultima_fin >= 1800:
                    self._financiacion()
                    ultima_fin = time.time()
            except Exception as e:
                self.diario.evento(self.ultimo_t or 0, "error_fondo", detalle=str(e)[:200])

    # ---------- un segundo ----------
    def procesar(self, t, fila_u, fila_f, en_vivo):
        self.serie.agregar(*fila_u)
        self.serie_fd.agregar(*fila_f)
        if self.ctx is not None and (t + SEG) % MIN == 0:
            self._nuevo_minuto(t + SEG)            # cerró un minuto: su vela entra antes de decidir
        self.ultimo_t = t
        self.estadisticas["segundos"] += 1
        if not en_vivo:
            self.estadisticas["rellenados"] += 1
        i = self.serie.largo - 1
        x = None
        if self.ctx is not None and i >= rp.VENTANA_MIN:
            x = rp.rasgos_segundo(self.serie, i, self.ctx.en(t + SEG))
        evs = {}
        if x is not None:
            for lv in self.libros.values():
                if lv.cfg not in evs:
                    evs[lv.cfg] = self.modelo.evaluar(x, lv.cfg)
        self.ultimo_ev = evs
        pausa = os.path.exists(os.path.join(CARPETA, "PAUSA"))
        bloqueo = self.externo.bloqueo(t + SEG) if en_vivo else None
        libros_reales = getattr(self.mercado, "libro", {}) or {}
        for clave, lv in self.libros.items():
            o, h, l, c = (fila_f if clave == "fdusd" else fila_u)[1:5]
            motivo = "pausa" if pausa else (bloqueo or ("relleno" if not en_vivo else None))
            if clave == "futuros":
                real = getattr(self.mercado, "marca", None) if en_vivo else None
            else:
                real = libros_reales.get("BTCFDUSD" if clave == "fdusd" else "BTCUSDT") if en_vivo else None
            lv.segundo(t, o, h, l, c, evs.get(lv.cfg), en_vivo and not pausa and bloqueo is None, motivo,
                       self.diario, en_vivo, real)
        if self.reproducir is None:
            self.diario.vela("BTCUSDT", fila_u)
            self.diario.vela("BTCFDUSD", fila_f)
        if (t + SEG) % MIN == 0 and evs:
            fila = {"hora": bogota(t + SEG).isoformat(timespec="seconds"), "precio": fila_u[4]}
            for cfg, (b, hh, d) in evs.items():
                etiqueta = f"{cfg[0]}s_k{cfg[1]}_min{cfg[2] * 100:.2f}"
                fila.update({f"barrera_{etiqueta}": round(b, 6), f"mov_{etiqueta}": round(hh, 4),
                             f"sube_{etiqueta}": round(d, 4)})
            for clave, lv in self.libros.items():
                fila[f"capital_{clave}"] = round(lv.libro.valor(fila_u[4]), 4)
            self.diario.minuto(t, fila)

    # ---------- arranque ----------
    def arrancar(self, sin_flujos=False):
        srv = self.mercado.hora_servidor()
        ultimo = srv // SEG * SEG - 2 * SEG
        self.diario.evento(ultimo, "arranque", modelos=self.modelo.generado,
                           libros={k: {"config": list(lv.cfg), "margen": lv.margen} for k, lv in self.libros.items()},
                           desfase_reloj_ms=int(time.time() * 1000) - srv)
        print(f"{ahora_bogota():%H:%M:%S} Calentando: contexto de 6 días, 1.000 horas e interés abierto…", flush=True)
        self._cargar_contexto(ultimo)
        desde = ultimo - (rp.VENTANA_MIN + 120) * SEG
        u = self.mercado.klines_rango("BTCUSDT", "1s", desde, ultimo + SEG, SEG)
        f = {x[0]: x for x in self.mercado.klines_rango("BTCFDUSD", "1s", desde, ultimo + SEG, SEG)}
        print(f"{ahora_bogota():%H:%M:%S} Calentando: {len(u)} segundos de historia…", flush=True)
        for fila in u:
            ff = f.get(fila[0]) or (fila[0],) + (self.serie_fd.c[-1] if self.serie_fd.largo else fila[4],) * 4 + (0.0, 0.0, 0.0)
            self.serie.agregar(*fila)
            self.serie_fd.agregar(*ff)
        self.ultimo_t = self.serie.t[-1]
        if sin_flujos:
            return
        # posiciones que quedaron abiertas si el agente se cortó: se cierran a mercado ya
        for lv in self.libros.values():
            pg = getattr(lv, "_posicion_guardada", None)
            if pg:
                lv.estado = "posicion"
                lv.pos = rp.Posicion(pg["largo"], pg["entrada"], pg["tp"], pg["sl"], pg["fin"], lv.inst.desliz)
                lv.pos_meta = {"q": pg["q"], "t_in": pg["t_in"], "creador": False,
                               "p": {"b": 0.0, "esperanza": 0.0, "dec": {"prob_mov": None, "prob_sube": None}}}
                lv.cerrar_ya(self.ultimo_t, self.serie.c[-1], "REINICIO", self.diario)
        self.mercado.arrancar_flujos()
        threading.Thread(target=self.externo.correr, daemon=True, name="contexto-tor").start()
        threading.Thread(target=self._fondo, daemon=True, name="binance-fondo").start()
        print(f"{ahora_bogota():%H:%M:%S} Agente en marcha (papel). Panel: {RUTA_PANEL}", flush=True)

    def _rellenar(self, hasta_t):
        """Pide a la API los segundos que faltan hasta hasta_t (exclusivo) y los procesa sin abrir ciclos."""
        desde = self.ultimo_t + SEG
        if hasta_t <= desde:
            return
        u = self.mercado.klines_rango("BTCUSDT", "1s", desde, hasta_t, SEG)
        f = {x[0]: x for x in self.mercado.klines_rango("BTCFDUSD", "1s", desde, hasta_t, SEG)}
        for fila in u:
            if fila[0] != self.ultimo_t + SEG:
                break
            ff = f.get(fila[0]) or (fila[0],) + (self.serie_fd.c[-1],) * 4 + (0.0, 0.0, 0.0)
            self.procesar(fila[0], fila, ff, en_vivo=False)
        self.diario.evento(self.ultimo_t, "relleno", segundos=len(u))

    def bucle(self):
        parar = os.path.join(CARPETA, "PARAR")
        reanudar = os.path.join(CARPETA, "REANUDAR")
        while not os.path.exists(parar):
            try:
                tipo, simbolo, fila = self.mercado.cola.get(timeout=1.0)
                if tipo == "vela" and fila[0] > self.ultimo_t:
                    self.pendientes[fila[0]][simbolo] = fila
            except queue.Empty:
                pass
            try:
                self._consumir()
                if os.path.exists(reanudar):
                    for lv in self.libros.values():
                        lv.libro.detenido = ""
                    os.remove(reanudar)
                    self.diario.evento(self.ultimo_t, "reanudado")
                if time.time() - self.ultimo_panel >= 5:
                    self.ultimo_panel = time.time()
                    self.guardar_estado()
            except Exception as e:
                self.estadisticas["errores"] += 1
                self.diario.evento(self.ultimo_t or 0, "error", detalle=f"{type(e).__name__}: {e}",
                                   pila=traceback.format_exc()[-800:])
                time.sleep(1)
        precio = self.serie.c[-1]
        for lv in self.libros.values():
            lv.cerrar_ya(self.ultimo_t, precio, "PARADA", self.diario)
        self.guardar_estado()
        os.remove(parar)
        self._parar_fondo.set()
        self.mercado.parar()
        self.externo.parar()
        print(f"{ahora_bogota():%H:%M:%S} Agente detenido; estado guardado.", flush=True)

    def _consumir(self):
        """Procesa en orden los segundos que ya tienen las dos velas; rellena huecos por la API."""
        while self.pendientes:
            t = self.ultimo_t + SEG
            par = self.pendientes.get(t, {})
            if "BTCUSDT" in par and "BTCFDUSD" in par:
                del self.pendientes[t]
                self.procesar(t, par["BTCUSDT"], par["BTCFDUSD"], en_vivo=True)
                continue
            mas_nuevo = max(self.pendientes)
            if mas_nuevo - t < 3 * SEG:
                break                                     # todavía puede llegar
            if "BTCUSDT" in par:                          # solo falta la de BTC/FDUSD: vela quieta,
                del self.pendientes[t]                    # sin esperar a la API (no abre ni cierra nada)
                self.estadisticas["fdusd_quietas"] += 1
                self.procesar(t, par["BTCUSDT"], (t,) + (self.serie_fd.c[-1],) * 4 + (0.0, 0.0, 0.0), en_vivo=True)
                continue
            if mas_nuevo - t > 6 * HORA:                  # el equipo estuvo apagado: se arranca de nuevo
                self._reiniciar_datos(mas_nuevo)
                continue
            con_usdt = [k for k, v in self.pendientes.items() if "BTCUSDT" in v]
            hasta = min(con_usdt) if con_usdt else mas_nuevo + SEG
            antes = self.ultimo_t
            self._rellenar(hasta)
            for viejo in [k for k in self.pendientes if k <= self.ultimo_t]:
                del self.pendientes[viejo]
            if self.ultimo_t == antes:
                break                                     # la API aún no las tiene: se reintenta luego

    def _reiniciar_datos(self, t_nuevo):
        precio = self.serie.c[-1]
        for lv in self.libros.values():
            lv.cerrar_ya(self.ultimo_t, precio, "HUECO_LARGO", self.diario)
        self.diario.evento(self.ultimo_t, "hueco_largo", horas=round((t_nuevo - self.ultimo_t) / HORA, 2))
        self.serie = vivo.SerieViva(rasgos=True)
        self.serie_fd = vivo.SerieViva(rasgos=False, guardar=7200)
        self.pendientes.clear()
        self.arrancar(sin_flujos=True)


def main():
    os.makedirs(DIARIO, exist_ok=True)
    if not os.path.exists(RUTA_MODELOS):
        print("Falta modelos/trading-seguido.json: corra antes  python -u -I banco_rapido.py")
        return 1
    parar = os.path.join(CARPETA, "PARAR")
    espera = 30
    sin_freno = sin_freno_de_windows()
    while not os.path.exists(parar):
        try:
            agente = Agente()
            agente.sin_freno = sin_freno
            agente.estadisticas["windows_sin_freno"] = int(sin_freno)
            agente.arrancar()
            agente.bucle()
            return 0
        except Exception:                          # sin red al encender, Binance caído…: se reintenta
            with open(os.path.join(DIARIO, "fallos-arranque.txt"), "a", encoding="utf-8") as f:
                f.write(f"{ahora_bogota().isoformat(timespec='seconds')}\n{traceback.format_exc()}\n")
            try:
                agente.mercado.parar()
                agente.externo.parar()
            except Exception:
                pass
            time.sleep(espera)
            espera = min(espera * 2, 600)
    os.remove(parar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
