"""Candado del aprobador (17/11/2026): el operador de Fable 5.2 solo envía una orden REAL si el nodo de este mismo equipo dejó
una decisión de Claude «COMPRAR SUBE» o «COMPRAR BAJA» vigente para ese mercado y ese sentido.

Pedido del dueño del 17/11/2026 (rutina constructora, sección H.5.b): Claude aprueba o no cada operación desde la nube y el
operador ejecuta con sus frenos. Aquí no se decide nada ni se cambia nada del operador: solo se lee la cola del archivo de
decisiones del nodo (~/nodo/decisiones.jsonl en el teléfono, /data/local/tmp/nodo/decisiones.jsonl en la caja) y se dice si
hay aprobación. El papel no pasa por aquí y sigue igual.

Vigente quiere decir: la ÚLTIMA decisión que el nodo de este equipo tomó para ese mercado (W minutos) y esa ventana (t de
apertura), en cualquier sentido, dice COMPRAR en el mismo sentido de la orden, tiene menos de CADUCIDAD_S segundos y la
ventana sigue abierta. Falla cerrado: sin archivo, ilegible, sin decisión, «NO COMPRAR», sin respuesta de Claude, el otro
sentido, otra ventana, decisión vieja, con la hora rara o copiada de otro equipo = no hay orden real. Nunca lanza errores:
cualquier cosa rara se vuelve un motivo para no comprar."""
import json
import os
import time

HOME = os.path.expanduser("~")
RUTAS = (os.path.join(HOME, "nodo", "decisiones.jsonl"), "/data/local/tmp/nodo/decisiones.jsonl")
CADUCIDAD_S = 600            # una aprobación vale como mucho 10 minutos, y nunca más allá del cierre de su ventana
FUTURO_S = 120               # una decisión fechada más adelante que esto viene de un reloj raro: no vale
COLA_BYTES = 262144          # solo se lee la cola del archivo (las decisiones de las últimas horas)
COMPRAR = {1: "COMPRAR SUBE", -1: "COMPRAR BAJA"}


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


def _hora(t):
    return time.strftime("%H:%M", time.gmtime(t - 5 * 3600))


def decisiones(W, t, r=None):
    """Las decisiones legibles del nodo de este equipo para el mercado W y la ventana t, de la más vieja a la más nueva."""
    r = r or ruta()
    if not r:
        return None
    out = []
    for linea in _cola(r):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("copia_de") or d.get("W") != W or d.get("ventana") != t:
            continue
        if not isinstance(d.get("t"), (int, float)):
            continue
        out.append(d)
    out.sort(key=lambda d: d["t"])
    return out


def falta(W, t, lado, ahora, r=None):
    """None si hay una aprobación vigente para comprar `lado` en el mercado de W min que abrió en t; si no, el motivo."""
    try:
        if lado not in COMPRAR:
            return "sin aprobación de Claude: sentido desconocido"
        if ahora >= t + 60 * W:
            return "sin aprobación de Claude: la ventana ya cerró"
        lista = decisiones(W, t, r)
        if lista is None:
            return "sin aprobación de Claude: no está el archivo de decisiones del nodo"
        validas = [d for d in lista if t - 120 <= d["t"] <= ahora + FUTURO_S]
        if not validas:
            return "sin aprobación de Claude: el nodo no ha decidido sobre este mercado"
        d = validas[-1]
        dec = d.get("decision")
        cuando = _hora(d["t"])
        if dec != COMPRAR[lado]:
            if dec in COMPRAR.values():
                return f"sin aprobación de Claude: a las {cuando} aprobó {dec[8:]}, no {COMPRAR[lado][8:]}"
            if dec == "NO COMPRAR":
                return f"sin aprobación de Claude: a las {cuando} dijo NO COMPRAR"
            return f"sin aprobación de Claude: a las {cuando} no hubo respuesta válida"
        if ahora - d["t"] > CADUCIDAD_S:
            return f"sin aprobación de Claude: la de las {cuando} ya venció ({CADUCIDAD_S // 60} min)"
        if d.get("dir") not in (None, lado):
            return "sin aprobación de Claude: la decisión no coincide con su punto"
        return None
    except Exception as ex:   # falla cerrado
        return f"sin aprobación de Claude: no pude leer las decisiones ({type(ex).__name__})"
