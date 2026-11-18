"""Candado del aprobador (17/11/2026; desde el 18/11/2026, la orden de la IA): lee lo que el nodo de este mismo equipo dejó
para cada mercado y dice si hay una orden vigente de la IA y de qué lado.

Orden del dueño del 18/11/2026: «ninguno de los dos programas ordena compra». El Centro y el operador de Fable 5.2 le mandan
todo a la IA por el nodo; la IA ordena comprar (SUBE), vender (BAJA) o nada, en cualquiera de los dos lados; el script
ejecuta esa orden tal cual (ejecutor.ejecutar_ia), con sus topes de dinero. Aquí no se decide nada: solo se lee la cola del
archivo de decisiones del nodo (~/nodo/decisiones.jsonl en el teléfono, /data/local/tmp/nodo/decisiones.jsonl en la caja).
El papel no pasa por aquí y sigue igual.

Vigente quiere decir: la ÚLTIMA decisión que el nodo de este equipo tomó para ese mercado (W minutos) y esa ventana (t de
apertura) dice COMPRAR SUBE o COMPRAR BAJA, tiene menos de CADUCIDAD_S segundos y la ventana sigue abierta. El lado es el que
ordenó la IA, aunque el punto trajera el otro. Falla cerrado: sin archivo, ilegible, sin decisión, «NO COMPRAR» (nada), sin
respuesta, otra ventana, decisión vieja, con la hora rara o copiada de otro equipo = no hay orden real. Nunca lanza errores:
cualquier cosa rara se vuelve un motivo para no comprar. Desde el 18/11/2026 (tarde) la decisión trae también «precios», los
que vio la IA; el ejecutor no paga más de 0,02 sobre ellos (ejecutor.precio_visto)."""
import json
import os
import time

HOME = os.path.expanduser("~")
RUTAS = (os.path.join(HOME, "nodo", "decisiones.jsonl"), "/data/local/tmp/nodo/decisiones.jsonl")
CADUCIDAD_S = 120            # una orden vale como mucho 2 minutos (era 10: 18/11/2026, paridad con la compra a mano; en el
                             # mercado de 5 min un lado cambia 0,15 por minuto) y nunca más allá del cierre de su ventana
FUTURO_S = 120               # una decisión fechada más adelante que esto viene de un reloj raro: no vale
COLA_BYTES = 262144          # solo se lee la cola del archivo (las decisiones de las últimas horas)
COMPRAR = {1: "COMPRAR SUBE", -1: "COMPRAR BAJA"}
ORDEN = {1: "comprar (SUBE)", -1: "vender (BAJA)"}
_CACHE = {"ruta": None, "marca": None, "filas": []}


def ruta():
    for r in RUTAS:
        if os.path.exists(r):
            return r
    return None


def _cola(r):
    with open(r, "rb") as f:
        f.seek(0, os.SEEK_END)
        n = f.tell()
        f.seek(max(0, n - COLA_BYTES))
        datos = f.read()
    if n > COLA_BYTES:
        datos = datos.split(b"\n", 1)[-1]          # la primera línea puede venir cortada
    return datos.decode("utf-8", "replace").splitlines()


def _filas(r):
    """Las filas legibles de la cola. El ejecutor pregunta en cada vuelta: solo se relee si el archivo cambió. La marca lleva
    inodo, tamaño, hora en ns y los últimos 512 bytes: dos escrituras seguidas pueden compartir tamaño y tic del reloj
    (pasó en la prueba: «COMPRAR SUBE» y «COMPRAR BAJA» miden lo mismo), y las decisiones nuevas caen siempre al final."""
    with open(r, "rb") as f:
        st = os.fstat(f.fileno())
        f.seek(max(0, st.st_size - 512))
        fin = f.read(512)
    marca = (st.st_ino, st.st_size, st.st_mtime_ns, fin)
    if _CACHE["ruta"] == r and _CACHE["marca"] == marca:
        return _CACHE["filas"]
    filas = []
    for linea in _cola(r):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if isinstance(d, dict):
            filas.append(d)
    _CACHE.update(ruta=r, marca=marca, filas=filas)
    return filas


def _hora(t):
    return time.strftime("%H:%M", time.gmtime(t - 5 * 3600))


def decisiones(W, t, r=None):
    """Las decisiones legibles del nodo de este equipo para el mercado W y la ventana t, de la más vieja a la más nueva."""
    r = r or ruta()
    if not r:
        return None
    out = [d for d in _filas(r) if not d.get("copia_de") and d.get("W") == W and d.get("ventana") == t
           and isinstance(d.get("t"), (int, float)) and not isinstance(d.get("t"), bool)]
    out.sort(key=lambda d: d["t"])
    return out


def orden(W, t, ahora, r=None):
    """La orden vigente de la IA para el mercado de W min que abrió en t: (lado, decisión) con lado 1 = comprar (SUBE) o
    -1 = vender (BAJA); (None, motivo) si no hay orden que ejecutar."""
    try:
        if ahora >= t + 60 * W:
            return None, "sin orden de la IA: la ventana ya cerró"
        lista = decisiones(W, t, r)
        if lista is None:
            return None, "sin orden de la IA: no está el archivo de decisiones del nodo"
        validas = [d for d in lista if t - 120 <= d["t"] <= ahora + FUTURO_S]
        if not validas:
            return None, "sin orden de la IA: el nodo no ha decidido sobre este mercado"
        d = validas[-1]
        dec = d.get("decision")
        cuando = _hora(d["t"])
        lado = next((k for k, v in COMPRAR.items() if v == dec), None)
        if lado is None:
            if dec == "NO COMPRAR":
                return None, f"sin orden de la IA: a las {cuando} dijo nada (NO COMPRAR)"
            return None, f"sin orden de la IA: a las {cuando} no hubo respuesta válida"
        if ahora - d["t"] > CADUCIDAD_S:
            return None, f"sin orden de la IA: la de las {cuando} ya venció ({CADUCIDAD_S // 60} min)"
        return lado, d
    except Exception as ex:   # falla cerrado
        return None, f"sin orden de la IA: no pude leer las decisiones ({type(ex).__name__})"


def falta(W, t, lado, ahora, r=None):
    """None si hay una orden vigente de la IA para `lado` en el mercado de W min que abrió en t; si no, el motivo."""
    if lado not in COMPRAR:
        return "sin orden de la IA: sentido desconocido"
    l, d = orden(W, t, ahora, r)
    if l is None:
        return d
    if l != lado:
        return f"sin orden de la IA: a las {_hora(d['t'])} ordenó {ORDEN[l]}, no {ORDEN[lado]}"
    return None
