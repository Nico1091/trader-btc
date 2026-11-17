"""Operador automático de binarias en la caja T95H (16/11/2026). Plan: PLAN-AUTOMATICO.md. Reglas: REGLAS-ANTES-DE-MEDIR.md
con su enmienda 2. Sin IA: un programa que mira, calcula, anota y, solo con todo el candado puesto, compra y cobra.

Mira los mercados «BTC Up or Down» de 15 y de 5 minutos de Binance Wallet. Al cierre de cada minuto calcula el vector de
ganancia (lo que vale cada lado según el modelo frente a lo que cuesta en el libro) y pasa solo de un estado a otro:
  1. Sin llave que pase: mide con velas públicas si el modelo acierta lo que dice. Ni papel ni órdenes.
  2. Con una llave que lee: papel con precios reales del libro y llenado honesto, la serie que decide si queda apto.
  3. Con la llave de operar propia de la caja y el archivo ARMADO: además compra de verdad, relee cada orden hasta que
     Binance la cierre, liquida y cobra lo ganado. El importe y los frenos están en ejecutor.py.
Todo queda en registro/AAAAMMDD.jsonl (cada mirada, decisión, orden, lectura, liquidación, cobro y aviso), en estado.json y en
operador.log, y lo importante llega a Telegram. Órdenes desde su Telegram: «operador estado», «operador parte», «operador
armar» (o «operador armar 15»), «operador armar igual», «operador parar», «operador prueba» y «operador ayuda».

Uso en la caja: python3 -I operador.py        Parar del todo: crear el archivo PARAR en esta carpeta.
       python3 -I operador.py estado          lo último que dejó en estado.json, en texto
       python3 -I operador.py prueba          la prueba sin fondos contra Binance, ahora (no envía órdenes)"""
import hashlib
import json
import os
import socket
import sys
import threading
import time
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import conexion as CONEXION  # noqa: E402
import ejecutor as EJ  # noqa: E402
import juez_op as J  # noqa: E402
import mensajes as M  # noqa: E402
import nucleo as N  # noqa: E402
import papel as PA  # noqa: E402
from comunes import con_signo, dia, escribir_json, hora, leer_json, num, pct, sentido, temperatura  # noqa: E402

VERSION = "1 · 16/11/2026"
PUERTO = 8794                # candado de instancia única (el 8792 y el 8793 son del centinela)
HORA_PARTE = 7               # hora de Colombia del parte diario
JUICIO_CADA_S = 6 * 3600
ARMAR_VENCE_S = 600
MENSAJE_VIEJO_S = 600
ESPERA_MERCADO_S = 30        # si Binance no publica el mercado en este tiempo, la ventana se mide solo con velas
NOMBRE_ESTADO = {0: "arrancando", 1: "sin llave que pase", 2: "papel con precios reales", 3: "ARMADO: compra de verdad"}
AYUDA = ("Operador · órdenes: «operador estado» (cómo va ahora), «operador parte» (el parte completo), «operador armar» "
         "(compras reales en los dos mercados; «operador armar 15» o «operador armar 5» para uno solo), «operador armar igual» "
         "(confirma un armado cuando el papel todavía no es apto), «operador parar» (no más compras; lo ya comprado se sigue "
         "leyendo y cobrando) y «operador prueba» (la prueba sin fondos contra Binance).")


def tomar_candado(puerto=PUERTO):
    """Un solo operador por equipo: quien reserva el puerto lo corre. Devuelve el enchufe (hay que conservarlo) o None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", puerto))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def prueba_sin_fondos(C, ahora, tipo):
    """Todo el camino de una compra contra el Binance real menos la compra: billetera, saldos, mercados en curso, libro de
    los dos lados, permisos de la llave y una cotización. No envía ninguna orden. Devuelve (texto, datos)."""
    L, datos = [], {"hora": round(ahora, 2), "llave": tipo}
    w, saldo, vistos = {}, {}, {}

    def paso(nombre, f):
        try:
            texto = f()
            datos[nombre] = texto
        except Exception as ex:
            texto = f"no pasó ({ex})"
            datos[nombre] = {"error": str(ex)[:200]}
        L.append(f"{len(L) + 1}. {nombre}: {texto}")

    def billetera():
        w.update(C.billetera() or {})
        d = w.get("walletAddress")
        return f"sí ({d[:6]}…{d[-4:]})" if d else "la cuenta no tiene billetera de predicción"

    def saldos():
        saldo.update(C.saldos())
        return (f"Spot {num(saldo.get('SPOT', 0))}, Fondos {num(saldo.get('FUNDING', 0))}, Predicción "
                f"{num(saldo.get('CeDeFi', 0))} USDT")

    def mercado(W):
        def f():
            t = int(C.ahora() // (60 * W)) * 60 * W
            m = C.mercado(W, t)
            if m is None:
                return f"Binance no publica ahora {C.slug(W, t)}"
            C.leer_libros(m)
            vistos[W] = m
            lados = []
            for k in (1, -1):
                q = m["ask"].get(k)
                hay = 0.0
                for p, s in m["asks"].get(k) or []:
                    if q and p <= q + 1e-9:
                        hay += s
                lados.append(f"{sentido(k)} se compra a {num(q, 2)} ({num(hay, 0)} contratos)" if q else f"{sentido(k)} sin ventas")
            return (f"{'abierto' if m['abierto'] else 'no figura abierto'}, apertura "
                    f"{num(m['strike']) if m.get('strike') else 'aún sin publicar'}; " + ", ".join(lados))
        return f

    def permisos():
        r = C.restricciones()
        si = [n for c, n in EJ.PROHIBIDOS.items() if r.get(c)]
        return (("restringida por IP" if r.get("ipRestrict") else "SIN restricción de IP") + "; "
                + ("trae permisos de más: " + ", ".join(si) if si else "sin retiros, transferencias, margen ni futuros")
                + ("; trae compraventa de contado" if r.get("enableSpotAndMarginTrading") else ""))

    def cotizacion():
        m = vistos.get(15) or vistos.get(5)
        if not m or not w.get("walletAddress"):
            return "no se pudo pedir (falta la billetera o el mercado)"
        lado = 1 if (m["ask"].get(1) or 9) <= (m["ask"].get(-1) or 9) else -1
        try:
            q = C.cotizar(w["walletAddress"], m["tokens"][lado], N.MIN_USDT, EJ.DESLIZAMIENTO_BPS, EJ.FUENTE)
        except Exception as ex:
            return (f"a una cotización de 2 USDT de {sentido(lado)} Binance contestó «{ex}»; con "
                    f"{num(saldo.get('CeDeFi', 0))} USDT en la billetera de predicción, eso es fallar solo por saldo si el mensaje habla de saldo")
        return f"2 USDT de {sentido(lado)} cotizan a {num(float(q.get('averagePrice') or 0), 3)} (hay saldo; no se envió nada)"

    paso("Billetera de predicción", billetera)
    paso("Saldos", saldos)
    paso("Mercado de 15 min en curso", mercado(15))
    paso("Mercado de 5 min en curso", mercado(5))
    paso("Permisos de la llave", permisos)
    paso("Cotización sin orden", cotizacion)
    cabeza = f"Operador · prueba sin fondos contra Binance, {hora(ahora, '%d/%m %H:%M')}, con la llave «{tipo}»:"
    return "\n".join([cabeza] + L + ["No se envió ninguna orden."]), datos


def limpiar(texto):
    t = unicodedata.normalize("NFKD", (texto or "").strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(t.replace("«", " ").replace("»", " ").replace(".", " ").replace(",", " ").split())


class Operador:
    def __init__(self, con=CONEXION, carpeta=AQUI, correo=None, juez_en_hilo=True):
        self.C, self.carpeta = con, carpeta
        self.datos, self.registro = os.path.join(carpeta, "datos"), os.path.join(carpeta, "registro")
        os.makedirs(self.datos, exist_ok=True)
        os.makedirs(self.registro, exist_ok=True)
        self.ruta_log, self.ruta_mem = os.path.join(carpeta, "operador.log"), os.path.join(self.datos, "operador.json")
        self.mem = leer_json(self.ruta_mem, {}) or {}
        self.mem.setdefault("vistos", [])
        self.correo = correo if correo is not None else M.Correo(self.log, self.mem["vistos"])
        self.modelos = {W: N.cargar(W) for W in N.VENTANAS}
        self.papel = {W: PA.Papel(con, W, self.fila, self.log, self.datos, self.modelos[W]) for W in N.VENTANAS}
        self.ej = EJ.Ejecutor(con, self.fila, self.log, self.avisar, carpeta, self.datos)
        self.mercado = {W: None for W in N.VENTANAS}
        self.busca = {W: {"t": None, "desde": 0.0, "visto": -1e9} for W in N.VENTANAS}
        self.llave = {"tipo": None, "marca": (None, None), "ok": False, "error": None, "t": -1e9}
        self.estado, self.inicio = 0, None
        self.juicio = self.mem.get("juicio") or {}
        self.juez_en_hilo, self.juez_hilo, self.juicio_nuevo, self.juicio_piden = juez_en_hilo, None, None, []
        self.pend_armar, self.t_estado, self.t_juicio, self.t_latido, self.t_reloj = None, -1e9, None, None, -1e9
        self.errores = {}
        for W in N.VENTANAS:
            if self.modelos[W] is None:
                self.log(f"falta el modelo de {W} min (datos/modelo_{W}.json): ese mercado no se mira")

    # ------------------------------------------------------------ registro
    def log(self, msg):
        try:
            t = self.C.ahora()
        except Exception:
            t = time.time()
        linea = f"{hora(t, '%Y-%m-%d %H:%M:%S')} {msg}"
        try:
            if os.path.exists(self.ruta_log) and os.path.getsize(self.ruta_log) > 4_000_000:
                os.replace(self.ruta_log, self.ruta_log + ".1")
            with open(self.ruta_log, "a", encoding="utf-8") as f:
                f.write(linea + "\n")
        except OSError:
            pass
        if os.environ.get("OPERADOR_ECO"):
            try:
                print(linea, flush=True)
            except Exception:
                pass

    def fila(self, fila):
        """Una línea en el registro del día (día de Colombia de la hora de la fila)."""
        t = fila.get("hora") or self.C.ahora()
        with open(os.path.join(self.registro, dia(t) + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def avisar(self, texto):
        self.correo.enviar(texto)
        try:
            self.fila({"tipo": "aviso", "hora": round(self.C.ahora(), 2), "texto": texto})
        except OSError:
            pass
        self.log("aviso: " + texto.replace("\n", " ")[:160])

    def _guardar_mem(self):
        self.mem["vistos"] = self.mem["vistos"][-400:]
        escribir_json(self.ruta_mem, self.mem)

    def _error(self, donde, ex, ahora):
        if getattr(ex, "codigo", None) in EJ.LLAVE_MALA and self.llave["ok"]:
            self._llave_cayo(ahora, ex)
            return
        texto = f"{donde}: {EJ.texto_error(ex)}"
        if ahora - self.errores.get(texto, -1e9) >= 300:
            self.errores[texto] = ahora
            self.log(texto)
            if len(self.errores) > 200:
                self.errores.clear()

    # ------------------------------------------------------------ llave y estados
    def _huella_llave(self):
        """Doce letras que distinguen una llave de otra sin guardar la llave."""
        par = self.C._claves.get("par")
        return hashlib.sha256(par[0].encode()).hexdigest()[:12] if par else None

    def _revisar_llave(self, ahora):
        tipo = self.C.llave()
        marca = self.C.marca_llave()
        k = self.llave
        if marca != k["marca"]:
            if k["tipo"] and not tipo:
                self.log("la llave ya no está en este equipo")
            elif tipo:
                self.log(f"llave «{tipo}» en este equipo: la pruebo")
            k.update(tipo=tipo, marca=marca, ok=False, error=None, t=-1e9)
        if tipo and not k["ok"] and ahora - k["t"] >= (300 if k["error"] in EJ.LLAVE_MALA else 30):
            k["t"] = ahora
            self._probar_llave(ahora)

    def _probar_llave(self, ahora):
        k = self.llave
        try:
            self.C.billetera()
            self.C.saldos()
        except Exception as ex:
            codigo = getattr(ex, "codigo", None)
            antes = k["error"]
            k.update(ok=False, error=codigo if codigo is not None else type(ex).__name__)
            if codigo in EJ.LLAVE_MALA:
                self._avisar_llave_mala(ahora, ex)
            elif antes != k["error"]:
                self.log(f"la llave no pasa todavía ({EJ.texto_error(ex)})")
            return
        volvio = k["error"] is not None
        k.update(ok=True, error=None)
        self.log(f"la llave «{k['tipo']}» pasa en Binance")
        huella = self._huella_llave()
        if self.mem.get("llave_probada") != huella:
            self.mem["llave_probada"] = huella
            self._guardar_mem()
            self.avisar(self.prueba_sin_fondos(ahora))
        elif volvio:
            self.avisar("Operador · la llave volvió a pasar en Binance: sigue el papel con precios reales"
                        + (" y las compras, porque está armado." if self.ej.armado() and k["tipo"] == "operar" else "."))

    def _avisar_llave_mala(self, ahora, ex):
        ip = self.C.ip_publica()
        clave = f"{getattr(ex, 'codigo', None)}:{ip}"
        v = self.mem.get("aviso_llave") or {}
        self.log(f"Binance rechaza la llave ({ex}); esta caja sale por la IP {ip or 'desconocida'}")
        if v.get("clave") == clave and ahora - v.get("t", 0) < 12 * 3600:
            return
        self.mem["aviso_llave"] = {"clave": clave, "t": round(ahora)}
        self._guardar_mem()
        self.avisar(f"Operador · Binance rechaza la llave de la caja ({ex}). La caja sale a internet por la IP "
                    f"{ip or 'que no pude averiguar'}: en la app de Binance, Gestión de API, edite la llave y deje esa IP. Mientras "
                    "tanto mido el modelo con velas; sin precios reales no hay papel ni órdenes. Vuelvo a probarla cada 5 minutos.")

    def _llave_cayo(self, ahora, ex):
        self.llave.update(ok=False, error=getattr(ex, "codigo", None), t=ahora)
        self._avisar_llave_mala(ahora, ex)

    def _estado(self):
        if not self.llave["ok"]:
            return 1
        return 3 if self.llave["tipo"] == "operar" and self.ej.armado() else 2

    def _cambio_estado(self, ahora, nuevo):
        self.fila({"tipo": "estado", "hora": round(ahora, 2), "de": self.estado, "a": nuevo, "llave": self.llave["tipo"]})
        self.log(f"estado {self.estado} → {nuevo}: {NOMBRE_ESTADO[nuevo]}")
        primero = self.estado == 0
        self.estado = nuevo
        if primero and ahora - self.mem.get("arranque", 0) > 1800:
            self.mem["arranque"] = round(ahora)
            self._guardar_mem()
            self.avisar(f"Operador en marcha en la caja (versión {VERSION}). " + self.linea_estado(ahora)
                        + " Escriba «operador ayuda» para ver las órdenes.")

    # ------------------------------------------------------------ mercados
    def _mercado(self, W, ahora):
        """El mercado de W minutos de la ventana en curso: el de Binance si la llave pasa, o uno armado con velas."""
        dur = 60 * W
        t = int(ahora // dur) * dur
        m = self.mercado[W]
        if m and m["t"] == t:
            if not m.get("sintetico") and (not m.get("strike") or not m.get("abierto")) and ahora - m.get("releido", 0) >= 10:
                m["releido"] = ahora   # Binance aún no traía la apertura o el mercado no figuraba abierto: se vuelve a leer
                self.C.releer(m)
            return m
        serie = self.papel[W].serie_abierta(t)
        b = self.busca[W]
        if b["t"] != t:
            b.update(t=t, desde=ahora, visto=-1e9)
        if self.llave["ok"] and serie != "sin_llave":
            if serie == "papel" or ahora - b["desde"] <= ESPERA_MERCADO_S:
                if ahora - b["visto"] < 3:
                    return None
                b["visto"] = ahora
                m = self.C.mercado(W, t)
                if m is None:
                    return None
                m["ask"], m["bid"], m["asks"] = {}, {}, {}
                self.mercado[W] = m
                return m
            self.log(f"Binance no publica el mercado de {W} min de las {hora(t, '%H:%M')}: esa ventana se mide solo con velas")
        elif serie == "papel":
            return None   # la ventana empezó con libro y la llave dejó de pasar: no se mezcla con la otra serie
        m = {"t": t, "W": W, "sintetico": True, "topic": None, "strike": None, "abierto": True}
        self.mercado[W] = m
        return m

    # ------------------------------------------------------------ bucle
    def paso(self):
        C = self.C
        ahora = C.ahora()
        if C.reloj_dudoso():
            if time.monotonic() - self.t_reloj > 300:
                self.t_reloj = time.monotonic()
                self.log("sin la hora de Binance todavía: espero")
            return
        if self.inicio is None:
            self.inicio = ahora
            self.log(f"operador en marcha · versión {VERSION} · modelos " + ", ".join(
                f"{W} min {m.get('huella') if m else 'FALTA'}" for W, m in self.modelos.items()))
        self._revisar_llave(ahora)
        nuevo = self._estado()
        if nuevo != self.estado:
            self._cambio_estado(ahora, nuevo)
        for W in N.VENTANAS:
            try:
                m = self._mercado(W, ahora)
                cand = self.papel[W].paso(C.ahora(), m)
                if cand and self._estado() == 3:
                    self.ej.intentar(C.ahora(), m, cand)
            except Exception as ex:
                self._error(f"mercado de {W} min", ex, ahora)
        if self.llave["ok"]:
            try:
                if self.llave["tipo"] == "operar":
                    self.ej.cuenta(ahora)
                self.ej.paso(C.ahora())
            except Exception as ex:
                self._error("ejecutor", ex, ahora)
        try:
            self._ordenes(ahora)
            self._periodicos(ahora)
        except Exception as ex:
            self._error("periódicos", ex, ahora)

    def pausa(self):
        """Segundos hasta la próxima vuelta: un cuarto de segundo cuando toca mirar o llenar, uno entero si no."""
        try:
            ahora = self.C.ahora()
            if any(self.papel[W].pendiente(ahora, self.mercado[W]) for W in N.VENTANAS) or ahora % 60 > 59.2:
                return 0.25
        except Exception:
            pass
        return 1.0

    # ------------------------------------------------------------ juicio (R5 y R6), en un hilo aparte
    def _juzgar(self, ahora, pide=None):
        if pide:
            self.juicio_piden.append(pide)
        if self.juez_hilo is not None and self.juez_hilo.is_alive():
            return
        self.t_juicio = ahora

        def trabajo():
            out = {}
            for W in N.VENTANAS:
                if self.modelos[W] is None:
                    continue
                try:
                    out[str(W)] = J.juzgar(self.registro, self.datos, W, self.modelos[W], dict(self.papel[W].pol))
                except Exception as ex:
                    out[str(W)] = {"W": W, "error": EJ.texto_error(ex), "apto": False, "criterios": [], "cumplidos": 0, "cambios": []}
            out["hora"] = round(ahora)
            self.juicio_nuevo = out

        if self.juez_en_hilo:
            self.juez_hilo = threading.Thread(target=trabajo, daemon=True)
            self.juez_hilo.start()
        else:
            trabajo()

    def _juicio_listo(self, ahora):
        nuevo, self.juicio_nuevo = self.juicio_nuevo, None
        for W in N.VENTANAS:
            j = nuevo.get(str(W)) or {}
            if j.get("error"):
                self.log(f"juicio del mercado de {W} min: no se pudo ({j['error']})")
            if j.get("cambios"):   # R5: el programa apaga o vuelve a encender celdas, y lo deja escrito
                pol = dict(j["politica"])
                pol["hecha"] = hora(ahora, "%d/%m/%Y %H:%M") + ", R5 aplicada por el operador"
                pol["nota"] = "; ".join(j["cambios"])[:400]
                escribir_json(os.path.join(self.datos, f"politica_{W}.json"), pol)
                self.fila({"tipo": "política", "W": W, "hora": round(ahora, 2), "politica": pol, "cambios": j["cambios"]})
                self.avisar(f"Operador · mercado de {W} min, regla R5: " + "; ".join(j["cambios"]) + ".")
            j.pop("politica", None)
        self.juicio = nuevo
        self.mem["juicio"] = nuevo
        self._guardar_mem()
        piden, self.juicio_piden = self.juicio_piden, []
        for pide in piden:
            if pide[0] == "armar":
                self.avisar(self._resolver_armar(ahora, pide[1], pide[2]))
            elif pide[0] == "parte":
                self.avisar(self.texto_parte(ahora))

    # ------------------------------------------------------------ órdenes del dueño
    def _ordenes(self, ahora):
        for msg in self.correo.recibidos():
            if msg["id"] in self.mem["vistos"]:
                continue
            self.mem["vistos"].append(msg["id"])
            self._guardar_mem()
            t = limpiar(msg["texto"])
            if ahora - msg["fecha"] > MENSAJE_VIEJO_S or t.split(" ")[0] not in ("operador", "op"):
                continue
            try:
                resp = self._atender(ahora, t.split(" ")[1:], msg)
            except Exception as ex:
                resp = f"Operador · no pude atender «{msg['texto'][:40]}» ({type(ex).__name__})."
                self.log(f"orden falló: {EJ.texto_error(ex)}")
            self.fila({"tipo": "orden del dueño", "hora": round(ahora, 2), "mensaje": msg["id"], "texto": msg["texto"][:200]})
            if resp:
                self.avisar(resp)

    def _atender(self, ahora, p, msg):
        cmd = p[0] if p else "ayuda"
        if cmd == "ayuda":
            return AYUDA
        if cmd == "estado":
            return self.texto_estado(ahora)
        if cmd == "parte":
            self._juzgar(ahora, ("parte",))
            return None
        if cmd in ("parar", "pare", "desarmar", "alto"):
            self.pend_armar = None
            if self.ej.desarmar(ahora, f"su orden por Telegram (mensaje {msg['id']})"):
                return ("Operador · desarmado: no hay más compras reales. Lo ya comprado se sigue leyendo, liquidando y cobrando. "
                        "El papel sigue midiendo. Para volver a comprar: «operador armar».")
            return "Operador · ya estaba desarmado: no hay compras reales. El papel sigue midiendo."
        if cmd == "prueba":
            if not self.llave["ok"]:
                return "Operador · no hay una llave que pase en Binance: la prueba sin fondos espera a la llave. " + self.linea_llave()
            return self.prueba_sin_fondos(ahora)
        if cmd == "armar":
            falta = self._falta_para_armar(ahora)
            if falta:
                return "Operador · no puedo armar todavía: " + falta
            if "igual" in p:
                pa = self.pend_armar
                if not pa or ahora - pa["t"] > ARMAR_VENCE_S:
                    return ("Operador · no hay un armado esperando su confirmación (vence a los 10 minutos). "
                            "Escriba primero «operador armar».")
                self.pend_armar = None
                d = self.ej.armar(ahora, pa["mercados"], f"su orden por Telegram (mensaje {msg['id']})", pa["apto"],
                                  "armado sin ser apto según R6, por decisión del dueño")
                return self._texto_armado(ahora, d)
            mercados = [W for W in N.VENTANAS if str(W) in p] or list(N.VENTANAS)
            self._juzgar(ahora, ("armar", mercados, msg["id"]))
            return None if not self.juez_en_hilo else "Operador · reviso el papel antes de armar; le contesto en un momento."
        return "Operador · no conozco esa orden. " + AYUDA

    def _falta_para_armar(self, ahora):
        k = self.llave
        if k["tipo"] != "operar":
            return ("en la caja no está la llave de operar. Créela en la app de Binance, Gestión de API, con Lectura y Predicción "
                    "y nada más, restringida a la IP de la casa; guárdela en el PC como caja.txt y oprima «Llave de la caja».")
        if not k["ok"]:
            return f"Binance todavía no deja pasar la llave ({k['error']})."
        try:
            ok, motivo = self.ej.revisar_llave(ahora)
            if not ok:
                return motivo + "."
            if not self.ej.cuenta(ahora, forzar=True):
                return "la cuenta no tiene billetera de predicción: créela en la app de Binance, en Predicción."
        except Exception as ex:
            return f"no pude leer la cuenta ({EJ.texto_error(ex)})."
        return None

    def _resolver_armar(self, ahora, mercados, mensaje):
        """Con el juicio recién hecho: arma si el papel de esos mercados es apto; si no, lo dice y espera «operador armar igual»."""
        apto = {str(W): bool((self.juicio.get(str(W)) or {}).get("apto")) for W in mercados}
        lineas = ["Operador · antes de armar, así va el papel con precios reales:"] + [self.linea_juicio(W) for W in mercados]
        if all(apto.values()):
            d = self.ej.armar(ahora, mercados, f"su orden por Telegram (mensaje {mensaje})", apto)
            return "\n".join(lineas + [self._texto_armado(ahora, d)])
        self.pend_armar = {"t": ahora, "mercados": mercados, "apto": apto}
        no = " y ".join(f"el de {W} min" for W in mercados if not apto[str(W)])
        lineas.append(f"Todavía no es apto {no}: no hay ventaja demostrada con precios reales, y lo más probable sin ella es perder "
                      "despacio por la comisión del 2 % y el precio. NO he armado. Si aun así quiere que compre, escriba «operador "
                      "armar igual» antes de 10 minutos; queda anotado como decisión suya.")
        return "\n".join(lineas)

    def _texto_armado(self, ahora, d):
        saldo = self.ej.saldo or 0.0
        t = (f"Operador · ARMADO a las {hora(ahora, '%H:%M')} para {' y '.join(str(w) + ' min' for w in d['mercados'])}. Billetera de "
             f"predicción: {num(saldo)} USDT. Cada compra: una cuarta parte del Kelly prudente, tope del 16 % del saldo "
             f"({num(0.16 * saldo)} USDT), mínimo 2 USDT, una por mercado, hasta 20 al día, y se detiene si lo perdido en el día "
             "llega al 16 %. «operador parar» lo desarma.")
        if saldo < N.MIN_USDT:
            t += " Con ese saldo no alcanza para el mínimo: no comprará hasta que pase USDT a la billetera de predicción."
        return t

    # ------------------------------------------------------------ prueba sin fondos (criterio 5)
    def prueba_sin_fondos(self, ahora):
        texto, datos = prueba_sin_fondos(self.C, ahora, self.llave["tipo"])
        self.fila({"tipo": "prueba sin fondos", **datos})
        return texto

    # ------------------------------------------------------------ textos
    def linea_llave(self):
        k = self.llave
        if not k["tipo"]:
            return "En la caja no hay llave de Binance."
        if k["ok"]:
            return f"Llave «{k['tipo']}»: pasa."
        return f"Llave «{k['tipo']}»: Binance no la deja pasar ({k['error']})."

    def linea_estado(self, ahora):
        e = self._estado() if self.estado else 0
        t = f"Estado {e} de 3: {NOMBRE_ESTADO[e]}. "
        if e == 1:
            t += self.linea_llave() + " Mido con velas de contado si el modelo acierta lo que dice; sin precios reales no hay papel ni órdenes."
        elif e == 2:
            t += self.linea_llave() + " Llevo el papel con los precios reales del libro. No compro: falta " + (
                "su orden «operador armar»." if self.llave["tipo"] == "operar" else "la llave de operar y su orden de armar.")
        elif e == 3:
            a = self.ej.armado() or {}
            t += (f"Armado desde el {a.get('cuando', '?')} para {' y '.join(str(w) + ' min' for w in a.get('mercados', []))}. "
                  f"Billetera de predicción: {num(self.ej.saldo or 0)} USDT.")
        return t

    def linea_modelo(self, W):
        """Lo que dijo el modelo frente a lo que pasó, en las dos series."""
        out = []
        for serie, nombre in (("sin_llave", "con velas"), ("papel", "con precios reales")):
            c = self.papel[W].calibracion(serie)
            if c["miradas"]:
                out.append(f"{nombre}, {c['miradas']} miradas en {c['ventanas']} ventanas: esperaba {num(c['esperados'], 1)} vueltas del "
                           f"lado que iba perdiendo y hubo {c['ocurridos']} ({con_signo(c['sigmas'], 1)} desviaciones); pérdida "
                           f"logarítmica {num(c['pl_modelo'], 4)} frente a {num(c['pl_normal'], 4)} de la fórmula normal")
        return f"Modelo de {W} min: " + ("; ".join(out) + "." if out else "aún sin ventanas resueltas.")

    def linea_papel(self, W):
        r = self.papel[W].resumen()
        a, b = r["libros"]["5"], r["libros"]["15"]
        if not a["n"] and not a["abiertas"] and not b["n"]:
            return f"Papel de {W} min con precios reales: sin compras todavía ({r['cont']['miradas'] - r['cont']['sin_libro']} miradas con libro)."
        return (f"Papel de {W} min con precios reales: {a['n']} compras cerradas, {a['k']} aciertos (el modelo esperaba "
                f"{num(a['esperados'], 1)}), neto {con_signo(a['neto'])} USDT con 1 USDT fijo y {con_signo(a['neto_b'])} con Kelly; "
                f"con 15 s de demora, {b['n']} compras y neto {con_signo(b['neto'])}. Abiertas: {a['abiertas']}.")

    def linea_juicio(self, W):
        j = self.juicio.get(str(W))
        if not j or j.get("error"):
            return f"Mercado de {W} min: sin juicio todavía."
        a = j["libro_a"]
        falta = [n for n, ok, _d in j["criterios"] if not ok]
        return (f"Mercado de {W} min: {a['n']} compras de papel, {a['k']} aciertos, neto {con_signo(a['neto'])} USDT; auditoría con "
                f"{j['diferencias']} diferencias; criterios de «apto»: {j['cumplidos']} de {len(j['criterios'])}. "
                + ("APTO en papel." if j["apto"] else "NO apto todavía" + (f" (falta: {falta[0]})." if falta else ".")))

    def linea_real(self, ahora):
        r = self.ej.resumen(ahora)
        if not r["compradas"] and not r["ordenes_hoy"] and not r["armado"]:
            return "Real: desarmado y sin órdenes."
        t = (f"Real: {'armado' if r['armado'] else 'desarmado'}; {r['ordenes_hoy']} órdenes hoy; compradas en total {r['compradas']}, "
             f"liquidadas {r['liquidadas']} con {r['aciertos']} aciertos y neto {con_signo(r['neto'])} USDT.")
        if r["abiertas"] or r["sin_liquidar"] or r["cobros_pendientes"] or r["sin_cobrar"]:
            t += (f" Pendiente: {r['abiertas']} órdenes abiertas, {r['sin_liquidar']} sin liquidar, {r['cobros_pendientes']} cobros en "
                  f"curso y {r['sin_cobrar']} que debe cobrar usted en la app.")
        if r["armado"] and r["saldo_inicial_dia"] is not None:
            t += f" Hoy puede arriesgar todavía {num(max(0.0, r['cupo_hoy']))} USDT antes del freno."
        return t

    def texto_estado(self, ahora):
        temp = temperatura()
        L = [f"Operador · {hora(ahora)} · " + self.linea_estado(ahora)]
        for W in N.VENTANAS:
            L += [self.linea_modelo(W), self.linea_papel(W)]
        L.append(self.linea_real(ahora))
        if temp is not None:
            L.append(f"Caja a {num(temp, 0)} °C.")
        return "\n".join(L)

    def texto_parte(self, ahora):
        L = [f"Operador · parte del {hora(ahora, '%d/%m/%Y %H:%M')} · " + self.linea_estado(ahora)]
        for W in N.VENTANAS:
            L += [self.linea_modelo(W), self.linea_papel(W), self.linea_juicio(W)]
        L.append(self.linea_real(ahora))
        marcha = (ahora - self.inicio) / 3600 if self.inicio else 0.0
        temp = temperatura()
        L.append(f"En marcha desde hace {num(marcha, 1)} h" + (f"; caja a {num(temp, 0)} °C" if temp is not None else "")
                 + ". «Apto en papel» no autoriza dinero: lo arma usted.")
        return "\n".join(L)

    # ------------------------------------------------------------ periódicos
    def foto(self, ahora):
        return {"hora": round(ahora), "cuando": hora(ahora, "%d/%m/%Y %H:%M:%S"), "version": VERSION, "estado": self._estado() if self.estado else 0,
                "estado_texto": NOMBRE_ESTADO[self._estado() if self.estado else 0], "inicio": round(self.inicio or ahora),
                "llave": {k: self.llave[k] for k in ("tipo", "ok", "error")},
                "mercados": {str(W): ({k: m.get(k) for k in ("t", "sintetico", "strike", "abierto", "topic")} | {
                    "ask": {str(k): v for k, v in (m.get("ask") or {}).items()}} if m else None) for W, m in self.mercado.items()},
                "papel": {str(W): self.papel[W].resumen() for W in N.VENTANAS}, "real": self.ej.resumen(ahora),
                "juicio": self.juicio, "temperatura": temperatura(), "texto": self.texto_estado(ahora)}

    def _periodicos(self, ahora):
        if self.juicio_nuevo is not None:
            self._juicio_listo(ahora)
        if self.t_juicio is None:
            self.t_juicio = ahora - JUICIO_CADA_S + 90      # el primero, al minuto y medio de arrancar
        if ahora - self.t_juicio >= JUICIO_CADA_S:
            self._juzgar(ahora)
        if self.pend_armar and ahora - self.pend_armar["t"] > ARMAR_VENCE_S:
            self.pend_armar = None
        if ahora - self.t_estado >= 30:
            self.t_estado = ahora
            escribir_json(os.path.join(self.carpeta, "estado.json"), self.foto(ahora))
        hoy = dia(ahora)
        if int(hora(ahora, "%H")) >= HORA_PARTE and self.mem.get("parte") != hoy and ahora - (self.inicio or ahora) > 120:
            self.mem["parte"] = hoy
            self._guardar_mem()
            self._juzgar(ahora, ("parte",))
        if self.t_latido is None or ahora - self.t_latido >= 3600:
            self.t_latido = ahora
            self.log("sigo · " + self.linea_estado(ahora) + " · " + " · ".join(
                f"{W} min: {self.papel[W].cont['miradas']} miradas, {self.papel[W].cont['perdidas']} perdidas" for W in N.VENTANAS))


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if argv and argv[0] == "estado":
        e = leer_json(os.path.join(AQUI, "estado.json"))
        print(e["texto"] + f"\n(foto de las {e['cuando']})" if e else "todavía no hay estado.json")
        return 0
    if argv and argv[0] == "prueba":
        tipo = CONEXION.llave()   # solo consulta y no toca los archivos del operador que esté corriendo
        print(prueba_sin_fondos(CONEXION, CONEXION.ahora(), tipo)[0] if tipo else "En este equipo no hay llave de Binance.")
        return 0
    if argv:
        print("uso: python3 -I operador.py [estado | prueba]")   # un argumento que no se reconoce no arranca nada
        return 2
    candado = tomar_candado()
    if candado is None:
        print("ya hay un operador corriendo en este equipo (puerto 8794): salgo")
        return 1
    parar = os.path.join(AQUI, "PARAR")
    op = Operador()
    op.correo.arrancar()
    while not os.path.exists(parar):
        try:
            op.paso()
        except Exception as ex:
            op.log(f"vuelta fallida: {EJ.texto_error(ex)}")
            time.sleep(3)
        time.sleep(op.pausa())
    op.log("PARAR: salgo")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
