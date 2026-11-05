"""Analista propio de la Mesa (04/11/2026): lee el mercado solo, sin IA y sin gastar nada.

Pedido suyo: «necesito que no sea el agente, sino solo el programa completo». Calcula en cada vuelta los dos precios que
dispararían la señal (la ruptura de 20 velas de 5 min) y escribe qué hacer en palabras. Función pura: no decide, solo explica lo
que dijo reglas.evaluar.
"""
import datetime as dt

COL = dt.timezone(dt.timedelta(hours=-5))


def miles(x):
    return f"{x:,.0f}".replace(",", ".")


def disparadores(velas):
    """(máximo, mínimo) de las 20 velas de 5 min completas: cerrar afuera de ese rango es la señal. None si faltan velas."""
    por5 = {}
    for t, _, hi, lo, _c in velas:
        a = por5.setdefault(t // 300, [-1e18, 1e18, 0])
        a[0], a[1], a[2] = max(a[0], hi), min(a[1], lo), a[2] + 1
    llaves = sorted(k for k, a in por5.items() if a[2] == 5)[-20:]
    if len(llaves) < 20:
        return None
    return max(por5[k][0] for k in llaves), min(por5[k][1] for k in llaves)


def fuerza(velas):
    """Aviso si hay un movimiento fuerte. P20: tras caer más de 1 % en una hora, SUBE acierta 53,1 % (lo más bajo) y no se filtra."""
    if len(velas) < 61:
        return ""
    h = velas[-1][4] / velas[-61][4] - 1
    q = velas[-1][4] / velas[-16][4] - 1
    if h <= -0.01:
        return f" Caída fuerte: {100 * h:.1f} % en una hora. Aquí SUBE acierta menos (53,1 %).".replace(".", ",", 1)
    if h >= 0.01:
        return f" Subida fuerte: +{100 * h:.1f} % en una hora. Aquí BAJA acierta 55,4 %.".replace(".", ",", 1)
    if abs(q) >= 0.005:
        return f" Movimiento rápido: {100 * q:+.1f} % en 15 min.".replace(".", ",", 1)
    return ""


def leer(e, velas, lineas, ahora):
    """Texto y marcas para la pantalla, según el nivel que fijó el arnés."""
    r = _leer(e, velas, lineas, ahora)
    r["explicacion"] += fuerza(velas)
    return r


def _leer(e, velas, lineas, ahora):
    precio = velas[-1][4] if velas else None
    d = disparadores(velas)
    prox = dt.datetime.fromtimestamp((int(ahora) // 900 + 1) * 900, COL).strftime("%H:%M")
    marcas = []
    if d:
        marcas = [{"tipo": "resistencia", "precio": d[0], "texto": "Cierre arriba: BAJA"}, {"tipo": "soporte", "precio": d[1], "texto": "Cierre abajo: SUBE"}]
    if e["nivel"] in ("COMPRE", "VENDA"):
        sube = e["sentido"] == 1
        return {"titular": f"{'Compre' if sube else 'Venda'}: el precio se estiró y se espera que se devuelva",
                "explicacion": f"La vela de 5 min cerró {'debajo del mínimo' if sube else 'encima del máximo'} de las 20 anteriores. {e['detalle']} Toque antes de 75 segundos.",
                "marcas": [{"tipo": "flecha_sube" if sube else "flecha_baja", "precio": precio, "texto": "SUBE" if sube else "BAJA"}]}
    if e["nivel"] == "ESPERE":
        return {"titular": "Hay señal, pero aún no es para dinero real", "explicacion": e["detalle"], "marcas": marcas}
    if not d or precio is None:
        return {"titular": "Reuniendo velas", "explicacion": e["detalle"], "marcas": []}
    if e["nivel"] == "ATENTO":
        txt = (f"La señal sale al cierre de las {prox}, si la vela de 5 min termina fuera del rango. Encima de {miles(d[0])}, la apuesta sería BAJA; "
               f"debajo de {miles(d[1])}, SUBE. El precio está en {miles(precio)}.")
        if lineas and "techo" in lineas and "piso" in lineas:
            txt += f" Sus líneas: techo {miles(lineas['techo']['ahora'])} y piso {miles(lineas['piso']['ahora'])}."
        return {"titular": "Vigilando: el borrador está dando", "explicacion": txt, "marcas": marcas}
    return {"titular": "No opere", "explicacion": f"{e['detalle']} El programa sigue midiendo en el borrador.", "marcas": marcas}
